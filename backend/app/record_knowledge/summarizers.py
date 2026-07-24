"""Content summarizers for different record content types."""

import logging
import re

from pydantic import BaseModel
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, AIMessage

from app.config.settings import settings
from app.record_knowledge.config import get_record_knowledge_config
from app.lib.context_handler import handle_text_context_length
import httpx

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


async def summarize_text(content: str) -> str:
    """Summarize text content using the text_summarizer agent."""
    from app.lib.agent_executor import execute_task
    from app.lib.json_parser import parse_json_output
    from app.lib.context_handler import handle_text_context_length

    class SummaryOutput(BaseModel):
        summary: str

    config = get_record_knowledge_config()
    max_length = config.max_summary_length

    if not content or not content.strip():
        return "Empty note with no content."

    if len(content.strip()) <= 100:
        return content.strip()

    fitted_content = await handle_text_context_length(content)

    from app.agents.models import Agent
    agent = Agent.from_spec("text_summarizer")

    raw = await execute_task(
        agent=agent,
        description=fitted_content,
        tools=[],
        expected_output=agent.expected_output,
        output_pydantic=SummaryOutput,
        use_system_prompt=True,
    )

    try:
        data = parse_json_output(raw)
        summary = data.get("summary", raw.strip())
    except Exception:
        summary = raw.strip() if raw else content[:max_length]

    return summary[:max_length]


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


async def summarize_image(content: str) -> str:

    try:
        extracted_text = await _image_ocr(content)
        print(extracted_text)
    except Exception as e:
        logger.warning(f"OCR failed: {e}")
        return ""

    if not extracted_text or not extracted_text.strip():
        return ""

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
                return f"{title}|||{summary}|||{extracted_text}"

            if attempt == MAX_RETRIES:
                
                fallback_title = extracted_text[:60].strip()
                return f"{fallback_title}|||{extracted_text}|||{extracted_text}"

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
        return ""


async def summarize_audio(content: str) -> str:
    """Summarize audio content."""
    if content.startswith("data:audio"):
        return "Audio recording uploaded by user."
    return content[:200] if content else "Audio content."


async def summarize_pdf(content: str) -> str:
    """Summarize PDF content."""
    if content.startswith("data:application/pdf"):
        return "PDF document uploaded by user."
    return content[:200] if content else "PDF document."


# Registry mapping content_type to summarizer function
SUMMARIZERS = {
    "text": summarize_text,
    "image": summarize_image,
    "audio": summarize_audio,
    "pdf": summarize_pdf,
}
