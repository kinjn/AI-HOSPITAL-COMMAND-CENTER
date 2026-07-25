import { Badge } from "@/components/ui/badge";
import { STAGE_LABELS, type EncounterStatus } from "@/types/domain";

const CLOSED: EncounterStatus[] = ["billing_ready", "closed"];

export function StatusBadge({ status }: { status: EncounterStatus }) {
  const isDone = CLOSED.includes(status);
  return <Badge variant={isDone ? "success" : "default"}>{STAGE_LABELS[status] ?? status}</Badge>;
}
