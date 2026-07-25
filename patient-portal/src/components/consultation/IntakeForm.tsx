import * as React from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Spinner } from "@/components/ui/spinner";
import type { IntakeFormValues } from "@/types/domain";

interface IntakeFormProps {
  initialValues: IntakeFormValues;
  onSubmit: (values: IntakeFormValues) => void;
  isSubmitting: boolean;
}

type FormErrors = Partial<Record<keyof IntakeFormValues, string>>;

export function IntakeForm({ initialValues, onSubmit, isSubmitting }: IntakeFormProps) {
  const [values, setValues] = React.useState<IntakeFormValues>(initialValues);
  const [errors, setErrors] = React.useState<FormErrors>({});

  function update<K extends keyof IntakeFormValues>(key: K, value: IntakeFormValues[K]) {
    setValues((v) => ({ ...v, [key]: value }));
    setErrors((e) => ({ ...e, [key]: undefined }));
  }

  function validate(): boolean {
    const next: FormErrors = {};
    if (!values.patient_name.trim()) next.patient_name = "Please enter your name.";
    const age = Number(values.age);
    if (!values.age || Number.isNaN(age) || age <= 0 || age > 130) next.age = "Enter a valid age.";
    if (!values.gender) next.gender = "Please select a gender.";
    if (!/^[0-9+\-\s]{7,15}$/.test(values.phone.trim())) next.phone = "Enter a valid phone number.";
    if (values.symptoms.trim().length < 10) next.symptoms = "Please describe your symptoms in a bit more detail.";
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (validate()) onSubmit(values);
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      <div className="grid gap-5 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="patient_name">Full name</Label>
          <Input
            id="patient_name"
            value={values.patient_name}
            onChange={(e) => update("patient_name", e.target.value)}
            invalid={!!errors.patient_name}
            placeholder="Jordan Lee"
            autoComplete="name"
          />
          {errors.patient_name && <p className="text-xs text-destructive">{errors.patient_name}</p>}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="phone">Phone number</Label>
          <Input
            id="phone"
            value={values.phone}
            onChange={(e) => update("phone", e.target.value)}
            invalid={!!errors.phone}
            placeholder="+1 555 010 1234"
            autoComplete="tel"
            inputMode="tel"
          />
          {errors.phone && <p className="text-xs text-destructive">{errors.phone}</p>}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="age">Age</Label>
          <Input
            id="age"
            type="number"
            min={0}
            max={130}
            value={values.age}
            onChange={(e) => update("age", e.target.value)}
            invalid={!!errors.age}
            placeholder="34"
          />
          {errors.age && <p className="text-xs text-destructive">{errors.age}</p>}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="gender">Gender</Label>
          <Select
            id="gender"
            value={values.gender}
            onChange={(e) => update("gender", e.target.value)}
            invalid={!!errors.gender}
          >
            <option value="">Select…</option>
            <option value="female">Female</option>
            <option value="male">Male</option>
            <option value="other">Other</option>
            <option value="prefer_not_to_say">Prefer not to say</option>
          </Select>
          {errors.gender && <p className="text-xs text-destructive">{errors.gender}</p>}
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="symptoms">What's going on?</Label>
        <Textarea
          id="symptoms"
          value={values.symptoms}
          onChange={(e) => update("symptoms", e.target.value)}
          invalid={!!errors.symptoms}
          placeholder="Tell us what you're experiencing — when it started, how severe it feels, and anything that makes it better or worse."
          rows={6}
        />
        <div className="flex items-center justify-between">
          {errors.symptoms ? (
            <p className="text-xs text-destructive">{errors.symptoms}</p>
          ) : (
            <p className="text-xs text-muted-foreground">The more detail you share, the more accurate your care plan will be.</p>
          )}
        </div>
      </div>

      <div className="space-y-1.5 rounded-md border border-border bg-muted/30 p-4">
        <Label htmlFor="known_medical_conditions">Prior medical history</Label>
        <Textarea
          id="known_medical_conditions"
          value={values.known_medical_conditions}
          onChange={(e) => update("known_medical_conditions", e.target.value)}
          placeholder="e.g. Type 2 diabetes, hypertension, past surgeries — or leave blank"
          rows={3}
        />
        <p className="text-xs text-muted-foreground">
          Optional — share any pre-existing conditions so your medical summary and follow-up guidance take them
          into account.
        </p>
      </div>

      <div className="rounded-lg bg-muted/60 px-4 py-3 text-xs text-muted-foreground">
        If you're experiencing a medical emergency — such as chest pain, difficulty breathing, or severe bleeding —
        please call your local emergency number or go to the nearest emergency room right away.
      </div>

      <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
        {isSubmitting ? (
          <>
            <Spinner /> Submitting…
          </>
        ) : (
          <>
            <Send /> Submit Consultation
          </>
        )}
      </Button>
    </form>
  );
}
