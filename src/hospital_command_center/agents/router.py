"""Router agent: selects care pathway (emergency, OPD, teleconsultation, specialist)."""

from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from hospital_command_center.agents.base import BaseAgent
from hospital_command_center.agents.structured_output import invoke_structured
from hospital_command_center.core.exceptions import NotConfiguredError, RoutingError
from hospital_command_center.domain.triage import TriageResult, UrgencyLevel
from hospital_command_center.domain.workflow import CarePathway, RoutingDecision
from hospital_command_center.prompts import load_prompt


class _RouterLLMOutput(BaseModel):
    pathway: CarePathway
    notes: str = Field(..., min_length=10, max_length=2000)


class RouterAgent(BaseAgent):
    name = "router"

    def run(
        self,
        *,
        encounter_id: UUID,
        symptoms: str = "",
        triage: dict[str, Any] | None = None,
        patient_name: str | None = None,
        age: int | None = None,
        gender: str | None = None,
        channel: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        triage_result = self._parse_triage(encounter_id, triage)

        user_lines: list[str] = []
        if triage_result:
            user_lines.append(f"Triage urgency: {triage_result.urgency.value}")
            user_lines.append(f"Triage rationale: {triage_result.rationale}")
        if symptoms.strip():
            user_lines.append(f"Symptoms: {symptoms.strip()}")
        if patient_name:
            user_lines.append(f"Patient name: {patient_name}")
        if age is not None:
            user_lines.append(f"Age: {age}")
        if gender:
            user_lines.append(f"Gender: {gender}")
        if channel:
            user_lines.append(f"Intake channel: {channel}")

        if not user_lines:
            raise RoutingError("Insufficient context for routing (need triage and/or symptoms).")

        messages = [
            SystemMessage(content=load_prompt("router")),
            HumanMessage(content="\n".join(user_lines)),
        ]

        try:
            output = invoke_structured(_RouterLLMOutput, messages)
        except NotConfiguredError:
            raise
        except Exception as exc:
            raise RoutingError(f"LLM routing failed: {exc}") from exc

        pathway, notes = self._apply_safety_rules(triage_result, output.pathway, output.notes)
        result = RoutingDecision(encounter_id=encounter_id, pathway=pathway, notes=notes)
        return result.model_dump(mode="json")

    @staticmethod
    def _parse_triage(encounter_id: UUID, raw: dict[str, Any] | None) -> TriageResult | None:
        if isinstance(raw, dict) and raw:
            return TriageResult.model_validate(raw)
        return None

    @staticmethod
    def _apply_safety_rules(
        triage: TriageResult | None,
        pathway: CarePathway,
        notes: str,
    ) -> tuple[CarePathway, str]:
        if triage is None:
            return pathway, notes

        if triage.urgency == UrgencyLevel.CRITICAL and pathway != CarePathway.EMERGENCY:
            return (
                CarePathway.EMERGENCY,
                f"Safety override: critical triage requires emergency care. LLM suggested {pathway.value}. {notes}",
            )

        if triage.urgency == UrgencyLevel.HIGH and pathway == CarePathway.TELECONSULTATION:
            return (
                CarePathway.OPD,
                f"Safety override: high urgency requires in-person evaluation. {notes}",
            )

        return pathway, notes
