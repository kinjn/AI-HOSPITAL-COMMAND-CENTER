import { AlertTriangle, RotateCw } from "lucide-react";
import { Button } from "./button";

interface ErrorCalloutProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorCallout({ message, onRetry }: ErrorCalloutProps) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-critical/30 bg-critical/5 px-4 py-3 text-sm text-foreground" role="alert">
      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-critical" />
      <div className="flex-1 space-y-2">
        <p>{message}</p>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            <RotateCw className="size-3.5" />
            Try again
          </Button>
        )}
      </div>
    </div>
  );
}
