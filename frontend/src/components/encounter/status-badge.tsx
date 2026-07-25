import { Badge } from "@/components/ui/badge";
import type { EncounterStatus } from "@/types/domain";

/** The encounter stays "Open" through every workflow stage (intake, triage,
 * routing, summary, billing_ready, ...) and only ever becomes "Closed" once
 * staff press "Approve Billing" (POST /encounters/{id}/billing/approve),
 * which is the only place that sets status = "closed". This intentionally
 * collapses the more granular backend stages into a single Open/Closed
 * signal for the badge — see the Timeline card for stage-level detail. */
export function StatusBadge({ status }: { status: EncounterStatus | string | null | undefined }) {
  if (!status) return <Badge variant="muted">Unknown</Badge>;
  const isClosed = status === "closed";
  return <Badge variant={isClosed ? "secondary" : "outline"}>{isClosed ? "Closed" : "Open"}</Badge>;
}
