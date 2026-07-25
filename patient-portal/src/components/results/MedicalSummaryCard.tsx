import { FileText, FlaskConical } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CaseSummaryDetail } from "@/types/domain";

export function MedicalSummaryCard({ summary }: { summary: CaseSummaryDetail | null }) {
  if (!summary) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary" />
          Medical summary
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <p className="text-sm leading-relaxed text-foreground">{summary.summary_text}</p>

        {summary.suggested_tests.length > 0 && (
          <div>
            <p className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <FlaskConical className="h-3.5 w-3.5" /> Recommended tests
            </p>
            <ul className="grid gap-2 sm:grid-cols-2">
              {summary.suggested_tests.map((test) => (
                <li
                  key={test}
                  className="rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm text-foreground"
                >
                  {test}
                </li>
              ))}
            </ul>
          </div>
        )}

        {summary.doctor_notes && (
          <div className="rounded-lg bg-accent px-4 py-3 text-sm text-accent-foreground">
            <p className="mb-1 text-xs font-medium uppercase tracking-wide opacity-80">Clinician notes</p>
            {summary.doctor_notes}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
