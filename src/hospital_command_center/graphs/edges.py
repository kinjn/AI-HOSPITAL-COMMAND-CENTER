"""Conditional edges for routing (triage outcome, pathway selection)."""

from hospital_command_center.domain.triage import TriageStatus
from hospital_command_center.graphs.state import PatientWorkflowState


def after_triage(state: PatientWorkflowState) -> str:
    triage = state.get("triage") or {}
    if triage.get("status") == TriageStatus.NEEDS_CLARIFICATION:
        return "pause"
    return "continue"
