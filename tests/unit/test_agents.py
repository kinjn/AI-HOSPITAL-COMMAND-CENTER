"""Unit tests for agents."""

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from hospital_command_center.agents.followup import FollowUpAgent
from hospital_command_center.domain.followup import FollowUpPlan, DietGuidance, ScheduledTask


@patch("hospital_command_center.agents.followup.get_chat_model")
def test_followup_agent_success(mock_get_chat_model):
    mock_llm = MagicMock()
    mock_structured_llm = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured_llm
    
    encounter_id = uuid4()
    fake_plan = FollowUpPlan(
        encounter_id=encounter_id,
        generated_at=datetime.now(timezone.utc),
        medication_reminders=[],
        lab_reminders=[],
        diet_guidance=DietGuidance(summary="Follow up low sodium diet."),
        escalation_enabled=True,
        escalation_rules=[],
        schedule=[
            ScheduledTask(
                task_type="symptom_checkin",
                due_at=datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc),
                channel="sms",
                note="Check on recovery status",
            )
        ]
    )
    mock_structured_llm.invoke.return_value = fake_plan
    mock_get_chat_model.return_value = mock_llm

    agent = FollowUpAgent()
    result = agent.run(
        encounter_id=encounter_id,
        symptoms="chest pain resolved, mild cough",
        urgency="medium",
        medical_summary="Patient presented with mild symptoms, advised rest."
    )
    
    assert result["encounter_id"] == str(encounter_id)
    assert len(result["schedule"]) == 1
    assert result["schedule"][0]["due_at"].startswith("2026-07-03")


def _plan_with(encounter_id, **overrides) -> FollowUpPlan:
    defaults = dict(
        encounter_id=encounter_id,
        generated_at=datetime.now(timezone.utc),
        medication_reminders=[],
        lab_reminders=[],
        diet_guidance=DietGuidance(summary="stub"),
        escalation_enabled=True,
        escalation_rules=[],
        schedule=[],
    )
    defaults.update(overrides)
    return FollowUpPlan(**defaults)


@patch("hospital_command_center.agents.followup.get_chat_model")
def test_followup_agent_drops_tests_not_suggested_by_summarizer(mock_get_chat_model):
    """The agent must never schedule a test the summarizer didn't actually suggest."""
    from hospital_command_center.domain.followup import LabReminder

    encounter_id = uuid4()
    fake_plan = _plan_with(
        encounter_id,
        lab_reminders=[
            LabReminder(test="CBC", due_in_days=3),
            LabReminder(test="MRI Brain", due_in_days=5),  # hallucinated, not suggested
        ],
    )

    mock_llm = MagicMock()
    mock_structured_llm = MagicMock()
    mock_structured_llm.invoke.return_value = fake_plan
    mock_llm.with_structured_output.return_value = mock_structured_llm
    mock_get_chat_model.return_value = mock_llm

    agent = FollowUpAgent()
    result = agent.run(
        encounter_id=encounter_id,
        symptoms="fatigue",
        urgency="low",
        medical_summary="Patient reports fatigue.",
        suggested_tests=["CBC"],
    )

    test_names = [r["test"] for r in result["lab_reminders"]]
    assert test_names == ["CBC"]
    assert "MRI Brain" not in test_names


@patch("hospital_command_center.agents.followup.get_chat_model")
def test_followup_agent_no_tests_when_summarizer_suggested_none(mock_get_chat_model):
    """If the summarizer suggested zero tests, lab_reminders must be empty regardless of LLM output."""
    from hospital_command_center.domain.followup import LabReminder

    encounter_id = uuid4()
    fake_plan = _plan_with(
        encounter_id,
        lab_reminders=[LabReminder(test="Glucose check", due_in_days=2)],
    )

    mock_llm = MagicMock()
    mock_structured_llm = MagicMock()
    mock_structured_llm.invoke.return_value = fake_plan
    mock_llm.with_structured_output.return_value = mock_structured_llm
    mock_get_chat_model.return_value = mock_llm

    agent = FollowUpAgent()
    result = agent.run(
        encounter_id=encounter_id,
        symptoms="mild headache",
        urgency="low",
        medical_summary="Self-limiting headache, no workup needed.",
        suggested_tests=[],
    )

    assert result["lab_reminders"] == []


@patch("hospital_command_center.agents.followup.get_chat_model")
def test_followup_agent_withholds_diet_plan_until_preference_known(mock_get_chat_model):
    """No specific meal guidance before veg/non-veg/allergy info is collected."""
    encounter_id = uuid4()
    fake_plan = _plan_with(
        encounter_id,
        diet_guidance=DietGuidance(
            summary="Eat well",
            recommended=["Grilled chicken", "Spinach"],
            avoid=["Fried food"],
            hydration_notes="Drink 8 glasses of water a day",
        ),
    )

    mock_llm = MagicMock()
    mock_structured_llm = MagicMock()
    mock_structured_llm.invoke.return_value = fake_plan
    mock_llm.with_structured_output.return_value = mock_structured_llm
    mock_get_chat_model.return_value = mock_llm

    agent = FollowUpAgent()
    result = agent.run(
        encounter_id=encounter_id,
        symptoms="mild sore throat",
        urgency="low",
        medical_summary="Viral pharyngitis, supportive care advised.",
        dietary_preference=None,
    )

    diet = result["diet_guidance"]
    assert diet["preferences_confirmed"] is False
    assert diet["recommended"] == []
    assert diet["avoid"] == []
    assert diet["hydration_notes"] == ""


@patch("hospital_command_center.agents.followup.get_chat_model")
def test_followup_agent_respects_vegetarian_preference_and_allergies(mock_get_chat_model):
    """Once preference is known, recommendations must respect veg/allergy constraints."""
    encounter_id = uuid4()
    fake_plan = _plan_with(
        encounter_id,
        diet_guidance=DietGuidance(
            summary="Bland diet for GI upset",
            recommended=["Grilled chicken", "Steamed rice", "Peanuts"],
            avoid=["Fried food"],
        ),
    )

    mock_llm = MagicMock()
    mock_structured_llm = MagicMock()
    mock_structured_llm.invoke.return_value = fake_plan
    mock_llm.with_structured_output.return_value = mock_structured_llm
    mock_get_chat_model.return_value = mock_llm

    agent = FollowUpAgent()
    result = agent.run(
        encounter_id=encounter_id,
        symptoms="stomach upset",
        urgency="low",
        medical_summary="Mild gastroenteritis.",
        dietary_preference="vegetarian",
        food_allergies="peanuts",
    )

    diet = result["diet_guidance"]
    assert diet["preferences_confirmed"] is True
    assert "Grilled chicken" not in diet["recommended"]
    assert "Peanuts" not in diet["recommended"]
    assert "Steamed rice" in diet["recommended"]


@patch("hospital_command_center.agents.followup.get_chat_model")
def test_followup_agent_clears_generic_hydration_advice(mock_get_chat_model):
    """Hydration notes should be cleared when nothing in the case justifies them."""
    encounter_id = uuid4()
    fake_plan = _plan_with(
        encounter_id,
        diet_guidance=DietGuidance(
            summary="General guidance",
            hydration_notes="Drink 8 glasses of water a day",
            preferences_confirmed=True,
        ),
    )

    mock_llm = MagicMock()
    mock_structured_llm = MagicMock()
    mock_structured_llm.invoke.return_value = fake_plan
    mock_llm.with_structured_output.return_value = mock_structured_llm
    mock_get_chat_model.return_value = mock_llm

    agent = FollowUpAgent()
    result = agent.run(
        encounter_id=encounter_id,
        symptoms="minor ankle sprain",
        urgency="low",
        medical_summary="Sprained ankle, RICE protocol advised.",
        dietary_preference="non-vegetarian",
    )

    assert result["diet_guidance"]["hydration_notes"] == ""


@patch("hospital_command_center.agents.followup.get_chat_model")
def test_followup_agent_keeps_hydration_advice_when_clinically_relevant(mock_get_chat_model):
    """Hydration notes should survive when the case actually involves fluid loss risk."""
    encounter_id = uuid4()
    fake_plan = _plan_with(
        encounter_id,
        diet_guidance=DietGuidance(
            summary="Supportive care",
            hydration_notes="Extra fluids to offset losses from vomiting and diarrhea",
            preferences_confirmed=True,
        ),
    )

    mock_llm = MagicMock()
    mock_structured_llm = MagicMock()
    mock_structured_llm.invoke.return_value = fake_plan
    mock_llm.with_structured_output.return_value = mock_structured_llm
    mock_get_chat_model.return_value = mock_llm

    agent = FollowUpAgent()
    result = agent.run(
        encounter_id=encounter_id,
        symptoms="vomiting and diarrhea for 2 days",
        urgency="medium",
        medical_summary="Acute gastroenteritis with dehydration risk.",
        dietary_preference="vegetarian",
    )

    assert result["diet_guidance"]["hydration_notes"] != ""


def test_escalation_rule_coerces_bare_string_notify_channels():
    """Regression test: the LLM sometimes returns a plain string like "immediate"
    for what used to be `notify_on` (now `notify_channels`), which previously
    crashed Pydantic validation and took down the entire follow-up plan
    generation (both the structured-output path and the manual-parse
    fallback), landing on the generic "processing error" plan.
    """
    from hospital_command_center.domain.followup import EscalationRule

    rule = EscalationRule(
        trigger="Chest pain",
        severity="critical",
        action="Visit ER immediately",
        notify_channels="immediate",  # bare string, not a list
    )
    assert rule.notify_channels == ["immediate"]


def test_escalation_rule_accepts_proper_list_notify_channels():
    from hospital_command_center.domain.followup import EscalationRule

    rule = EscalationRule(
        trigger="Chest pain",
        severity="critical",
        action="Visit ER immediately",
        notify_channels=["doctor", "emergency_contact"],
        notify_within="immediate",
    )
    assert rule.notify_channels == ["doctor", "emergency_contact"]
    assert rule.notify_within == "immediate"


@patch("hospital_command_center.agents.followup.get_chat_model")
def test_followup_agent_survives_notify_channels_type_slip(mock_get_chat_model):
    """End-to-end: even if the raw LLM dict has notify_channels as a bare
    string, the agent should still produce a valid plan instead of falling
    all the way through to the generic-error fallback.
    """
    encounter_id = uuid4()

    # Simulate structured_output raising (as it would against a raw dict with
    # the wrong type), forcing the manual-JSON fallback path, which is where
    # the coercion needs to also hold up.
    raw_json = json.dumps({
        "encounter_id": str(encounter_id),
        "medication_reminders": [],
        "lab_reminders": [],
        "diet_guidance": {"summary": "stub", "preferences_confirmed": True},
        "escalation_rules": [
            {
                "trigger": "Chest pain",
                "severity": "critical",
                "action": "Visit ER",
                "notify_channels": "immediate",
                "notify_within": "immediate",
            }
        ],
        "schedule": [],
    })

    mock_llm = MagicMock()
    mock_structured_llm = MagicMock()
    mock_structured_llm.invoke.side_effect = Exception("simulated structured-output failure")
    mock_llm.with_structured_output.return_value = mock_structured_llm
    mock_response = MagicMock()
    mock_response.content = raw_json
    mock_llm.invoke.return_value = mock_response
    mock_get_chat_model.return_value = mock_llm

    agent = FollowUpAgent()
    result = agent.run(
        encounter_id=encounter_id,
        symptoms="chest pain",
        urgency="critical",
        medical_summary="Possible cardiac event.",
        dietary_preference="vegetarian",
    )

    assert result["notes"] != "Generic follow-up plan generated due to processing error."
    assert result["escalation_rules"][0]["notify_channels"] == ["immediate"]
