import { apiClient } from "./client";
import type { EncounterDetail, EncounterListResponse } from "@/types/domain";

export async function fetchEncounters(): Promise<EncounterListResponse> {
  const { data } = await apiClient.get<EncounterListResponse>("/encounters");
  return data;
}

export async function fetchEncounterById(id: string): Promise<EncounterDetail> {
  const { data } = await apiClient.get<EncounterDetail>(`/encounters/${id}`);
  return data;
}

export interface DietaryUpdatePayload {
  dietary_preference?: string | null;
  food_allergies?: string | null;
}

export async function updateDietaryPreference(
  encounterId: string,
  payload: DietaryUpdatePayload,
): Promise<EncounterDetail> {
  const { data } = await apiClient.patch<EncounterDetail>(`/encounters/${encounterId}/dietary`, payload);
  return data;
}

/** Marks the encounter's latest billing record approved and closes the
 * encounter (status -> "closed"). Backend: POST /encounters/{id}/billing/approve. */
export async function approveBilling(encounterId: string): Promise<EncounterDetail> {
  const { data } = await apiClient.post<EncounterDetail>(`/encounters/${encounterId}/billing/approve`);
  return data;
}

/** Accepts a patient's pending "Demand insurance document" request — the
 * document becomes visible/downloadable on the Patient Portal.
 * Backend: POST /encounters/{id}/insurance-document/accept. */
export async function acceptInsuranceDocumentRequest(encounterId: string): Promise<EncounterDetail> {
  const { data } = await apiClient.post<EncounterDetail>(`/encounters/${encounterId}/insurance-document/accept`);
  return data;
}

/** Rejects a patient's pending "Demand insurance document" request — the
 * Patient Portal shows a rejection message instead of the document.
 * Backend: POST /encounters/{id}/insurance-document/reject. */
export async function rejectInsuranceDocumentRequest(encounterId: string): Promise<EncounterDetail> {
  const { data } = await apiClient.post<EncounterDetail>(`/encounters/${encounterId}/insurance-document/reject`);
  return data;
}
