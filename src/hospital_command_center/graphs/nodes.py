"""Graph node bindings wrapping agents and services."""

from uuid import UUID

from hospital_command_center.agents.billing_insurance import BillingInsuranceAgent
from hospital_command_center.agents.followup import FollowUpAgent
from hospital_command_center.agents.medical_summarizer import MedicalSummarizerAgent
from hospital_command_center.agents.router import RouterAgent
from hospital_command_center.agents.triage import TriageAgent
from hospital_command_center.core.config import WELCOME_MESSAGE
from hospital_command_center.graphs.state import PatientWorkflowState

_triage = TriageAgent()
_router = RouterAgent()
_summarizer = MedicalSummarizerAgent()
_billing = BillingInsuranceAgent()
_followup = FollowUpAgent()


def welcome_node(state: PatientWorkflowState) -> PatientWorkflowState:
    return {**state, "message": WELCOME_MESSAGE}


def triage_node(state: PatientWorkflowState) -> PatientWorkflowState:
    eid = UUID(state["encounter_id"])
    return {
        **state,
        "triage": _triage.run(
            encounter_id=eid,
            symptoms=state.get("symptoms", ""),
            patient_name=state.get("patient_name"),
            age=state.get("age"),
            gender=state.get("gender"),
            phone=state.get("phone"),
            channel=state.get("channel"),
        ),
    }


def route_node(state: PatientWorkflowState) -> PatientWorkflowState:
    eid = UUID(state["encounter_id"])
    return {**state, "routing": _router.run(
        encounter_id=eid,
        symptoms=state.get("symptoms", ""),
        triage=state.get("triage"),
        patient_name=state.get("patient_name"),
        age=state.get("age"),
        gender=state.get("gender"),
        channel=state.get("channel"),
    )}


def summarize_node(state: PatientWorkflowState) -> PatientWorkflowState:
    eid = UUID(state["encounter_id"])
    triage = state.get("triage", {})
    return {
        **state,
        "medical_summary": _summarizer.run(
            encounter_id=eid,
            symptoms=state.get("symptoms", ""),
            urgency=triage.get("urgency"),
            triage_rationale=triage.get("rationale"),
            patient_name=state.get("patient_name"),
            age=state.get("age"),
            gender=state.get("gender"),
        ),
    }


def billing_node(state: PatientWorkflowState) -> PatientWorkflowState:
    eid = UUID(state["encounter_id"])
    return {
        **state,
        "billing": _billing.run(
            encounter_id=eid,
            triage=state.get("triage"),
            routing=state.get("routing"),
            medical_summary=state.get("medical_summary"),
            symptoms=state.get("symptoms", ""),
        ),
    }


def followup_node(state: PatientWorkflowState) -> PatientWorkflowState:
    eid = UUID(state["encounter_id"])
    triage_data = state.get("triage") or {}
    summary_data = state.get("medical_summary") or {}

    # NOTE: these dict keys must match the actual field names in
    # domain/triage.py (`urgency`) and domain/medical.py (`case_summary`),
    # not the DB column names (`urgency_level`, `summary_text`). Using the
    # wrong keys here silently produced "Not provided" for both fields on
    # every run, which is why the follow-up agent always had zero real
    # clinical context to reason from.
    urgency = triage_data.get("urgency") or "Not provided"
    medical_summary = summary_data.get("case_summary") or "Not provided"
    suggested_tests = summary_data.get("suggested_tests") or []

    return {
        **state,
        "followup": _followup.run(
            encounter_id=eid,
            symptoms=state.get("symptoms", "Not provided"),
            urgency=urgency,
            medical_summary=medical_summary,
            suggested_tests=suggested_tests,
            dietary_preference=state.get("dietary_preference"),
            food_allergies=state.get("food_allergies"),
        ),
    }