"""Urgency classification and triage result models."""

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_CLARIFYING_QUESTIONS = 2


class UrgencyLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TriageStatus(StrEnum):
    COMPLETE = "complete"
    NEEDS_CLARIFICATION = "needs_clarification"


class TriageTurn(BaseModel):
    question: str
    answer: str | None = None


class TriageResult(BaseModel):
    encounter_id: UUID
    status: TriageStatus = TriageStatus.COMPLETE
    urgency: UrgencyLevel | None = None
    rationale: str = Field(default="Stub triage — not yet evaluated by LLM.")
    clarifying_questions: list[str] = Field(default_factory=list)

    @field_validator("clarifying_questions")
    @classmethod
    def _limit_questions(cls, value: list[str]) -> list[str]:
        cleaned = [q.strip() for q in value if q and q.strip()]
        return cleaned[:MAX_CLARIFYING_QUESTIONS]

    @model_validator(mode="after")
    def _validate_status_fields(self) -> "TriageResult":
        if self.status == TriageStatus.COMPLETE and self.urgency is None:
            raise ValueError("urgency is required when triage status is complete")
        if self.status == TriageStatus.NEEDS_CLARIFICATION and not self.clarifying_questions:
            raise ValueError("clarifying_questions required when status is needs_clarification")
        return self


class TriageClarificationSubmission(BaseModel):
    """Patient answers to pending triage clarifying questions (max 2)."""

    answers: list[str] = Field(..., min_length=1, max_length=MAX_CLARIFYING_QUESTIONS)

    @field_validator("answers")
    @classmethod
    def _answers_not_blank(cls, value: list[str]) -> list[str]:
        cleaned = [a.strip() for a in value if a and a.strip()]
        if not cleaned:
            raise ValueError("at least one non-empty answer is required")
        return cleaned


def parse_triage_conversation(raw: list[dict[str, Any]] | None) -> list[TriageTurn]:
    if not raw:
        return []
    return [TriageTurn.model_validate(item) for item in raw]
