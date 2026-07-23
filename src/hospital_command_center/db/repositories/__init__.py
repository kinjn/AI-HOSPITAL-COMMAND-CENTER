"""Repository layer — one repository per model."""

from hospital_command_center.db.repositories.appointment import AppointmentRepository
from hospital_command_center.db.repositories.billing_record import BillingRecordRepository
from hospital_command_center.db.repositories.case_summary import CaseSummaryRepository
from hospital_command_center.db.repositories.doctor import DoctorRepository
from hospital_command_center.db.repositories.encounter import EncounterRepository
from hospital_command_center.db.repositories.followup import FollowUpRepository
from hospital_command_center.db.repositories.patient import PatientRepository
from hospital_command_center.db.repositories.triage_result import TriageResultRepository

__all__ = [
    "AppointmentRepository",
    "BillingRecordRepository",
    "CaseSummaryRepository",
    "DoctorRepository",
    "EncounterRepository",
    "FollowUpRepository",
    "PatientRepository",
    "TriageResultRepository",
]