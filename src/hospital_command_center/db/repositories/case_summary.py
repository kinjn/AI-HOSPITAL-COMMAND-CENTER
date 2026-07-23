"""Case summary repository — all DB operations for the case_summaries table."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.db.models.case_summary import CaseSummaryModel


class CaseSummaryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, case_summary: CaseSummaryModel) -> CaseSummaryModel:
        self.session.add(case_summary)
        await self.session.commit()
        await self.session.refresh(case_summary)
        return case_summary

    async def get_by_id(self, case_summary_id: str) -> CaseSummaryModel | None:
        result = await self.session.execute(
            select(CaseSummaryModel).where(CaseSummaryModel.id == case_summary_id)
        )
        return result.scalar_one_or_none()

    async def get_by_encounter_id(self, encounter_id: str) -> CaseSummaryModel | None:
        result = await self.session.execute(
            select(CaseSummaryModel).where(CaseSummaryModel.encounter_id == encounter_id)
        )
        return result.scalar_one_or_none()

    async def update(self, case_summary: CaseSummaryModel) -> CaseSummaryModel:
        await self.session.commit()
        await self.session.refresh(case_summary)
        return case_summary

    async def delete(self, case_summary: CaseSummaryModel) -> None:
        await self.session.delete(case_summary)
        await self.session.commit()