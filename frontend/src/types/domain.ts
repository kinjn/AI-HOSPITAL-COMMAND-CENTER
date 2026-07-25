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

export type IntakeChannel = "whatsapp" | "web" | "mobile_app";

export interface PatientRef {
  id: string | null;
  full_name: string;
  phone: string | null;
  gender: string | null;
}

export interface BillingSummary {
  id: string;
  estimated_cost: number | null;
  currency: string;
  status: "draft" | "submitted" | "approved" | "rejected";
  insurance_provider: string | null;
  insurance_request_status: "requested" | "approved" | "rejected" | null;
  insurance_requested_at: string | null;
  insurance_responded_at: string | null;
  created_at: string | null;
}

export interface FollowUpSummary {
  id: string;
  status: "pending" | "sent" | "acknowledged" | "escalated" | "done";
  followup_type: string;
  scheduled_at: string | null;
  created_at: string | null;
}

export interface EncounterRow {
  id: string;
  patient: PatientRef;
  age: number | null;
  symptoms: string;
  status: EncounterStatus;
  pathway: CarePathway | null;
  source_channel: IntakeChannel;
  urgency: Urgency | null;
  created_at: string | null;
  updated_at: string | null;
  billing: BillingSummary | null;
  followup: FollowUpSummary | null;
}

export interface EncounterListResponse {
  items: EncounterRow[];
}

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
  id: string;
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
  id: string;
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

export interface EncounterDetail extends EncounterRow {
  triage: TriageDetail | null;
  case_summary: CaseSummaryDetail | null;
  billing_records: BillingRecordDetail[];
  followups: FollowUpPlanDetail[];
  timeline: TimelineEntry[];
}

export interface IntakeFormValues {
  patient_name: string;
  age: string;
  gender: string;
  phone: string;
  symptoms: string;
  dietary_preference: string;
  food_allergies: string;
  known_medical_conditions: string;
}

export interface TriageConversationTurn {
  question: string;
  answer: string | null;
}

export interface WorkflowStateSnapshot {
  triage?: { status: "complete" | "needs_clarification"; urgency?: Urgency; clarifying_questions?: string[] };
  triage_conversation?: TriageConversationTurn[];
  routing?: { pathway?: CarePathway };
  medical_summary?: CaseSummaryDetail;
  billing?: Record<string, unknown>;
  followup?: Record<string, unknown>;
}

export interface IntakeResponse {
  patient: { id: string; full_name: string; phone: string | null };
  encounter: {
    id: string;
    patient_id: string | null;
    symptoms: string;
    status: EncounterStatus;
    pathway: CarePathway | null;
    source_channel: IntakeChannel;
  };
  workflow_state: WorkflowStateSnapshot;
  awaiting_triage_clarification: boolean;
}
