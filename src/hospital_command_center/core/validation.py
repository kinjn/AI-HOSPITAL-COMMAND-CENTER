"""Shared input validation helpers for patient intake."""

import re

from hospital_command_center.core.phone import validate_phone

_PATIENT_NAME_PATTERN = re.compile(r"^[A-Za-z\s'\-\.]+$")


def validate_patient_name(name: str) -> str:
    """Validate and return a normalized patient full name."""
    if not name or not name.strip():
        raise ValueError("Patient name is required.")

    cleaned = " ".join(name.split())

    if len(cleaned) < 2:
        raise ValueError("Patient name must be at least 2 characters.")

    if len(cleaned) > 100:
        raise ValueError("Patient name must not exceed 100 characters.")

    if not _PATIENT_NAME_PATTERN.fullmatch(cleaned):
        raise ValueError(
            "Patient name may only contain letters, spaces, hyphens, apostrophes, and periods."
        )

    parts = cleaned.split()
    if len(parts) < 2:
        raise ValueError("Please enter the patient's full name (first and last name).")

    return cleaned


__all__ = ["validate_patient_name", "validate_phone"]
