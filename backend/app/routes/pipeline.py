import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.rag_pipeline.interface import DocumentSource, SourceType
from app.rag_pipeline.pipeline import Pipeline


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/pipeline/webhook/ingestion")
async def pipeline_ingestion_webhook(
    file: UploadFile = File(...),
    business_id: str = Form(...),
    document_id: str = Form(...),
    collection_name: str = Form(...),
    bucket: str = Form(...),
    object_key: str = Form(...),
):
    business_id = business_id.strip()
    document_id = document_id.strip()
    collection_name = collection_name.strip()
    bucket = bucket.strip()
    object_key = object_key.strip()

    if not business_id:
        raise HTTPException(
            status_code=400,
            detail="business_id is required",
        )

    if not document_id:
        raise HTTPException(
            status_code=400,
            detail="document_id is required",
        )

    if not collection_name:
        raise HTTPException(
            status_code=400,
            detail="collection_name is required",
        )

    if not bucket:
        raise HTTPException(
            status_code=400,
            detail="bucket is required",
        )

    if not object_key:
        raise HTTPException(
            status_code=400,
            detail="object_key is required",
        )

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="filename is required",
        )

    suffix = Path(file.filename).suffix

    temp_file = None

    logger.info(
        "[RAG WEBHOOK] Received ingestion request "
        "business_id=%s document_id=%s collection=%s "
        "bucket=%s object_key=%s",
        business_id,
        document_id,
        collection_name,
        bucket,
        object_key,
    )

    # ==============================================================
    # IMPORTANT DB TRACKING POINT #1
    # ==============================================================
    #
    # The document record should ALREADY exist in the database because
    # /documents/upload created it when the frontend uploaded the file.
    #
    # At this point you can optionally update the existing record to:
    #
    #     status = "processing"
    #
    # Example:
    #
    # await document_repository.update_status(
    #     business_id=business_id,
    #     document_id=document_id,
    #     status="processing",
    # )
    #
    # DO NOT create a second document record here.
    #
    # The identity of the existing document is:
    #
    #     business_id
    #     document_id
    #     bucket
    #     object_key
    #
    # ==============================================================

    try:
        # ----------------------------------------------------------
        # Copy the document received from Kafka consumer to a
        # temporary local file.
        # ----------------------------------------------------------

        temp_file = tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        )

        try:
            while chunk := await file.read(1024 * 1024):
                temp_file.write(chunk)

        finally:
            temp_file.close()

        source = DocumentSource(
            value=temp_file.name,
            source_type=SourceType.FILE,
        )

        logger.info(
            "[RAG WEBHOOK] Starting RAG ingestion "
            "business_id=%s document_id=%s "
            "collection=%s file=%s",
            business_id,
            document_id,
            collection_name,
            temp_file.name,
        )

        pipeline = Pipeline(
            namespace=business_id,
        )

        # ==========================================================
        # RAG INGESTION
        # ==========================================================
        #
        # This is the actual success/failure boundary.
        #
        # If this succeeds:
        #
        #     uploaded = SUCCESS
        #
        # If this raises an exception:
        #
        #     uploaded = FAILED
        #
        # The Kafka consumer receives the HTTP response from this
        # webhook and uses it as the final ingestion result.
        #
        # ==========================================================

        result = await pipeline.ingest(
            collection=collection_name,
            source=source,
        )

        logger.info(
            "[RAG WEBHOOK] RAG ingestion successful "
            "business_id=%s document_id=%s "
            "collection=%s",
            business_id,
            document_id,
            collection_name,
        )

        # ==============================================================
        # IMPORTANT DB TRACKING POINT #2 — RAG SUCCESS
        # ==============================================================
        #
        # UPDATE THE EXISTING DOCUMENT RECORD HERE.
        #
        # This is where the frontend's original "uploaded" document
        # becomes fully successful.
        #
        # Example:
        #
        # await document_repository.update_status(
        #     business_id=business_id,
        #     document_id=document_id,
        #     status="uploaded",
        #     rag_status="completed",
        #     rag_result=result,
        # )
        #
        # If your DB only has one status field:
        #
        #     status = "uploaded"
        #
        # The important rule is:
        #
        #     RAG SUCCESS -> DB status = uploaded
        #
        # ==============================================================

        return {
            "status": "uploaded",
            "rag_status": "completed",
            "business_id": business_id,
            "document_id": document_id,
            "filename": file.filename,
            "bucket": bucket,
            "object_key": object_key,
            "collection_name": collection_name,
            "result": result,
        }

    except Exception as exc:
        logger.exception(
            "[RAG WEBHOOK] RAG ingestion failed "
            "business_id=%s document_id=%s "
            "collection=%s object_key=%s",
            business_id,
            document_id,
            collection_name,
            object_key,
        )

        # ==============================================================
        # IMPORTANT DB TRACKING POINT #3 — RAG FAILURE
        # ==============================================================
        #
        # UPDATE THE EXISTING DOCUMENT RECORD HERE.
        #
        # Example:
        #
        # await document_repository.update_status(
        #     business_id=business_id,
        #     document_id=document_id,
        #     status="failed",
        #     rag_status="failed",
        #     error=str(exc),
        # )
        #
        # The frontend should ultimately see this document as FAILED,
        # not "uploaded", because RAG ingestion did not complete.
        #
        # IMPORTANT:
        # Do NOT delete the MinIO document.
        # It remains available for inspection/reprocessing.
        #
        # ==============================================================

        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "rag_status": "failed",
                "business_id": business_id,
                "document_id": document_id,
                "bucket": bucket,
                "object_key": object_key,
                "collection_name": collection_name,
                "error": str(exc),
            },
        ) from exc

    finally:
        await file.close()

        if temp_file is not None:
            try:
                Path(temp_file.name).unlink(
                    missing_ok=True,
                )
            except Exception:
                logger.warning(
                    "[RAG WEBHOOK] Failed to remove temporary file: %s",
                    temp_file.name,
                    exc_info=True,
                )
