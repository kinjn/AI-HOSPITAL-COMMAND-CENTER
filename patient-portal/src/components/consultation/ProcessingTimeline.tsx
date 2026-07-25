import { motion } from "framer-motion";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ProcessingStep {
  key: string;
  label: string;
}

export const CONSULTATION_STEPS: ProcessingStep[] = [
  { key: "intake", label: "Intake complete" },
  { key: "analyzing", label: "Analyzing your symptoms" },
  { key: "urgency", label: "Determining urgency" },
  { key: "pathway", label: "Selecting your care pathway" },
  { key: "summary", label: "Preparing your medical summary" },
  { key: "billing", label: "Estimating billing" },
  { key: "followup", label: "Generating follow-up instructions" },
];

interface ProcessingTimelineProps {
  steps?: ProcessingStep[];
  activeIndex: number; // index of the step currently in progress
  errored?: boolean;
}

export function ProcessingTimeline({ steps = CONSULTATION_STEPS, activeIndex, errored }: ProcessingTimelineProps) {
  return (
    <ol className="relative">
      {steps.map((step, i) => {
        const isComplete = i < activeIndex || (errored && i < activeIndex + 1 && i !== activeIndex);
        const isActive = i === activeIndex && !errored;
        const isFailed = errored && i === activeIndex;
        const isLast = i === steps.length - 1;

        return (
          <li key={step.key} className="relative flex gap-4 pb-8 last:pb-0">
            {!isLast && (
              <span
                className={cn(
                  "absolute left-[15px] top-8 h-[calc(100%-1.5rem)] w-0.5",
                  isComplete ? "bg-success" : "bg-border",
                )}
                aria-hidden
              />
            )}
            <span className="relative flex h-8 w-8 shrink-0 items-center justify-center">
              {isActive && (
                <span className="absolute inset-0 rounded-full bg-primary/40 animate-pulse-ring" aria-hidden />
              )}
              <span
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-semibold transition-colors",
                  isComplete && "border-success bg-success text-success-foreground",
                  isActive && "border-primary bg-primary text-primary-foreground",
                  isFailed && "border-destructive bg-destructive text-destructive-foreground",
                  !isComplete && !isActive && !isFailed && "border-border bg-muted text-muted-foreground",
                )}
              >
                {isComplete ? <Check className="h-4 w-4" /> : i + 1}
              </span>
            </span>
            <motion.div
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.04 }}
              className="pt-1"
            >
              <p
                className={cn(
                  "text-sm font-medium",
                  isComplete && "text-foreground",
                  isActive && "text-foreground",
                  isFailed && "text-destructive",
                  !isComplete && !isActive && !isFailed && "text-muted-foreground",
                )}
              >
                {step.label}
              </p>
              {isActive && <p className="mt-0.5 text-xs text-muted-foreground">This usually takes a few moments…</p>}
              {isFailed && <p className="mt-0.5 text-xs text-destructive">We hit a snag here. Please try again.</p>}
            </motion.div>
          </li>
        );
      })}
    </ol>
  );
}
