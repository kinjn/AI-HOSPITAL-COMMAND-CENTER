"""Case summary ORM model — medical summarizer agent output."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hospital_command_center.db.base import Base


class CaseSummaryModel(Base):
    __tablename__ = "case_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    encounter_id: Mapped[str] = mapped_column(String(36), ForeignKey("encounters.id"))

    summary_text: Mapped[str] = mapped_column(Text, default="")
    suggested_tests_json: Mapped[str] = mapped_column(Text, default="[]")   # JSON array: ["CBC", "ECG"]
    extracted_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    doctor_notes: Mapped[str | None] = mapped_column(Text, nullable=True)   # added by reviewing doctor

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    encounter: Mapped["EncounterModel"] = relationship("EncounterModel", back_populates="case_summary")