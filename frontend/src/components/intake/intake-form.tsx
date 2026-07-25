import * as React from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import type { IntakeFormValues } from "@/types/domain";

/** Mirrors the backend's phone normalization so client-side validation
 * matches exactly what the server will accept (strict 10-digit Indian
 * mobile number, optionally prefixed with +91/91/0). */
function extractIndianMobileDigits(phone: string): string {
  const cleaned = phone.trim();
  const digits = cleaned.startsWith("+")
    ? cleaned.slice(1).replace(/\D/g, "")
    : cleaned.replace(/\D/g, "");
  if (digits.length === 12 && digits.startsWith("91")) return digits.slice(2);
  if (digits.length === 11 && digits.startsWith("0")) return digits.slice(1);
  return digits;
}

interface IntakeFormProps {
  onSubmit: (values: IntakeFormValues) => void;
  disabled?: boolean;
}

type FormErrors = Partial<Record<keyof IntakeFormValues, string>>;

const initialValues: IntakeFormValues = {
  patient_name: "",
  age: "",
  gender: "",
  phone: "",
  symptoms: "",
  dietary_preference: "",
  food_allergies: "",
  known_medical_conditions: "",
};

export function IntakeForm({ onSubmit, disabled }: IntakeFormProps) {
  const [values, setValues] = React.useState<IntakeFormValues>(initialValues);
  const [errors, setErrors] = React.useState<FormErrors>({});

  function update<K extends keyof IntakeFormValues>(key: K, value: IntakeFormValues[K]) {
    setValues((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => ({ ...prev, [key]: undefined }));
  }

  function validate(): FormErrors {
    const next: FormErrors = {};

    const trimmedName = values.patient_name.trim();
    if (!trimmedName) {
      next.patient_name = "Patient name is required.";
    } else if (!/^[A-Za-z\s'\-.]+$/.test(trimmedName)) {
      next.patient_name = "Name may only contain letters, spaces, hyphens, apostrophes, and periods.";
    } else if (trimmedName.split(/\s+/).filter(Boolean).length < 2) {
      next.patient_name = "Enter the patient's full name (first and last name).";
    }

    if (!values.age.trim()) {
      next.age = "Age is required.";
    } else {
      const ageNum = Number(values.age);
      if (!Number.isFinite(ageNum) || ageNum < 0 || ageNum > 150) next.age = "Enter a valid age (0–150).";
    }
    if (!values.gender) next.gender = "Select a gender.";

    if (!values.phone.trim()) {
      next.phone = "Phone number is required.";
    } else {
      const digits = extractIndianMobileDigits(values.phone);
      if (digits.length !== 10) {
        next.phone = "Enter a 10-digit mobile number.";
      } else if (!"6789".includes(digits[0])) {
        next.phone = "Mobile number must start with 6, 7, 8, or 9.";
      }
    }

    if (!values.symptoms.trim()) next.symptoms = "Describe the patient's symptoms.";
    return next;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const nextErrors = validate();
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length === 0) {
      onSubmit(values);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      <div className="grid gap-5 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="patient_name" required>
            Patient name
          </Label>
          <Input
            id="patient_name"
            autoComplete="name"
            placeholder="e.g. Priya Sharma"
            value={values.patient_name}
            onChange={(e) => update("patient_name", e.target.value)}
            error={Boolean(errors.patient_name)}
            aria-invalid={Boolean(errors.patient_name)}
            aria-describedby={errors.patient_name ? "patient_name-error" : undefined}
            disabled={disabled}
          />
          {errors.patient_name && (
            <p id="patient_name-error" className="text-xs text-critical">
              {errors.patient_name}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="age" required>
            Age
          </Label>
          <Input
            id="age"
            type="number"
            min={0}
            max={150}
            inputMode="numeric"
            value={values.age}
            onChange={(e) => update("age", e.target.value)}
            error={Boolean(errors.age)}
            aria-invalid={Boolean(errors.age)}
            aria-describedby={errors.age ? "age-error" : undefined}
            disabled={disabled}
          />
          {errors.age && (
            <p id="age-error" className="text-xs text-critical">
              {errors.age}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="gender" required>
            Gender
          </Label>
          <Select
            id="gender"
            value={values.gender}
            onChange={(e) => update("gender", e.target.value)}
            error={Boolean(errors.gender)}
            aria-invalid={Boolean(errors.gender)}
            aria-describedby={errors.gender ? "gender-error" : undefined}
            disabled={disabled}
          >
            <option value="">Select…</option>
            <option value="female">Female</option>
            <option value="male">Male</option>
            <option value="other">Other</option>
          </Select>
          {errors.gender && (
            <p id="gender-error" className="text-xs text-critical">
              {errors.gender}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="phone" required>
            Phone
          </Label>
          <Input
            id="phone"
            type="tel"
            autoComplete="tel"
            placeholder="10-digit mobile number"
            value={values.phone}
            onChange={(e) => update("phone", e.target.value)}
            error={Boolean(errors.phone)}
            aria-invalid={Boolean(errors.phone)}
            aria-describedby={errors.phone ? "phone-error" : undefined}
            disabled={disabled}
          />
          {errors.phone && (
            <p id="phone-error" className="text-xs text-critical">
              {errors.phone}
            </p>
          )}
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="symptoms" required>
          Symptoms
        </Label>
        <Textarea
          id="symptoms"
          rows={6}
          placeholder="Describe the patient's symptoms, onset, and severity…"
          value={values.symptoms}
          onChange={(e) => update("symptoms", e.target.value)}
          error={Boolean(errors.symptoms)}
          aria-invalid={Boolean(errors.symptoms)}
          aria-describedby={errors.symptoms ? "symptoms-error" : undefined}
          disabled={disabled}
        />
        {errors.symptoms && (
          <p id="symptoms-error" className="text-xs text-critical">
            {errors.symptoms}
          </p>
        )}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="known_medical_conditions">Pre-existing conditions</Label>
        <Input
          id="known_medical_conditions"
          placeholder="e.g. Type 2 diabetes, hypertension (or leave blank)"
          value={values.known_medical_conditions}
          onChange={(e) => update("known_medical_conditions", e.target.value)}
          disabled={disabled}
        />
        <p className="text-xs text-muted-foreground">Optional — helps triage and the clinical summary account for existing conditions.</p>
      </div>

      <div className="space-y-4 rounded-md border border-border bg-muted/30 p-4">
        <div>
          <p className="text-sm font-medium text-foreground">Dietary information</p>
          <p className="text-xs text-muted-foreground">
            Optional — provide this now so follow-up meal guidance can be specific instead of generic.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="dietary_preference">Dietary preference</Label>
            <Select
              id="dietary_preference"
              value={values.dietary_preference}
              onChange={(e) => update("dietary_preference", e.target.value)}
              disabled={disabled}
            >
              <option value="">Not specified</option>
              <option value="vegetarian">Vegetarian</option>
              <option value="non-vegetarian">Non-vegetarian</option>
              <option value="vegan">Vegan</option>
              <option value="other">Other</option>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="food_allergies">Known food allergies</Label>
            <Input
              id="food_allergies"
              placeholder="e.g. peanuts, shellfish (or leave blank)"
              value={values.food_allergies}
              onChange={(e) => update("food_allergies", e.target.value)}
              disabled={disabled}
            />
          </div>
        </div>
      </div>

      <Button type="submit" size="lg" disabled={disabled} className="w-full sm:w-auto">
        Start Intake
      </Button>
    </form>
  );
}
