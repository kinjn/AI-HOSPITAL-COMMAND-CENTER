"""Care pathway enums and routing decision models."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class CarePathway(StrEnum):
    EMERGENCY = "emergency"
    OPD = "opd"
    TELECONSULTATION = "teleconsultation"
    SPECIALIST_REFERRAL = "specialist_referral"


class RoutingDecision(BaseModel):
    encounter_id: UUID
    pathway: CarePathway = CarePathway.OPD
    notes: str = Field(default="Routing decision pending.")
