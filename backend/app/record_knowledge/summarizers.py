import json
import logging
import re

from app.llm.client import get_client
from app.runtime.llm_vendors.langchain import LangChainLLM
from app.runtime.agents.agent import Agent
from app.runtime.memory.factory import create_memory_provider
from app.runtime.memory.factory import (
    create_memory_provider,
)
from app.runtime.rag.factory import (
    create_rag_provider
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
MAX_LENGTH = 500

_llm_instance = None


def _get_llm():
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LangChainLLM(model=get_client())
    return _llm_instance


system_prompt = (
    "You summarize content naturally, as if explaining it to someone who hasn't seen it.\n\n"
    "Style:\n"
    "- Write naturally and conversationally, not robotically.\n"
    "- State facts, findings, and knowledge directly.\n"
    "- Never describe what the content is — just explain what it says.\n"
    "- Be concise but complete.\n\n"
    "Rules:\n"
    "- Use only information present in the content.\n"
    "- Do not invent or speculate.\n"
    "- If a previous summary exists, merge it with new content into one coherent summary.\n"
    "- The title should reference the main subject or entity found in the content (2-30 words).\n"
    "- Generate up to 3 questions that reference specific facts, findings, or details from the content. Each question must mention something concrete from the content.\n\n"
    "Respond exactly as:\n"
    "<title>short title referencing the main subject or entity found in the content</title>\n"
    "<summary>natural explanation of the content focusing on facts and findings</summary>\n"
)

user_prompt = (
    "Summarize this naturally. Explain what it says, not what it is.\n\n"
    "Content:\n{content}"
)


record_system_prompt = (
    "You are an business overview specialist.\n\n"

    "Never expose internal workings or implementation details. "
    "Present only the relevant information and its meaning to the business owner."

    "Synthesize the available information into one coherent naturally explanation and conversationally, not robotically. "
    "Connect related information and explain what it collectively means. "
    "Do not present separate findings, topics, relationships, or conclusions.\n\n"

    "Explain what is happening, how the information connects, and what it means. "

    "Combine related information without forcing unrelated connections. "
    "Distinguish facts from interpretations and recommendations. "
    "Do not invent, speculate, or introduce unsupported information. "
    "If the information does not support an impact or recommendation, say so.\n\n"

    "Present the insight as a natural explanation, not a list of findings. "

    "Output requirements:\n"
    "- Insight (maximum 300 words).\n"
    "- Generate up to 2-3 useful follow-up questions (maximum 30 words).\n"

    "Format:\n"
    "<insight>\n"
    "Unified explanation.\n"
    "</insight>\n"
    "<suggestion_questions>\n"
    "[\"question insight 1?\", \"question insight 2?\", \"question insight 3?\"]\n"
    "</suggestion_questions>"
)

record_user_prompt = (
    "Synthesize the available information into one coherent overview. "
    "Explain what is happening, how the information connects, and what it means."
)


def _extract_tag(
    text: str,
    tag: str,
) -> str:
    """
    Extract the content of a tag.

    Supports both:
    - properly closed tags
    - incomplete tags where the closing tag is missing
    """

    tag = re.escape(tag)

    # First: normal closed tag.
    match = re.search(
        rf"<{tag}>\s*(.*?)\s*</{tag}>",
        text,
        re.DOTALL | re.IGNORECASE,
    )

    if match:
        return match.group(1).strip()

    # Fallback: opening tag exists but closing tag is missing.
    match = re.search(
        rf"<{tag}>\s*(.*)",
        text,
        re.DOTALL | re.IGNORECASE,
    )

    if match:
        return match.group(1).strip()

    return ""


def _extract_json_list(
    text: str,
    tag: str,
    max_items: int = 3,
) -> list[str]:

    raw = _extract_tag(
        text,
        tag,
    )

    if not raw:
        return []

    # Remove accidental markdown code fences.
    raw = re.sub(
        r"```(?:json)?",
        "",
        raw,
        flags=re.IGNORECASE,
    ).strip()

    raw = raw.replace(
        "```",
        "",
    ).strip()

    # Normal valid JSON.
    try:
        parsed = json.loads(raw)

        if isinstance(parsed, list):
            return [
                str(item).strip()
                for item in parsed[:max_items]
                if str(item).strip()
            ]

    except (
        json.JSONDecodeError,
        TypeError,
    ):
        pass

    # Fallback for partially generated JSON.
    questions = re.findall(
        r'"((?:\\.|[^"\\])*)"',
        raw,
    )

    result: list[str] = []

    for value in questions:
        try:
            value = json.loads(
                f'"{value}"',
            )
        except json.JSONDecodeError:
            continue

        value = value.strip()

        if value:
            result.append(value)

        if len(result) >= max_items:
            break

    return result


def _parse_response(
    text: str,
    *,
    content_tags: list[str],
    questions_tag: str,
) -> tuple[dict[str, str], list[str]]:

    contents = {
        tag: _extract_tag(
            text,
            tag,
        )
        for tag in content_tags
    }

    questions = _extract_json_list(
        text,
        questions_tag,
    )

    return contents, questions


async def generate_record_summary(content: str, max_length: int = MAX_LENGTH) -> dict:

    title = ""
    summary = ""
    suggested_questions = []

    for attempt in range(MAX_RETRIES):
        try:

            agent = Agent(
                name="Summarizer Specialist",
                llm=_get_llm(),
                instructions=system_prompt,
                max_iteration=4,
                max_reasoning_steps=2
            )
            _session = agent.create_session()
            response = await _session.run(user_prompt.replace("{content}",  str(content)))
            response_text = response.text if hasattr(
                response, "text") else str(response)
            contents, suggested_questions = _parse_response(
                response_text,
                content_tags=["title", "summary"],
                questions_tag="insights",
            )
            title = contents.get("title", "")
            summary = contents.get("summary", "")
            if title and summary:
                break

            # Tags not found — ask the same session to reformat
            response = await _session.run(
                "Your response was not in the correct format. "
                "Respond exactly as:\n"
                "<title>short title</title>\n"
                "<summary>natural explanation</summary>"
            )
            response_text = response.text if hasattr(
                response, "text") else str(response)
            contents, suggested_questions = _parse_response(
                response_text,
                content_tags=["title", "summary"],
                questions_tag="insights",
            )
            title = contents.get("title", "")
            summary = contents.get("summary", "")
            if title and summary:
                break
        except Exception as e:
            logger.error(f"Summary attempt {attempt + 1} failed: {e}")
            if attempt == MAX_RETRIES - 1:
                summary = content[:max_length]
                title = content[:60].strip()

    summary = summary.strip()[:max_length]
    title = title or content[:60].strip()

    return {"title": title, "summary": summary, "suggested_questions": suggested_questions, "content": content}


async def generate_record_overview(business_id: str, record_id: str) -> dict:

    insight = ""
    suggestions = []

    try:
        scopes = [
            f"business/{business_id}/record/{record_id}", f"business/{business_id}"]

        agent = Agent(
            name="Insight Specialist",
            llm=_get_llm(),
            memory=create_memory_provider(
                namespace=business_id, scopes=scopes, ignore_threshold=True),
            rag=create_rag_provider(
                namespace=business_id, scopes=scopes, ignore_threshold=True),
            instructions=record_system_prompt,
            max_iteration=6,
            max_reasoning_steps=3,
            enable_runtime_rag_mem=True
        )

        for attempt in range(MAX_RETRIES):
            try:
                session = agent.create_session()
                response = await session.run(record_user_prompt)
                response_text = response.text if hasattr(
                    response, "text") else str(response)
                print(f"Overview raw response >>>: {response_text[:500]}")
                contents, suggestions = _parse_response(
                    response_text,
                    content_tags=["insight"],
                    questions_tag="suggestion_questions",
                )
                insight = contents.get("insight", "")
                if insight:
                    break

                # Tags not found — ask the same session to reformat
                response = await session.run(
                    "Your response was not in the correct format. "
                    "Respond exactly in this format:\n"
                    "<insight>your comprehensive overview here</insight>\n"
                    '<suggestion_questions>["question insight 1?", "question insight 2?"]</suggestion_questions>'
                )
                response_text = response.text if hasattr(
                    response, "text") else str(response)
                contents, suggestions = _parse_response(
                    response_text,
                    content_tags=["insight"],
                    questions_tag="suggestion_questions",
                )
                insight = contents.get("insight", "")
                if insight:
                    break
            except Exception as e:
                logger.error(f"Overview attempt {attempt + 1} failed: {e}")
                if attempt == MAX_RETRIES - 1:
                    return {"insight": "", "suggestions": []}

    except Exception as e:
        logger.error(f"Failed to generate overview: {e}")

    return {"insight": insight, "suggestions": suggestions}
