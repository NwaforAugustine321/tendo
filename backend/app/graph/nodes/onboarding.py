"""Onboarding node — collects business profile info through structured conversation."""

import json
import logging

from langgraph.types import interrupt, Command

from app.llm.client import get_client as get_llm
from app.llm.specs import load
from app.lib.prompt_trimmer import trim_and_archive
from app.models.state import GraphState

logger = logging.getLogger(__name__)


async def onboarding_node(state: GraphState) -> dict:
    event = state.get("event", {})
    user_message = event.get("text", "")
    business_id = state.get("business_id") or event.get("business_id", "")
    thread_id = state.get("thread_id") or event.get("thread_id", "")

    config = load("onboarding")
    llm = get_llm()

    history = state.get("messages", [])
    logger.info(f"Onboarding: history has {len(history)} messages, business_id={business_id}")

    # Include memory context so agent knows what was collected in previous sessions
    memory_context = state.get("memory_context") or ""
    system_content = config.system_prompt
    if memory_context:
        system_content += "\n" + memory_context

    prompt = [{"role": "system", "content": system_content}]
    prompt.extend(history[-12:])
    prompt.append({"role": "user", "content": user_message})

    prompt = await trim_and_archive(prompt, business_id, thread_id)

    llm_response = await llm.ainvoke(prompt)
    raw = llm_response.content.strip()

    logger.info(f"Onboarding raw LLM output: {raw[:300]}")

    parsed = _parse_response(raw)
    text = parsed.get("response", raw)
    output_type = parsed.get("type", "answer")
    questions = parsed.get("questions")

    logger.info(f"Onboarding type={output_type}: {text[:80]}")

    response_data = {"mode": "conversation", "text": text}

    if questions:
        response_data["input"] = questions

    extracted = parsed.get("extracted")
    if extracted:
        response_data["extracted"] = extracted

    is_complete = parsed.get("status") == "complete"
    business_data = {}

    if is_complete:
        business_data = {
            "business_name": parsed.get("business_name", ""),
            "business_type": parsed.get("business_type", ""),
            "description": parsed.get("description", ""),
            "phone_number": parsed.get("phone_number", ""),
            "location": parsed.get("location", ""),
            "logo_url": parsed.get("logo", ""),
            "metadata": parsed.get("metadata", {}),
            "onboarding_complete": True,
        }
        response_data["business_data"] = business_data
        response_data["text"] = text

    result = {
        "response": response_data,
        "output_mode": "conversation",
        "routed_domain": None,
        "messages": [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": raw},
        ],
    }

    if is_complete:
        logo = business_data["logo_url"]
        result["tool_requests"] = [{
            "tool": "update_business_profile",
            "params": {
                "business_id": business_id,
                "name": business_data["business_name"],
                "category": business_data["business_type"],
                "description": business_data["description"],
                "phone": business_data["phone_number"],
                "location": business_data["location"],
                "logo_url": logo if isinstance(logo, str) and logo.startswith("http") else "",
                "onboarding_completed": True,
                "metadata": business_data["metadata"],
            }
        }]

    if output_type == "question" and questions:
        user_answer = interrupt({"text": text, "questions": questions, "extracted": extracted})
        formatted_answer = _format_user_answer(str(user_answer), questions)
        logger.info(f"Onboarding resumed with: {formatted_answer[:100]}")
        result["messages"] = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": raw},
            {"role": "user", "content": formatted_answer},
        ]
        result["event"] = {"text": formatted_answer, "thread_id": thread_id, "business_id": business_id}
        result["routed_domain"] = "onboarding"
        result["response"] = None

    return result


def _format_user_answer(answer: str, questions: dict) -> str:
    fields = questions.get("fields", [])
    if not fields:
        return answer

    field = fields[0]
    field_type = field.get("type", "")

    # Only add field context for radio selections (user clicked a specific option)
    if field_type == "radio":
        options = field.get("options", [])
        for opt in options:
            if opt.get("id") == answer:
                return f"user response: {answer}\nlabel name: {opt.get('name', '')}\nlabel description: {opt.get('description', '')}"
        # Not a known radio option — pass as-is (could be typed text)
        return answer

    # For text fields, just pass the raw answer — no wrapping needed
    return answer


def _parse_response(raw: str) -> dict:
    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        if clean.startswith("{"):
            depth = 0
            for i, ch in enumerate(clean):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return json.loads(clean[: i + 1])
        return json.loads(clean)
    except (json.JSONDecodeError, IndexError, ValueError):
        return {"response": raw, "type": "answer"}
