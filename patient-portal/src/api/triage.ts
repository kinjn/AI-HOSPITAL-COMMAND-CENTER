import { apiClient } from "./client";
import type { TrackingSubmissionResult } from "@/types/domain";

/**
 * REQUIRED BACKEND ENDPOINT (not yet implemented — see BACKEND_REQUIREMENTS.md):
 *   POST /patient/encounter/{tracking_id}/clarify -> TrackingSubmissionResult
 *
 * A Tracking-ID-addressed counterpart to the existing
 * POST /triage/encounters/{encounter_id}/clarify. Same
 * TriageClarificationSubmission body and workflow.continue_triage logic
 * underneath — the backend just resolves tracking_id -> encounter_id first
 * instead of taking the internal id directly from the client.
 */
export async function submitTriageClarification(
  trackingId: string,
  answers: string[],
): Promise<TrackingSubmissionResult> {
  const { data } = await apiClient.post<TrackingSubmissionResult>(
    `/patient/encounter/${trackingId}/clarify`,
    { answers },
  );
  return data;
}
