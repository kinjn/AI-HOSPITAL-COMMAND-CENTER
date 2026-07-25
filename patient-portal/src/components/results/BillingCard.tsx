import { CheckCircle2, Download, FileWarning, Receipt, ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { BillingRecordDetail } from "@/types/domain";
import { formatCurrency } from "@/lib/utils";
import { downloadTextAsPdf } from "@/lib/pdf";
import { useRequestInsuranceDocument } from "@/hooks/useEncounters";
import { extractErrorMessage } from "@/api/client";

const LINE_ITEMS: Array<{ key: keyof BillingRecordDetail; label: string }> = [
  { key: "consultation_fee", label: "Consultation fee" },
  { key: "test_cost", label: "Tests" },
  { key: "medication_cost", label: "Medication" },
  { key: "misc_cost", label: "Other charges" },
];

/** Triggers a browser download of the insurance document's full narrative
 * text as a PDF — no backend file storage needed, since the generated
 * document text is already part of the API response. */
function downloadInsuranceDocument(billing: BillingRecordDetail) {
  const text = billing.insurance_document?.documentation;
  if (!text) return;
  const filename = billing.insurance_document?.reference_number
    ? `insurance-document-${billing.insurance_document.reference_number}.pdf`
    : "insurance-document.pdf";
  downloadTextAsPdf("Insurance Pre-Authorization Document", text, filename);
}

function InsuranceDocumentRequest({ billing, trackingId }: { billing: BillingRecordDetail; trackingId: string }) {
  const requestMutation = useRequestInsuranceDocument(trackingId);
  const status = billing.insurance_request_status;

  return (
    <div className="rounded-lg border border-border p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="flex items-center gap-1.5 text-sm font-medium text-foreground">
          <ShieldCheck className="h-4 w-4 text-primary" />
          Insurance document
        </p>
        {status && (
          <Badge
            variant={status === "approved" ? "success" : status === "rejected" ? "critical" : "secondary"}
            className="capitalize"
          >
            {status === "requested" ? "Pending review" : status}
          </Badge>
        )}
      </div>

      <div className="mt-3">
        {!status && (
          <>
            <p className="mb-3 text-xs text-muted-foreground">
              You can request a copy of your insurance pre-authorization document for submission to your insurer.
            </p>
            <Button size="sm" disabled={requestMutation.isPending} onClick={() => requestMutation.mutate()}>
              {requestMutation.isPending ? "Requesting…" : "Demand insurance document"}
            </Button>
          </>
        )}

        {status === "requested" && (
          <p className="text-sm text-muted-foreground">
            Your request has been sent to the hospital and is awaiting review.
          </p>
        )}

        {status === "approved" && (
          <div className="space-y-3">
            <p className="flex items-center gap-1.5 text-sm font-medium text-success">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              Your request was approved. Your document is ready to download.
            </p>
            <Button size="sm" onClick={() => downloadInsuranceDocument(billing)}>
              <Download className="h-4 w-4" />
              Download insurance document
            </Button>
          </div>
        )}

        {status === "rejected" && (
          <div className="space-y-3">
            <p className="flex items-center gap-1.5 text-sm font-medium text-destructive">
              <FileWarning className="h-4 w-4 shrink-0" />
              Your request was rejected. Please contact the hospital for any query.
            </p>
            <Button
              size="sm"
              variant="outline"
              disabled={requestMutation.isPending}
              onClick={() => requestMutation.mutate()}
            >
              {requestMutation.isPending ? "Requesting…" : "Request again"}
            </Button>
          </div>
        )}

        {requestMutation.isError && (
          <p className="mt-2 text-sm text-destructive">{extractErrorMessage(requestMutation.error)}</p>
        )}
      </div>
    </div>
  );
}

export function BillingCard({
  billing,
  trackingId,
}: {
  billing: BillingRecordDetail | null;
  trackingId: string;
}) {
  if (!billing) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Receipt className="h-5 w-5 text-primary" />
          Billing estimate
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {billing.status === "approved" && (
          <div className="flex items-center gap-2 rounded-lg border border-success/30 bg-success/10 px-4 py-3 text-sm font-medium text-success">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            Your billing has been approved. This consultation is now complete.
          </div>
        )}

        <div className="rounded-xl bg-accent p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-accent-foreground/80">
            Estimated total
          </p>
          <p className="font-display text-3xl font-semibold text-accent-foreground">
            {formatCurrency(billing.estimated_cost, billing.currency)}
          </p>
          <p className="mt-1 text-xs text-accent-foreground/70">
            This is an estimate, not a final bill — actual charges may vary.
          </p>
        </div>

        <div className="space-y-2">
          {LINE_ITEMS.map(({ key, label }) => (
            <div key={key} className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">{label}</span>
              <span className="font-medium text-foreground">
                {formatCurrency(billing[key] as number, billing.currency)}
              </span>
            </div>
          ))}
        </div>

        <InsuranceDocumentRequest billing={billing} trackingId={trackingId} />

        {billing.insurance_provider && (
          <div className="rounded-lg border border-border p-4">
            <div className="flex items-center justify-between">
              <p className="flex items-center gap-1.5 text-sm font-medium text-foreground">
                <ShieldCheck className="h-4 w-4 text-primary" />
                {billing.insurance_provider}
              </p>
              <Badge variant="secondary" className="capitalize">
                {billing.status}
              </Badge>
            </div>
            {billing.insurance_document && (
              <div className="mt-3 space-y-1.5 text-xs text-muted-foreground">
                <p>Reference: {billing.insurance_document.reference_number}</p>
                <p>{billing.insurance_document.coverage_notes}</p>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
