"""SQLAlchemy table models.

Import order matters — all models must be imported here before any
relationship is resolved to avoid forward-reference errors.
"""

from hospital_command_center.db.models.patient import PatientModel
from hospital_command_center.db.models.doctor import DoctorModel
from hospital_command_center.db.models.encounter import EncounterModel
from hospital_command_center.db.models.triage_result import TriageResultModel
from hospital_command_center.db.models.case_summary import CaseSummaryModel
from hospital_command_center.db.models.billing_record import BillingRecordModel
from hospital_command_center.db.models.appointment import AppointmentModel
from hospital_command_center.db.models.followup import FollowUpModel

__all__ = [
    "PatientModel",
    "DoctorModel",
    "EncounterModel",
    "TriageResultModel",
    "CaseSummaryModel",
    "BillingRecordModel",
    "AppointmentModel",
    "FollowUpModel",
]