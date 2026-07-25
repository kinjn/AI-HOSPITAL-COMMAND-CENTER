import { EncounterQueueTable } from "@/components/encounter/encounter-table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorCallout } from "@/components/ui/error-callout";
import { useEncounters } from "@/hooks/useEncounters";
import { extractErrorMessage } from "@/api/client";
import { formatDateTime, isDueToday, titleCase } from "@/lib/utils";

export default function FollowUps() {
  const { data, isLoading, isError, error, refetch } = useEncounters();
  const encounters = (data?.items ?? []).filter((e) => e.followup !== null);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-foreground">Follow-ups</h1>
        <p className="text-sm text-muted-foreground">
          Medication, lab, diet, and escalation follow-up plans and their schedule.
        </p>
      </div>

      {isError ? (
        <ErrorCallout message={extractErrorMessage(error)} onRetry={() => refetch()} />
      ) : isLoading ? (
        <Skeleton className="h-96 w-full" />
      ) : (
        <EncounterQueueTable
          encounters={encounters}
          emptyMessage="Follow-up plans appear here once an encounter is scheduled."
          extraColumn={{
            header: "Next follow-up",
            render: (encounter) => {
              const followup = encounter.followup;
              if (!followup) return <span className="text-muted-foreground">—</span>;
              const dueToday = isDueToday(followup.scheduled_at);
              return (
                <div className="flex items-center gap-2 whitespace-nowrap">
                  <span className="text-sm text-muted-foreground">{formatDateTime(followup.scheduled_at)}</span>
                  {dueToday && <Badge variant="medium">Due today</Badge>}
                  <Badge variant={followup.status === "done" ? "low" : "muted"}>{titleCase(followup.status)}</Badge>
                </div>
              );
            },
          }}
        />
      )}
    </div>
  );
}
