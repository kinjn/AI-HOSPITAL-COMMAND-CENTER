"""Billing and insurance ORM model.

1-to-many with encounters — one encounter can produce multiple billing
entries (initial estimate → revised after tests → insurance claim → final invoice).
patient_id removed; reach patient via encounter.patient instead.
"""
from __future__ import annotations

from decimal import Decimal
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hospital_command_center.db.base import Base

if TYPE_CHECKING:
    from hospital_command_center.db.models.encounter import EncounterModel


class BillingRecordModel(Base):
    __tablename__ = "billing_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    encounter_id: Mapped[str] = mapped_column(String(36), ForeignKey("encounters.id"))

    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="INR")

    # --- Itemized cost columns (normalized from cost_breakdown) ---
    consultation_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    test_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    medication_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    misc_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))

    # --- Pre-authorization reference (indexed, nullable, NOT unique:
    #     one encounter may produce multiple billing records) ---
    preauth_reference: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # --- Serialized clinical code lists ---
    icd10_codes_json: Mapped[str] = mapped_column(Text, default="[]")
    cpt_codes_json: Mapped[str] = mapped_column(Text, default="[]")

    insurance_provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    insurance_doc_json: Mapped[str] = mapped_column(Text, default="{}")  # full insurance doc blob

    # draft | submitted | approved | rejected
    status: Mapped[str] = mapped_column(String(32), default="draft")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    encounter: Mapped[EncounterModel] = relationship(
        "EncounterModel", back_populates="billing_records"
    )