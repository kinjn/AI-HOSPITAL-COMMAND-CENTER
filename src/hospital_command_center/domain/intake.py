"""Symptom submission and channel-specific intake payloads."""

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from hospital_command_center.core.validation import validate_patient_name, validate_phone


class IntakeChannel(StrEnum):
    WHATSAPP = "whatsapp"
    WEB = "web"
    MOBILE_APP = "mobile_app"


class IntakeSubmission(BaseModel):
    patient_id: UUID | None = None
    channel: IntakeChannel
    symptoms: str
    patient_name: str | None = None
    age: int | None = Field(default=None, ge=0, le=150)
    gender: str | None = None
    phone: str | None = None
    # Optional at intake time; the follow-up agent will ask for these before
    # giving any specific meal guidance if they're not supplied here.
    dietary_preference: str | None = None
    food_allergies: str | None = None
    # Optional; fed to the medical summarizer as prior clinical context
    # (e.g. "Type 2 diabetes, hypertension").
    known_medical_conditions: str | None = None
    id: UUID = Field(default_factory=uuid4)

    @field_validator("symptoms")
    @classmethod
    def symptoms_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("symptoms must not be empty")
        return value.strip()

    @field_validator("patient_name")
    @classmethod
    def patient_name_valid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_patient_name(value)

    @field_validator("phone")
    @classmethod
    def phone_valid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return validate_phone(value)
