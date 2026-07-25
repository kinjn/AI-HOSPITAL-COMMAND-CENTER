"""Patient symptom submission endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.api.deps import db_session_dep, workflow_service_dep
from hospital_command_center.channels.mobile_app import MobileAppChannel
from hospital_command_center.channels.web import WebChannel
from hospital_command_center.domain.intake import IntakeSubmission
from hospital_command_center.services.workflow_service import WorkflowService

router = APIRouter(prefix="/intake", tags=["intake"])


def _validation_detail(exc: ValidationError) -> list[dict]:
    """Flatten pydantic errors into the same shape FastAPI uses for its own
    422 responses, so the frontend's existing error handling works for both."""
    return [
        {"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]}
        for err in exc.errors()
    ]


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
    try:
        submission = WebChannel().to_intake(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_validation_detail(exc)) from exc
    return await workflow.start_from_intake(session, submission)


@router.post("/app")
async def submit_app_intake(
    raw: dict,
    session: AsyncSession = Depends(db_session_dep),
    workflow: WorkflowService = Depends(workflow_service_dep),
) -> dict:
    """Mobile app intake. Same JSON shape as `/web`."""
    try:
        submission = MobileAppChannel().to_intake(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_validation_detail(exc)) from exc
    return await workflow.start_from_intake(session, submission)
