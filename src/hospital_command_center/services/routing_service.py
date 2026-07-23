"""Apply routing rules and enqueue pathway-specific actions."""

from typing import Any
from uuid import UUID

from hospital_command_center.agents.router import RouterAgent
from hospital_command_center.domain.workflow import RoutingDecision


class RoutingService:
    def __init__(self) -> None:
        self._agent = RouterAgent()

    def route(self, encounter_id: UUID, **context: Any) -> RoutingDecision:
        data = self._agent.run(encounter_id=encounter_id, **context)
        return RoutingDecision.model_validate(data)
