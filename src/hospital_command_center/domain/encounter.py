"""End-to-end encounter aggregate linking intake through follow-up."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from hospital_command_center.domain.workflow import CarePathway


class EncounterStatus(StrEnum):
    INTAKE = "intake"
    TRIAGED = "triaged"
    ROUTED = "routed"
    SUMMARIZED = "summarized"
    BILLED = "billed"
    FOLLOW_UP_SCHEDULED = "follow_up_scheduled"
    COMPLETED = "completed"


class Encounter(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    patient_id: UUID | None = None
    symptoms: str = ""
    status: EncounterStatus = EncounterStatus.INTAKE
    pathway: CarePathway | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
