import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  label: string;
  value: number | string;
  icon: LucideIcon;
  tone?: "default" | "critical" | "warning" | "success";
}

const TONE_STYLES: Record<NonNullable<KpiCardProps["tone"]>, string> = {
  default: "border-l-primary",
  critical: "border-l-critical",
  warning: "border-l-warning",
  success: "border-l-success",
};

const ICON_TONE: Record<NonNullable<KpiCardProps["tone"]>, string> = {
  default: "text-primary bg-primary/10",
  critical: "text-critical bg-critical/10",
  warning: "text-warning bg-warning/10",
  success: "text-success bg-success/10",
};

export function KpiCard({ label, value, icon: Icon, tone = "default" }: KpiCardProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-4 rounded-lg border border-l-4 border-border bg-card p-5 shadow-panel",
        TONE_STYLES[tone],
      )}
    >
      <div className={cn("flex size-10 shrink-0 items-center justify-center rounded-md", ICON_TONE[tone])}>
        <Icon className="size-5" />
      </div>
      <div>
        <p className="font-mono text-2xl font-semibold tabular-nums leading-none text-foreground">{value}</p>
        <p className="mt-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      </div>
    </div>
  );
}
