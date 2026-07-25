import { Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export const WORKFLOW_STEPS = [
  "Intake",
  "Triage",
  "Routing",
  "Medical Summary",
  "Billing",
  "Follow-up",
] as const;

interface WorkflowStepperProps {
  /** Index of the step currently in progress (0-based). */
  activeIndex: number;
  /** True once all steps are complete. */
  complete?: boolean;
}

export function WorkflowStepper({ activeIndex, complete = false }: WorkflowStepperProps) {
  return (
    <ol className="space-y-3" aria-label="Encounter processing progress">
      {WORKFLOW_STEPS.map((step, index) => {
        const isDone = complete || index < activeIndex;
        const isActive = !complete && index === activeIndex;
        return (
          <li key={step} className="flex items-center gap-3">
            <span
              className={cn(
                "flex size-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold transition-colors",
                isDone && "border-success bg-success/15 text-success",
                isActive && "border-primary bg-primary/10 text-primary",
                !isDone && !isActive && "border-border bg-muted text-muted-foreground",
              )}
              aria-hidden="true"
            >
              {isDone ? <Check className="size-4" /> : isActive ? <Loader2 className="size-4 animate-spin" /> : index + 1}
            </span>
            <span
              className={cn(
                "text-sm",
                isDone && "text-foreground",
                isActive && "font-medium text-foreground",
                !isDone && !isActive && "text-muted-foreground",
              )}
            >
              {step}
            </span>
            {isActive && <span className="sr-only"> — in progress</span>}
            {isDone && <span className="sr-only"> — complete</span>}
          </li>
        );
      })}
    </ol>
  );
}
