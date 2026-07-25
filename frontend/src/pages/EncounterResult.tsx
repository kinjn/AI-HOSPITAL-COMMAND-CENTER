import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CalendarClock,
  CheckCircle2,
  ClipboardPlus,
  FileText,
  ListChecks,
  Receipt,
  ShieldCheck,
  Stethoscope,
  XCircle,
} from "lucide-react";
import { Badge, urgencyBadgeVariant } from "@/components/ui/badge";
import { StatusBadge } from "@/components/encounter/status-badge";
import { DietaryUpdateForm } from "@/components/encounter/dietary-update-form";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorCallout } from "@/components/ui/error-callout";
import {
  useAcceptInsuranceDocument,
  useApproveBilling,
  useEncounterDetail,
  useRejectInsuranceDocument,
} from "@/hooks/useEncounters";
import { extractErrorMessage } from "@/api/client";
import { formatCurrency, formatDateTime, titleCase } from "@/lib/utils";

export default function EncounterResult() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: encounter, isLoading, isError, error, refetch } = useEncounterDetail(id);
  const approveBillingMutation = useApproveBilling(id);
  const acceptInsuranceMutation = useAcceptInsuranceDocument(id);
  const rejectInsuranceMutation = useRejectInsuranceDocument(id);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (isError || !encounter) {
    return <ErrorCallout message={extractErrorMessage(error) || "Encounter not found."} onRetry={() => refetch()} />;
  }

  const latestBilling = encounter.billing_records[encounter.billing_records.length - 1] ?? null;
  const latestFollowup = encounter.followups[encounter.followups.length - 1] ?? null;
  const dietGuidance = latestFollowup?.plan.diet_guidance;

  return (
    <div className="space-y-6">
      <button
        type="button"
        onClick={() => navigate("/dashboard/encounters")}
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        Back to encounters
      </button>

      {/* Patient header */}
      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-4 pt-6">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-foreground">
              {encounter.patient.full_name}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {encounter.age ? `${encounter.age} years` : "Age not recorded"}
              {encounter.patient.gender ? ` · ${titleCase(encounter.patient.gender)}` : ""}
              {encounter.patient.phone ? ` · ${encounter.patient.phone}` : ""}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={urgencyBadgeVariant(encounter.urgency)} dot>
              {encounter.urgency ? titleCase(encounter.urgency) : "Pending"}
            </Badge>
            <Badge variant="outline">{encounter.pathway ? titleCase(encounter.pathway) : "Pathway pending"}</Badge>
            <StatusBadge status={encounter.status} />
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          {/* Clinical summary */}
          <Card>
            <CardHeader className="flex-row items-center gap-2 space-y-0">
              <Stethoscope className="size-4 text-primary" />
              <CardTitle className="text-sm font-semibold text-foreground">Clinical summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {encounter.case_summary ? (
                <>
                  <p className="text-sm leading-relaxed text-foreground">{encounter.case_summary.summary_text}</p>
                  {encounter.case_summary.suggested_tests.length > 0 && (
                    <div>
                      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Suggested tests
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {encounter.case_summary.suggested_tests.map((test) => (
                          <Badge key={test} variant="secondary">
                            {test}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  {encounter.case_summary.extracted_history && (
                    <details className="group rounded-md border border-border" open>
                      <summary className="cursor-pointer select-none px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground hover:text-foreground">
                        Extracted patient history
                      </summary>
                      <p className="border-t border-border px-3 py-3 text-sm leading-relaxed text-foreground">
                        {encounter.case_summary.extracted_history}
                      </p>
                    </details>
                  )}
                  {encounter.case_summary.doctor_notes && (
                    <details className="group rounded-md border border-border" open>
                      <summary className="cursor-pointer select-none px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground hover:text-foreground">
                        Doctor SOAP briefing
                      </summary>
                      <p className="whitespace-pre-line border-t border-border px-3 py-3 text-sm leading-relaxed text-foreground">
                        {encounter.case_summary.doctor_notes}
                      </p>
                    </details>
                  )}
                </>
              ) : (
                <p className="text-sm text-muted-foreground">Summary not yet available.</p>
              )}
            </CardContent>
          </Card>

          {/* Billing estimate */}
          <Card>
            <CardHeader className="flex-row items-center gap-2 space-y-0">
              <Receipt className="size-4 text-primary" />
              <CardTitle className="text-sm font-semibold text-foreground">Billing &amp; insurance</CardTitle>
            </CardHeader>
            <CardContent>
              {latestBilling ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Estimated cost</span>
                    <span className="font-mono text-lg font-semibold tabular-nums text-foreground">
                      {formatCurrency(latestBilling.estimated_cost, latestBilling.currency)}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4">
                    <CostLine label="Consultation" value={latestBilling.consultation_fee} currency={latestBilling.currency} />
                    <CostLine label="Tests" value={latestBilling.test_cost} currency={latestBilling.currency} />
                    <CostLine label="Medication" value={latestBilling.medication_cost} currency={latestBilling.currency} />
                    <CostLine label="Miscellaneous" value={latestBilling.misc_cost} currency={latestBilling.currency} />
                  </div>
                  <div className="flex flex-wrap items-center gap-2 border-t border-border pt-3">
                    <Badge variant={latestBilling.status === "approved" ? "low" : latestBilling.status === "rejected" ? "critical" : "muted"}>
                      Insurance: {titleCase(latestBilling.status)}
                    </Badge>
                    {latestBilling.insurance_provider && (
                      <span className="text-sm text-muted-foreground">{latestBilling.insurance_provider}</span>
                    )}
                    {latestBilling.preauth_reference && (
                      <span className="font-mono text-xs text-muted-foreground">
                        Ref: {latestBilling.preauth_reference}
                      </span>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-3 border-t border-border pt-4">
                    {encounter.status === "closed" || latestBilling.status === "approved" ? (
                      <span className="inline-flex items-center gap-1.5 text-sm font-medium text-success">
                        <CheckCircle2 className="size-4" />
                        Billing approved — encounter closed
                      </span>
                    ) : (
                      <>
                        <Button
                          size="sm"
                          disabled={approveBillingMutation.isPending}
                          onClick={() => {
                            if (window.confirm("Approve billing for this encounter? This closes the encounter and notifies the patient.")) {
                              approveBillingMutation.mutate();
                            }
                          }}
                        >
                          <CheckCircle2 className="size-4" />
                          {approveBillingMutation.isPending ? "Approving…" : "Approve Billing"}
                        </Button>
                        {approveBillingMutation.isError && (
                          <span className="text-sm text-destructive">
                            {extractErrorMessage(approveBillingMutation.error)}
                          </span>
                        )}
                      </>
                    )}
                  </div>

                  {latestBilling.insurance_request_status && (
                    <div className="space-y-3 border-t border-border pt-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Patient insurance document request
                      </p>

                      {latestBilling.insurance_request_status === "requested" && (
                        <div className="flex flex-wrap items-center gap-3">
                          <span className="inline-flex items-center gap-1.5 text-sm text-foreground">
                            <ShieldCheck className="size-4 text-primary" />
                            Patient has requested their insurance document.
                          </span>
                          <div className="flex flex-wrap gap-2">
                            <Button
                              size="sm"
                              disabled={acceptInsuranceMutation.isPending}
                              onClick={() => acceptInsuranceMutation.mutate()}
                            >
                              <CheckCircle2 className="size-4" />
                              {acceptInsuranceMutation.isPending ? "Accepting…" : "Accept"}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={rejectInsuranceMutation.isPending}
                              onClick={() => rejectInsuranceMutation.mutate()}
                            >
                              <XCircle className="size-4" />
                              {rejectInsuranceMutation.isPending ? "Rejecting…" : "Reject"}
                            </Button>
                          </div>
                        </div>
                      )}

                      {latestBilling.insurance_request_status === "approved" && (
                        <span className="inline-flex items-center gap-1.5 text-sm font-medium text-success">
                          <CheckCircle2 className="size-4" />
                          Request accepted — document is available to the patient for download.
                        </span>
                      )}

                      {latestBilling.insurance_request_status === "rejected" && (
                        <span className="inline-flex items-center gap-1.5 text-sm font-medium text-destructive">
                          <XCircle className="size-4" />
                          Request rejected — the patient has been notified.
                        </span>
                      )}

                      {(acceptInsuranceMutation.isError || rejectInsuranceMutation.isError) && (
                        <span className="block text-sm text-destructive">
                          {extractErrorMessage(acceptInsuranceMutation.error ?? rejectInsuranceMutation.error)}
                        </span>
                      )}
                    </div>
                  )}

                  {latestBilling.insurance_document && (
                    <div className="space-y-3 border-t border-border pt-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Pre-authorization document
                      </p>
                      <dl className="grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
                        <div>
                          <dt className="text-xs text-muted-foreground">Reference number</dt>
                          <dd className="font-mono text-foreground">{latestBilling.insurance_document.reference_number}</dd>
                        </div>
                        <div>
                          <dt className="text-xs text-muted-foreground">Document type</dt>
                          <dd className="text-foreground">{titleCase(latestBilling.insurance_document.document_type)}</dd>
                        </div>
                        <div>
                          <dt className="text-xs text-muted-foreground">Patient name</dt>
                          <dd className="text-foreground">
                            {latestBilling.insurance_document.patient_name || "As per hospital registration"}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-xs text-muted-foreground">Treating facility</dt>
                          <dd className="text-foreground">{latestBilling.insurance_document.treating_facility}</dd>
                        </div>
                        <div className="sm:col-span-2">
                          <dt className="text-xs text-muted-foreground">Clinical indication</dt>
                          <dd className="text-foreground">{latestBilling.insurance_document.clinical_indication}</dd>
                        </div>
                        {latestBilling.insurance_document.proposed_services.length > 0 && (
                          <div className="sm:col-span-2">
                            <dt className="mb-1.5 text-xs text-muted-foreground">Proposed services</dt>
                            <dd className="flex flex-wrap gap-1.5">
                              {latestBilling.insurance_document.proposed_services.map((service) => (
                                <Badge key={service} variant="secondary">
                                  {service}
                                </Badge>
                              ))}
                            </dd>
                          </div>
                        )}
                        {(latestBilling.insurance_document.icd10_codes.length > 0 ||
                          latestBilling.insurance_document.cpt_codes.length > 0) && (
                          <div className="sm:col-span-2">
                            <dt className="mb-1.5 text-xs text-muted-foreground">Diagnosis &amp; procedure codes</dt>
                            <dd className="flex flex-wrap gap-1.5">
                              {latestBilling.insurance_document.icd10_codes.map((code) => (
                                <Badge key={code} variant="outline">
                                  {code}
                                </Badge>
                              ))}
                              {latestBilling.insurance_document.cpt_codes.map((code) => (
                                <Badge key={code} variant="outline">
                                  {code}
                                </Badge>
                              ))}
                            </dd>
                          </div>
                        )}
                        <div className="sm:col-span-2">
                          <dt className="text-xs text-muted-foreground">Coverage notes</dt>
                          <dd className="text-foreground">{latestBilling.insurance_document.coverage_notes}</dd>
                        </div>
                        <div className="sm:col-span-2">
                          <dt className="text-xs text-muted-foreground">Submission instructions</dt>
                          <dd className="text-foreground">{latestBilling.insurance_document.submission_instructions}</dd>
                        </div>
                      </dl>

                      {latestBilling.insurance_document.documentation && (
                        <details className="group rounded-md border border-border">
                          <summary className="cursor-pointer select-none px-3 py-2 text-xs font-medium text-muted-foreground hover:text-foreground">
                            View full document text (for printing / submission)
                          </summary>
                          <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words border-t border-border bg-muted/30 p-3 font-mono text-xs leading-relaxed text-foreground">
                            {latestBilling.insurance_document.documentation}
                          </pre>
                        </details>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Billing estimate not yet available.</p>
              )}
            </CardContent>
          </Card>

          {/* Follow-up instructions */}
          <Card>
            <CardHeader className="flex-row items-center gap-2 space-y-0">
              <ListChecks className="size-4 text-primary" />
              <CardTitle className="text-sm font-semibold text-foreground">Follow-up instructions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {latestFollowup ? (
                <>
                  {latestFollowup.plan.medication_reminders && latestFollowup.plan.medication_reminders.length > 0 && (
                    <div>
                      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Medication
                      </p>
                      <ul className="space-y-1.5">
                        {latestFollowup.plan.medication_reminders.map((med) => (
                          <li key={med.medication} className="text-sm text-foreground">
                            <span className="font-medium">{med.medication}</span> — {med.dosage}, {med.frequency}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {latestFollowup.plan.lab_reminders && latestFollowup.plan.lab_reminders.length > 0 && (
                    <div>
                      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Lab work
                      </p>
                      <ul className="space-y-1.5">
                        {latestFollowup.plan.lab_reminders.map((lab) => (
                          <li key={lab.test} className="text-sm text-foreground">
                            <span className="font-medium">{lab.test}</span> — due in {lab.due_in_days} day(s)
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {dietGuidance && (
                    <div>
                      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Diet &amp; hydration guidance
                      </p>
                      <p className="text-sm text-foreground">{dietGuidance.summary}</p>
                      {(dietGuidance.recommended.length > 0 || dietGuidance.avoid.length > 0) && (
                        <div className="mt-3 grid gap-4 sm:grid-cols-2">
                          {dietGuidance.recommended.length > 0 && (
                            <div>
                              <p className="mb-1 text-xs font-medium text-success">Recommended</p>
                              <ul className="list-inside list-disc space-y-1 text-sm text-foreground">
                                {dietGuidance.recommended.map((item) => (
                                  <li key={item}>{item}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                          {dietGuidance.avoid.length > 0 && (
                            <div>
                              <p className="mb-1 text-xs font-medium text-critical">Avoid</p>
                              <ul className="list-inside list-disc space-y-1 text-sm text-foreground">
                                {dietGuidance.avoid.map((item) => (
                                  <li key={item}>{item}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}
                      {dietGuidance.hydration_notes && (
                        <p className="mt-3 text-sm text-muted-foreground">
                          <span className="font-medium text-foreground">Hydration: </span>
                          {dietGuidance.hydration_notes}
                        </p>
                      )}
                      {dietGuidance.special_instructions && (
                        <p className="mt-1.5 text-sm text-muted-foreground">
                          <span className="font-medium text-foreground">Special instructions: </span>
                          {dietGuidance.special_instructions}
                        </p>
                      )}
                      {!dietGuidance.preferences_confirmed && id && (
                        <div className="mt-3">
                          <DietaryUpdateForm encounterId={id} />
                        </div>
                      )}
                    </div>
                  )}
                  {latestFollowup.plan.escalation_rules && latestFollowup.plan.escalation_rules.length > 0 && (
                    <div>
                      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        Red flags (escalation)
                      </p>
                      <ul className="space-y-2.5">
                        {latestFollowup.plan.escalation_rules.map((rule) => (
                          <li key={rule.trigger} className="rounded-md border border-border p-3 text-sm">
                            <div className="mb-1 flex flex-wrap items-center gap-2">
                              <Badge variant={urgencyBadgeVariant(rule.severity)}>{rule.severity.toUpperCase()}</Badge>
                              <span className="font-medium text-foreground">{rule.trigger}</span>
                            </div>
                            <p className="text-foreground">
                              <span className="text-muted-foreground">Action: </span>
                              {rule.action}
                            </p>
                            {(rule.notify_channels.length > 0 || rule.notify_within) && (
                              <p className="mt-1 text-xs text-muted-foreground">
                                Notify: {rule.notify_within && `within ${rule.notify_within}`}
                                {rule.notify_within && rule.notify_channels.length > 0 && " via "}
                                {rule.notify_channels.join(", ")}
                                {rule.contact ? ` (${rule.contact})` : ""}
                              </p>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {!latestFollowup.plan.medication_reminders?.length &&
                    !latestFollowup.plan.lab_reminders?.length &&
                    !latestFollowup.plan.escalation_rules?.length &&
                    !dietGuidance && <p className="text-sm text-muted-foreground">No specific follow-up items yet.</p>}
                </>
              ) : (
                <p className="text-sm text-muted-foreground">Follow-up plan not yet available.</p>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          {/* Timeline */}
          <Card>
            <CardHeader className="flex-row items-center gap-2 space-y-0">
              <CalendarClock className="size-4 text-primary" />
              <CardTitle className="text-sm font-semibold text-foreground">Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="space-y-4">
                {encounter.timeline.map((entry, index) => (
                  <li key={entry.stage} className="relative flex gap-3 pl-1">
                    <div className="flex flex-col items-center">
                      <span className="size-2 rounded-full bg-primary" />
                      {index < encounter.timeline.length - 1 && (
                        <span className="mt-1 h-full w-px flex-1 bg-border" />
                      )}
                    </div>
                    <div className="-mt-1 pb-1">
                      <p className="text-sm font-medium text-foreground">{entry.label}</p>
                      <p className="text-xs text-muted-foreground">{formatDateTime(entry.at)}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>

          {/* Actions */}
          <Card>
            <CardContent className="space-y-2.5 pt-6">
              <Button className="w-full" onClick={() => navigate("/dashboard/new-patient")}>
                <ClipboardPlus className="size-4" />
                Add New Patient
              </Button>
              <Button variant="outline" className="w-full" onClick={() => navigate("/dashboard/encounters")}>
                <FileText className="size-4" />
                View in Queue
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function CostLine({ label, value, currency }: { label: string; value: number; currency: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-mono tabular-nums text-foreground">{formatCurrency(value, currency)}</p>
    </div>
  );
}
