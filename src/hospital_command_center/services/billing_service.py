"""Generate insurance docs and cost estimates."""

from typing import Any
from uuid import UUID

from hospital_command_center.agents.billing_insurance import BillingInsuranceAgent
from hospital_command_center.domain.billing import BillingEstimate


class BillingService:
    def __init__(self) -> None:
        self._agent = BillingInsuranceAgent()

    def estimate(self, encounter_id: UUID, **context: Any) -> BillingEstimate:
        data = self._agent.run(encounter_id=encounter_id, **context)
        return BillingEstimate.model_validate(data)
