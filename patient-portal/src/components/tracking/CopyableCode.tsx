import * as React from "react";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";

export function CopyableCode({ value, className }: { value: string; className?: string }) {
  const [copied, setCopied] = React.useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard access can be blocked by the browser — the code is still visible to copy manually.
    }
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      className={cn(
        "group inline-flex items-center gap-2 rounded-lg border border-border bg-muted/50 px-4 py-2.5 font-mono text-sm font-medium text-foreground transition-colors hover:bg-muted",
        className,
      )}
    >
      {value}
      {copied ? (
        <Check className="h-4 w-4 text-success" />
      ) : (
        <Copy className="h-4 w-4 text-muted-foreground group-hover:text-foreground" />
      )}
    </button>
  );
}
