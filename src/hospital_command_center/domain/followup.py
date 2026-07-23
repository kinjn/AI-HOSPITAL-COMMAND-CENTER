"""Follow-up tasks: reminders, diet guidance, escalation triggers."""

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


def _coerce_str_list(value: object) -> object:
    """Tolerate an LLM returning a single string where a list was expected
    (e.g. "immediate" instead of ["immediate"]) instead of failing plan
    generation outright over a minor formatting slip.
    """
    if isinstance(value, str):
        return [value] if value else []
    return value


class MedicationReminder(BaseModel):
    medication: str
    dosage: str
    frequency: str
    times: list[str] = Field(default_factory=list)
    duration_days: int | None = None
    notes: str | None = None
    priority: str = "medium"  # low, medium, high

    _coerce_times = field_validator("times", mode="before")(_coerce_str_list)


class LabReminder(BaseModel):
    test: str
    due_in_days: int
    instructions: str = ""
    fasting_required: bool = False
    priority: str = "medium"


class DietGuidance(BaseModel):
    summary: str
    recommended: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    hydration_notes: str = ""
    special_instructions: str | None = None
    # False until the patient's veg/non-veg preference and any food allergies
    # have actually been collected. While False, `recommended`/`avoid` must
    # stay empty — no meal-specific advice should be given without this info.
    preferences_confirmed: bool = False

    _coerce_recommended = field_validator("recommended", mode="before")(_coerce_str_list)
    _coerce_avoid = field_validator("avoid", mode="before")(_coerce_str_list)


class EscalationRule(BaseModel):
    trigger: str
    severity: str = "medium"  # medium, high, critical
    action: str
    # Who/what should be alerted, e.g. ["doctor", "emergency_contact", "sms"].
    # NOTE: this field used to be called `notify_on`, which models routinely
    # (and reasonably) misread as "when to notify" rather than "who to
    # notify" and filled with a timing string like "immediate" — that's a
    # str-vs-list mismatch that failed Pydantic validation and took down the
    # entire follow-up plan. Renamed for clarity, and `notify_within` added
    # as the actual place for that timing information.
    notify_channels: list[str] = Field(default_factory=list)
    # How urgently this should be acted on, e.g. "immediate", "within 24 hours".
    notify_within: str = ""
    contact: str | None = None

    _coerce_notify_channels = field_validator("notify_channels", mode="before")(_coerce_str_list)


class ScheduledTask(BaseModel):
    task_type: str  # medication_checkin, lab_reminder, diet_followup, symptom_checkin
    due_at: datetime
    channel: str  # sms, whatsapp, app, email, phone
    auto_dispatch: bool = True
    note: str = ""
    status: str = "pending"  # pending, sent, acknowledged, skipped


class FollowUpPlan(BaseModel):
    encounter_id: UUID
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    medication_reminders: list[MedicationReminder] = Field(default_factory=list)
    lab_reminders: list[LabReminder] = Field(default_factory=list)
    diet_guidance: DietGuidance = Field(default_factory=lambda: DietGuidance(summary="Stub diet guidance."))
    escalation_enabled: bool = True
    escalation_rules: list[EscalationRule] = Field(default_factory=list)
    schedule: list[ScheduledTask] = Field(default_factory=list)
    notes: str = ""
