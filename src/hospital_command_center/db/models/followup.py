"""Follow-up and reminder ORM model.

One encounter can produce multiple follow-up rows — one per reminder cycle.
Covers: medication reminders, lab reminders, diet guidance, escalation checks.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hospital_command_center.db.base import Base


class FollowUpModel(Base):
    __tablename__ = "followups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    encounter_id: Mapped[str] = mapped_column(String(36), ForeignKey("encounters.id"))

    # medication | lab | diet | escalation
    followup_type: Mapped[str] = mapped_column(String(32), default="medication")

    # Full reminder plan — items, message text, delivery channel
    plan_json: Mapped[str] = mapped_column(Text, default="{}")

    # pending → sent → acknowledged → escalated | done
    status: Mapped[str] = mapped_column(String(32), default="pending")

    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    encounter: Mapped["EncounterModel"] = relationship("EncounterModel", back_populates="followups")