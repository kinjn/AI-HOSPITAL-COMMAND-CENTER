"""Patient repository — all DB operations for the patients table."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.core.phone import normalize_phone
from hospital_command_center.db.models.patient import PatientModel


class PatientRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, patient: PatientModel) -> PatientModel:
        self.session.add(patient)
        await self.session.commit()
        await self.session.refresh(patient)
        return patient

    async def get_by_id(self, patient_id: str) -> PatientModel | None:
        result = await self.session.execute(
            select(PatientModel).where(PatientModel.id == patient_id)
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> PatientModel | None:
        normalized = normalize_phone(phone)
        result = await self.session.execute(
            select(PatientModel).where(PatientModel.phone == normalized)
        )
        return result.scalar_one_or_none()

    async def get_by_name_and_phone(self, full_name: str, phone: str) -> PatientModel | None:
        normalized_phone = normalize_phone(phone)
        result = await self.session.execute(
            select(PatientModel).where(
                func.lower(PatientModel.full_name) == full_name.strip().lower(),
                PatientModel.phone == normalized_phone,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> PatientModel | None:
        result = await self.session.execute(
            select(PatientModel).where(PatientModel.email == email)
        )
        return result.scalar_one_or_none()

    async def update(self, patient: PatientModel) -> PatientModel:
        await self.session.commit()
        await self.session.refresh(patient)
        return patient

    async def delete(self, patient: PatientModel) -> None:
        await self.session.delete(patient)
        await self.session.commit()