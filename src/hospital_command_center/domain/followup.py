"""Follow-up tasks: reminders, diet guidance, escalation triggers."""

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field


class MedicationReminder(BaseModel):
    medication: str
    dosage: str
    frequency: str
    times: list[str] = Field(default_factory=list)
    duration_days: int | None = None
    notes: str | None = None
    priority: str = "medium"  # low, medium, high


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


class EscalationRule(BaseModel):
    trigger: str
    severity: str = "medium"  # medium, high, critical
    action: str
    notify_on: list[str] = Field(default_factory=list)
    contact: str | None = None


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
