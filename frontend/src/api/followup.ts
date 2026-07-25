import { apiClient } from "./client";
import type { FollowUpPlanDetail } from "@/types/domain";

export async function fetchFollowUpPlan(encounterId: string): Promise<FollowUpPlanDetail> {
  const { data } = await apiClient.get<FollowUpPlanDetail>(`/followup/${encounterId}`);
  return data;
}

export async function scheduleFollowUpPlan(encounterId: string): Promise<FollowUpPlanDetail> {
  const { data } = await apiClient.post<FollowUpPlanDetail>(`/followup/${encounterId}/schedule`);
  return data;
}
