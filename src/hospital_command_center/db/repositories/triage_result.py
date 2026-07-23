"""Triage result repository — all DB operations for the triage_results table."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.db.models.triage_result import TriageResultModel


class TriageResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, triage_result: TriageResultModel) -> TriageResultModel:
        self.session.add(triage_result)
        await self.session.commit()
        await self.session.refresh(triage_result)
        return triage_result

    async def get_by_id(self, triage_result_id: str) -> TriageResultModel | None:
        result = await self.session.execute(
            select(TriageResultModel).where(TriageResultModel.id == triage_result_id)
        )
        return result.scalar_one_or_none()

    async def get_by_encounter_id(self, encounter_id: str) -> TriageResultModel | None:
        result = await self.session.execute(
            select(TriageResultModel).where(TriageResultModel.encounter_id == encounter_id)
        )
        return result.scalar_one_or_none()

    async def get_by_urgency_level(self, urgency_level: str) -> list[TriageResultModel]:
        result = await self.session.execute(
            select(TriageResultModel)
            .where(TriageResultModel.urgency_level == urgency_level)
            .order_by(TriageResultModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, triage_result: TriageResultModel) -> TriageResultModel:
        await self.session.commit()
        await self.session.refresh(triage_result)
        return triage_result

    async def delete(self, triage_result: TriageResultModel) -> None:
        await self.session.delete(triage_result)
        await self.session.commit()