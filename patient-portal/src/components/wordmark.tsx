import { cn } from "@/lib/utils";

/**
 * Simple wordmark for the patient-facing product. Deliberately named and
 * styled differently from the internal Staff Portal so the two never look
 * like the same product to a patient.
 */
export function Wordmark({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-primary text-primary-foreground">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            d="M12 3C9 6.5 5 8.8 5 13.2 5 17.5 8.1 21 12 21s7-3.5 7-7.8C19 8.8 15 6.5 12 3Z"
            fill="currentColor"
          />
          <path d="M12 9v7M8.5 12.5h7" stroke="hsl(var(--primary))" strokeWidth="1.4" strokeLinecap="round" />
        </svg>
      </span>
      <span className="font-display text-lg font-semibold tracking-tight text-foreground">MyCare</span>
    </div>
  );
}
