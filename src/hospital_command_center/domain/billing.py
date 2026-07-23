"""Insurance documentation and treatment cost estimate models."""

import re
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Code-normalization helpers
# ---------------------------------------------------------------------------

# ICD-10: letter(s) followed by digits, optional dot + more digits/letters
# Covers: R51.9, J06.9, I10, E11.9, R68.89, Z00.00, etc.
_ICD10_RE = re.compile(r"\b([A-Z][A-Z0-9]{0,2}(?:\.[A-Z0-9]{1,4})?)\b")

# CPT: exactly 5 consecutive digits
_CPT_RE = re.compile(r"\b(\d{5})\b")


def _extract_code(value: str, pattern: re.Pattern) -> str | None:
    """Return the first match of *pattern* in *value*, or None."""
    m = pattern.search(value.strip())
    return m.group(1) if m else None


def _normalize_codes(values: list[str], pattern: re.Pattern) -> list[str]:
    """Normalise a list of code strings.

    For each entry:
    - Extract the first code matching *pattern*.
    - Silently drop entries that contain no recognisable code.
    - Remove duplicates while preserving insertion order.
    """
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        code = _extract_code(str(raw), pattern)
        if code and code not in seen:
            seen.add(code)
            result.append(code)
    return result


class BillingStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class CostBreakdown(BaseModel):
    consultation_fee: Decimal = Field(default=Decimal("0.00"), ge=0)
    test_cost: Decimal = Field(default=Decimal("0.00"), ge=0)
    medication_cost: Decimal = Field(default=Decimal("0.00"), ge=0)
    miscellaneous_cost: Decimal = Field(default=Decimal("0.00"), ge=0)
    total: Decimal = Field(default=Decimal("0.00"), ge=0)

    @model_validator(mode="after")
    def sync_total(self) -> Self:
        computed = (
            self.consultation_fee
            + self.test_cost
            + self.medication_cost
            + self.miscellaneous_cost
        )
        object.__setattr__(self, "total", computed)
        return self


class InsuranceDocument(BaseModel):
    encounter_id: UUID
    document_type: str = Field(default="pre_authorization_request")
    reference_number: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    clinical_indication: str
    proposed_services: list[str] = Field(default_factory=list)
    estimated_amount_inr: Decimal = Field(ge=0)
    currency: str = "INR"
    icd10_codes: list[str] = Field(default_factory=list)
    cpt_codes: list[str] = Field(default_factory=list)

    @field_validator("icd10_codes", mode="before")
    @classmethod
    def normalize_icd10_codes(cls, values: list) -> list[str]:
        """Strip descriptions and deduplicate ICD-10 codes."""
        return _normalize_codes([str(v) for v in values], _ICD10_RE)

    @field_validator("cpt_codes", mode="before")
    @classmethod
    def normalize_cpt_codes(cls, values: list) -> list[str]:
        """Strip descriptions and deduplicate CPT codes."""
        return _normalize_codes([str(v) for v in values], _CPT_RE)
    coverage_notes: str = Field(default="Subject to policy terms and insurer review.")
    submission_instructions: str = Field(
        default="Attach clinical summary and itemized cost breakdown for pre-authorization."
    )


class BillingEstimate(BaseModel):
    encounter_id: UUID
    estimated_cost_inr: Decimal = Field(ge=0)
    currency: str = "INR"
    cost_breakdown: CostBreakdown
    insurance_documentation: str
    insurance_document: InsuranceDocument
    status: BillingStatus = BillingStatus.DRAFT

    @model_validator(mode="after")
    def sync_estimated_cost(self) -> Self:
        object.__setattr__(self, "estimated_cost_inr", self.cost_breakdown.total)
        return self
