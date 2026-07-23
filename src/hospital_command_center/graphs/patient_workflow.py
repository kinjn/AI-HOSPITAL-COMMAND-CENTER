"""Main LangGraph: intake → triage → route → summarize → bill → follow-up."""

from uuid import UUID

from langgraph.graph import END, START, StateGraph

from hospital_command_center.graphs import nodes
from hospital_command_center.graphs.edges import after_triage
from hospital_command_center.graphs.state import PatientWorkflowState

_compiled_graph = None


def build_patient_workflow():
    graph = StateGraph(PatientWorkflowState)
    graph.add_node("welcome", nodes.welcome_node)
    graph.add_node("triage", nodes.triage_node)
    graph.add_node("route", nodes.route_node)
    graph.add_node("summarize", nodes.summarize_node)
    graph.add_node("billing", nodes.billing_node)
    graph.add_node("followup", nodes.followup_node)

    graph.add_edge(START, "welcome")
    graph.add_edge("welcome", "triage")
    graph.add_conditional_edges(
        "triage",
        after_triage,
        {
            "pause": END,
            "continue": "route",
        },
    )
    graph.add_edge("route", "summarize")
    graph.add_edge("summarize", "billing")
    graph.add_edge("billing", "followup")
    graph.add_edge("followup", END)
    return graph.compile()


def get_patient_workflow():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_patient_workflow()
    return _compiled_graph


def _apply_context(
    initial: PatientWorkflowState,
    *,
    patient_name: str | None = None,
    age: int | None = None,
    gender: str | None = None,
    phone: str | None = None,
    channel: str | None = None,
    patient_history: str | None = None,
    triage_conversation: list[dict[str, str]] | None = None,
    dietary_preference: str | None = None,
    food_allergies: str | None = None,
) -> PatientWorkflowState:
    if patient_name:
        initial["patient_name"] = patient_name
    if age is not None:
        initial["age"] = age
    if gender:
        initial["gender"] = gender
    if phone:
        initial["phone"] = phone
    if channel:
        initial["channel"] = channel
    if patient_history:
        initial["patient_history"] = patient_history
    if triage_conversation:
        initial["triage_conversation"] = triage_conversation
    if dietary_preference:
        initial["dietary_preference"] = dietary_preference
    if food_allergies:
        initial["food_allergies"] = food_allergies
    return initial


def run_patient_workflow(
    *,
    encounter_id: UUID,
    symptoms: str = "",
    patient_name: str | None = None,
    age: int | None = None,
    gender: str | None = None,
    phone: str | None = None,
    channel: str | None = None,
    patient_history: str | None = None,
    triage_conversation: list[dict[str, str]] | None = None,
    dietary_preference: str | None = None,
    food_allergies: str | None = None,
) -> dict:
    workflow = get_patient_workflow()
    initial: PatientWorkflowState = {
        "encounter_id": str(encounter_id),
        "symptoms": symptoms,
    }
    _apply_context(
        initial,
        patient_name=patient_name,
        age=age,
        gender=gender,
        phone=phone,
        channel=channel,
        patient_history=patient_history,
        triage_conversation=triage_conversation,
        dietary_preference=dietary_preference,
        food_allergies=food_allergies,
    )
    return workflow.invoke(initial)


def run_remaining_workflow(state: PatientWorkflowState) -> dict:
    """Run route → summarize → billing → follow-up after triage is complete."""
    state = nodes.route_node(state)
    state = nodes.summarize_node(state)
    state = nodes.billing_node(state)
    state = nodes.followup_node(state)
    return state
