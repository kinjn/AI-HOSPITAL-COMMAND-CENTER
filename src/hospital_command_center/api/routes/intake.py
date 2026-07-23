"""Patient symptom submission endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.api.deps import db_session_dep, workflow_service_dep
from hospital_command_center.channels.mobile_app import MobileAppChannel
from hospital_command_center.channels.web import WebChannel
from hospital_command_center.domain.intake import IntakeSubmission
from hospital_command_center.services.workflow_service import WorkflowService

router = APIRouter(prefix="/intake", tags=["intake"])


@router.post("")
async def submit_intake(
    payload: IntakeSubmission,
    session: AsyncSession = Depends(db_session_dep),
    workflow: WorkflowService = Depends(workflow_service_dep),
) -> dict:
    """Generic intake — include `channel`, `patient_name`, `phone`, and `symptoms`."""
    return await workflow.start_from_intake(session, payload)


@router.post("/web")
async def submit_web_intake(
    raw: dict,
    session: AsyncSession = Depends(db_session_dep),
    workflow: WorkflowService = Depends(workflow_service_dep),
) -> dict:
    """Web form intake. Body: `{ "symptoms": "...", "patient_name": "...", "phone": "..." }`"""
    submission = WebChannel().to_intake(raw)
    return await workflow.start_from_intake(session, submission)


@router.post("/app")
async def submit_app_intake(
    raw: dict,
    session: AsyncSession = Depends(db_session_dep),
    workflow: WorkflowService = Depends(workflow_service_dep),
) -> dict:
    """Mobile app intake. Same JSON shape as `/web`."""
    submission = MobileAppChannel().to_intake(raw)
    return await workflow.start_from_intake(session, submission)
