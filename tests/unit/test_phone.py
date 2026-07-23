"""Unit tests for phone number validation."""

import pytest

from hospital_command_center.core.phone import extract_mobile_digits, validate_phone


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("9876543210", "9876543210"),
        ("+91 98765 43210", "9876543210"),
        ("919876543210", "9876543210"),
        ("09876543210", "9876543210"),
        ("98765-43210", "9876543210"),
    ],
)
def test_validate_phone_accepts_valid_formats(raw: str, expected: str) -> None:
    assert validate_phone(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "12345",
        "12345678901",
        "5876543210",
        "0123456789",
        "abcdefghij",
        "+1 555-0199",
    ],
)
def test_validate_phone_rejects_invalid_numbers(raw: str) -> None:
    with pytest.raises(ValueError):
        validate_phone(raw)


def test_extract_mobile_digits_strips_country_code() -> None:
    assert extract_mobile_digits("+91 98765 43210") == "9876543210"
