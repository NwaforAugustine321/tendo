"""Content extractors — extract raw text from different content types.

Handles OCR, audio transcription, PDF extraction.
Returns chunked text ready for embedding using langchain text splitter with overlap.
"""

import base64
import logging
import os
import tempfile

import httpx
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config.settings import settings

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks using langchain splitter."""
    if not text or not text.strip():
        return []
    chunks = _splitter.split_text(text)
    chunks = [c for c in chunks if c.strip()]
    print(chunks)
    return chunks


async def extract_content(content_type: str, content: str) -> str:
    """Extract raw text from content based on its type. Returns full text."""
    extractor = EXTRACTORS.get(content_type, _extract_text)
    return await extractor(content)


async def extract_and_chunk(content_type: str, content: str) -> list[str]:
    """Extract text from content and return chunked list for embedding."""
    raw_text = await extract_content(content_type, content)
  
    if not raw_text or not raw_text.strip():
        return []
    return chunk_text(raw_text)


async def _extract_text(content: str) -> str:
    return content or ""


async def image_ocr(image_data_url: str) -> str:
    """Run NVIDIA OCR on an image data URL and return extracted text."""
    ocr_url = "https://ai.api.nvidia.com/v1/cv/nvidia/nemotron-ocr-v2"
    headers = {
        "Authorization": f"Bearer {settings.nvidia_api_key}",
        "Accept": "application/json",
    }
    payload = {
        "input": [
            {"type": "image_url", "url": image_data_url}
        ]
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(ocr_url, headers=headers, json=payload)
        resp.raise_for_status()
        ocr_data = resp.json()

    if not isinstance(ocr_data, dict) or "data" not in ocr_data:
        return ""

    texts: list[str] = []
    for page in ocr_data.get("data", []):
        for detection in page.get("text_detections", []):
            text_pred = detection.get("text_prediction", {})
            text = text_pred.get("text", "").strip()
            if text:
                texts.append(text)

    return "\n".join(texts)


async def audio_transcribe(audio_data_url: str) -> str:
    """Transcribe audio data URL to text using NVIDIA Riva ASR."""
    import riva.client

    try:
        header, b64_data = audio_data_url.split(",", 1)
        audio_bytes = base64.b64decode(b64_data)

        with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        wav_path = tmp_path + ".wav"
        try:
            import subprocess
            subprocess.run(
                ["ffmpeg", "-y", "-i", tmp_path, "-ar", "16000", "-ac", "1", "-f", "wav", wav_path],
                capture_output=True, timeout=60
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            wav_path = tmp_path

        try:
            metadata = [
                ("function-id", "71203149-d3b7-4460-8231-1be2543a1fca"),
                ("authorization", f"Bearer {settings.nvidia_api_key}"),
            ]
            auth = riva.client.Auth(
                uri="grpc.nvcf.nvidia.com:443",
                use_ssl=True,
                metadata_args=metadata,
            )
            asr_service = riva.client.ASRService(auth)

            with open(wav_path, "rb") as f:
                audio_content = f.read()

            AUDIO_CHUNK_SIZE = 960000
            AUDIO_OVERLAP_SIZE = 32000

            config = riva.client.RecognitionConfig(
                language_code="en-US",
                max_alternatives=1,
                enable_automatic_punctuation=True,
                encoding=riva.client.AudioEncoding.LINEAR_PCM,
                sample_rate_hertz=16000,
                audio_channel_count=1,
            )

            if len(audio_content) <= AUDIO_CHUNK_SIZE + 44:
                response = asr_service.offline_recognize(audio_content, config)
                transcript_parts = []
                for result in response.results:
                    if result.alternatives:
                        transcript_parts.append(result.alternatives[0].transcript)
                return " ".join(transcript_parts)

            wav_header = audio_content[:44]
            raw_audio = audio_content[44:]
            all_transcripts = []

            offset = 0
            while offset < len(raw_audio):
                chunk = raw_audio[offset:offset + AUDIO_CHUNK_SIZE]
                chunk_with_header = wav_header + chunk

                try:
                    response = asr_service.offline_recognize(chunk_with_header, config)
                    for result in response.results:
                        if result.alternatives:
                            all_transcripts.append(result.alternatives[0].transcript)
                except Exception as e:
                    logger.warning(f"Chunk transcription failed at offset {offset}: {e}")

                offset += AUDIO_CHUNK_SIZE - AUDIO_OVERLAP_SIZE

            return " ".join(all_transcripts)

        finally:
            os.unlink(tmp_path)
            if wav_path != tmp_path and os.path.exists(wav_path):
                os.unlink(wav_path)

    except Exception as e:
        logger.warning(f"Audio transcription failed: {e}")
        return ""


async def extract_pdf_pages(content: str) -> list[dict]:
    """Extract PDF into per-page data with markdown, JSON blocks, and images."""
    import json as json_mod
    import shutil
    import pymupdf as fitz

    header, b64_data = content.split(",", 1)
    pdf_bytes = base64.b64decode(b64_data)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        doc = fitz.open(tmp_path)
        num_pages = len(doc)
        logger.info(f"PDF has {num_pages} pages, splitting for opendataloader")

        page_dir = tempfile.mkdtemp()
        page_paths: list[str] = []

        for page_idx in range(num_pages):
            single_doc = fitz.open()
            single_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
            page_path = os.path.join(page_dir, f"page_{page_idx + 1}.pdf")
            single_doc.save(page_path)
            single_doc.close()
            page_paths.append(page_path)

        doc.close()

        import opendataloader_pdf
        import glob as glob_mod

        output_dir = tempfile.mkdtemp()
        opendataloader_pdf.convert(
            input_path=page_paths,
            output_dir=output_dir,
            format="markdown,json",
            quiet=True,
            image_output="external",
            image_format="jpeg",
            content_safety_off="all",
            use_struct_tree=True,
        )

        pages: list[dict] = []

        for page_idx, page_path in enumerate(page_paths):
            page_num = page_idx + 1
            stem = os.path.splitext(os.path.basename(page_path))[0]

            md_path = os.path.join(output_dir, stem + ".md")
            json_path = os.path.join(output_dir, stem + ".json")

            md_content = ""
            json_content = None

            if os.path.exists(md_path):
                with open(md_path, "r", encoding="utf-8") as f:
                    md_content = f.read().strip()

            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    json_content = json_mod.load(f)

            page_images: list[str] = []
            image_dir = os.path.join(output_dir, stem)
            if not os.path.isdir(image_dir):
                image_dir = output_dir

            for img_file in sorted(glob_mod.glob(os.path.join(image_dir, f"{stem}*.jpeg")) +
                                   glob_mod.glob(os.path.join(image_dir, f"{stem}*.jpg")) +
                                   glob_mod.glob(os.path.join(image_dir, f"{stem}*.png"))):
                try:
                    with open(img_file, "rb") as img_f:
                        img_bytes = img_f.read()
                    ext = os.path.splitext(img_file)[1].lower().lstrip(".")
                    mime = "image/jpeg" if ext in ("jpeg", "jpg") else f"image/{ext}"
                    b64 = base64.b64encode(img_bytes).decode("utf-8")
                    page_images.append(f"data:{mime};base64,{b64}")
                except Exception as img_err:
                    logger.warning(f"Failed to read image {img_file}: {img_err}")

            blocks = _extract_page_blocks(json_content)
            matched_blocks = _match_blocks_to_markdown(md_content, blocks)

            pages.append({
                "page_number": page_num,
                "markdown": md_content,
                "json_blocks": matched_blocks,
                "images": page_images,
            })

        shutil.rmtree(page_dir, ignore_errors=True)
        shutil.rmtree(output_dir, ignore_errors=True)

        return pages

    except ImportError:
        logger.error("opendataloader-pdf not installed.")
        return []
    except Exception as e:
        logger.error(f"opendataloader extraction failed: {e}", exc_info=True)
        return []
    finally:
        os.unlink(tmp_path)


async def _extract_image_content(content: str) -> str:
    if not content:
        return ""
    if not content.startswith("data:"):
        return ""
    try:
        return await image_ocr(content)
    except Exception as e:
        logger.warning(f"OCR extraction failed: {e}")
        return ""


async def _extract_audio_content(content: str) -> str:
    if not content:
        return ""
    if not content.startswith("data:audio"):
        return ""
    try:
        return await audio_transcribe(content)
    except Exception as e:
        logger.warning(f"Audio transcription failed: {e}")
        return ""


async def _extract_pdf_content(content: str) -> str:
    if not content or not content.startswith("data:application/pdf"):
        return ""
    try:
        page_data = await extract_pdf_pages(content)
        all_texts = [p["markdown"] for p in page_data if p.get("markdown")]
        return "\n\n".join(all_texts)
    except Exception as e:
        logger.warning(f"PDF extraction failed: {e}")
        return ""


def _extract_page_blocks(json_content: dict | None) -> list[dict]:
    if not json_content or not isinstance(json_content, dict):
        return []
    kids = json_content.get("kids", [])
    return [element for element in kids if isinstance(element, dict)]


def _match_blocks_to_markdown(markdown: str, blocks: list[dict]) -> list[dict]:
    matched: list[dict] = []
    for block in blocks:
        content = block.get("content", "")
        if not content and block.get("type") == "table":
            content = _extract_table_text(block)
        if not content and "kids" in block:
            content = _extract_kids_text(block.get("kids", []))

        md_position = -1
        if content and len(content) > 5:
            search_key = content[:100].strip()
            md_position = markdown.find(search_key)

        entry = dict(block)
        entry["md_position"] = md_position
        matched.append(entry)

    matched.sort(key=lambda b: b["md_position"] if b["md_position"] >= 0 else 9999)
    return matched


def _extract_table_text(table_element: dict) -> str:
    rows = table_element.get("rows", [])
    lines = []
    for row in rows:
        cells = row.get("cells", [])
        cell_texts = []
        for cell in cells:
            kids = cell.get("kids", [])
            cell_text = _extract_kids_text(kids)
            cell_texts.append(cell_text)
        if cell_texts:
            lines.append(" | ".join(cell_texts))
    return "\n".join(lines)


def _extract_kids_text(kids: list) -> str:
    texts = []
    for kid in kids:
        if isinstance(kid, dict):
            content = kid.get("content", "")
            if content:
                texts.append(content)
            if "kids" in kid:
                texts.append(_extract_kids_text(kid["kids"]))
    return " ".join(t for t in texts if t)


EXTRACTORS = {
    "text": _extract_text,
    "image": _extract_image_content,
    "audio": _extract_audio_content,
    "pdf": _extract_pdf_content,
}
