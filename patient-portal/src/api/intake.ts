import { apiClient } from "./client";
import type { IntakeFormValues, TrackingSubmissionResult } from "@/types/domain";

/**
 * REQUIRED BACKEND ENDPOINT (not yet implemented — see BACKEND_REQUIREMENTS.md):
 *   POST /patient/intake -> TrackingSubmissionResult
 *
 * A thin wrapper around the existing, unmodified POST /intake/web /
 * workflow.start_from_intake logic. The only difference from the existing
 * endpoint is the response: instead of returning the raw internal
 * encounter_id/patient_id, it issues (and returns) a short, human-friendly
 * Tracking ID — e.g. "HCC-83AF92" — that the patient saves and uses to look
 * up this one encounter later. No business logic changes.
 */
export async function submitConsultation(values: IntakeFormValues): Promise<TrackingSubmissionResult> {
  const { data } = await apiClient.post<TrackingSubmissionResult>("/patient/intake", {
    patient_name: values.patient_name,
    age: values.age ? Number(values.age) : undefined,
    gender: values.gender || undefined,
    phone: values.phone,
    symptoms: values.symptoms,
    known_medical_conditions: values.known_medical_conditions.trim() || undefined,
  });
  return data;
}
