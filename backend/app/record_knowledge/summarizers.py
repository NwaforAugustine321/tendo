"""Content summarizers for different record content types."""

import logging
import re

from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, AIMessage

from app.config.settings import settings
from app.record_knowledge.config import get_record_knowledge_config
from app.lib.context_handler import handle_text_context_length
import httpx
import base64
import tempfile
import os
import riva.client
import pymupdf as fitz

logger = logging.getLogger(__name__)


IMAGE_SUMMARY_PROMPT = (
    "Given the following text extracted from an image, generate:\n"
    "1. A natural title.\n"
    "2. A natural overview in concise details of the document.\n\n"
    "Rules:\n"
    "- Focus on the main purpose and key information, not every line.\n"
    "- Combine related details into a concise overview instead of listing them individually.\n"
    "- Mention important entities (people, organisations, dates, amounts or references) only when they help identify or understand the document.\n"
    "- Write from an outside perspective; never as the person in the document.\n"
    "- Do not invent, interpret or add information that is not present.\n"
    "- Do not start with 'This document...' or 'The image shows...'.\n"
    "- Write naturally, as if explaining the document to someone who hasn't opened it.\n\n"
    "Extracted text:\n{text}\n\n"
    "Respond exactly as:\n"
    "<title>...</title>\n"
    "<summary>...</summary>"
)

MAX_RETRIES = 2


def _parse_tagged_response(text: str) -> tuple[str, str]:
    """Extract title and summary from <title></title> and <summary></summary> tags."""
    title_match = re.search(r"<title>(.*?)</title>", text, re.DOTALL)
    summary_match = re.search(r"<summary>(.*?)</summary>", text, re.DOTALL)
    title = title_match.group(1).strip() if title_match else ""
    summary = summary_match.group(1).strip() if summary_match else ""
    return title, summary


async def summarize_text(content: str) -> dict:
    """Summarize text content using plain LLM."""
    from app.lib.context_handler import handle_text_context_length
    from app.llm.client import get_client as get_llm_client
    from langchain_core.messages import HumanMessage

    config = get_record_knowledge_config()
    max_length = config.max_summary_length

    if not content or not content.strip():
        return {"title": "", "summary": "Empty note with no content.", "content": ""}

    if len(content.strip()) <= 100:
        return {"title": content[:60].strip(), "summary": content.strip(), "content": content.strip()}

    fitted_content = await handle_text_context_length(content)

    llm = get_llm_client()
    prompt = (
        "Summarize the following text in 2-3 concise sentences. "
        "Focus on the main points and key information.\n\n"
        f"Text:\n{fitted_content}\n\n"
        "Respond with only the summary, nothing else."
    )

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        summary = response.content if hasattr(response, "content") else str(response)
        summary = summary.strip()[:max_length]
    except Exception:
        summary = content[:max_length]

    title = content[:60].strip()
    return {"title": title, "summary": summary, "content": content}


async def _image_ocr(image_data_url: str) -> str:

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


async def summarize_image(content: str) -> dict:

    try:
        extracted_text = await _image_ocr(content)
    except Exception as e:
        logger.warning(f"OCR failed: {e}")
        return {}

    if not extracted_text or not extracted_text.strip():
        return {}

    try:
        from app.lib.context_handler import handle_text_context_length
        fitted_text = await handle_text_context_length(extracted_text)

        summary_llm = ChatNVIDIA(
            model=settings.nvidia_model,
            api_key=settings.nvidia_api_key,
        )

        summary_prompt = IMAGE_SUMMARY_PROMPT.format(text=fitted_text)
        messages: list = [HumanMessage(content=summary_prompt)]

        for attempt in range(MAX_RETRIES + 1):
            response = await summary_llm.ainvoke(messages)
            raw = response.content if hasattr(response, "content") else str(response)

            title, summary = _parse_tagged_response(raw)
            if title and summary:
                return {"title": title, "summary": summary, "content": extracted_text}

            if attempt == MAX_RETRIES:
                fallback_title = extracted_text[:60].strip()
                return {"title": fallback_title, "summary": extracted_text, "content": extracted_text}

            messages.append(AIMessage(content=raw))
            messages.append(HumanMessage(content=(
                "Your response was not in the required format. "
                "You MUST use these exact XML tags:\n"
                "<title>specific title with real details from the text</title>\n"
                "<summary>clean summary of the key information</summary>\n"
                "Do NOT use generic titles. Include actual names, amounts, or dates."
            )))

    except Exception as e:
        logger.warning(f"Image analysis failed: {e}")
        return {}


async def _audio_transcribe(audio_data_url: str) -> str:


    try:
        header, b64_data = audio_data_url.split(",", 1)
        audio_bytes = base64.b64decode(b64_data)

        mime = audio_data_url.split(";")[0].split(":")[1] if ":" in audio_data_url else ""

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

            # Split audio into ~30 second chunks (30s * 16000 Hz * 2 bytes = 960000 bytes)
            CHUNK_SIZE = 960000  # ~30 seconds of 16kHz mono 16-bit audio
            OVERLAP_SIZE = 32000  # ~1 second overlap

            config = riva.client.RecognitionConfig(
                language_code="en-US",
                max_alternatives=1,
                enable_automatic_punctuation=True,
                encoding=riva.client.AudioEncoding.LINEAR_PCM,
                sample_rate_hertz=16000,
                audio_channel_count=1,
            )

            # If audio is small enough, process in one go
            if len(audio_content) <= CHUNK_SIZE + 44:  # +44 for WAV header
                response = asr_service.offline_recognize(audio_content, config)
                transcript_parts = []
                for result in response.results:
                    if result.alternatives:
                        transcript_parts.append(result.alternatives[0].transcript)
                return " ".join(transcript_parts)

            # Chunk the audio (skip WAV header for chunking)
            wav_header = audio_content[:44]
            raw_audio = audio_content[44:]
            all_transcripts = []

            offset = 0
            while offset < len(raw_audio):
                chunk = raw_audio[offset:offset + CHUNK_SIZE]
                # Prepend WAV header to each chunk
                chunk_with_header = wav_header + chunk

                try:
                    response = asr_service.offline_recognize(chunk_with_header, config)
                    for result in response.results:
                        if result.alternatives:
                            all_transcripts.append(result.alternatives[0].transcript)
                except Exception as e:
                    logger.warning(f"Chunk transcription failed at offset {offset}: {e}")

                offset += CHUNK_SIZE - OVERLAP_SIZE

            return " ".join(all_transcripts)

        finally:
            os.unlink(tmp_path)
            if wav_path != tmp_path and os.path.exists(wav_path):
                os.unlink(wav_path)

    except Exception as e:
        logger.warning(f"Audio transcription failed: {e}")
        return ""


async def summarize_audio(content: str) -> dict:
    if not content.startswith("data:audio"):
        return {}

    transcribed_text = await _audio_transcribe(content)

    if not transcribed_text or not transcribed_text.strip():
        return {}

    try:
        from app.lib.context_handler import handle_text_context_length

        fitted_text = await handle_text_context_length(transcribed_text)

        summary_llm = ChatNVIDIA(
            model=settings.nvidia_model,
            api_key=settings.nvidia_api_key,
        )

        summary_prompt = IMAGE_SUMMARY_PROMPT.format(text=fitted_text)
        messages: list = [HumanMessage(content=summary_prompt)]

        for attempt in range(MAX_RETRIES + 1):
            response = await summary_llm.ainvoke(messages)
            raw = response.content if hasattr(response, "content") else str(response)

            title, summary = _parse_tagged_response(raw)
            if title and summary:
                return {"title": title, "summary": summary, "content": transcribed_text}

            if attempt == MAX_RETRIES:
                fallback_title = transcribed_text[:60].strip()
                return {"title": fallback_title, "summary": transcribed_text, "content": transcribed_text}

            messages.append(AIMessage(content=raw))
            messages.append(HumanMessage(content=(
                "Your response was not in the required format. "
                "You MUST use these exact XML tags:\n"
                "<title>specific title based on content</title>\n"
                "<summary>clean summary of the key information</summary>\n"
                "Use actual details from the text."
            )))

    except Exception as e:
        logger.warning(f"Audio summary failed: {e}")
        return {"title": transcribed_text[:60], "summary": transcribed_text, "content": transcribed_text}


PDF_PAGE_PROMPT = ""  # Kept for reference but no longer used with opendataloader approach


async def summarize_pdf(content: str) -> dict:
    """Process PDF using opendataloader for extraction + reasoning model for summary."""
    if not content.startswith("data:application/pdf"):
        return {}

    try:
        # Step 1: Extract markdown and JSON from PDF using opendataloader
        page_data = await _extract_pdf_with_opendataloader(content)
        if not page_data:
            return {}

        logger.info(f"PDF extracted: {len(page_data)} pages via opendataloader")

        # Step 2: Build per-page chunks for embedding (markdown + matched JSON blocks)
        page_chunks: list[dict] = []
        all_page_texts: list[str] = []

        for page in page_data:
            page_num = page["page_number"]
            md_text = page["markdown"]
            json_blocks = page.get("json_blocks", [])
            page_images = page.get("images", [])

            if not md_text.strip():
                all_page_texts.append("")
                continue

            # Embed only the markdown text — JSON blocks go into metadata
            chunk_text = md_text

            all_page_texts.append(md_text)

            # Sliding window overlap
            pages_covered = [page_num]
            embed_text = chunk_text

            if page_num > 1 and len(all_page_texts) >= 2 and all_page_texts[-2]:
                prev_sentences = all_page_texts[-2].split(".")[-3:]
                embed_text = ". ".join(s.strip() for s in prev_sentences if s.strip()) + "\n\n" + embed_text
                pages_covered.insert(0, page_num - 1)

            chunk_entry = {
                "page_number": page_num,
                "pages_covered": pages_covered,
                "text": embed_text,
                "raw_text": md_text,
                "json_blocks": json_blocks,
            }
            if page_images:
                chunk_entry["images"] = page_images

            page_chunks.append(chunk_entry)

        # Add next-page overlap (second pass)
        for i in range(len(page_chunks) - 1):
            next_raw = page_chunks[i + 1]["raw_text"]
            if next_raw:
                next_sentences = next_raw.split(".")[:2]
                page_chunks[i]["text"] += "\n\n" + ". ".join(s.strip() for s in next_sentences if s.strip())
                if page_chunks[i + 1]["page_number"] not in page_chunks[i]["pages_covered"]:
                    page_chunks[i]["pages_covered"].append(page_chunks[i + 1]["page_number"])

        # Step 3: Generate overall title + summary using reasoning model
        all_text_combined = "\n\n".join(f"[Page {i+1}]: {t}" for i, t in enumerate(all_page_texts) if t)

        if not all_text_combined.strip():
            return {}

        from app.lib.context_handler import handle_text_context_length
        fitted_text = await handle_text_context_length(all_text_combined)

        # Use the configured LLM provider for summary
        from app.llm.client import get_client as get_llm_client
        summary_llm = get_llm_client()

        summary_prompt = IMAGE_SUMMARY_PROMPT.format(text=fitted_text)
        messages_list: list = [HumanMessage(content=summary_prompt)]

        for attempt in range(MAX_RETRIES + 1):
            response = await summary_llm.ainvoke(messages_list)
            raw = response.content if hasattr(response, "content") else str(response)

            title, summary = _parse_tagged_response(raw)
            if title and summary:
                logger.info(f"PDF processed: {title} ({len(page_chunks)} chunks)")
                return {"title": title, "summary": summary, "content": all_text_combined, "page_chunks": page_chunks}

            if attempt == MAX_RETRIES:
                fallback_title = all_text_combined[:60].strip()
                return {"title": fallback_title, "summary": all_text_combined[:500], "content": all_text_combined, "page_chunks": page_chunks}

            messages_list.append(AIMessage(content=raw))
            messages_list.append(HumanMessage(content=(
                "Respond with exactly:\n"
                "<title>specific title</title>\n"
                "<summary>summary</summary>"
            )))

    except Exception as e:
        logger.error(f"PDF processing failed: {e}", exc_info=True)
        return {}


async def _extract_pdf_with_opendataloader(content: str) -> list[dict]:
    """Split PDF into pages first, then run opendataloader on each page for markdown + JSON."""
    import json as json_mod
    import shutil

    # Decode PDF from base64
    header, b64_data = content.split(",", 1)
    pdf_bytes = base64.b64decode(b64_data)

    # Write full PDF to temp file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        # Step 1: Split PDF into individual page PDFs using pymupdf
        doc = fitz.open(tmp_path)
        num_pages = len(doc)
        logger.info(f"PDF has {num_pages} pages, splitting for opendataloader")

        page_dir = tempfile.mkdtemp()
        page_paths: list[str] = []

        for page_idx in range(num_pages):
            single_doc = fitz.open()  # new empty PDF
            single_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
            page_path = os.path.join(page_dir, f"page_{page_idx + 1}.pdf")
            single_doc.save(page_path)
            single_doc.close()
            page_paths.append(page_path)

        doc.close()

        # Step 2: Run opendataloader on all single-page PDFs in one batch call
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

        # Step 3: Read each page's markdown and JSON output + external images
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

            # Collect external images for this page as base64 data URLs
            page_images: list[str] = []
            # Look for images in a subdirectory named after the stem or in output_dir directly
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

            # Step 4: Extract JSON blocks (type, content, bounding_box) and match to markdown
            blocks = _extract_page_blocks(json_content)
            matched_blocks = _match_blocks_to_markdown(md_content, blocks)

            pages.append({
                "page_number": page_num,
                "markdown": md_content,
                "json_blocks": matched_blocks,
                "images": page_images,
            })

        # Cleanup
        shutil.rmtree(page_dir, ignore_errors=True)
        shutil.rmtree(output_dir, ignore_errors=True)

        return pages

    except ImportError:
        logger.error("opendataloader-pdf not installed. Install with: pip install -U opendataloader-pdf")
        return []
    except Exception as e:
        logger.error(f"opendataloader extraction failed: {e}", exc_info=True)
        return []
    finally:
        os.unlink(tmp_path)


def _extract_page_blocks(json_content: dict | None) -> list[dict]:
    """Extract blocks from a single-page opendataloader JSON output.
    Reads the entire element object from each kid.
    Returns list of full element dicts as-is from the JSON."""
    if not json_content or not isinstance(json_content, dict):
        return []

    kids = json_content.get("kids", [])
    return [element for element in kids if isinstance(element, dict)]


def _match_blocks_to_markdown(markdown: str, blocks: list[dict]) -> list[dict]:
    """Match each JSON block (full element object) to its position in the markdown using content text."""
    matched: list[dict] = []

    for block in blocks:
        content = block.get("content", "")

        # For tables/elements with kids but no direct content, extract text
        if not content and block.get("type") == "table":
            content = _extract_table_text(block)
        if not content and "kids" in block:
            content = _extract_kids_text(block.get("kids", []))

        md_position = -1
        if content and len(content) > 5:
            search_key = content[:100].strip()
            md_position = markdown.find(search_key)

        # Store the entire element with md_position added
        entry = dict(block)
        entry["md_position"] = md_position
        matched.append(entry)

    # Sort by position in markdown (reading order)
    matched.sort(key=lambda b: b["md_position"] if b["md_position"] >= 0 else 9999)
    return matched


def _extract_table_text(table_element: dict) -> str:
    """Extract text from table rows/cells into readable format."""
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
    """Recursively extract text content from nested kids elements."""
    texts = []
    for kid in kids:
        if isinstance(kid, dict):
            content = kid.get("content", "")
            if content:
                texts.append(content)
            if "kids" in kid:
                texts.append(_extract_kids_text(kid["kids"]))
    return " ".join(t for t in texts if t)


def _match_json_blocks_to_markdown(markdown: str, json_blocks: list[dict]) -> str:
    """Combine each JSON block with the page's markdown into a single chunk string.
    Each block's content is paired with the full page markdown for that page."""
    import json as json_mod

    if not json_blocks:
        return ""

    # Combine: page markdown + all JSON blocks as structured data
    combined = f"## Markdown\n{markdown}\n\n## Structured Blocks\n"
    for block in json_blocks:
        block_type = block.get("type", "unknown")
        content = block.get("content", "")
        if not content and block_type == "table":
            content = _extract_table_text(block)
        if not content and "kids" in block:
            content = _extract_kids_text(block.get("kids", []))
        bbox = block.get("bounding box", block.get("boundingBox", None))

        combined += f"[{block_type}] {content}"
        if bbox:
            combined += f" (bbox: {bbox})"
        combined += "\n"

    return combined


# Registry mapping content_type to summarizer function
SUMMARIZERS = {
    "text": summarize_text,
    "image": summarize_image,
    "audio": summarize_audio,
    "pdf": summarize_pdf,
}
