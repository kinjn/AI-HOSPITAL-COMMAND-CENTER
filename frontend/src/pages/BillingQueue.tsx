import { EncounterQueueTable } from "@/components/encounter/encounter-table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorCallout } from "@/components/ui/error-callout";
import { useEncounters } from "@/hooks/useEncounters";
import { extractErrorMessage } from "@/api/client";
import { formatCurrency, titleCase } from "@/lib/utils";

export default function BillingQueue() {
  const { data, isLoading, isError, error, refetch } = useEncounters();
  const encounters = (data?.items ?? []).filter((e) => e.billing !== null);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-foreground">Billing Queue</h1>
        <p className="text-sm text-muted-foreground">
          Cost estimates and insurance status for encounters that have reached billing.
        </p>
      </div>

      {isError ? (
        <ErrorCallout message={extractErrorMessage(error)} onRetry={() => refetch()} />
      ) : isLoading ? (
        <Skeleton className="h-96 w-full" />
      ) : (
        <EncounterQueueTable
          encounters={encounters}
          emptyMessage="Encounters appear here once a billing estimate has been generated."
          extraColumn={{
            header: "Billing",
            render: (encounter) => {
              const billing = encounter.billing;
              if (!billing) return <span className="text-muted-foreground">—</span>;
              return (
                <div className="flex items-center gap-2 whitespace-nowrap">
                  <span className="font-mono text-sm tabular-nums">
                    {formatCurrency(billing.estimated_cost, billing.currency)}
                  </span>
                  <Badge variant={billing.status === "approved" ? "low" : billing.status === "rejected" ? "critical" : "muted"}>
                    {titleCase(billing.status)}
                  </Badge>
                </div>
              );
            },
          }}
        />
      )}
    </div>
  );
}
