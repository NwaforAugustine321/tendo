import logging
import re

from app.llm.client import get_client
from app.runtime.llm_vendors.langchain import LangChainLLM
from app.runtime.agents.agent import Agent

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
MAX_LENGTH = 500

_llm = get_client()

llm = LangChainLLM(
    model=_llm
)

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


record_system_prompt = ()
record_user_prompt = ()

agent = Agent(
    name="Summarizer Specialist",
    llm=llm,
    instructions=system_prompt,
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
        import json
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


async def generate_record_overview(business_id: str, record_id: str):

    try:

        scopes = [f"business/{business_id}/record/{record_id}"]

        agent = Agent(
            name="Insight Specialist",
            llm=llm,
            memory=create_memory_provider(
                namespace=business_id, scopes=scopes),
            rag=create_rag_provider(namespace=business_id, scopes=scopes),
            instructions=prompt,
        )

        session = agent.create_session()
        response = await session.run(
            user_message
        )

    except Exception as e:
        logger.error(f"Failed to generate overview: {e}")
