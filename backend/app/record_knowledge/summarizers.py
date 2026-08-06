import logging
import re
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, AIMessage

from app.config.settings import settings
from app.record_knowledge.config import get_record_knowledge_config
from app.lib.context_handler import handle_text_context_length
from app.record_knowledge.extractors import (
    image_ocr as _image_ocr,
    audio_transcribe as _audio_transcribe,
    extract_pdf_pages as _extract_pdf_with_opendataloader,
    _extract_page_blocks,
    _match_blocks_to_markdown,
    _extract_table_text,
    _extract_kids_text,
)

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


SUMMARIZERS = {
    "text": summarize_text,
    "image": summarize_image,
    "audio": summarize_audio,
    "pdf": summarize_pdf,
}
