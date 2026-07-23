"""Triage agent: classifies symptom urgency via LLM, with optional clarifying questions."""

from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, model_validator

from hospital_command_center.agents.base import BaseAgent
from hospital_command_center.agents.structured_output import invoke_structured
from hospital_command_center.core.exceptions import NotConfiguredError, TriageError
from hospital_command_center.domain.triage import (
    MAX_CLARIFYING_QUESTIONS,
    TriageResult,
    TriageStatus,
    UrgencyLevel,
)
from hospital_command_center.prompts import load_prompt


class _TriageLLMOutput(BaseModel):
    status: TriageStatus
    urgency: UrgencyLevel | None = None
    rationale: str = Field(..., min_length=10, max_length=2000)
    clarifying_questions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_output(self) -> "_TriageLLMOutput":
        questions = [q.strip() for q in self.clarifying_questions if q and q.strip()][
            :MAX_CLARIFYING_QUESTIONS
        ]
        object.__setattr__(self, "clarifying_questions", questions)

        if self.status == TriageStatus.COMPLETE and self.urgency is None:
            raise ValueError("urgency is required when status is complete")
        if self.status == TriageStatus.NEEDS_CLARIFICATION and not questions:
            raise ValueError("clarifying_questions required when status is needs_clarification")
        return self


class TriageAgent(BaseAgent):
    name = "triage"

    def run(
        self,
        *,
        encounter_id: UUID,
        symptoms: str = "",
        patient_name: str | None = None,
        age: int | None = None,
        gender: str | None = None,
        phone: str | None = None,
        channel: str | None = None,
        patient_history: str | None = None,
        triage_conversation: list[dict[str, str]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not symptoms.strip():
            raise TriageError("Symptoms are required for triage classification.")

        user_lines = [f"Symptoms: {symptoms.strip()}"]
        if patient_history:
            user_lines.append(f"Prior visit history:\n{patient_history}")
        if patient_name:
            user_lines.append(f"Patient name: {patient_name}")
        if age is not None:
            user_lines.append(f"Age: {age}")
        if gender:
            user_lines.append(f"Gender: {gender}")
        if phone:
            user_lines.append(f"Contact: {phone}")
        if channel:
            user_lines.append(f"Intake channel: {channel}")

        system_prompt = load_prompt("triage")
        messages: list[SystemMessage | HumanMessage] = [SystemMessage(content=system_prompt)]

        for turn in triage_conversation or []:
            question = turn.get("question", "").strip()
            answer = (turn.get("answer") or "").strip()
            if question:
                messages.append(HumanMessage(content=f"Clarifying question: {question}"))
            if answer:
                messages.append(HumanMessage(content=f"Patient answer: {answer}"))

        messages.append(HumanMessage(content="\n".join(user_lines)))

        try:
            output = invoke_structured(_TriageLLMOutput, messages)
        except NotConfiguredError:
            raise
        except Exception as exc:
            raise TriageError(f"LLM triage classification failed: {exc}") from exc

        if output.status == TriageStatus.NEEDS_CLARIFICATION:
            result = TriageResult(
                encounter_id=encounter_id,
                status=TriageStatus.NEEDS_CLARIFICATION,
                rationale=output.rationale,
                clarifying_questions=output.clarifying_questions,
            )
        else:
            result = TriageResult(
                encounter_id=encounter_id,
                status=TriageStatus.COMPLETE,
                urgency=output.urgency,
                rationale=output.rationale,
            )
        return result.model_dump(mode="json")
