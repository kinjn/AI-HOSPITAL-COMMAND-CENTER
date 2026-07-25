import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  acceptInsuranceDocumentRequest,
  approveBilling,
  fetchEncounterById,
  fetchEncounters,
  rejectInsuranceDocumentRequest,
  updateDietaryPreference,
} from "@/api/encounters";
import type { DietaryUpdatePayload } from "@/api/encounters";

export const encounterKeys = {
  all: ["encounters"] as const,
  detail: (id: string) => ["encounters", id] as const,
};

/** Auto-refreshes every 15s per the operations dashboard spec, while
 * keeping previously loaded data on screen (no flash/loss of scroll or
 * filter state) via `placeholderData`. */
export function useEncounters() {
  return useQuery({
    queryKey: encounterKeys.all,
    queryFn: fetchEncounters,
    refetchInterval: 15_000,
    refetchIntervalInBackground: true,
    placeholderData: (previous) => previous,
    staleTime: 10_000,
  });
}

export function useEncounterDetail(id: string | undefined) {
  return useQuery({
    queryKey: encounterKeys.detail(id ?? ""),
    queryFn: () => fetchEncounterById(id as string),
    enabled: Boolean(id),
    refetchInterval: 15_000,
  });
}

export function useUpdateDietaryPreference(encounterId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DietaryUpdatePayload) => updateDietaryPreference(encounterId as string, payload),
    onSuccess: () => {
      if (encounterId) queryClient.invalidateQueries({ queryKey: encounterKeys.detail(encounterId) });
      queryClient.invalidateQueries({ queryKey: encounterKeys.all });
    },
  });
}

export function useApproveBilling(encounterId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => approveBilling(encounterId as string),
    onSuccess: (detail) => {
      if (encounterId) queryClient.setQueryData(encounterKeys.detail(encounterId), detail);
      queryClient.invalidateQueries({ queryKey: encounterKeys.all });
    },
  });
}

export function useAcceptInsuranceDocument(encounterId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => acceptInsuranceDocumentRequest(encounterId as string),
    onSuccess: (detail) => {
      if (encounterId) queryClient.setQueryData(encounterKeys.detail(encounterId), detail);
      queryClient.invalidateQueries({ queryKey: encounterKeys.all });
    },
  });
}

export function useRejectInsuranceDocument(encounterId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => rejectInsuranceDocumentRequest(encounterId as string),
    onSuccess: (detail) => {
      if (encounterId) queryClient.setQueryData(encounterKeys.detail(encounterId), detail);
      queryClient.invalidateQueries({ queryKey: encounterKeys.all });
    },
  });
}
