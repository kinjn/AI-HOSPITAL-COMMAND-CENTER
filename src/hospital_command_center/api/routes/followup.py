"""Follow-up schedule and escalation endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.api.deps import db_session_dep
from hospital_command_center.services.followup_service import FollowUpService

router = APIRouter(prefix="/followup", tags=["followup"])


@router.get("/{encounter_id}")
async def get_followup_plan(
    encounter_id: UUID,
    session: AsyncSession = Depends(db_session_dep),
) -> dict:
    # Uses the encounter's real triage/summary/intake data rather than
    # generating a plan with no context.
    plan = await FollowUpService().plan_from_encounter(encounter_id, session)
    return plan.model_dump(mode="json")


@router.post("/{encounter_id}/schedule")
async def schedule_followup_plan(
    encounter_id: UUID,
    session: AsyncSession = Depends(db_session_dep),
) -> dict:
    plan = await FollowUpService().plan_and_store_from_encounter(encounter_id, session)
    return plan.model_dump(mode="json")
