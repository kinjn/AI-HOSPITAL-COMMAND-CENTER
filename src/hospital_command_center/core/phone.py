"""Phone number normalization and validation for patient intake."""

INDIAN_MOBILE_LENGTH = 10
INDIAN_MOBILE_FIRST_DIGITS = frozenset("6789")


def extract_mobile_digits(phone: str) -> str:
    """Extract digits from a phone string, stripping an optional +91/91 prefix."""
    cleaned = phone.strip()
    if cleaned.startswith("+"):
        digits = "".join(c for c in cleaned[1:] if c.isdigit())
    else:
        digits = "".join(c for c in cleaned if c.isdigit())

    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        return digits[1:]
    return digits


def validate_phone(phone: str) -> str:
    """Validate and return a normalized 10-digit Indian mobile number."""
    if not phone or not phone.strip():
        raise ValueError("Phone number is required.")

    digits = extract_mobile_digits(phone)

    if len(digits) != INDIAN_MOBILE_LENGTH:
        raise ValueError("Phone number must be exactly 10 digits.")

    if digits[0] not in INDIAN_MOBILE_FIRST_DIGITS:
        raise ValueError("Phone number must start with 6, 7, 8, or 9.")

    return digits


def normalize_phone(phone: str) -> str:
    """Normalize a phone number for storage and lookup."""
    return validate_phone(phone)
