"""Onboarding node — collects business profile info through structured conversation."""

import json
import logging

from langgraph.types import interrupt, Command

from app.llm.client import get_client as get_llm
from app.llm.specs import load
from app.models.state import GraphState

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ["business_name", "business_type", "description"]


async def onboarding_node(state: GraphState) -> dict:
    event = state.get("event", {})
    user_message = event.get("text", "")

    config = load("onboarding")
    llm = get_llm()

    history = state.get("messages", [])

    # Filter to only onboarding-relevant messages
    onboarding_history = []
    for msg in history:
        if msg.get("role") == "user":
            onboarding_history.append(msg)
        elif msg.get("role") == "assistant":
            content = msg.get("content", "")
            if content.startswith("{"):
                onboarding_history.append(msg)

    prompt = [{"role": "system", "content": config.system_prompt}]
    prompt.extend(onboarding_history[-12:])
    prompt.append({"role": "user", "content": user_message})

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

    if parsed.get("status") == "complete":
        response_data["onboarding_complete"] = True
        response_data["business_data"] = {
            "business_name": parsed.get("business_name", ""),
            "business_type": parsed.get("business_type", ""),
            "description": parsed.get("description", ""),
        }

    result = {
        "response": response_data,
        "output_mode": "conversation",
        "routed_domain": None,
        "messages": [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": raw},
        ],
    }

    # If we need user input, interrupt the graph — it will pause here
    # and resume when user responds
    if output_type == "question" and questions:
        user_answer = interrupt({"text": text, "questions": questions})
        # Graph resumes here with user's answer
        formatted_answer = _format_user_answer(str(user_answer), questions)
        logger.info(f"Onboarding resumed with: {formatted_answer[:100]}")
        result["messages"] = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": raw},
            {"role": "user", "content": formatted_answer},
        ]
        result["event"] = {"text": formatted_answer, "thread_id": event.get("thread_id"), "business_id": event.get("business_id")}
        # Keep routing to onboarding for the next step
        result["routed_domain"] = "onboarding"
        # Clear the response so MOA doesn't think we're done
        result["response"] = None

    return result


def _format_user_answer(answer: str, questions: dict) -> str:
    """Format user answer with field context for the agent."""
    fields = questions.get("fields", [])
    if not fields:
        return f"user response: {answer}"

    field = fields[0]
    field_type = field.get("type", "")

    if field_type == "text":
        name = field.get("name", "")
        description = field.get("description", "")
        return f"user response: {answer}\nlabel name: {name}\nlabel description: {description}"

    if field_type == "radio":
        options = field.get("options", [])
        for opt in options:
            if opt.get("id") == answer:
                return f"user response: {answer}\nlabel name: {opt.get('name', '')}\nlabel description: {opt.get('description', '')}"
        # If no exact match, still format with first option's name
        name = options[0].get("name", "") if options else ""
        return f"user response: {answer}\nlabel name: {name}\nlabel description: "

    return f"user response: {answer}"


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
