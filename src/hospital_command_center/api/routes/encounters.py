"""Encounter queries for the operations dashboard.

`list_encounters` and `get_encounter` were previously a stub that returned
only id/patient_id/status/pathway — not enough to render an operations
dashboard (patient name, age, urgency, billing status, follow-up due dates).
This fleshes out the read side only: no business logic, workflow, or
persistence behavior changes. All fields below are read directly from rows
already written by the existing workflow/persistence services.
"""

import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.api.deps import db_session_dep
from hospital_command_center.db.models.encounter import EncounterModel
from hospital_command_center.db.repositories.billing_record import BillingRecordRepository
from hospital_command_center.db.repositories.encounter import EncounterRepository
from hospital_command_center.services.followup_service import FollowUpService

router = APIRouter(prefix="/encounters", tags=["encounters"])


def _age_from_intake(encounter: EncounterModel) -> int | None:
    try:
        ctx = json.loads(encounter.intake_context_json or "{}")
    except json.JSONDecodeError:
        return None
    age = ctx.get("age")
    return int(age) if isinstance(age, (int, float)) else None


def _insurance_document(record) -> dict | None:
    """`insurance_doc_json` is persisted as
    `{"documentation": <narrative str>, "document": <InsuranceDocument fields>,
    "cost_breakdown": {...}}` — unwrap `.document` and fold the narrative in
    as `documentation` so the frontend gets a flat, usable object."""
    try:
        blob = json.loads(record.insurance_doc_json or "{}")
    except json.JSONDecodeError:
        return None
    document = blob.get("document")
    if not document:
        return None
    return {**document, "documentation": blob.get("documentation")}


def _latest_billing(encounter: EncounterModel) -> dict | None:
    if not encounter.billing_records:
        return None
    latest = max(encounter.billing_records, key=lambda b: b.created_at)
    return {
        "id": latest.id,
        "estimated_cost": float(latest.estimated_cost) if latest.estimated_cost is not None else None,
        "currency": latest.currency,
        "status": latest.status,
        "insurance_provider": latest.insurance_provider,
        "insurance_request_status": latest.insurance_request_status,
        "insurance_requested_at": latest.insurance_requested_at.isoformat()
        if latest.insurance_requested_at
        else None,
        "insurance_responded_at": latest.insurance_responded_at.isoformat()
        if latest.insurance_responded_at
        else None,
        "created_at": latest.created_at.isoformat() if latest.created_at else None,
    }


def _latest_followup(encounter: EncounterModel) -> dict | None:
    if not encounter.followups:
        return None
    latest = max(encounter.followups, key=lambda f: f.created_at)
    return {
        "id": latest.id,
        "status": latest.status,
        "followup_type": latest.followup_type,
        "scheduled_at": latest.scheduled_at.isoformat() if latest.scheduled_at else None,
        "created_at": latest.created_at.isoformat() if latest.created_at else None,
    }


def _serialize_row(encounter: EncounterModel) -> dict:
    patient = encounter.patient
    triage = encounter.triage_result
    return {
        "id": encounter.id,
        "patient": {
            "id": patient.id if patient else None,
            "full_name": patient.full_name if patient else "Unknown patient",
            "phone": patient.phone if patient else None,
            "gender": patient.gender if patient else None,
        },
        "age": _age_from_intake(encounter),
        "symptoms": encounter.symptoms,
        "status": encounter.status,
        "pathway": encounter.pathway,
        "source_channel": encounter.source_channel,
        "urgency": triage.urgency_level if triage else None,
        "created_at": encounter.created_at.isoformat() if encounter.created_at else None,
        "updated_at": encounter.updated_at.isoformat() if encounter.updated_at else None,
        "billing": _latest_billing(encounter),
        "followup": _latest_followup(encounter),
    }


@router.get("")
async def list_encounters(
    session: AsyncSession = Depends(db_session_dep),
) -> dict:
    repo = EncounterRepository(session)
    rows = await repo.list_all_with_relations()
    return {"items": [_serialize_row(r) for r in rows]}


def build_encounter_detail(encounter: EncounterModel) -> dict:
    """Full detail payload for a single encounter: everything `_serialize_row`
    returns, plus triage reasoning, medical summary, billing records,
    follow-up plans, and a timeline.

    Extracted from `get_encounter` (previously inline there) so it can be
    reused by the Patient Portal's `GET /patient/encounter/{tracking_id}`
    (api/routes/patient.py) without duplicating this logic. Output is
    unchanged for the existing `/encounters/{id}` route below.
    """
    triage = encounter.triage_result
    summary = encounter.case_summary
    billing_records = sorted(encounter.billing_records, key=lambda b: b.created_at)
    followups = sorted(encounter.followups, key=lambda f: f.created_at)

    def _dt(value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    timeline = [{"stage": "intake", "label": "Intake", "at": _dt(encounter.created_at)}]
    if triage:
        timeline.append({"stage": "triage", "label": "Triage & routing", "at": _dt(triage.created_at)})
    if summary:
        timeline.append({"stage": "medical_summary", "label": "Medical summary", "at": _dt(summary.created_at)})
    if billing_records:
        timeline.append({"stage": "billing", "label": "Billing", "at": _dt(billing_records[0].created_at)})
    if followups:
        timeline.append({"stage": "followup", "label": "Follow-up", "at": _dt(followups[0].created_at)})

    row = _serialize_row(encounter)
    row.update(
        {
            "triage": {
                "urgency_level": triage.urgency_level,
                "suggested_pathway": triage.suggested_pathway,
                "reasoning": triage.reasoning,
            }
            if triage
            else None,
            "case_summary": {
                "summary_text": summary.summary_text,
                "suggested_tests": json.loads(summary.suggested_tests_json or "[]"),
                "extracted_history": summary.extracted_history,
                "doctor_notes": summary.doctor_notes,
            }
            if summary
            else None,
            "billing_records": [
                {
                    "id": b.id,
                    "estimated_cost": float(b.estimated_cost) if b.estimated_cost is not None else None,
                    "currency": b.currency,
                    "consultation_fee": float(b.consultation_fee),
                    "test_cost": float(b.test_cost),
                    "medication_cost": float(b.medication_cost),
                    "misc_cost": float(b.misc_cost),
                    "preauth_reference": b.preauth_reference,
                    "icd10_codes": json.loads(b.icd10_codes_json or "[]"),
                    "cpt_codes": json.loads(b.cpt_codes_json or "[]"),
                    "insurance_provider": b.insurance_provider,
                    "insurance_document": _insurance_document(b),
                    "status": b.status,
                    "insurance_request_status": b.insurance_request_status,
                    "insurance_requested_at": b.insurance_requested_at.isoformat()
                    if b.insurance_requested_at
                    else None,
                    "insurance_responded_at": b.insurance_responded_at.isoformat()
                    if b.insurance_responded_at
                    else None,
                    "created_at": _dt(b.created_at),
                }
                for b in billing_records
            ],
            "followups": [
                {
                    "id": f.id,
                    "followup_type": f.followup_type,
                    "status": f.status,
                    "plan": json.loads(f.plan_json or "{}"),
                    "scheduled_at": _dt(f.scheduled_at),
                    "created_at": _dt(f.created_at),
                }
                for f in followups
            ],
            "timeline": timeline,
        }
    )
    return row


@router.get("/{encounter_id}")
async def get_encounter(
    encounter_id: str,
    session: AsyncSession = Depends(db_session_dep),
) -> dict:
    repo = EncounterRepository(session)
    encounter = await repo.get_by_id_with_relations(encounter_id)
    if encounter is None:
        raise HTTPException(status_code=404, detail=f"Encounter {encounter_id} not found.")
    return build_encounter_detail(encounter)


class DietaryUpdate(BaseModel):
    """Lets staff supply dietary preference/allergies after intake, for
    encounters where the patient didn't provide it up front — the intake
    form only asked once, with no way to add it later otherwise."""

    dietary_preference: str | None = None
    food_allergies: str | None = None


async def apply_dietary_update(
    session: AsyncSession,
    encounter: EncounterModel,
    dietary_preference: str | None,
    food_allergies: str | None,
) -> None:
    """Shared by the Staff Portal's PATCH /encounters/{id}/dietary and the
    Patient Portal's PATCH /patient/encounter/{tracking_id}/dietary
    (api/routes/patient.py). Updates the stored intake context and
    regenerates the follow-up plan so the new preference actually surfaces
    in diet guidance, instead of being saved but never used.

    Mutates `encounter` in place and commits. The new follow-up plan is
    persisted through a separate repository call that does NOT update this
    `encounter` object's already-loaded `followups` collection in memory —
    callers that need an up-to-date `followups` list for a response must
    explicitly `await session.refresh(encounter, attribute_names=["followups"])`
    afterward (see the two callers below). A second full re-query of the row
    instead of a targeted refresh() was the original code's approach here,
    and is what caused a MissingGreenlet crash in the sibling clarify
    endpoint's equivalent pattern — refresh() is the awaited, async-safe way
    to repopulate a specific relationship on an object already in the
    session's identity map.
    """
    try:
        intake_context = json.loads(encounter.intake_context_json or "{}")
    except json.JSONDecodeError:
        intake_context = {}

    if dietary_preference is not None:
        intake_context["dietary_preference"] = dietary_preference
    if food_allergies is not None:
        intake_context["food_allergies"] = food_allergies
    encounter.intake_context_json = json.dumps(intake_context)
    await session.commit()

    # Regenerate and store a fresh follow-up plan so the update actually
    # shows up — the follow-up agent only runs at intake time otherwise,
    # so without this the new dietary info would be saved but never used.
    followup_service = FollowUpService()
    await followup_service.plan_and_store_from_encounter(UUID(encounter.id), session)


@router.patch("/{encounter_id}/dietary")
async def update_dietary_preference(
    encounter_id: str,
    payload: DietaryUpdate,
    session: AsyncSession = Depends(db_session_dep),
) -> dict:
    repo = EncounterRepository(session)
    encounter = await repo.get_by_id_with_relations(encounter_id)
    if encounter is None:
        raise HTTPException(status_code=404, detail=f"Encounter {encounter_id} not found.")

    await apply_dietary_update(session, encounter, payload.dietary_preference, payload.food_allergies)
    await session.refresh(encounter, attribute_names=["followups"])

    return _serialize_row(encounter)


@router.post("/{encounter_id}/billing/approve")
async def approve_billing(
    encounter_id: str,
    session: AsyncSession = Depends(db_session_dep),
) -> dict:
    """Marks the encounter's latest billing record as approved and closes
    the encounter — the only place in the app that ever sets
    `status = "closed"` (see encounter_persistence.persist_workflow_state,
    which deliberately stops at "billing_ready" once a follow-up plan is
    generated, precisely so this manual approval step is what closes it).

    Shared by both portals in spirit: the Staff Portal calls this directly;
    the Patient Portal's encounter view reflects the same `status` and
    `billing_records[*].status` fields the next time it polls, since both
    portals read from the same encounter row via `build_encounter_detail`.
    """
    repo = EncounterRepository(session)
    encounter = await repo.get_by_id_with_relations(encounter_id)
    if encounter is None:
        raise HTTPException(status_code=404, detail=f"Encounter {encounter_id} not found.")

    if not encounter.billing_records:
        raise HTTPException(status_code=400, detail="This encounter has no billing estimate to approve yet.")

    latest_billing = max(encounter.billing_records, key=lambda b: b.created_at)
    latest_billing.status = "approved"
    billing_repo = BillingRecordRepository(session)
    await billing_repo.update(latest_billing)

    encounter.status = "closed"
    encounter.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(encounter, attribute_names=["billing_records"])

    return build_encounter_detail(encounter)


async def _respond_to_insurance_request(
    encounter_id: str,
    session: AsyncSession,
    *,
    new_status: str,
) -> EncounterModel:
    """Shared logic for the staff portal's Accept/Reject buttons on a
    patient's "Demand insurance document" request. `new_status` is either
    "approved" (document becomes visible/downloadable to the patient) or
    "rejected" (patient sees a rejection message instead).
    """
    repo = EncounterRepository(session)
    encounter = await repo.get_by_id_with_relations(encounter_id)
    if encounter is None:
        raise HTTPException(status_code=404, detail=f"Encounter {encounter_id} not found.")

    if not encounter.billing_records:
        raise HTTPException(status_code=400, detail="This encounter has no insurance document yet.")

    latest_billing = max(encounter.billing_records, key=lambda b: b.created_at)
    if latest_billing.insurance_request_status != "requested":
        raise HTTPException(
            status_code=400,
            detail="There is no pending insurance document request for this encounter.",
        )

    latest_billing.insurance_request_status = new_status
    latest_billing.insurance_responded_at = datetime.utcnow()
    billing_repo = BillingRecordRepository(session)
    await billing_repo.update(latest_billing)

    return encounter


@router.post("/{encounter_id}/insurance-document/accept")
async def accept_insurance_document_request(
    encounter_id: str,
    session: AsyncSession = Depends(db_session_dep),
) -> dict:
    """Staff Portal: accept a patient's pending "Demand insurance document"
    request. The document then becomes visible and downloadable on the
    Patient Portal."""
    encounter = await _respond_to_insurance_request(encounter_id, session, new_status="approved")
    return build_encounter_detail(encounter)


@router.post("/{encounter_id}/insurance-document/reject")
async def reject_insurance_document_request(
    encounter_id: str,
    session: AsyncSession = Depends(db_session_dep),
) -> dict:
    """Staff Portal: reject a patient's pending "Demand insurance document"
    request. The Patient Portal then shows a rejection message instead of
    the document."""
    encounter = await _respond_to_insurance_request(encounter_id, session, new_status="rejected")
    return build_encounter_detail(encounter)
