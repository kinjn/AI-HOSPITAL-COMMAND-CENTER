"""Triage clarification endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.api.deps import db_session_dep, workflow_service_dep
from hospital_command_center.domain.triage import TriageClarificationSubmission
from hospital_command_center.services.workflow_service import WorkflowService

router = APIRouter(prefix="/triage", tags=["triage"])


@router.post("/encounters/{encounter_id}/clarify")
async def submit_triage_clarification(
    encounter_id: UUID,
    payload: TriageClarificationSubmission,
    session: AsyncSession = Depends(db_session_dep),
    workflow: WorkflowService = Depends(workflow_service_dep),
) -> dict:
    """Submit patient answers to pending triage clarifying questions (max 2)."""
    return await workflow.continue_triage(session, encounter_id, payload)
