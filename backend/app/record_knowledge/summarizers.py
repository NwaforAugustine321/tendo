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
    '<insights>["question referencing a specific fact from the content?", "question about a specific finding?", "question about a detail mentioned?"]</insights>'
)

user_prompt = (
    "Summarize this naturally. Explain what it says, not what it is.\n\n"
    "Content:\n{content}"
)


record_system_prompt = (
    "You are an information overview specialist.\n\n"
    "Explain what the information says, not what it is or where it came from.\n\n"
    "Before analyzing the information, construct a broad, comprehensive query "
    "that captures the main subject, related topics, concepts, entities, facts, "
    "events, findings, decisions, and relationships needed to understand the whole picture. "
    "Do not construct a query around only one detail\n\n"
    "Instructions:\n"
    "- Use the good phrase query to gather information covering the full subject and its related areas.\n"
    "- Connect related information across all available topics rather than focusing on one record.\n"
    "- Identify the major topics, themes, entities, and areas of information.\n"
    "- Explain each major topic separately.\n"
    "- Under each topic, present each distinct piece of information as a clear bullet point or parameter.\n"
    "- Combine related information from different records when they describe the same topic, entity, event, or idea.\n"
    "- Include important facts, evidence, findings, ideas, decisions, insights, observations, "
    "perspectives, assumptions, patterns, relationships, and conclusions.\n"
    "- Explain how different topics, findings, decisions, and ideas connect to or influence one another.\n"
    "- Distinguish established facts and evidence from interpretations, assumptions, ideas, and conclusions.\n"
    "- Do not invent, speculate, or introduce unsupported information.\n"
    "- Do not describe the information as coming from a document, record, source, retrieval, "
    "database, context, or any other external origin.\n"
    "- Present the information directly and naturally as an explanation of what is known.\n"
    "- Be comprehensive but concise and avoid unnecessary repetition.\n"
    "- Generate 2-3 useful follow-up questions based on specific details or relationships.\n\n"
    "Respond exactly in this format:\n"
    "<insight>\n"
    "## Topic 1\n"
    "- Point: explanation\n"
    "- Point: explanation\n\n"
    "## Topic 2\n"
    "- Point: explanation\n"
    "- Point: explanation\n\n"
    "## Relationships\n"
    "- Relationship: explanation\n"
    "- Relationship: explanation\n"
    "</insight>\n"
    '<suggestion_questions>["question 1?", "question 2?", "question 3?"]</suggestion_questions>'
)

record_user_prompt = (
    "Explain the available information comprehensively. "
    "then provide a comprehensive overview covering all major topics, distinct information ,points, and relationships"
    "as a clear point, then explain how the topics relate to one another."
)


def _parse_tagged_response(text: str) -> tuple[str, str, list[str]]:
    """Extract title, summary, and questions from tagged response."""
    title_match = re.search(r"<title>(.*?)</title>", text, re.DOTALL)
    summary_match = re.search(r"<summary>(.*?)</summary>", text, re.DOTALL)
    questions_match = re.search(
        r"<insights>(.*?)</insights>", text, re.DOTALL)
    title = title_match.group(1).strip() if title_match else ""
    summary = summary_match.group(1).strip() if summary_match else ""
    questions = []
    if questions_match:
        raw = questions_match.group(1).strip()
        try:
            questions = json.loads(raw)[:3]
        except (json.JSONDecodeError, TypeError):
            questions = []
    return title, summary, questions


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
            )
            _session = agent.create_session()
            response = await _session.run(user_prompt.replace("{content}",  str(content)))
            response_text = response.text if hasattr(
                response, "text") else str(response)
            title, summary, suggested_questions = _parse_tagged_response(
                response_text)
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


def _parse_record_overview_response(text: str) -> tuple[str, list[str]]:
    """Extract insight and suggestion_questions from tagged response."""
    insight_match = re.search(r"<insight>(.*?)</insight>", text, re.DOTALL)
    questions_match = re.search(
        r"<suggestion_questions>(.*?)</suggestion_questions>", text, re.DOTALL)
    insight = insight_match.group(1).strip() if insight_match else ""
    suggestions = []
    if questions_match:
        raw = questions_match.group(1).strip()
        try:
            suggestions = json.loads(raw)[:3]
        except (json.JSONDecodeError, TypeError):
            suggestions = []
    return insight, suggestions


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
        )

        for attempt in range(MAX_RETRIES):
            try:
                session = agent.create_session()
                response = await session.run(record_user_prompt)
                response_text = response.text if hasattr(
                    response, "text") else str(response)
                logger.info(f"Overview raw response: {response_text[:500]}")
                insight, suggestions = _parse_record_overview_response(
                    response_text)
                if insight:
                    break
                # If no tags found but we got a response, use it as insight directly
                if response_text.strip() and not insight:
                    insight = response_text.strip()
                    break
            except Exception as e:
                logger.error(f"Overview attempt {attempt + 1} failed: {e}")
                if attempt == MAX_RETRIES - 1:
                    return {"insight": "", "suggestions": []}

    except Exception as e:
        logger.error(f"Failed to generate overview: {e}")

    return {"insight": insight, "suggestions": suggestions}
