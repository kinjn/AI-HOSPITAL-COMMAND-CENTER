"""Case summary, suggested tests, and history extraction models."""

from uuid import UUID

from pydantic import BaseModel, Field


class MedicalSummary(BaseModel):
    encounter_id: UUID
    case_summary: str = Field(default="Stub case summary.")
    suggested_tests: list[str] = Field(default_factory=lambda: ["CBC", "Basic metabolic panel"])
    history_notes: str = Field(default="Stub history — no prior records loaded.")
    doctor_briefing: str = Field(default="Stub doctor briefing — not yet generated.")
