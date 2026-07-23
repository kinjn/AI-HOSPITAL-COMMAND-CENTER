"""Appointment ORM model — links patient, doctor, and encounter."""
# encounter_id is nullable because some appointments (e.g. walk-ins, direct teleconsults) may be booked before an encounter is created. patient_id is kept as a direct FK for this reason — do not remove it.
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hospital_command_center.db.base import Base


class AppointmentModel(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"))
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("doctors.id"))
    encounter_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("encounters.id"), nullable=True)

    # opd | teleconsult | specialist
    appointment_type: Mapped[str] = mapped_column(String(32))

    scheduled_at: Mapped[datetime] = mapped_column(DateTime)

    # scheduled | completed | cancelled | no_show
    status: Mapped[str] = mapped_column(String(32), default="scheduled")

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    patient: Mapped["PatientModel"] = relationship("PatientModel", back_populates="appointments")
    doctor: Mapped["DoctorModel"] = relationship("DoctorModel", back_populates="appointments")
    encounter: Mapped["EncounterModel | None"] = relationship("EncounterModel", back_populates="appointments")