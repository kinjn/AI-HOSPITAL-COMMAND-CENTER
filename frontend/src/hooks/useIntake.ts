import { useMutation, useQueryClient } from "@tanstack/react-query";
import { submitIntake } from "@/api/intake";
import { submitTriageClarification } from "@/api/triage";
import { encounterKeys } from "./useEncounters";

export function useSubmitIntake() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: submitIntake,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: encounterKeys.all });
    },
  });
}

export function useSubmitTriageClarification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ encounterId, answers }: { encounterId: string; answers: string[] }) =>
      submitTriageClarification(encounterId, answers),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: encounterKeys.all });
    },
  });
}
