import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getEncounterByTrackingId,
  requestInsuranceDocument,
  updateDietaryPreference,
  type DietaryUpdatePayload,
} from "@/api/encounters";

/** The only encounter read hook in this app — always scoped to one Tracking ID. */
export function useEncounterByTrackingId(trackingId: string | undefined) {
  return useQuery({
    queryKey: ["encounter", trackingId],
    queryFn: () => getEncounterByTrackingId(trackingId!),
    enabled: !!trackingId,
    retry: false,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      const stillProcessing = status && !["billing_ready", "closed"].includes(status);
      return stillProcessing ? 4_000 : false;
    },
  });
}

/** Confirms dietary preference / allergies for one encounter and refreshes its cached detail with the response. */
export function useUpdateDietaryPreference(trackingId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DietaryUpdatePayload) => updateDietaryPreference(trackingId!, payload),
    onSuccess: (detail) => {
      if (trackingId) queryClient.setQueryData(["encounter", trackingId], detail);
    },
  });
}

/** The "Demand insurance document" button. Flags the request as pending
 * for the Staff Portal to Accept/Reject, and refreshes the cached detail
 * with the response so the pending state shows immediately. */
export function useRequestInsuranceDocument(trackingId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => requestInsuranceDocument(trackingId!),
    onSuccess: (detail) => {
      if (trackingId) queryClient.setQueryData(["encounter", trackingId], detail);
    },
  });
}
