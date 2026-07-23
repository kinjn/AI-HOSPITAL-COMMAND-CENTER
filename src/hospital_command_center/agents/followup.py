"""Follow-up agent: reminders, diet guidance, escalation rules using LLM.

This agent deliberately does not trust the LLM to police itself on three
safety-sensitive behaviors:

1. It must never invent lab tests beyond what the medical summarizer agent
   already suggested.
2. It must never give specific meal/food guidance before the patient's
   dietary preference (veg/non-veg/vegan/etc.) and food allergies are known.
3. It must never emit generic, one-size-fits-all hydration advice
   ("drink 8 glasses of water") unless the case actually calls for it.

The prompt asks the LLM to follow these rules, but `_apply_safety_constraints`
enforces them deterministically afterward, on both the structured-output path
and the manual-JSON-parsing fallback path, so a non-compliant LLM response
can't leak unsafe content into the final plan.
"""

import json
import re
from typing import Any
from datetime import datetime, timezone
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate

from hospital_command_center.agents.base import BaseAgent
from hospital_command_center.agents.llm import get_chat_model
from hospital_command_center.core.logging import get_logger
from hospital_command_center.domain.followup import DietGuidance, FollowUpPlan
from pathlib import Path

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "followup.md"

logger = get_logger(__name__)

_VALID_PRIORITIES = {"low", "medium", "high"}
_VALID_SEVERITIES = {"low", "medium", "high", "critical"}
_VALID_STATUSES = {"pending", "sent", "acknowledged", "skipped"}

# Values that mean "we don't actually know the patient's dietary preference yet".
_UNKNOWN_DIET_VALUES = {"", "not provided", "unknown", "none", "n/a", "na", "not specified"}

# Keywords that indicate fluid intake is actually clinically relevant for this case.
# If none of these show up in the symptoms/summary, hydration_notes gets cleared —
# this is what stops the agent from defaulting to a generic "drink 8 glasses" line.
_HYDRATION_RELEVANT_KEYWORDS = [
    "fever", "vomit", "diarrh", "dehydrat", "kidney", "stone", "urin", "uti",
    "heat", "sweat", "sweating", "diabetes", "diabetic", "surger", "post-op",
    "postop", "burn", "blood loss", "hemorrhage", "sepsis", "electrolyte",
]

# Lightweight keyword blocklist for enforcing veg/vegan preference and known
# allergies against whatever the LLM proposes as "recommended" foods. This is
# a best-effort safety net, not a substitute for the prompt-level instruction.
_NON_VEG_KEYWORDS = [
    "chicken", "mutton", "beef", "pork", "fish", "prawn", "shrimp", "meat",
    "bacon", "sausage", "lamb", "turkey", "seafood", "crab", "egg",
]
_VEGAN_ONLY_EXTRA_KEYWORDS = ["milk", "dairy", "cheese", "paneer", "yogurt", "curd", "ghee", "butter", "honey"]


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower()


def _dietary_preference_known(dietary_preference: str | None) -> bool:
    return _normalize(dietary_preference) not in _UNKNOWN_DIET_VALUES


def _matches_any(text: str, keywords: list[str]) -> bool:
    text = text.lower()
    return any(keyword in text for keyword in keywords)


def _filter_lab_reminders(plan: FollowUpPlan, suggested_tests: list[str]) -> None:
    """Keep only lab reminders that correspond to a test the summarizer actually suggested."""
    allowed = [_normalize(t) for t in suggested_tests if t and _normalize(t)]
    if not allowed:
        if plan.lab_reminders:
            logger.info(
                "Dropping %d lab reminder(s) not suggested by the summarizer",
                len(plan.lab_reminders),
            )
        plan.lab_reminders = []
        return

    kept = []
    for reminder in plan.lab_reminders:
        test_name = _normalize(reminder.test)
        if any(test_name in a or a in test_name for a in allowed):
            kept.append(reminder)
        else:
            logger.info("Dropping hallucinated lab reminder not in summarizer output: %s", reminder.test)
    plan.lab_reminders = kept


def _gate_diet_guidance(
    plan: FollowUpPlan,
    dietary_preference: str | None,
    food_allergies: str | None,
) -> None:
    """Ensure meal-specific advice never appears before we know what the patient can eat."""
    if not _dietary_preference_known(dietary_preference):
        plan.diet_guidance = DietGuidance(
            summary=(
                "Please confirm the patient's dietary preference (vegetarian / "
                "non-vegetarian / vegan / other) and any known food allergies "
                "before specific meal guidance can be provided."
            ),
            recommended=[],
            avoid=[],
            hydration_notes="",
            special_instructions=None,
            preferences_confirmed=False,
        )
        return

    plan.diet_guidance.preferences_confirmed = True

    pref = _normalize(dietary_preference)
    blocked_keywords: list[str] = []
    if "vegan" in pref:
        blocked_keywords = _NON_VEG_KEYWORDS + _VEGAN_ONLY_EXTRA_KEYWORDS
    elif "veg" in pref and "non" not in pref and "nonveg" not in pref.replace(" ", ""):
        # covers "veg", "vegetarian" but not "non-veg"/"non vegetarian"
        blocked_keywords = _NON_VEG_KEYWORDS

    allergy_terms = [t.strip().lower() for t in re.split(r"[,;/]", food_allergies or "") if t.strip()]

    def is_safe(item: str) -> bool:
        item_l = item.lower()
        if any(kw in item_l for kw in blocked_keywords):
            return False
        if any(term and term in item_l for term in allergy_terms):
            return False
        return True

    removed = [item for item in plan.diet_guidance.recommended if not is_safe(item)]
    if removed:
        logger.info("Removing diet recommendations conflicting with preference/allergies: %s", removed)
    plan.diet_guidance.recommended = [item for item in plan.diet_guidance.recommended if is_safe(item)]


def _gate_hydration_notes(plan: FollowUpPlan, symptoms: str, medical_summary: str) -> None:
    """Strip hydration advice unless the case actually indicates it's relevant."""
    context = f"{symptoms}\n{medical_summary}"
    if plan.diet_guidance.hydration_notes and not _matches_any(context, _HYDRATION_RELEVANT_KEYWORDS):
        logger.info("Clearing non-clinically-justified hydration notes")
        plan.diet_guidance.hydration_notes = ""


def _apply_safety_constraints(
    plan: FollowUpPlan,
    *,
    encounter_id: UUID,
    symptoms: str,
    medical_summary: str,
    suggested_tests: list[str],
    dietary_preference: str | None,
    food_allergies: str | None,
) -> FollowUpPlan:
    plan.encounter_id = encounter_id
    plan.generated_at = datetime.now(timezone.utc)

    for reminder in plan.medication_reminders:
        if reminder.priority not in _VALID_PRIORITIES:
            reminder.priority = "medium"
    for reminder in plan.lab_reminders:
        if reminder.priority not in _VALID_PRIORITIES:
            reminder.priority = "medium"
    for rule in plan.escalation_rules:
        if rule.severity not in _VALID_SEVERITIES:
            rule.severity = "medium"
    for task in plan.schedule:
        if task.status not in _VALID_STATUSES:
            task.status = "pending"

    _filter_lab_reminders(plan, suggested_tests)
    _gate_diet_guidance(plan, dietary_preference, food_allergies)
    _gate_hydration_notes(plan, symptoms, medical_summary)

    return plan


class FollowUpAgent(BaseAgent):
    name = "followup"

    def __init__(self) -> None:
        self.llm = get_chat_model()
        with open(_PROMPT_PATH, "r") as f:
            self.prompt_template = f.read()

    def run(
        self,
        *,
        encounter_id: UUID,
        symptoms: str = "Not provided",
        urgency: str = "Not provided",
        medical_summary: str = "Not provided",
        suggested_tests: list[str] | None = None,
        dietary_preference: str | None = None,
        food_allergies: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        logger.info("Running FollowUpAgent", extra={"encounter_id": str(encounter_id)})
        suggested_tests = suggested_tests or []
        current_time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        prompt = PromptTemplate.from_template(self.prompt_template).format(
            symptoms=symptoms,
            urgency=urgency,
            medical_summary=medical_summary,
            suggested_tests=", ".join(suggested_tests) if suggested_tests else "None",
            dietary_preference=dietary_preference or "Not provided",
            food_allergies=food_allergies or "None reported",
            current_time=current_time_str,
        )

        structured_llm = self.llm.with_structured_output(FollowUpPlan, method="json_schema")

        try:
            plan = structured_llm.invoke(prompt)
            plan = _apply_safety_constraints(
                plan,
                encounter_id=encounter_id,
                symptoms=symptoms,
                medical_summary=medical_summary,
                suggested_tests=suggested_tests,
                dietary_preference=dietary_preference,
                food_allergies=food_allergies,
            )
            return plan.model_dump(mode="json")
        except Exception as e:
            logger.warning("Structured output failed, falling back to manual parsing", extra={"error": str(e)})

            messages = [
                SystemMessage(content="You are a medical coordination assistant. Output ONLY valid JSON."),
                HumanMessage(content=prompt),
            ]
            response = self.llm.invoke(messages)
            content = response.content

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            try:
                data = json.loads(content)
                data["encounter_id"] = str(encounter_id)
                plan = FollowUpPlan.model_validate(data)
                plan = _apply_safety_constraints(
                    plan,
                    encounter_id=encounter_id,
                    symptoms=symptoms,
                    medical_summary=medical_summary,
                    suggested_tests=suggested_tests,
                    dietary_preference=dietary_preference,
                    food_allergies=food_allergies,
                )
                return plan.model_dump(mode="json")
            except Exception as e2:
                logger.error("All follow-up generation methods failed", extra={"error": str(e2)})
                fallback = FollowUpPlan(
                    encounter_id=encounter_id,
                    notes="Generic follow-up plan generated due to processing error.",
                )
                # Even the error-path fallback must respect the "ask before advising" rule.
                fallback = _apply_safety_constraints(
                    fallback,
                    encounter_id=encounter_id,
                    symptoms=symptoms,
                    medical_summary=medical_summary,
                    suggested_tests=suggested_tests,
                    dietary_preference=dietary_preference,
                    food_allergies=food_allergies,
                )
                return fallback.model_dump(mode="json")
