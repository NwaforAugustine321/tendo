
from fastapi import APIRouter, File, HTTPException, UploadFile

import logging
import os

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError


logger = logging.getLogger(__name__)


MINIO_ENDPOINT = os.getenv(
    "MINIO_ENDPOINT",
    "http://tendo-minio:9000",
)

MINIO_PUBLIC_ENDPOINT = os.getenv(
    "MINIO_PUBLIC_ENDPOINT",
    "http://localhost:9000",
)

MINIO_ACCESS_KEY = os.getenv(
    "MINIO_ACCESS_KEY",
    "minioadmin",
)

MINIO_SECRET_KEY = os.getenv(
    "MINIO_SECRET_KEY",
    "minioadmin",
)

MINIO_BUCKET = os.getenv(
    "MINIO_BUCKET",
    "tendo-documents",
)


s3 = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    config=Config(
        signature_version="s3v4",
    ),
)


router = APIRouter()


@router.post("/documents/upload")
async def upload_document(
    business_id: str,
    document_id: str,
    file: UploadFile = File(...),
):
    business_id = business_id.strip()
    document_id = document_id.strip()

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

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A filename is required",
        )

    filename = os.path.basename(file.filename)

    if not filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename",
        )

    object_key = (
        f"{business_id}/"
        f"{document_id}/"
        f"{filename}"
    )

    logger.info(
        "[DOCUMENT UPLOAD] Uploading "
        "business_id=%s document_id=%s "
        "bucket=%s key=%s",
        business_id,
        document_id,
        MINIO_BUCKET,
        object_key,
    )

    try:
        s3.upload_fileobj(
            file.file,
            MINIO_BUCKET,
            object_key,
            ExtraArgs={
                "ContentType": (
                    file.content_type
                    or "application/octet-stream"
                ),
            },
        )

    except (BotoCoreError, ClientError) as exc:
        logger.exception(
            "[DOCUMENT UPLOAD] MinIO upload failed "
            "business_id=%s document_id=%s key=%s",
            business_id,
            document_id,
            object_key,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to upload document to object storage",
        ) from exc

    except Exception as exc:
        logger.exception(
            "[DOCUMENT UPLOAD] Unexpected upload error "
            "business_id=%s document_id=%s key=%s",
            business_id,
            document_id,
            object_key,
        )

        raise HTTPException(
            status_code=500,
            detail="Unexpected error while uploading document",
        ) from exc

    finally:
        await file.close()

    document_url = (
        f"{MINIO_PUBLIC_ENDPOINT.rstrip('/')}/"
        f"{MINIO_BUCKET}/"
        f"{object_key}"
    )

    logger.info(
        "[DOCUMENT UPLOAD] Successfully uploaded "
        "business_id=%s document_id=%s key=%s",
        business_id,
        document_id,
        object_key,
    )

    return {
        "document_id": document_id,
        "business_id": business_id,
        "filename": filename,
        "bucket": MINIO_BUCKET,
        "object_key": object_key,
        "document_url": document_url,
        "status": "uploaded",
        "message": (
            "Document uploaded successfully. "
            "RAG ingestion will be processed asynchronously."
        ),
    }
