"""Unit tests for triage clarification domain and workflow routing."""

from uuid import uuid4

import pytest

from hospital_command_center.domain.triage import (
    MAX_CLARIFYING_QUESTIONS,
    TriageClarificationSubmission,
    TriageResult,
    TriageStatus,
    UrgencyLevel,
)
from hospital_command_center.graphs.edges import after_triage


class TestTriageResult:
    def test_complete_requires_urgency(self) -> None:
        with pytest.raises(ValueError, match="urgency is required"):
            TriageResult(
                encounter_id=uuid4(),
                status=TriageStatus.COMPLETE,
                rationale="Enough detail to classify.",
            )

    def test_needs_clarification_requires_questions(self) -> None:
        with pytest.raises(ValueError, match="clarifying_questions required"):
            TriageResult(
                encounter_id=uuid4(),
                status=TriageStatus.NEEDS_CLARIFICATION,
                rationale="Symptoms are too vague.",
            )

    def test_questions_capped_at_two(self) -> None:
        result = TriageResult(
            encounter_id=uuid4(),
            status=TriageStatus.NEEDS_CLARIFICATION,
            rationale="Need more detail about pain and duration.",
            clarifying_questions=["Q1", "Q2", "Q3"],
        )
        assert len(result.clarifying_questions) == MAX_CLARIFYING_QUESTIONS

    def test_complete_result(self) -> None:
        result = TriageResult(
            encounter_id=uuid4(),
            status=TriageStatus.COMPLETE,
            urgency=UrgencyLevel.HIGH,
            rationale="High fever with spreading rash in a child.",
        )
        assert result.status == TriageStatus.COMPLETE
        assert result.urgency == UrgencyLevel.HIGH


class TestTriageClarificationSubmission:
    def test_rejects_blank_answers(self) -> None:
        with pytest.raises(ValueError):
            TriageClarificationSubmission(answers=["  "])

    def test_accepts_up_to_two_answers(self) -> None:
        payload = TriageClarificationSubmission(answers=["2 days", "6/10 pain"])
        assert len(payload.answers) == 2


class TestAfterTriageEdge:
    def test_pauses_when_clarification_needed(self) -> None:
        state = {
            "triage": {
                "status": "needs_clarification",
                "clarifying_questions": ["How long?"],
            }
        }
        assert after_triage(state) == "pause"

    def test_continues_when_complete(self) -> None:
        state = {
            "triage": {
                "status": "complete",
                "urgency": "medium",
            }
        }
        assert after_triage(state) == "continue"
