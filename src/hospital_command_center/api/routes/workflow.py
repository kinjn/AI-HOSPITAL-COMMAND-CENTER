"""Workflow status and manual trigger endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends

from hospital_command_center.api.deps import workflow_service_dep
from hospital_command_center.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflow", tags=["workflow"])


@router.post("/run")
async def run_workflow(
    workflow: WorkflowService = Depends(workflow_service_dep),
    encounter_id: UUID | None = None,
) -> dict:
    return workflow.run_stub(encounter_id=encounter_id)
