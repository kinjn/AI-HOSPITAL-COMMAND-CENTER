"""Patient-facing endpoints, addressed by Tracking ID instead of internal ids.

This is the backend half of BACKEND_REQUIREMENTS.md from the Patient Portal.
It wraps the exact same business logic the Staff-Portal-facing routes use —
`WorkflowService.start_from_intake`, `WorkflowService.continue_triage`, and
the encounter detail assembly in `api/routes/encounters.py` — with no
changes to the AI workflow, LangGraph, or persistence logic. The only new
behavior is:

  1. Minting a short, unguessable Tracking ID (e.g. "HCC-83AF92") for a new
     encounter and returning that instead of the raw internal id.
  2. Resolving a Tracking ID back to an encounter for the clarify/lookup
     endpoints, so a patient never needs to know or handle the internal id.
  3. Returning an explicit allow-listed subset of fields — no internal
     database ids anywhere in these responses, ever.

Security model: possession of the exact Tracking ID is what grants access to
an encounter. There is no endpoint here that lists or enumerates encounters.
"""

import secrets
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.api.deps import db_session_dep, workflow_service_dep
from hospital_command_center.api.routes.encounters import apply_dietary_update, build_encounter_detail
from hospital_command_center.channels.web import WebChannel
from hospital_command_center.core.exceptions import IntakeError, NotConfiguredError, TriageError
from hospital_command_center.db.models.encounter import EncounterModel
from hospital_command_center.db.repositories.billing_record import BillingRecordRepository
from hospital_command_center.db.repositories.encounter import EncounterRepository
from hospital_command_center.domain.triage import TriageClarificationSubmission
from hospital_command_center.services.workflow_service import WorkflowService

router = APIRouter(prefix="/patient", tags=["patient"])

_TRACKING_ID_PREFIX = "HCC-"
_TRACKING_ID_MINT_ATTEMPTS = 10


def _generate_tracking_id() -> str:
    return f"{_TRACKING_ID_PREFIX}{secrets.token_hex(3).upper()}"


async def _mint_unique_tracking_id(repo: EncounterRepository) -> str:
    for _ in range(_TRACKING_ID_MINT_ATTEMPTS):
        candidate = _generate_tracking_id()
        if await repo.get_by_tracking_id(candidate) is None:
            return candidate
    # Astronomically unlikely with 16.7M possibilities, but fail loudly
    # rather than silently reuse/collide if it ever happens.
    raise IntakeError("Could not generate a unique Tracking ID. Please try again.")


def _tracking_submission_result(tracking_id: str, service_response: dict) -> dict:
    """Trim WorkflowService's response (built for the Staff Portal's
    intake/triage routes) down to what a patient should see: a Tracking ID
    instead of internal encounter_id/patient_id, no patient contact block
    (already collected once, at intake)."""
    encounter = service_response["encounter"]
    return {
        "tracking_id": tracking_id,
        "status": encounter["status"],
        "pathway": encounter["pathway"],
        "workflow_state": service_response["workflow_state"],
        "awaiting_triage_clarification": service_response["awaiting_triage_clarification"],
    }


def _patient_encounter_view(detail: dict, tracking_id: str) -> dict:
    """Build the patient-facing detail response by explicitly allow-listing
    fields from the full internal detail dict, rather than blocklisting ids.
    Allow-listing is the safer default here: a field added to
    build_encounter_detail() later stays hidden from patients unless someone
    deliberately adds it below, instead of leaking automatically."""
    patient = detail["patient"]
    return {
        "tracking_id": tracking_id,
        "patient": {
            "full_name": patient["full_name"],
            "phone": patient["phone"],
            "gender": patient["gender"],
        },
        "age": detail["age"],
        "symptoms": detail["symptoms"],
        "status": detail["status"],
        "pathway": detail["pathway"],
        "urgency": detail["urgency"],
        "created_at": detail["created_at"],
        "updated_at": detail["updated_at"],
        "triage": detail["triage"],
        "case_summary": detail["case_summary"],
        "billing_records": [{k: v for k, v in b.items() if k != "id"} for b in detail["billing_records"]],
        "followups": [{k: v for k, v in f.items() if k != "id"} for f in detail["followups"]],
        "timeline": detail["timeline"],
    }


@router.post("/intake")
async def submit_patient_intake(
    raw: dict,
    session: AsyncSession = Depends(db_session_dep),
    workflow: WorkflowService = Depends(workflow_service_dep),
) -> dict:
    """Same request body and behavior as POST /intake/web:
    `{ "symptoms": "...", "patient_name": "...", "age": ..., "gender": "...", "phone": "..." }`.
    Returns a Tracking ID instead of the raw internal encounter/patient ids.
    """
    try:
        submission = WebChannel().to_intake(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    result = await workflow.start_from_intake(session, submission)

    repo = EncounterRepository(session)
    encounter: EncounterModel | None = await repo.get_by_id(result["encounter"]["id"])
    if encounter is None:
        # Shouldn't happen — start_from_intake just created and persisted it.
        raise HTTPException(status_code=500, detail="Consultation was created but could not be retrieved.")

    tracking_id = await _mint_unique_tracking_id(repo)
    encounter.tracking_id = tracking_id
    await repo.update(encounter)

    return _tracking_submission_result(tracking_id, result)


@router.post("/encounter/{tracking_id}/clarify")
async def submit_patient_clarification(
    tracking_id: str,
    payload: TriageClarificationSubmission,
    session: AsyncSession = Depends(db_session_dep),
    workflow: WorkflowService = Depends(workflow_service_dep),
) -> dict:
    """Tracking-ID-addressed counterpart to
    POST /triage/encounters/{encounter_id}/clarify — same
    TriageClarificationSubmission body and continue_triage logic, just
    resolved via Tracking ID instead of a client-supplied internal id."""
    repo = EncounterRepository(session)
    # Use the eager-loading lookup (not the plain get_by_tracking_id) even
    # though we only need encounter.id here. Reason: this query and the one
    # continue_triage() runs internally (get_encounter_with_patient) share
    # the same AsyncSession, so the same row ends up in SQLAlchemy's
    # identity map for both. If this first query doesn't eager-load
    # `patient`, the object it returns to the identity map still has that
    # relationship unloaded — and continue_triage()'s later `encounter.patient`
    # access lazy-loads it, which isn't valid on an async session outside a
    # greenlet context and raises MissingGreenlet. Eager-loading it here
    # means it's already populated by the time continue_triage() reads it.
    encounter = await repo.get_by_tracking_id_with_relations(tracking_id)
    if encounter is None:
        raise HTTPException(status_code=404, detail="No consultation found for that Tracking ID.")

    try:
        result = await workflow.continue_triage(session, UUID(encounter.id), payload)
    except NotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except IntakeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TriageError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    return _tracking_submission_result(tracking_id, result)


class PatientDietaryUpdate(BaseModel):
    """Lets a patient confirm dietary preference / food allergies after
    their consultation, when the follow-up plan's diet guidance is still
    waiting on that ("Please confirm the patient's dietary preference...").
    Mirrors the Staff Portal's DietaryUpdate (api/routes/encounters.py)."""

    dietary_preference: str | None = None
    food_allergies: str | None = None


@router.patch("/encounter/{tracking_id}/dietary")
async def update_patient_dietary_preference(
    tracking_id: str,
    payload: PatientDietaryUpdate,
    session: AsyncSession = Depends(db_session_dep),
) -> dict:
    """Tracking-ID-addressed counterpart to the Staff Portal's
    PATCH /encounters/{id}/dietary — same apply_dietary_update() logic
    underneath, just resolved via Tracking ID and returning the
    patient-facing detail shape instead of the staff row shape."""
    repo = EncounterRepository(session)
    encounter = await repo.get_by_tracking_id_with_relations(tracking_id)
    if encounter is None:
        raise HTTPException(status_code=404, detail="No consultation found for that Tracking ID.")

    await apply_dietary_update(session, encounter, payload.dietary_preference, payload.food_allergies)
    await session.refresh(encounter, attribute_names=["followups"])

    detail = build_encounter_detail(encounter)
    return _patient_encounter_view(detail, tracking_id)


@router.post("/encounter/{tracking_id}/insurance-document/request")
async def request_insurance_document(
    tracking_id: str,
    session: AsyncSession = Depends(db_session_dep),
) -> dict:
    """Patient Portal's "Demand insurance document" button. Marks the
    encounter's latest billing record as having a pending insurance
    document request, for the Staff Portal to Accept or Reject. No document
    is generated here — the insurance document is already produced
    automatically during the billing step of the AI workflow; this just
    requests hospital sign-off before it's released to the patient.
    """
    repo = EncounterRepository(session)
    encounter = await repo.get_by_tracking_id_with_relations(tracking_id)
    if encounter is None:
        raise HTTPException(status_code=404, detail="No consultation found for that Tracking ID.")

    if not encounter.billing_records:
        raise HTTPException(
            status_code=400,
            detail="Your insurance document isn't ready yet. Please check back once billing is complete.",
        )

    latest_billing = max(encounter.billing_records, key=lambda b: b.created_at)
    if latest_billing.insurance_request_status == "requested":
        raise HTTPException(status_code=400, detail="Your insurance document request is already pending review.")
    if latest_billing.insurance_request_status == "approved":
        raise HTTPException(status_code=400, detail="Your insurance document has already been approved.")

    latest_billing.insurance_request_status = "requested"
    latest_billing.insurance_requested_at = datetime.utcnow()
    latest_billing.insurance_responded_at = None
    billing_repo = BillingRecordRepository(session)
    await billing_repo.update(latest_billing)

    detail = build_encounter_detail(encounter)
    return _patient_encounter_view(detail, tracking_id)


@router.get("/encounter/{tracking_id}")
async def get_patient_encounter(
    tracking_id: str,
    session: AsyncSession = Depends(db_session_dep),
) -> dict:
    """The only encounter-read endpoint the Patient Portal ever calls.
    Returns 404 for both "no such Tracking ID" and any other lookup
    failure — the two cases must be indistinguishable to the caller."""
    repo = EncounterRepository(session)
    encounter = await repo.get_by_tracking_id_with_relations(tracking_id)
    if encounter is None:
        raise HTTPException(status_code=404, detail="No consultation found for that Tracking ID.")

    detail = build_encounter_detail(encounter)
    return _patient_encounter_view(detail, tracking_id)
