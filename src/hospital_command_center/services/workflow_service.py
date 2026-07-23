"""Top-level workflow runner invoking the LangGraph."""

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.agents.triage import TriageAgent
from hospital_command_center.core.exceptions import IntakeError
from hospital_command_center.domain.intake import IntakeSubmission
from hospital_command_center.domain.triage import TriageClarificationSubmission, TriageStatus
from hospital_command_center.graphs.patient_workflow import run_patient_workflow, run_remaining_workflow
from hospital_command_center.graphs.state import PatientWorkflowState
from hospital_command_center.services.encounter_persistence import EncounterPersistenceService


class WorkflowService:
    def _build_response(
        self,
        *,
        patient,
        encounter,
        state: dict,
        patient_history: str | None = None,
    ) -> dict:
        return {
            "patient": {
                "id": patient.id,
                "full_name": patient.full_name,
                "phone": patient.phone,
            },
            "encounter": {
                "id": encounter.id,
                "patient_id": encounter.patient_id,
                "symptoms": encounter.symptoms,
                "status": encounter.status,
                "pathway": encounter.pathway,
                "source_channel": encounter.source_channel,
            },
            "workflow_state": state,
            "patient_history_used": patient_history,
            "awaiting_triage_clarification": (
                (state.get("triage") or {}).get("status") == TriageStatus.NEEDS_CLARIFICATION
            ),
        }

    def _workflow_context_from_encounter(self, encounter, intake_context: dict) -> dict:
        return {
            "symptoms": encounter.symptoms,
            "patient_name": intake_context.get("patient_name") or (
                encounter.patient.full_name if encounter.patient else None
            ),
            "age": intake_context.get("age"),
            "gender": intake_context.get("gender") or (
                encounter.patient.gender if encounter.patient else None
            ),
            "phone": intake_context.get("phone") or (
                encounter.patient.phone if encounter.patient else None
            ),
            "channel": intake_context.get("channel")
            or encounter.source_channel,
            "dietary_preference": intake_context.get("dietary_preference"),
            "food_allergies": intake_context.get("food_allergies"),
        }

    async def start_from_intake(self, session: AsyncSession, payload: IntakeSubmission) -> dict:
        persistence = EncounterPersistenceService(session)
        patient = await persistence.ensure_patient(payload)
        encounter = await persistence.create_encounter(patient, payload)
        encounter_id = UUID(encounter.id)

        patient_history = await persistence.load_history_text(
            patient.id,
            exclude_encounter_id=encounter.id,
        )

        state = run_patient_workflow(
            encounter_id=encounter_id,
            symptoms=payload.symptoms,
            patient_name=payload.patient_name,
            age=payload.age,
            gender=payload.gender,
            phone=payload.phone,
            channel=payload.channel.value,
            patient_history=patient_history,
            dietary_preference=payload.dietary_preference,
            food_allergies=payload.food_allergies,
        )

        triage = state.get("triage") or {}
        if triage.get("status") == TriageStatus.NEEDS_CLARIFICATION:
            state["triage_conversation"] = persistence.load_triage_conversation(encounter)
            saved_encounter = await persistence.persist_triage_pause(encounter.id, state)
        else:
            saved_encounter = await persistence.persist_workflow_state(encounter.id, state)

        return self._build_response(
            patient=patient,
            encounter=saved_encounter,
            state=state,
            patient_history=patient_history,
        )

    async def continue_triage(
        self,
        session: AsyncSession,
        encounter_id: UUID,
        payload: TriageClarificationSubmission,
    ) -> dict:
        persistence = EncounterPersistenceService(session)
        encounter = await persistence.get_encounter_with_patient(str(encounter_id))

        if encounter.status != "awaiting_triage_clarification":
            raise IntakeError(
                f"Encounter {encounter_id} is not awaiting triage clarification "
                f"(status={encounter.status})."
            )

        conversation = persistence.apply_clarification_answers(encounter, payload.answers)
        await session.commit()

        intake_context = persistence.load_intake_context(encounter)
        context = self._workflow_context_from_encounter(encounter, intake_context)

        patient_history = ""
        if encounter.patient_id:
            patient_history = await persistence.load_history_text(
                encounter.patient_id,
                exclude_encounter_id=encounter.id,
            )

        triage_agent = TriageAgent()
        triage = triage_agent.run(
            encounter_id=encounter_id,
            triage_conversation=conversation,
            patient_history=patient_history,
            **context,
        )

        state: PatientWorkflowState = {
            "encounter_id": str(encounter_id),
            "symptoms": context["symptoms"],
            "triage": triage,
            "triage_conversation": conversation,
        }
        if context.get("patient_name"):
            state["patient_name"] = context["patient_name"]
        if context.get("age") is not None:
            state["age"] = context["age"]
        if context.get("gender"):
            state["gender"] = context["gender"]
        if context.get("phone"):
            state["phone"] = context["phone"]
        if context.get("channel"):
            state["channel"] = context["channel"]
        if context.get("dietary_preference"):
            state["dietary_preference"] = context["dietary_preference"]
        if context.get("food_allergies"):
            state["food_allergies"] = context["food_allergies"]
        if patient_history:
            state["patient_history"] = patient_history

        if triage.get("status") == TriageStatus.NEEDS_CLARIFICATION:
            saved_encounter = await persistence.persist_triage_pause(encounter.id, state)
        else:
            state = run_remaining_workflow(state)
            saved_encounter = await persistence.persist_workflow_state(encounter.id, state)

        patient = encounter.patient
        if patient is None:
            raise IntakeError(f"Encounter {encounter_id} has no linked patient.")

        return self._build_response(
            patient=patient,
            encounter=saved_encounter,
            state=state,
            patient_history=patient_history or None,
        )

    def run_stub(self, encounter_id: UUID | None = None, symptoms: str = "stub") -> dict:
        eid = encounter_id or uuid4()
        return run_patient_workflow(encounter_id=eid, symptoms=symptoms)
