"""Helpers for structured LLM responses (Ollama-compatible fallback)."""

import json
import re
from typing import TypeVar

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, ValidationError

from hospital_command_center.agents.llm import get_chat_model, is_ollama_backend
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
    """Invoke LLM and parse response into a Pydantic model.

    Ollama's OpenAI-compatible endpoint rejects the strict `json_schema`
    response format with a 400, so against that backend we skip straight to
    the plain-text + manual-parse path below instead of paying for a
    round-trip that's guaranteed to fail on every call.
    """
    llm = get_chat_model()

    if not is_ollama_backend():
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
