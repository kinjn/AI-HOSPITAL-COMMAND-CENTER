"""Channel webhooks (e.g. WhatsApp)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.api.deps import db_session_dep, workflow_service_dep
from hospital_command_center.channels.whatsapp import WhatsAppChannel
from hospital_command_center.services.workflow_service import WorkflowService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/whatsapp")
async def whatsapp_webhook(
    raw: dict,
    session: AsyncSession = Depends(db_session_dep),
    workflow: WorkflowService = Depends(workflow_service_dep),
) -> dict:
    """
    WhatsApp stub webhook (no Twilio yet).

    Example body:
    `{ "Body": "fever and cough", "From": "+919876543210", "patient_name": "Ravi" }`
    """
    submission = WhatsAppChannel().to_intake(raw)
    return await workflow.start_from_intake(session, submission)
