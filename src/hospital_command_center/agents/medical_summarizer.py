"""Medical summarizer: case summary, tests, history extraction, doctor briefing."""

import json
import re
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from hospital_command_center.agents.base import BaseAgent
from hospital_command_center.agents.llm import get_chat_model
from hospital_command_center.core.exceptions import NotConfiguredError, SummarizationError
from hospital_command_center.domain.medical import MedicalSummary
from hospital_command_center.prompts import load_prompt

try:
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:  # pragma: no cover
    HumanMessage = None
    SystemMessage = None


class _MedicalSummaryLLMOutput(BaseModel):
    case_summary: str = Field(default="Summary not available.")
    suggested_tests: list[str] = Field(default_factory=list)
    history_notes: str = Field(default="No prior history on record.")
    doctor_briefing: str = Field(default="Doctor briefing not available.")

    @field_validator("case_summary", "history_notes", "doctor_briefing", mode="before")
    @classmethod
    def _coerce_to_text(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return "\n".join(f"{key}: {val}" for key, val in value.items())
        if isinstance(value, list):
            return "\n".join(str(item) for item in value)
        return value

    @field_validator("suggested_tests", mode="before")
    @classmethod
    def _coerce_tests(cls, value: Any) -> Any:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        if isinstance(value, list):
            flat = []
            seen: set[str] = set()
            for item in value:
                if isinstance(item, dict):
                    text = str(item.get("test") or item.get("name") or item)
                else:
                    text = str(item).strip()
                if not text:
                    continue
                key = text.casefold()
                if key in seen:
                    # Drop exact duplicates rather than letting them count against the cap.
                    continue
                seen.add(key)
                flat.append(text)
            # An empty list is a valid, deliberate clinical decision (no workup needed) —
            # cap the upper bound only, never force a minimum here.
            return flat[:4]
        return value


def _parse_llm_response(text: str) -> dict:
    """Robustly parse the LLM's JSON response, handling common local model quirks."""

    # Strip markdown code fences
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
        clean = clean.strip()

    # Try 1: direct parse
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    # Try 2: replace literal newlines inside string values
    fixed = re.sub(r'\n', '\\\\n', clean)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Try 3: extract each field individually with regex as last resort
    result: dict[str, Any] = {}

    m = re.search(r'"case_summary"\s*:\s*"(.*?)"(?=\s*,\s*")', clean, re.DOTALL)
    if m:
        result["case_summary"] = m.group(1).replace("\\n", "\n")

    m = re.search(r'"suggested_tests"\s*:\s*\[(.*?)\]', clean, re.DOTALL)
    if m:
        result["suggested_tests"] = re.findall(r'"([^"]+)"', m.group(1))

    m = re.search(r'"history_notes"\s*:\s*"(.*?)"(?=\s*,\s*")', clean, re.DOTALL)
    if m:
        result["history_notes"] = m.group(1).replace("\\n", "\n")

    m = re.search(r'"doctor_briefing"\s*:\s*"(.*?)"(?=\s*})', clean, re.DOTALL)
    if m:
        result["doctor_briefing"] = m.group(1).replace("\\n", "\n")

    if result:
        return result

    raise ValueError(f"Could not parse LLM response as JSON. Raw response: {text[:200]}")


class MedicalSummarizerAgent(BaseAgent):
    name = "medical_summarizer"

    def run(
        self,
        *,
        encounter_id: UUID,
        symptoms: str = "",
        urgency: str | None = None,
        triage_rationale: str | None = None,
        patient_name: str | None = None,
        age: int | None = None,
        gender: str | None = None,
        prior_history: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not symptoms.strip():
            return MedicalSummary(encounter_id=encounter_id).model_dump(mode="json")

        user_lines = [f"[Encounter: {encounter_id}]"]
        user_lines.append(f"Symptoms: {symptoms.strip()}")
        if patient_name:
            user_lines.append(f"Patient name: {patient_name}")
        if age is not None:
            user_lines.append(f"Age: {age}")
        if gender:
            user_lines.append(f"Gender: {gender}")
        if urgency:
            user_lines.append(f"Triage urgency: {urgency}")
        if triage_rationale:
            user_lines.append(f"Triage rationale: {triage_rationale}")
        if prior_history:
            user_lines.append(f"Prior medical history: {prior_history}")
        else:
            user_lines.append("Prior medical history: none on record (new patient).")

        system_prompt = load_prompt("medical_summarizer")
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="\n".join(user_lines)),
        ]

        try:
            llm = get_chat_model(max_tokens=2048)
            response = llm.invoke(messages)
            raw_text = response.content if hasattr(response, "content") else str(response)
            parsed = _parse_llm_response(raw_text)
            output = _MedicalSummaryLLMOutput(**parsed)

        except NotConfiguredError:
            raise
        except Exception as exc:
            raise SummarizationError(f"LLM medical summarization failed: {exc}") from exc

        # NOTE: an empty suggested_tests list from the LLM is a valid, deliberate
        # clinical decision (e.g. mild/self-limiting complaint needing no workup) —
        # it must NOT be replaced with the generic stub defaults (CBC, BMP, etc.).
        # Only genuinely missing/unparseable output should fall back to stub text.
        result = MedicalSummary(
            encounter_id=encounter_id,
            case_summary=output.case_summary,
            suggested_tests=output.suggested_tests,
            history_notes=output.history_notes,
            doctor_briefing=output.doctor_briefing,
        )
        return result.model_dump(mode="json")