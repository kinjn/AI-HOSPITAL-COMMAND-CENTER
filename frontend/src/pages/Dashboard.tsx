import * as React from "react";
import { Activity, AlertOctagon, ListChecks, Receipt } from "lucide-react";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { EncounterQueueTable } from "@/components/encounter/encounter-table";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorCallout } from "@/components/ui/error-callout";
import { useEncounters } from "@/hooks/useEncounters";
import { extractErrorMessage } from "@/api/client";
import { isDueToday } from "@/lib/utils";

export default function Dashboard() {
  const { data, isLoading, isError, error, refetch } = useEncounters();
  const encounters = data?.items ?? [];

  const stats = React.useMemo(() => {
    const active = encounters.filter((e) => e.status !== "closed").length;
    const critical = encounters.filter((e) => e.urgency === "critical").length;
    const awaitingBilling = encounters.filter(
      (e) => e.status === "summary_ready" || (e.billing && e.billing.status === "draft"),
    ).length;
    const followUpsDueToday = encounters.filter(
      (e) => e.followup && e.followup.status !== "done" && isDueToday(e.followup.scheduled_at),
    ).length;
    return { active, critical, awaitingBilling, followUpsDueToday };
  }, [encounters]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-foreground">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Live view of patient encounters across intake, triage, billing, and follow-up.
        </p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-[86px]" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard label="Active Encounters" value={stats.active} icon={Activity} />
          <KpiCard label="Critical Cases" value={stats.critical} icon={AlertOctagon} tone="critical" />
          <KpiCard label="Awaiting Billing" value={stats.awaitingBilling} icon={Receipt} tone="warning" />
          <KpiCard
            label="Follow-ups Due Today"
            value={stats.followUpsDueToday}
            icon={ListChecks}
            tone="success"
          />
        </div>
      )}

      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-foreground">Encounter queue</h2>
        {isError ? (
          <ErrorCallout message={extractErrorMessage(error)} onRetry={() => refetch()} />
        ) : isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : (
          <EncounterQueueTable encounters={encounters} emptyMessage="New intakes will appear here as they arrive." />
        )}
      </div>
    </div>
  );
}
