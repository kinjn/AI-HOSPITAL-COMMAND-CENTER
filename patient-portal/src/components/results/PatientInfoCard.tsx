import { Card, CardContent } from "@/components/ui/card";
import { UrgencyBadge } from "@/components/encounters/UrgencyBadge";
import { StatusBadge } from "@/components/encounters/StatusBadge";
import { PATHWAY_LABELS, type PatientEncounterDetail } from "@/types/domain";
import { formatDateTime } from "@/lib/utils";

export function PatientInfoCard({ encounter }: { encounter: PatientEncounterDetail }) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="font-mono text-xs font-medium tracking-wide text-primary">{encounter.tracking_id}</p>
            <h2 className="font-display text-xl font-semibold text-foreground">{encounter.patient.full_name}</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {encounter.age ? `${encounter.age} years` : "Age not recorded"}
              {encounter.patient.gender ? ` · ${encounter.patient.gender}` : ""}
            </p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <UrgencyBadge urgency={encounter.urgency} />
            <StatusBadge status={encounter.status} />
          </div>
        </div>

        <div className="mt-5 grid gap-4 border-t border-border pt-4 sm:grid-cols-3">
          <div>
            <p className="text-xs text-muted-foreground">Care pathway</p>
            <p className="text-sm font-medium text-foreground">
              {encounter.pathway ? PATHWAY_LABELS[encounter.pathway] : "Pending"}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Submitted</p>
            <p className="text-sm font-medium text-foreground">{formatDateTime(encounter.created_at)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Last updated</p>
            <p className="text-sm font-medium text-foreground">{formatDateTime(encounter.updated_at)}</p>
          </div>
        </div>

        <div className="mt-4 border-t border-border pt-4">
          <p className="text-xs text-muted-foreground">Reported symptoms</p>
          <p className="mt-1 text-sm text-foreground">{encounter.symptoms}</p>
        </div>
      </CardContent>
    </Card>
  );
}
