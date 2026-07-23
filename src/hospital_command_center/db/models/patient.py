"""Patient ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hospital_command_center.db.base import Base


class PatientModel(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[str | None] = mapped_column(String(16), nullable=True)  # YYYY-MM-DD
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)         # male | female | other
    source_channel: Mapped[str] = mapped_column(String(32), default="web")        # whatsapp | web | app
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    encounters: Mapped[list["EncounterModel"]] = relationship("EncounterModel", back_populates="patient", lazy="select")
    appointments: Mapped[list["AppointmentModel"]] = relationship("AppointmentModel", back_populates="patient", lazy="select")