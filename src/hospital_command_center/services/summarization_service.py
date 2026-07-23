"""Orchestrate medical summarizer outputs."""

from uuid import UUID

from hospital_command_center.agents.medical_summarizer import MedicalSummarizerAgent
from hospital_command_center.domain.medical import MedicalSummary


class SummarizationService:
    def __init__(self) -> None:
        self._agent = MedicalSummarizerAgent()

    def summarize(self, encounter_id: UUID, symptoms: str = "", **context) -> MedicalSummary:
        """
        Run the medical summarizer agent for an encounter.

        `context` can include: urgency, triage_rationale, patient_name, age,
        prior_history — anything the agent's `run()` accepts as kwargs.
        """
        data = self._agent.run(encounter_id=encounter_id, symptoms=symptoms, **context)
        return MedicalSummary.model_validate(data)
