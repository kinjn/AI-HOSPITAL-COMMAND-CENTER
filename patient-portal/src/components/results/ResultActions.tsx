import { Link } from "react-router-dom";
import { Download, Search, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { PatientEncounterDetail } from "@/types/domain";
import { formatDate } from "@/lib/utils";
import { downloadSectionsAsPdf } from "@/lib/pdf";

function downloadReport(encounter: PatientEncounterDetail) {
  const billing = encounter.billing_records[0];
  downloadSectionsAsPdf(
    `Consultation Report — ${encounter.patient.full_name}`,
    [
      {
        body: [
          `Tracking ID: ${encounter.tracking_id}`,
          `Date: ${formatDate(encounter.created_at)}`,
          `Status: ${encounter.status}`,
          `Urgency: ${encounter.urgency ?? "N/A"}`,
          `Care pathway: ${encounter.pathway ?? "Pending"}`,
        ].join("\n"),
      },
      { heading: "Symptoms", body: encounter.symptoms },
      { heading: "Medical summary", body: encounter.case_summary?.summary_text ?? "Not yet available." },
      {
        heading: "Recommended tests",
        body: encounter.case_summary?.suggested_tests.length
          ? encounter.case_summary.suggested_tests.map((t) => `- ${t}`).join("\n")
          : "None",
      },
      {
        heading: "Billing estimate",
        body: billing ? `${billing.estimated_cost ?? "—"} ${billing.currency}` : "Not yet available.",
      },
    ],
    `consultation-report-${encounter.tracking_id}.pdf`,
  );
}

export function ResultActions({ encounter }: { encounter: PatientEncounterDetail }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      <Button variant="outline" className="flex-1" onClick={() => downloadReport(encounter)}>
        <Download /> Download report
      </Button>
      <Button asChild variant="outline" className="flex-1">
        <Link to="/encounter/lookup">
          <Search /> Look up another encounter
        </Link>
      </Button>
      <Button asChild className="flex-1">
        <Link to="/consult/new">
          <RotateCcw /> Start new consultation
        </Link>
      </Button>
    </div>
  );
}
