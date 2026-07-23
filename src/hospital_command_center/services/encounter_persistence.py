"""Persist patients, encounters, and workflow outputs to the database."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.core.exceptions import IntakeError
from hospital_command_center.core.phone import normalize_phone
from hospital_command_center.db.models.billing_record import BillingRecordModel
from hospital_command_center.db.models.case_summary import CaseSummaryModel
from hospital_command_center.db.models.encounter import EncounterModel
from hospital_command_center.db.models.followup import FollowUpModel
from hospital_command_center.db.models.patient import PatientModel
from hospital_command_center.db.models.triage_result import TriageResultModel
from hospital_command_center.db.repositories.encounter import EncounterRepository
from hospital_command_center.db.repositories.patient import PatientRepository
from hospital_command_center.domain.followup import FollowUpPlan
from hospital_command_center.domain.intake import IntakeSubmission
from hospital_command_center.services.patient_history import format_patient_history


def _channel_to_db(channel: str) -> str:
    if channel == "mobile_app":
        return "app"
    return channel


def _pathway_to_db(pathway: str) -> str:
    mapping = {
        "teleconsultation": "teleconsult",
        "specialist_referral": "specialist",
    }
    return mapping.get(pathway, pathway)


def _to_decimal(value: object) -> Decimal:
    """Safely coerce *value* to Decimal.

    Handles: None, empty string, existing Decimal, int, float, and numeric strings.
    Falls back to Decimal("0.00") for any value that cannot be parsed.
    """
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return Decimal("0.00")


class _DecimalEncoder(json.JSONEncoder):
    """JSON encoder that serializes Decimal values as plain floats.

    Used when persisting ``insurance_doc_json`` blobs that may contain
    Decimal amounts coming directly from Pydantic domain models.
    """

    def default(self, obj: object) -> object:
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def _gender_to_db(gender: str | None) -> str | None:
    if not gender:
        return None
    return gender.strip().lower()


def _channel_from_db(channel: str) -> str:
    if channel == "app":
        return "mobile_app"
    return channel


class EncounterPersistenceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._patients = PatientRepository(session)
        self._encounters = EncounterRepository(session)

    async def ensure_patient(self, payload: IntakeSubmission) -> PatientModel:
        if not payload.patient_name or not payload.patient_name.strip():
            raise IntakeError("Patient name is required to store the encounter.")
        if not payload.phone or not payload.phone.strip():
            raise IntakeError("Phone number is required to identify the patient.")

        name = payload.patient_name.strip()
        phone = normalize_phone(payload.phone)
        existing = await self._patients.get_by_name_and_phone(name, phone)
        if existing:
            if payload.gender:
                existing.gender = _gender_to_db(payload.gender)
            await self._session.commit()
            await self._session.refresh(existing)
            return existing

        patient = PatientModel(
            full_name=name,
            phone=phone,
            gender=_gender_to_db(payload.gender),
            source_channel=_channel_to_db(payload.channel.value),
        )
        return await self._patients.create(patient)

    async def create_encounter(
        self, patient: PatientModel, payload: IntakeSubmission
    ) -> EncounterModel:
        intake_context = {
            "patient_name": payload.patient_name,
            "age": payload.age,
            "gender": payload.gender,
            "phone": payload.phone,
            "channel": payload.channel.value,
            "dietary_preference": payload.dietary_preference,
            "food_allergies": payload.food_allergies,
        }
        encounter = EncounterModel(
            patient_id=patient.id,
            symptoms=payload.symptoms,
            source_channel=_channel_to_db(payload.channel.value),
            status="intake",
            intake_context_json=json.dumps(intake_context),
        )
        return await self._encounters.create(encounter)

    async def load_history_text(self, patient_id: str, *, exclude_encounter_id: str) -> str:
        encounters = await self._encounters.get_patient_history(
            patient_id,
            exclude_encounter_id=exclude_encounter_id,
            limit=10,
        )
        return format_patient_history(encounters)

    async def get_encounter_with_patient(self, encounter_id: str) -> EncounterModel:
        encounter = await self._encounters.get_by_id_with_patient(encounter_id)
        if encounter is None:
            raise IntakeError(f"Encounter {encounter_id} not found.")
        return encounter

    def load_intake_context(self, encounter: EncounterModel) -> dict:
        try:
            return json.loads(encounter.intake_context_json or "{}")
        except json.JSONDecodeError:
            return {}

    def load_triage_conversation(self, encounter: EncounterModel) -> list[dict[str, str | None]]:
        try:
            raw = json.loads(encounter.triage_conversation_json or "[]")
            return raw if isinstance(raw, list) else []
        except json.JSONDecodeError:
            return []

    def apply_clarification_answers(
        self, encounter: EncounterModel, answers: list[str]
    ) -> list[dict[str, str | None]]:
        conversation = self.load_triage_conversation(encounter)
        pending = [turn for turn in conversation if not turn.get("answer")]
        if not pending:
            raise IntakeError("No pending triage questions for this encounter.")
        if len(answers) != len(pending):
            raise IntakeError(
                f"Expected {len(pending)} answer(s) for pending question(s), got {len(answers)}."
            )
        for turn, answer in zip(pending, answers):
            turn["answer"] = answer.strip()
        encounter.triage_conversation_json = json.dumps(conversation)
        return conversation

    async def persist_triage_pause(self, encounter_id: str, state: dict) -> EncounterModel:
        encounter = await self._encounters.get_by_id(encounter_id)
        if encounter is None:
            raise IntakeError(f"Encounter {encounter_id} not found for persistence.")

        triage = state.get("triage") or {}
        conversation = self.load_triage_conversation(encounter)

        for question in triage.get("clarifying_questions", []):
            if not any(turn.get("question") == question for turn in conversation):
                conversation.append({"question": question, "answer": None})

        encounter.triage_conversation_json = json.dumps(conversation)
        encounter.status = "awaiting_triage_clarification"
        encounter.updated_at = datetime.utcnow()
        await self._session.commit()
        await self._session.refresh(encounter)
        return encounter

    async def persist_workflow_state(self, encounter_id: str, state: dict) -> EncounterModel:
        encounter = await self._encounters.get_by_id(encounter_id)
        if encounter is None:
            raise IntakeError(f"Encounter {encounter_id} not found for persistence.")

        triage = state.get("triage") or {}
        routing = state.get("routing") or {}
        medical = state.get("medical_summary") or {}
        billing = state.get("billing") or {}
        followup = state.get("followup") or {}

        pathway = _pathway_to_db(routing.get("pathway", "")) if routing.get("pathway") else None

        triage_status = triage.get("status", "complete")
        if triage and triage_status == "complete" and triage.get("urgency"):
            self._session.add(
                TriageResultModel(
                    encounter_id=encounter_id,
                    urgency_level=str(triage.get("urgency", "medium")),
                    suggested_pathway=pathway or "opd",
                    reasoning=triage.get("rationale"),
                    raw_llm_response=json.dumps(triage),
                )
            )
            encounter.status = "triaged"

        if routing and pathway:
            encounter.pathway = pathway
            encounter.status = "routed"

        if medical:
            self._session.add(
                CaseSummaryModel(
                    encounter_id=encounter_id,
                    summary_text=medical.get("case_summary", ""),
                    suggested_tests_json=json.dumps(medical.get("suggested_tests", [])),
                    extracted_history=medical.get("history_notes"),
                    doctor_notes=medical.get("doctor_briefing"),
                )
            )
            encounter.status = "summary_ready"

        if billing:
            cost = billing.get("estimated_cost_inr")
            breakdown = billing.get("cost_breakdown") or {}
            ins_doc = billing.get("insurance_document") or {}

            self._session.add(
                BillingRecordModel(
                    encounter_id=encounter_id,
                    estimated_cost=_to_decimal(cost) if cost is not None else None,
                    currency=billing.get("currency", "INR"),
                    # --- Itemized cost columns (normalized) ---
                    consultation_fee=_to_decimal(breakdown.get("consultation_fee")),
                    test_cost=_to_decimal(breakdown.get("test_cost")),
                    medication_cost=_to_decimal(breakdown.get("medication_cost")),
                    misc_cost=_to_decimal(breakdown.get("miscellaneous_cost")),
                    # --- Pre-authorization reference ---
                    preauth_reference=ins_doc.get("reference_number") or None,
                    # --- Serialized clinical code lists ---
                    icd10_codes_json=json.dumps(ins_doc.get("icd10_codes") or []),
                    cpt_codes_json=json.dumps(ins_doc.get("cpt_codes") or []),
                    # --- Full doc blob retained for UI compatibility ---
                    # DecimalEncoder converts any Decimal values from Pydantic models
                    # into JSON-safe floats before persisting the blob.
                    insurance_doc_json=json.dumps(
                        {
                            "documentation": billing.get("insurance_documentation"),
                            "document": ins_doc,
                            "cost_breakdown": breakdown,
                        },
                        cls=_DecimalEncoder,
                    ),
                    status=str(billing.get("status", "draft")),
                )
            )
            encounter.status = "billing_ready"

        if followup:
            plan = FollowUpPlan.model_validate(followup)
            scheduled_at = min(task.due_at for task in plan.schedule) if plan.schedule else None
            self._session.add(
                FollowUpModel(
                    encounter_id=encounter_id,
                    plan_json=json.dumps(plan.model_dump(mode="json")),
                    scheduled_at=scheduled_at,
                    followup_type="comprehensive_plan",
                )
            )
            encounter.status = "closed"

        encounter.updated_at = datetime.utcnow()
        await self._session.commit()
        await self._session.refresh(encounter)
        return encounter
