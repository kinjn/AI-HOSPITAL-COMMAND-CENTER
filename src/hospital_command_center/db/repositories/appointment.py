"""Appointment repository — all DB operations for the appointments table."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.db.models.appointment import AppointmentModel


class AppointmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, appointment: AppointmentModel) -> AppointmentModel:
        self.session.add(appointment)
        await self.session.commit()
        await self.session.refresh(appointment)
        return appointment

    async def get_by_id(self, appointment_id: str) -> AppointmentModel | None:
        result = await self.session.execute(
            select(AppointmentModel).where(AppointmentModel.id == appointment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_patient_id(self, patient_id: str) -> list[AppointmentModel]:
        result = await self.session.execute(
            select(AppointmentModel)
            .where(AppointmentModel.patient_id == patient_id)
            .order_by(AppointmentModel.scheduled_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_encounter_id(self, encounter_id: str) -> list[AppointmentModel]:
        result = await self.session.execute(
            select(AppointmentModel)
            .where(AppointmentModel.encounter_id == encounter_id)
            .order_by(AppointmentModel.scheduled_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_doctor_id(self, doctor_id: str) -> list[AppointmentModel]:
        result = await self.session.execute(
            select(AppointmentModel)
            .where(AppointmentModel.doctor_id == doctor_id)
            .order_by(AppointmentModel.scheduled_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_status(self, status: str) -> list[AppointmentModel]:
        result = await self.session.execute(
            select(AppointmentModel)
            .where(AppointmentModel.status == status)
            .order_by(AppointmentModel.scheduled_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, appointment: AppointmentModel) -> AppointmentModel:
        await self.session.commit()
        await self.session.refresh(appointment)
        return appointment

    async def delete(self, appointment: AppointmentModel) -> None:
        await self.session.delete(appointment)
        await self.session.commit()