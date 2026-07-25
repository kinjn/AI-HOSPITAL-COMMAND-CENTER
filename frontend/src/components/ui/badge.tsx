import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium tabular-nums",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        outline: "border-border text-foreground",
        critical: "border-transparent bg-critical/15 text-critical dark:bg-critical/20",
        high: "border-transparent bg-warning/15 text-warning dark:bg-warning/20",
        medium: "border-transparent bg-medium/15 text-medium dark:bg-medium/25",
        low: "border-transparent bg-success/15 text-success dark:bg-success/20",
        muted: "border-transparent bg-muted text-muted-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  dot?: boolean;
}

function Badge({ className, variant, dot, children, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant, className }))} {...props}>
      {dot && (
        <span
          className={cn(
            "size-1.5 rounded-full",
            variant === "critical" && "bg-critical",
            variant === "high" && "bg-warning",
            variant === "medium" && "bg-medium",
            variant === "low" && "bg-success",
            !variant || variant === "default" ? "bg-primary-foreground" : "",
          )}
        />
      )}
      {children}
    </span>
  );
}

export function urgencyBadgeVariant(urgency: string | null | undefined): BadgeProps["variant"] {
  switch (urgency) {
    case "critical":
      return "critical";
    case "high":
      return "high";
    case "medium":
      return "medium";
    case "low":
      return "low";
    default:
      return "muted";
  }
}

export { Badge, badgeVariants };
