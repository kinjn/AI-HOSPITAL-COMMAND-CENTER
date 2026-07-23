"""Triage result ORM model — LLM urgency classification output."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hospital_command_center.db.base import Base


class TriageResultModel(Base):
    __tablename__ = "triage_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    encounter_id: Mapped[str] = mapped_column(String(36), ForeignKey("encounters.id"))

    # low | medium | high | critical
    urgency_level: Mapped[str] = mapped_column(String(32))

    # emergency | opd | teleconsult | specialist
    suggested_pathway: Mapped[str] = mapped_column(String(32))

    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)         # LLM explanation
    raw_llm_response: Mapped[str | None] = mapped_column(Text, nullable=True)  # full output for audit

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    encounter: Mapped["EncounterModel"] = relationship("EncounterModel", back_populates="triage_result")