"""Unit tests for the medical summarizer agent."""

import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

from hospital_command_center.agents.medical_summarizer import (
    MedicalSummarizerAgent,
    _MedicalSummaryLLMOutput,
)
from hospital_command_center.domain.medical import MedicalSummary


def test_returns_stub_when_no_symptoms():
    """If no symptoms are given (encounter not yet triaged), return stub."""
    agent = MedicalSummarizerAgent()
    encounter_id = uuid4()

    result = agent.run(encounter_id=encounter_id, symptoms="")

    summary = MedicalSummary.model_validate(result)
    assert summary.encounter_id == encounter_id
    assert summary.case_summary == "Stub case summary."


@patch("hospital_command_center.agents.medical_summarizer.get_chat_model")
def test_generates_summary_from_llm(mock_get_chat_model):
    """With symptoms provided, the agent calls the LLM and returns structured output."""
    fake_json = json.dumps({
        "case_summary": "45-year-old male with chest pain, classified as high urgency.",
        "suggested_tests": ["ECG", "Troponin", "CBC"],
        "history_notes": "New patient, no prior records.",
        "doctor_briefing": "S: Chest pain. | O: Suggested ECG. | A: Possible cardiac event. | P: Urgent evaluation.",
    })

    fake_response = MagicMock()
    fake_response.content = fake_json

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = fake_response
    mock_get_chat_model.return_value = mock_llm

    agent = MedicalSummarizerAgent()
    encounter_id = uuid4()

    result = agent.run(
        encounter_id=encounter_id,
        symptoms="chest pain, sweating, dizziness",
        urgency="high",
        triage_rationale="Possible cardiac event",
        patient_name="Ravi Kumar",
        age=45,
    )

    summary = MedicalSummary.model_validate(result)
    assert summary.encounter_id == encounter_id
    assert "chest pain" in summary.case_summary.lower()
    assert "ECG" in summary.suggested_tests
    assert "S:" in summary.doctor_briefing


@patch("hospital_command_center.agents.medical_summarizer.get_chat_model")
def test_empty_test_list_is_preserved_not_overridden(mock_get_chat_model):
    """A deliberate empty suggested_tests list (no workup needed) must not be
    replaced with generic stub tests like CBC / Basic metabolic panel."""
    fake_json = json.dumps({
        "case_summary": "24-year-old with a mild sore throat and runny nose for one day, low urgency.",
        "suggested_tests": [],
        "history_notes": "New patient, no prior records.",
        "doctor_briefing": "S: Mild sore throat, runny nose, no fever. | O: Well appearing. "
        "| A: Likely viral URI. | P: Supportive care, no diagnostic workup indicated.",
    })

    fake_response = MagicMock()
    fake_response.content = fake_json

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = fake_response
    mock_get_chat_model.return_value = mock_llm

    agent = MedicalSummarizerAgent()
    encounter_id = uuid4()

    result = agent.run(
        encounter_id=encounter_id,
        symptoms="mild sore throat and runny nose for one day, no fever",
        urgency="low",
    )

    summary = MedicalSummary.model_validate(result)
    assert summary.suggested_tests == []
    assert "CBC" not in summary.suggested_tests
    assert "Basic metabolic panel" not in summary.suggested_tests


def test_suggested_tests_are_deduplicated_and_capped():
    """Duplicate tests (case-insensitive) are collapsed, and the list is capped at 4."""
    output = _MedicalSummaryLLMOutput(
        case_summary="Summary.",
        suggested_tests=["ECG", "ecg", "Troponin", "CBC", "CBC", "Chest X-ray", "D-dimer"],
        history_notes="No prior history.",
        doctor_briefing="S: | O: | A: | P:",
    )

    assert output.suggested_tests == ["ECG", "Troponin", "CBC", "Chest X-ray"]