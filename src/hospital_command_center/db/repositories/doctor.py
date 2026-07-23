"""Doctor repository — all DB operations for the doctors table."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.db.models.doctor import DoctorModel


class DoctorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, doctor: DoctorModel) -> DoctorModel:
        self.session.add(doctor)
        await self.session.commit()
        await self.session.refresh(doctor)
        return doctor

    async def get_by_id(self, doctor_id: str) -> DoctorModel | None:
        result = await self.session.execute(
            select(DoctorModel).where(DoctorModel.id == doctor_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[DoctorModel]:
        result = await self.session.execute(
            select(DoctorModel).order_by(DoctorModel.full_name)
        )
        return list(result.scalars().all())

    async def get_available(self) -> list[DoctorModel]:
        result = await self.session.execute(
            select(DoctorModel)
            .where(DoctorModel.is_available == True)  # noqa: E712
            .order_by(DoctorModel.full_name)
        )
        return list(result.scalars().all())

    async def get_by_specialization(self, specialization: str) -> list[DoctorModel]:
        result = await self.session.execute(
            select(DoctorModel)
            .where(DoctorModel.specialization == specialization)
            .order_by(DoctorModel.full_name)
        )
        return list(result.scalars().all())

    async def update(self, doctor: DoctorModel) -> DoctorModel:
        await self.session.commit()
        await self.session.refresh(doctor)
        return doctor

    async def delete(self, doctor: DoctorModel) -> None:
        await self.session.delete(doctor)
        await self.session.commit()