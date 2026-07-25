import { apiClient } from "./client";
import type { IntakeFormValues, IntakeResponse } from "@/types/domain";

export async function submitIntake(values: IntakeFormValues): Promise<IntakeResponse> {
  const { data } = await apiClient.post<IntakeResponse>("/intake/web", {
    patient_name: values.patient_name.trim(),
    age: values.age ? Number(values.age) : null,
    gender: values.gender || null,
    phone: values.phone.trim(),
    symptoms: values.symptoms.trim(),
    dietary_preference: values.dietary_preference || null,
    food_allergies: values.food_allergies.trim() || null,
    known_medical_conditions: values.known_medical_conditions.trim() || null,
  });
  return data;
}
