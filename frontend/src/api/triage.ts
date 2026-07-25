import { apiClient } from "./client";
import type { IntakeResponse } from "@/types/domain";

export async function submitTriageClarification(
  encounterId: string,
  answers: string[],
): Promise<IntakeResponse> {
  const { data } = await apiClient.post<IntakeResponse>(
    `/triage/encounters/${encounterId}/clarify`,
    { answers },
  );
  return data;
}
