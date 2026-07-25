/**
 * These mirror the backend response shapes for the tracking-ID based patient
 * endpoints described in BACKEND_REQUIREMENTS.md. There is no patient
 * "account" and no endpoint that lists more than one encounter — every
 * shape here is scoped to a single encounter, reached only via its tracking
 * ID. Internal database ids are intentionally not part of any of these
 * types; the tracking ID is the only identifier the frontend ever handles.
 */

export type Urgency = "low" | "medium" | "high" | "critical";

export type CarePathway = "emergency" | "opd" | "teleconsult" | "specialist";

export type EncounterStatus =
  | "intake"
  | "awaiting_triage_clarification"
  | "triaged"
  | "routed"
  | "summary_ready"
  | "billing_ready"
  | "closed";

export interface TriageDetail {
  urgency_level: Urgency;
  suggested_pathway: CarePathway;
  reasoning: string | null;
}

export interface CaseSummaryDetail {
  summary_text: string;
  suggested_tests: string[];
  extracted_history: string | null;
  doctor_notes: string | null;
}

export interface InsuranceDocument {
  document_type: string;
  reference_number: string;
  generated_at: string | null;
  patient_name: string | null;
  treating_facility: string;
  clinical_indication: string;
  proposed_services: string[];
  estimated_amount_inr: number;
  currency: string;
  icd10_codes: string[];
  cpt_codes: string[];
  coverage_notes: string;
  submission_instructions: string;
  documentation: string | null;
}

export interface BillingRecordDetail {
  estimated_cost: number | null;
  currency: string;
  consultation_fee: number;
  test_cost: number;
  medication_cost: number;
  misc_cost: number;
  preauth_reference: string | null;
  icd10_codes: string[];
  cpt_codes: string[];
  insurance_provider: string | null;
  insurance_document: InsuranceDocument | null;
  status: string;
  insurance_request_status: "requested" | "approved" | "rejected" | null;
  insurance_requested_at: string | null;
  insurance_responded_at: string | null;
  created_at: string | null;
}

export interface FollowUpPlanDetail {
  followup_type: string;
  status: string;
  plan: {
    medication_reminders?: Array<{
      medication: string;
      dosage: string;
      frequency: string;
      times: string[];
      duration_days: number | null;
      notes: string | null;
      priority: string;
    }>;
    lab_reminders?: Array<{
      test: string;
      due_in_days: number;
      instructions: string;
      fasting_required: boolean;
      priority: string;
    }>;
    diet_guidance?: {
      summary: string;
      recommended: string[];
      avoid: string[];
      hydration_notes: string;
      special_instructions: string | null;
      preferences_confirmed: boolean;
    };
    escalation_rules?: Array<{
      trigger: string;
      severity: string;
      action: string;
      notify_channels: string[];
      notify_within: string;
      contact?: string | null;
    }>;
    notes?: string;
  };
  scheduled_at: string | null;
  created_at: string | null;
}

export interface TimelineEntry {
  stage: string;
  label: string;
  at: string | null;
}

/** What the patient submits to start a consultation. No account/tracking-id field — the backend issues one. */
export interface IntakeFormValues {
  patient_name: string;
  age: string;
  gender: string;
  phone: string;
  symptoms: string;
  /** Optional prior/pre-existing medical history (e.g. "Type 2 diabetes, hypertension").
   * Mirrors the Staff Portal's `known_medical_conditions` field — fed to the same
   * backend `IntakeSubmission.known_medical_conditions`, which the medical
   * summarizer and triage agents already use as clinical context, and which
   * flows into the medical summary text the follow-up plan is built from. */
  known_medical_conditions: string;
}

export interface WorkflowStateSnapshot {
  triage?: { status: "complete" | "needs_clarification"; urgency?: Urgency; clarifying_questions?: string[] };
  routing?: { pathway?: CarePathway };
  medical_summary?: CaseSummaryDetail;
  billing?: Record<string, unknown>;
  followup?: Record<string, unknown>;
}

/** Response from POST /patient/intake and POST /patient/encounter/{tracking_id}/clarify. */
export interface TrackingSubmissionResult {
  tracking_id: string;
  status: EncounterStatus;
  pathway: CarePathway | null;
  workflow_state: WorkflowStateSnapshot;
  awaiting_triage_clarification: boolean;
}

/** Response from GET /patient/encounter/{tracking_id}. The only "detail" shape this app ever renders. */
export interface PatientEncounterDetail {
  tracking_id: string;
  patient: {
    full_name: string;
    phone: string | null;
    gender: string | null;
  };
  age: number | null;
  symptoms: string;
  status: EncounterStatus;
  pathway: CarePathway | null;
  urgency: Urgency | null;
  created_at: string | null;
  updated_at: string | null;
  triage: TriageDetail | null;
  case_summary: CaseSummaryDetail | null;
  billing_records: BillingRecordDetail[];
  followups: FollowUpPlanDetail[];
  timeline: TimelineEntry[];
}

/** Patient-facing labels for each clinical workflow stage — no agent/graph names ever surface in the UI. */
export const STAGE_LABELS: Record<string, string> = {
  intake: "Intake complete",
  triage: "Analyzing your symptoms",
  awaiting_triage_clarification: "A quick follow-up question",
  triaged: "Urgency determined",
  routed: "Care pathway selected",
  summary_ready: "Medical summary ready",
  billing_ready: "Billing estimate ready",
  closed: "Consultation complete",
};

export const URGENCY_LABELS: Record<Urgency, string> = {
  low: "Low priority",
  medium: "Moderate priority",
  high: "High priority",
  critical: "Urgent — seek care now",
};

export const PATHWAY_LABELS: Record<CarePathway, string> = {
  emergency: "Emergency care",
  opd: "Outpatient visit",
  teleconsult: "Video consultation",
  specialist: "Specialist referral",
};
