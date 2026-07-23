"""Schedule and dispatch follow-up automations."""

import json
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.agents.followup import FollowUpAgent
from hospital_command_center.db.repositories.case_summary import CaseSummaryRepository
from hospital_command_center.db.repositories.encounter import EncounterRepository
from hospital_command_center.db.repositories.followup import FollowUpRepository
from hospital_command_center.db.repositories.triage_result import TriageResultRepository
from hospital_command_center.domain.followup import FollowUpPlan


class FollowUpService:
    def __init__(self) -> None:
        self._agent = FollowUpAgent()

    def plan(
        self,
        encounter_id: UUID,
        symptoms: str = "Not provided",
        urgency: str = "Not provided",
        medical_summary: str = "Not provided",
        suggested_tests: list[str] | None = None,
        dietary_preference: str | None = None,
        food_allergies: str | None = None,
    ) -> FollowUpPlan:
        data = self._agent.run(
            encounter_id=encounter_id,
            symptoms=symptoms,
            urgency=urgency,
            medical_summary=medical_summary,
            suggested_tests=suggested_tests,
            dietary_preference=dietary_preference,
            food_allergies=food_allergies,
        )
        return FollowUpPlan.model_validate(data)

    async def _load_context_from_db(self, encounter_id: UUID, session: AsyncSession) -> dict:
        """Pull the real triage/summary/intake data for an encounter instead of
        silently falling back to "Not provided" placeholders, which is what
        left this endpoint generating follow-up plans with zero real context.
        """
        encounter_repo = EncounterRepository(session)
        triage_repo = TriageResultRepository(session)
        case_summary_repo = CaseSummaryRepository(session)

        encounter = await encounter_repo.get_by_id(str(encounter_id))
        triage_result = await triage_repo.get_by_encounter_id(str(encounter_id))
        case_summary = await case_summary_repo.get_by_encounter_id(str(encounter_id))

        intake_context: dict = {}
        if encounter and encounter.intake_context_json:
            try:
                intake_context = json.loads(encounter.intake_context_json)
            except json.JSONDecodeError:
                intake_context = {}

        suggested_tests: list[str] = []
        if case_summary and case_summary.suggested_tests_json:
            try:
                suggested_tests = json.loads(case_summary.suggested_tests_json)
            except json.JSONDecodeError:
                suggested_tests = []

        return {
            "symptoms": (encounter.symptoms if encounter and encounter.symptoms else "Not provided"),
            "urgency": (triage_result.urgency_level if triage_result else "Not provided"),
            "medical_summary": (case_summary.summary_text if case_summary and case_summary.summary_text else "Not provided"),
            "suggested_tests": suggested_tests,
            "dietary_preference": intake_context.get("dietary_preference"),
            "food_allergies": intake_context.get("food_allergies"),
        }

    async def plan_from_encounter(self, encounter_id: UUID, session: AsyncSession) -> FollowUpPlan:
        """Build a follow-up plan for an encounter using its real, persisted
        triage/summary/intake data — used by the standalone GET/POST
        `/followup/{encounter_id}` endpoints so they no longer generate plans
        blind (with no symptoms, no urgency, and no summarizer tests).
        """
        context = await self._load_context_from_db(encounter_id, session)
        return self.plan(encounter_id, **context)

    async def plan_and_store_from_encounter(
        self, encounter_id: UUID, session: AsyncSession
    ) -> FollowUpPlan:
        """Build a plan from the encounter's real persisted data and store it —
        used by the `/followup/{encounter_id}/schedule` endpoint.
        """
        context = await self._load_context_from_db(encounter_id, session)
        return await self.plan_and_store(encounter_id, session, **context)

    async def plan_and_store(
        self,
        encounter_id: UUID,
        session: AsyncSession,
        symptoms: str = "Not provided",
        urgency: str = "Not provided",
        medical_summary: str = "Not provided",
        suggested_tests: list[str] | None = None,
        dietary_preference: str | None = None,
        food_allergies: str | None = None,
    ) -> FollowUpPlan:
        plan = self.plan(
            encounter_id,
            symptoms=symptoms,
            urgency=urgency,
            medical_summary=medical_summary,
            suggested_tests=suggested_tests,
            dietary_preference=dietary_preference,
            food_allergies=food_allergies,
        )
        repository = FollowUpRepository(session)
        await repository.create(encounter_id, plan)
        return plan
