"""Follow-up repository — all DB operations for the followups table."""

from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.db.models.followup import FollowUpModel
from hospital_command_center.domain.followup import FollowUpPlan


class FollowUpRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, encounter_id: UUID, plan: FollowUpPlan) -> FollowUpModel:
        # Extract earliest scheduled task for the DB record
        scheduled_at = None
        if plan.schedule:
            scheduled_at = min(task.due_at for task in plan.schedule)

        record = FollowUpModel(
            encounter_id=str(encounter_id),
            plan_json=json.dumps(plan.model_dump(mode="json")),
            scheduled_at=scheduled_at,
            followup_type="comprehensive_plan",
        )
        self._session.add(record)
        await self._session.commit()
        await self._session.refresh(record)
        return record

    async def get_by_id(self, followup_id: str) -> FollowUpModel | None:
        result = await self._session.execute(
            select(FollowUpModel).where(FollowUpModel.id == followup_id)
        )
        return result.scalar_one_or_none()

    async def get_by_encounter_id(self, encounter_id: str) -> list[FollowUpModel]:
        result = await self._session.execute(
            select(FollowUpModel)
            .where(FollowUpModel.encounter_id == encounter_id)
            .order_by(FollowUpModel.scheduled_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_status(self, status: str) -> list[FollowUpModel]:
        result = await self._session.execute(
            select(FollowUpModel)
            .where(FollowUpModel.status == status)
            .order_by(FollowUpModel.scheduled_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_type(self, followup_type: str) -> list[FollowUpModel]:
        result = await self._session.execute(
            select(FollowUpModel)
            .where(FollowUpModel.followup_type == followup_type)
            .order_by(FollowUpModel.scheduled_at.asc())
        )
        return list(result.scalars().all())

    async def get_pending(self) -> list[FollowUpModel]:
        result = await self._session.execute(
            select(FollowUpModel)
            .where(FollowUpModel.status == "pending")
            .order_by(FollowUpModel.scheduled_at.asc())
        )
        return list(result.scalars().all())

    async def update(self, followup: FollowUpModel) -> FollowUpModel:
        await self._session.commit()
        await self._session.refresh(followup)
        return followup

    async def delete(self, followup: FollowUpModel) -> None:
        await self._session.delete(followup)
        await self._session.commit()