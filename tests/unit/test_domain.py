"""Unit tests for intake domain validation."""

import pytest
from pydantic import ValidationError

from hospital_command_center.core.validation import validate_patient_name
from hospital_command_center.domain.intake import IntakeChannel, IntakeSubmission


def test_intake_submission_accepts_valid_payload() -> None:
    payload = IntakeSubmission(
        channel=IntakeChannel.WEB,
        symptoms="Fever for 2 days",
        patient_name="Ravi Kumar",
        phone="9876543210",
        age=30,
        gender="male",
    )
    assert payload.phone == "9876543210"
    assert payload.patient_name == "Ravi Kumar"


@pytest.mark.parametrize(
    "phone",
    ["12345", "5876543210", "0123456789", "+1 555-0199"],
)
def test_intake_submission_rejects_invalid_phone(phone: str) -> None:
    with pytest.raises(ValidationError):
        IntakeSubmission(
            channel=IntakeChannel.WEB,
            symptoms="Fever for 2 days",
            patient_name="Ravi Kumar",
            phone=phone,
        )


@pytest.mark.parametrize(
    "name",
    ["", "Ravi", "Ravi123"],
)
def test_intake_submission_rejects_invalid_name(name: str) -> None:
    with pytest.raises(ValidationError):
        IntakeSubmission(
            channel=IntakeChannel.WEB,
            symptoms="Fever for 2 days",
            patient_name=name,
            phone="9876543210",
        )


def test_validate_patient_name_normalizes_whitespace() -> None:
    assert validate_patient_name("  Ravi   Kumar  ") == "Ravi Kumar"
