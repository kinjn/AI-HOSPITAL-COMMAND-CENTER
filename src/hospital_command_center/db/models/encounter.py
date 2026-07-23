"""Encounter ORM model — one row per patient visit/submission."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hospital_command_center.db.base import Base


class EncounterModel(Base):
    __tablename__ = "encounters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("patients.id"), nullable=True)
    symptoms: Mapped[str] = mapped_column(Text, default="")
    source_channel: Mapped[str] = mapped_column(String(32), default="web")  # whatsapp | web | app

    # Workflow state: intake → triaged → routed → summary_ready → billing_ready → closed
    status: Mapped[str] = mapped_column(String(32), default="intake")

    # Set after triage: emergency | opd | teleconsult | specialist
    pathway: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Serialized triage Q&A while awaiting patient clarification
    triage_conversation_json: Mapped[str] = mapped_column(Text, default="[]")

    # Intake demographics for workflow resume (age is not on patients table)
    intake_context_json: Mapped[str] = mapped_column(Text, default="{}")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, onupdate=datetime.utcnow)

    # Relationships
    patient: Mapped["PatientModel | None"] = relationship("PatientModel", back_populates="encounters")
    triage_result: Mapped["TriageResultModel | None"] = relationship("TriageResultModel", back_populates="encounter", uselist=False)
    case_summary: Mapped["CaseSummaryModel | None"] = relationship("CaseSummaryModel", back_populates="encounter", uselist=False)
    billing_records: Mapped[list["BillingRecordModel"]] = relationship("BillingRecordModel", back_populates="encounter", lazy="select")
    appointments: Mapped[list["AppointmentModel"]] = relationship("AppointmentModel", back_populates="encounter", lazy="select")
    followups: Mapped[list["FollowUpModel"]] = relationship("FollowUpModel", back_populates="encounter", lazy="select")