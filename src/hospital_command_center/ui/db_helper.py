"""Asynchronous database helpers for the Streamlit frontend.

Queries and updates encounters, patients, and agent results for the Command Center.
"""

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID
from typing import Any

from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.db.session import get_session_factory
from hospital_command_center.db.models.encounter import EncounterModel
from hospital_command_center.db.models.patient import PatientModel
from hospital_command_center.db.models.triage_result import TriageResultModel
from hospital_command_center.db.models.case_summary import CaseSummaryModel
from hospital_command_center.db.models.billing_record import BillingRecordModel
from hospital_command_center.db.models.followup import FollowUpModel


async def fetch_dashboard_stats() -> dict[str, Any]:
    """Calculate key performance indicators from the database."""
    factory = get_session_factory()
    async with factory() as session:
        # Total encounters
        total_stmt = select(func.count(EncounterModel.id))
        total_res = await session.execute(total_stmt)
        total_count = total_res.scalar() or 0

        # Active encounters (status != closed)
        active_stmt = select(func.count(EncounterModel.id)).where(EncounterModel.status != "closed")
        active_res = await session.execute(active_stmt)
        active_count = active_res.scalar() or 0

        # Critical / High urgency encounters
        critical_stmt = (
            select(func.count(EncounterModel.id))
            .join(TriageResultModel, EncounterModel.id == TriageResultModel.encounter_id)
            .where(
                or_(
                    func.lower(TriageResultModel.urgency_level) == "critical",
                    func.lower(TriageResultModel.urgency_level) == "high",
                )
            )
        )
        critical_res = await session.execute(critical_stmt)
        critical_count = critical_res.scalar() or 0

        # Pathway breakdown
        pathway_stmt = select(EncounterModel.pathway, func.count(EncounterModel.id)).group_by(EncounterModel.pathway)
        pathway_res = await session.execute(pathway_stmt)
        pathway_counts = {row[0]: row[1] for row in pathway_res.all() if row[0] is not None}

        # Billing total estimate
        billing_stmt = select(func.sum(BillingRecordModel.estimated_cost))
        billing_res = await session.execute(billing_stmt)
        total_billing = billing_res.scalar() or 0.0

        return {
            "total_encounters": total_count,
            "active_encounters": active_count,
            "critical_cases": critical_count,
            "pathway_counts": pathway_counts,
            "total_billing_est": total_billing,
        }


async def fetch_encounters(
    *,
    status_filter: str | None = None,
    pathway_filter: str | None = None,
    urgency_filter: str | None = None,
    search_query: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Query encounters with filtering and eager relationships."""
    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(EncounterModel)
            .options(
                selectinload(EncounterModel.patient),
                selectinload(EncounterModel.triage_result),
                selectinload(EncounterModel.case_summary),
                selectinload(EncounterModel.billing_records),
                selectinload(EncounterModel.followups),
            )
            .join(PatientModel, EncounterModel.patient_id == PatientModel.id)
            .order_by(EncounterModel.created_at.desc())
        )

        if status_filter and status_filter != "All":
            stmt = stmt.where(EncounterModel.status == status_filter.lower())

        if pathway_filter and pathway_filter != "All":
            # Map clean names back to db abbreviations
            db_pathway = pathway_filter.lower()
            if db_pathway == "teleconsultation":
                db_pathway = "teleconsult"
            elif db_pathway == "specialist referral":
                db_pathway = "specialist"
            stmt = stmt.where(EncounterModel.pathway == db_pathway)

        if urgency_filter and urgency_filter != "All":
            stmt = stmt.join(TriageResultModel, EncounterModel.id == TriageResultModel.encounter_id).where(
                func.lower(TriageResultModel.urgency_level) == urgency_filter.lower()
            )

        if search_query:
            q = f"%{search_query.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(PatientModel.full_name).like(q),
                    func.lower(PatientModel.phone).like(q),
                    func.lower(EncounterModel.symptoms).like(q),
                )
            )

        stmt = stmt.limit(limit)
        res = await session.execute(stmt)
        encounters = res.scalars().all()

        results = []
        for e in encounters:
            patient_name = e.patient.full_name if e.patient else "Unknown"
            patient_phone = e.patient.phone if e.patient else "—"
            patient_age = getattr(e.patient, "age", "—")  # Fallback just in case
            # Triage info
            urgency = e.triage_result.urgency_level if e.triage_result else "unknown"
            triage_rationale = e.triage_result.reasoning if e.triage_result else ""
            # Billing info
            total_bill = 0.0
            billing_status = "none"
            if e.billing_records:
                # Get the latest billing record
                latest_bill = sorted(e.billing_records, key=lambda br: br.created_at)[-1]
                total_bill = latest_bill.estimated_cost or 0.0
                billing_status = latest_bill.status

            results.append(
                {
                    "id": e.id,
                    "patient_id": e.patient_id,
                    "patient_name": patient_name,
                    "patient_phone": patient_phone,
                    "patient_gender": e.patient.gender if e.patient else "—",
                    "symptoms": e.symptoms,
                    "status": e.status,
                    "pathway": e.pathway,
                    "urgency": urgency,
                    "triage_rationale": triage_rationale,
                    "total_billing": total_bill,
                    "billing_status": billing_status,
                    "created_at": e.created_at,
                    "source_channel": e.source_channel,
                }
            )
        return results


async def fetch_encounter_by_id(encounter_id: str) -> dict[str, Any] | None:
    """Fetch complete detail for a single encounter."""
    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(EncounterModel)
            .options(
                selectinload(EncounterModel.patient),
                selectinload(EncounterModel.triage_result),
                selectinload(EncounterModel.case_summary),
                selectinload(EncounterModel.billing_records),
                selectinload(EncounterModel.followups),
            )
            .where(EncounterModel.id == encounter_id)
        )
        res = await session.execute(stmt)
        e = res.scalar_one_or_none()
        if not e:
            return None

        # Build state dict corresponding to run_patient_workflow output state
        triage_dict = {}
        if e.triage_result:
            try:
                triage_dict = json.loads(e.triage_result.raw_llm_response or "{}")
            except Exception:
                triage_dict = {
                    "urgency": e.triage_result.urgency_level,
                    "rationale": e.triage_result.reasoning,
                    "pathway": e.triage_result.suggested_pathway,
                }

        summary_dict = {}
        if e.case_summary:
            try:
                tests = json.loads(e.case_summary.suggested_tests_json or "[]")
            except Exception:
                tests = []
            summary_dict = {
                "case_summary": e.case_summary.summary_text,
                "suggested_tests": tests,
                "history_notes": e.case_summary.extracted_history,
                "doctor_briefing": e.case_summary.doctor_notes,
            }

        billing_dict = {}
        if e.billing_records:
            # Sort by created_at desc to find latest
            latest_bill = sorted(e.billing_records, key=lambda br: br.created_at)[-1]
            try:
                insurance_doc = json.loads(latest_bill.insurance_doc_json or "{}")
                # insurance_doc_json holds: {"documentation": ..., "document": ..., "cost_breakdown": ...}
                billing_dict = {
                    "estimated_cost_inr": latest_bill.estimated_cost,
                    "currency": latest_bill.currency,
                    "cost_breakdown": insurance_doc.get("cost_breakdown", {
                        "consultation_fee": latest_bill.consultation_fee,
                        "test_cost": latest_bill.test_cost,
                        "medication_cost": latest_bill.medication_cost,
                        "miscellaneous_cost": latest_bill.misc_cost,
                    }),
                    "insurance_document": insurance_doc.get("document", {
                        "reference_number": latest_bill.preauth_reference,
                        "document_type": "Pre-Authorization Document",
                        "clinical_indication": "Triage Symptoms Details",
                        "proposed_services": [],
                        "icd10_codes": json.loads(latest_bill.icd10_codes_json or "[]"),
                        "cpt_codes": json.loads(latest_bill.cpt_codes_json or "[]"),
                    }),
                    "insurance_documentation": insurance_doc.get("documentation", latest_bill.insurance_provider),
                    "status": latest_bill.status,
                }
            except Exception:
                billing_dict = {
                    "estimated_cost_inr": latest_bill.estimated_cost,
                    "currency": latest_bill.currency,
                    "cost_breakdown": {
                        "consultation_fee": latest_bill.consultation_fee,
                        "test_cost": latest_bill.test_cost,
                        "medication_cost": latest_bill.medication_cost,
                        "miscellaneous_cost": latest_bill.misc_cost,
                    },
                    "insurance_document": {
                        "reference_number": latest_bill.preauth_reference,
                        "document_type": "Pre-Authorization Document",
                        "clinical_indication": "",
                        "proposed_services": [],
                        "icd10_codes": json.loads(latest_bill.icd10_codes_json or "[]"),
                        "cpt_codes": json.loads(latest_bill.cpt_codes_json or "[]"),
                    },
                    "insurance_documentation": latest_bill.insurance_provider,
                    "status": latest_bill.status,
                }

        followup_dict = {}
        if e.followups:
            latest_followup = sorted(e.followups, key=lambda f: f.created_at)[-1]
            try:
                followup_dict = json.loads(latest_followup.plan_json or "{}")
            except Exception:
                followup_dict = {"notes": f"Raw Followup Plan status: {latest_followup.status}"}

        return {
            "patient": {
                "id": e.patient.id if e.patient else "—",
                "full_name": e.patient.full_name if e.patient else "Unknown",
                "phone": e.patient.phone if e.patient else "—",
                "gender": e.patient.gender if e.patient else "—",
                "email": e.patient.email if e.patient else "—",
            },
            "encounter": {
                "id": e.id,
                "patient_id": e.patient_id,
                "symptoms": e.symptoms,
                "status": e.status,
                "pathway": e.pathway,
                "source_channel": e.source_channel,
                "created_at": e.created_at,
            },
            "workflow_state": {
                "encounter_id": e.id,
                "symptoms": e.symptoms,
                "triage": triage_dict,
                "routing": {
                    "pathway": e.pathway,
                    "notes": triage_dict.get("rationale") or "",
                },
                "medical_summary": summary_dict,
                "billing": billing_dict,
                "followup": followup_dict,
            },
        }


async def override_pathway(encounter_id: str, new_pathway: str) -> bool:
    """Manually override recommended care pathway for an encounter."""
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(EncounterModel).where(EncounterModel.id == encounter_id)
        res = await session.execute(stmt)
        e = res.scalar_one_or_none()
        if not e:
            return False

        e.pathway = new_pathway
        if e.status == "triaged":
            e.status = "routed"
        e.updated_at = datetime.utcnow()
        await session.commit()
        return True


async def update_status(encounter_id: str, new_status: str) -> bool:
    """Change the state machine status of an encounter."""
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(EncounterModel).where(EncounterModel.id == encounter_id)
        res = await session.execute(stmt)
        e = res.scalar_one_or_none()
        if not e:
            return False

        e.status = new_status
        e.updated_at = datetime.utcnow()
        await session.commit()
        return True


async def add_doctor_notes(encounter_id: str, notes: str) -> bool:
    """Append reviewing doctor notes to the case summary."""
    factory = get_session_factory()
    async with factory() as session:
        # Check if case summary exists
        stmt = select(CaseSummaryModel).where(CaseSummaryModel.encounter_id == encounter_id)
        res = await session.execute(stmt)
        cs = res.scalar_one_or_none()
        if not cs:
            # If summary isn't created, we make a stub one
            cs = CaseSummaryModel(
                encounter_id=encounter_id,
                summary_text="No automated summary.",
                suggested_tests_json="[]",
                doctor_notes=notes,
            )
            session.add(cs)
        else:
            cs.doctor_notes = notes

        # Move status to summary_ready or update status to include reviewed if appropriate
        enc_stmt = select(EncounterModel).where(EncounterModel.id == encounter_id)
        enc_res = await session.execute(enc_stmt)
        e = enc_res.scalar_one_or_none()
        if e and e.status in ["intake", "triaged", "routed"]:
            e.status = "summary_ready"

        await session.commit()
        return True


async def approve_billing_status(encounter_id: str, new_status: str = "approved") -> bool:
    """Update status of the billing record (e.g. approve preauth/estimate)."""
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(BillingRecordModel).where(BillingRecordModel.encounter_id == encounter_id)
        res = await session.execute(stmt)
        brs = res.scalars().all()
        if not brs:
            return False

        # Get latest and update its status
        latest = sorted(brs, key=lambda r: r.created_at)[-1]
        latest.status = new_status

        # If billing is approved, progress encounter to closed or keep billing_ready
        if new_status == "approved":
            enc_stmt = select(EncounterModel).where(EncounterModel.id == encounter_id)
            enc_res = await session.execute(enc_stmt)
            e = enc_res.scalar_one_or_none()
            if e and e.status == "billing_ready":
                e.status = "closed"

        await session.commit()
        return True


async def fetch_dietary_context(encounter_id: str) -> dict[str, str | None]:
    """Read the currently stored dietary preference/allergies/conditions for an encounter."""
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(EncounterModel).where(EncounterModel.id == encounter_id)
        res = await session.execute(stmt)
        e = res.scalar_one_or_none()
        if not e:
            return {}
        try:
            context = json.loads(e.intake_context_json or "{}")
        except json.JSONDecodeError:
            context = {}
        return {
            "dietary_preference": context.get("dietary_preference"),
            "food_allergies": context.get("food_allergies"),
            "known_medical_conditions": context.get("known_medical_conditions"),
        }


async def update_dietary_context_and_regenerate_followup(
    encounter_id: str,
    *,
    dietary_preference: str | None,
    food_allergies: str | None,
    known_medical_conditions: str | None,
) -> bool:
    """Update the dietary/allergy/condition info on an *existing* encounter and
    regenerate only its follow-up plan — without creating a new patient or
    encounter, and without re-running triage/routing/summarizer/billing.
    """
    # Local imports to avoid a circular import at module load time
    # (followup_service -> agents -> ... eventually touches ui in tests).
    from hospital_command_center.services.followup_service import FollowUpService

    factory = get_session_factory()
    async with factory() as session:
        stmt = select(EncounterModel).where(EncounterModel.id == encounter_id)
        res = await session.execute(stmt)
        e = res.scalar_one_or_none()
        if not e:
            return False

        try:
            context = json.loads(e.intake_context_json or "{}")
        except json.JSONDecodeError:
            context = {}

        context["dietary_preference"] = dietary_preference
        context["food_allergies"] = food_allergies
        context["known_medical_conditions"] = known_medical_conditions
        e.intake_context_json = json.dumps(context)
        e.updated_at = datetime.utcnow()
        await session.commit()

        await FollowUpService().plan_and_store_from_encounter(UUID(encounter_id), session)
        return True
