"""Encounter repository — all DB operations for the encounters table."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hospital_command_center.db.models.encounter import EncounterModel


class EncounterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, encounter: EncounterModel) -> EncounterModel:
        self.session.add(encounter)
        await self.session.commit()
        await self.session.refresh(encounter)
        return encounter
    
    async def list_all(self) -> list[EncounterModel]:
        result = await self.session.execute(
            select(EncounterModel).order_by(EncounterModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, encounter_id: str) -> EncounterModel | None:
        result = await self.session.execute(
            select(EncounterModel).where(EncounterModel.id == encounter_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_with_patient(self, encounter_id: str) -> EncounterModel | None:
        result = await self.session.execute(
            select(EncounterModel)
            .options(selectinload(EncounterModel.patient))
            .where(EncounterModel.id == encounter_id)
        )
        return result.scalar_one_or_none()

    async def get_by_patient_id(self, patient_id: str) -> list[EncounterModel]:
        result = await self.session.execute(
            select(EncounterModel)
            .where(EncounterModel.patient_id == patient_id)
            .order_by(EncounterModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_patient_history(
        self,
        patient_id: str,
        *,
        exclude_encounter_id: str | None = None,
        limit: int = 10,
    ) -> list[EncounterModel]:
        stmt = (
            select(EncounterModel)
            .options(
                selectinload(EncounterModel.triage_result),
                selectinload(EncounterModel.case_summary),
            )
            .where(EncounterModel.patient_id == patient_id)
            .order_by(EncounterModel.created_at.desc())
            .limit(limit)
        )
        if exclude_encounter_id:
            stmt = stmt.where(EncounterModel.id != exclude_encounter_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_status(self, status: str) -> list[EncounterModel]:
        result = await self.session.execute(
            select(EncounterModel)
            .where(EncounterModel.status == status)
            .order_by(EncounterModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_pathway(self, pathway: str) -> list[EncounterModel]:
        result = await self.session.execute(
            select(EncounterModel)
            .where(EncounterModel.pathway == pathway)
            .order_by(EncounterModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, encounter: EncounterModel) -> EncounterModel:
        await self.session.commit()
        await self.session.refresh(encounter)
        return encounter

    async def delete(self, encounter: EncounterModel) -> None:
        await self.session.delete(encounter)
        await self.session.commit()