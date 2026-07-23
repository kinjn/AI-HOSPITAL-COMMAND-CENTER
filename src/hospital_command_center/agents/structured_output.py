"""Helpers for structured LLM responses (Ollama-compatible fallback)."""

import json
import re
from typing import TypeVar

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, ValidationError

from hospital_command_center.agents.llm import get_chat_model
from hospital_command_center.core.exceptions import NotConfiguredError

T = TypeVar("T", bound=BaseModel)


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        return json.loads(fence.group(1).strip())

    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        return json.loads(brace.group(0))

    raise ValueError(f"No JSON object found in LLM response: {text[:200]}")


def invoke_structured(schema: type[T], messages: list[BaseMessage]) -> T:
    """Invoke LLM and parse response into a Pydantic model."""
    llm = get_chat_model()
    try:
        structured = llm.with_structured_output(schema, method="json_schema")
        return structured.invoke(messages)
    except NotConfiguredError:
        raise
    except (ValidationError, ValueError, json.JSONDecodeError):
        pass
    except Exception:
        pass

    raw = llm.invoke(messages)
    content = raw.content if isinstance(raw.content, str) else str(raw.content)
    return schema.model_validate(_extract_json(content))
