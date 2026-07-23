"""Shared TypedDict state for the patient care graph."""

from typing import Any, TypedDict


class PatientWorkflowState(TypedDict, total=False):
    encounter_id: str
    symptoms: str
    patient_name: str
    age: int
    gender: str
    phone: str
    channel: str
    patient_history: str
    triage_conversation: list[dict[str, Any]]
    dietary_preference: str
    food_allergies: str
    message: str
    triage: dict
    routing: dict
    medical_summary: dict
    billing: dict
    followup: dict
