"""Normalize and persist patient symptom submissions."""

from hospital_command_center.domain.encounter import Encounter, EncounterStatus
from hospital_command_center.domain.intake import IntakeSubmission


class IntakeService:
    def submit(self, payload: IntakeSubmission) -> Encounter:
        return Encounter(
            patient_id=payload.patient_id,
            symptoms=payload.symptoms,
            status=EncounterStatus.INTAKE,
        )
