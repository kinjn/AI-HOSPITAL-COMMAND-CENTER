"""Run triage classification and persist results."""

from uuid import UUID

from hospital_command_center.agents.triage import TriageAgent
from hospital_command_center.domain.triage import TriageResult


class TriageService:
    def __init__(self) -> None:
        self._agent = TriageAgent()

    def classify(self, encounter_id: UUID, symptoms: str, **context) -> TriageResult:
        data = self._agent.run(encounter_id=encounter_id, symptoms=symptoms, **context)
        return TriageResult.model_validate(data)
