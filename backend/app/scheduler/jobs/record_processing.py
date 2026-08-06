"""Scheduler job — process record content extraction via APScheduler.

Schedules each extraction immediately using the scheduler for recovery features.
Extracts text, chunks it, uses Memory.remember_many to embed and store.
"""

import asyncio
import logging
import random
import string
from uuid import uuid4

from app.db.tools.data_sources import update_record_content_status
from app.db.tools.records import create_record, add_record_content
from app.record_knowledge.extractors import extract_and_chunk
from app.memory.memory import Memory
from app.scheduler.engine import get_scheduler

logger = logging.getLogger(__name__)

_pending_futures: dict[str, asyncio.Future] = {}


async def _run_extraction(
    job_id: str,
    business_id: str,
    record_id: str | None,
    content_type: str,
    content: str,
    content_id: str,
    metadata: dict | None,
):
    """Extract text, chunk, use remember_many to embed and store."""
    chunks = []
    try:
        if not record_id:
            short_id = '#' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
            title = (metadata or {}).get("title", short_id)
            record = await create_record(business_id=business_id, title=title)
            record_id = record.get("id", "")
            if not record_id:
                logger.error("Failed to create record")
                future = _pending_futures.pop(job_id, None)
                if future and not future.done():
                    future.set_result("")
                return

            # Emit new record event to frontend
            try:
                from app.ws.socketio_server import sio
                await sio.emit("new_record", {
                    "id": record_id,
                    "business_id": business_id,
                    "title": title,
                    "is_read": False,
                    "content_type": content_type,
                    "first_content": "",
                    "created_at": record.get("created_at", ""),
                })
            except Exception:
                pass

        chunks = await extract_and_chunk(content_type, content)

        # Summarize extracted text for title and record content 
        summary_text = ""
        title_from_summary = ""
        if chunks:
            extracted_text = "\n".join(chunks)
            try:
                from app.record_knowledge.summarizers import summarize_text
                summary_result = await summarize_text(extracted_text)
                title_from_summary = summary_result.get("title", "")
                summary_text = summary_result.get("summary", extracted_text)
            except Exception as e:
                logger.warning(f"Summarization failed, using raw text: {e}")
                summary_text = extracted_text

        # Save summary to record_content table, update record title
        if chunks:
            file_url = (metadata or {}).get("file_url", "")
            if not content_id:
                from app.db.client import get_client as _get_client
                db = _get_client()
                entry_data = {
                    "business_id": business_id,
                    "record_id": record_id,
                    "content_type": content_type,
                    "content": summary_text,
                    "file_url": file_url,
                    "status": "completed",
                }
                result = db.table("record_content").insert(entry_data).execute()
                content_id = result.data[0]["id"] if result.data else ""
            else:
                update_record_content_status(content_id, business_id, "completed", content=summary_text)

            # Update record title from summary title
            if title_from_summary and record_id:
                try:
                    from app.db.tools.records import update_record
                    await update_record(business_id, record_id, title=title_from_summary)
                except Exception:
                    pass

        if chunks:
            structured = metadata if isinstance(metadata, dict) else {}

            images: list[str] = []
            audio: list[str] = []
            videos: list[str] = []

            if "images" in structured:
                raw_images = structured["images"]
                if isinstance(raw_images, list):
                    images = raw_images
            if "audio" in structured:
                raw_audio = structured["audio"]
                if isinstance(raw_audio, list):
                    audio = raw_audio
            if "videos" in structured:
                raw_videos = structured["videos"]
                if isinstance(raw_videos, list):
                    videos = raw_videos

            clean_metadata = {"content_type": content_type}
            for key, value in structured.items():
                if key not in ("images", "audio", "videos"):
                    clean_metadata[key] = value

            memory = Memory(
                scopes=f"/{business_id}/record/{record_id}",
                business_id=business_id,
            )

            await memory.remember_many(
                contents=chunks,
                scope=f"/{business_id}/record/{record_id}",
                metadata=clean_metadata,
                images=images,
                audio=audio,
                videos=videos,
            )

        # Mark as completed after all processing
        if content_id:
            update_record_content_status(content_id, business_id, "completed")

        # Emit updated record with summary content to frontend
        try:
            from app.ws.socketio_server import sio
            await sio.emit("record_updated", {
                "id": record_id,
                "business_id": business_id,
                "title": title_from_summary or title if not record_id else "",
                "first_content": summary_text[:200] if summary_text else "",
            })
        except Exception:
            pass

        logger.info(f"Processed {content_type} content for record {record_id} ({len(chunks)} chunks)")

    except Exception as e:
        logger.error(f"Extraction failed for record {record_id}: {e}", exc_info=True)
        if content_id:
            try:
                update_record_content_status(content_id, business_id, "failed")
            except Exception:
                pass

    full_text = "\n".join(chunks) if chunks else ""
    future = _pending_futures.pop(job_id, None)
    if future and not future.done():
        future.set_result(full_text)


async def schedule_extraction(
    business_id: str,
    record_id: str | None,
    content_type: str,
    content: str,
    content_id: str = "",
    metadata: dict | None = None,
) -> str:

    try:
        job_id = f"extract_{uuid4().hex[:8]}"
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        _pending_futures[job_id] = future

        scheduler = get_scheduler()
        if scheduler and scheduler.running:
            scheduler.add_job(
                _run_extraction,
                args=[job_id, business_id, record_id, content_type, content, content_id, metadata],
                id=job_id,
                max_instances=1,
                replace_existing=True,
            )
        else:
            logger.warning("Scheduler not running, executing extraction inline")
            await _run_extraction(job_id, business_id, record_id, content_type, content, content_id, metadata)

        return await future
    except Exception as e:
        logger.error(f"schedule_extraction failed: {e}", exc_info=True)
        return ""
