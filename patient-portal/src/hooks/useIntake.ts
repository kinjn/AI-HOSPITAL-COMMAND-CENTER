import { useMutation } from "@tanstack/react-query";
import { submitConsultation } from "@/api/intake";
import type { IntakeFormValues } from "@/types/domain";

export function useSubmitConsultation() {
  return useMutation({
    mutationFn: (values: IntakeFormValues) => submitConsultation(values),
  });
}
