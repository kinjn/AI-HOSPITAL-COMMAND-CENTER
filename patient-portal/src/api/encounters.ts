import { apiClient } from "./client";
import type { PatientEncounterDetail } from "@/types/domain";

/**
 * GET /patient/encounter/{tracking_id} -> PatientEncounterDetail
 *
 * This is the only way this app ever reads encounter data. There is no
 * endpoint anywhere in this app that lists multiple encounters — a patient
 * can only ever fetch the single encounter whose Tracking ID they provide.
 * The backend validates the Tracking ID and returns only the matching
 * encounter (404 if it doesn't resolve to one); the response never
 * includes raw internal database ids.
 */
export async function getEncounterByTrackingId(trackingId: string): Promise<PatientEncounterDetail> {
  const { data } = await apiClient.get<PatientEncounterDetail>(
    `/patient/encounter/${encodeURIComponent(trackingId.trim())}`,
  );
  return data;
}

export interface DietaryUpdatePayload {
  dietary_preference?: string;
  food_allergies?: string;
}

/**
 * PATCH /patient/encounter/{tracking_id}/dietary -> PatientEncounterDetail
 *
 * Tracking-ID-addressed counterpart to the Staff Portal's
 * PATCH /encounters/{id}/dietary. Lets a patient confirm dietary
 * preference / food allergies after the fact, when the follow-up plan's
 * diet guidance is waiting on that (diet_guidance.preferences_confirmed).
 */
export async function updateDietaryPreference(
  trackingId: string,
  payload: DietaryUpdatePayload,
): Promise<PatientEncounterDetail> {
  const { data } = await apiClient.patch<PatientEncounterDetail>(
    `/patient/encounter/${encodeURIComponent(trackingId.trim())}/dietary`,
    payload,
  );
  return data;
}

/**
 * POST /patient/encounter/{tracking_id}/insurance-document/request -> PatientEncounterDetail
 *
 * The "Demand insurance document" button. Flags the encounter's insurance
 * document as awaiting hospital sign-off; the Staff Portal then Accepts
 * (document becomes downloadable here) or Rejects (a rejection message is
 * shown here instead) the request.
 */
export async function requestInsuranceDocument(trackingId: string): Promise<PatientEncounterDetail> {
  const { data } = await apiClient.post<PatientEncounterDetail>(
    `/patient/encounter/${encodeURIComponent(trackingId.trim())}/insurance-document/request`,
  );
  return data;
}
