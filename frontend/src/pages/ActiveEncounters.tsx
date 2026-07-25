import { EncounterQueueTable } from "@/components/encounter/encounter-table";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorCallout } from "@/components/ui/error-callout";
import { useEncounters } from "@/hooks/useEncounters";
import { extractErrorMessage } from "@/api/client";

export default function ActiveEncounters() {
  const { data, isLoading, isError, error, refetch } = useEncounters();
  const encounters = (data?.items ?? []).filter((e) => e.status !== "closed");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-foreground">Active Encounters</h1>
        <p className="text-sm text-muted-foreground">
          Encounters currently moving through intake, triage, routing, or summary.
        </p>
      </div>

      {isError ? (
        <ErrorCallout message={extractErrorMessage(error)} onRetry={() => refetch()} />
      ) : isLoading ? (
        <Skeleton className="h-96 w-full" />
      ) : (
        <EncounterQueueTable
          encounters={encounters}
          emptyMessage="No encounters are currently active. New intakes will show up here."
        />
      )}
    </div>
  );
}
