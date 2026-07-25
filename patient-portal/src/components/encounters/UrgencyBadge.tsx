import { AlertTriangle, CircleAlert, CircleCheck, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { URGENCY_LABELS, type Urgency } from "@/types/domain";

const CONFIG: Record<Urgency, { variant: "success" | "warning" | "critical"; icon: typeof Info }> = {
  low: { variant: "success", icon: CircleCheck },
  medium: { variant: "warning", icon: Info },
  high: { variant: "warning", icon: CircleAlert },
  critical: { variant: "critical", icon: AlertTriangle },
};

export function UrgencyBadge({ urgency }: { urgency: Urgency | null }) {
  if (!urgency) return <Badge variant="secondary">Assessing…</Badge>;
  const { variant, icon: Icon } = CONFIG[urgency];
  return (
    <Badge variant={variant}>
      <Icon className="h-3.5 w-3.5" />
      {URGENCY_LABELS[urgency]}
    </Badge>
  );
}
