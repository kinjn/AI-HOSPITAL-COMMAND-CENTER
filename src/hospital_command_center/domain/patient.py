"""Patient identity, demographics, and contact models."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PatientBase(BaseModel):
    full_name: str
    phone: str | None = None
    email: str | None = None


class PatientCreate(PatientBase):
    pass


class Patient(PatientBase):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
