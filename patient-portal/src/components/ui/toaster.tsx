import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, X, XCircle, Info } from "lucide-react";
import { useToast } from "@/context/ToastContext";
import { cn } from "@/lib/utils";

const ICONS = {
  default: Info,
  success: CheckCircle2,
  destructive: XCircle,
};

export function Toaster() {
  const { toasts, dismiss } = useToast();

  return (
    <div className="fixed inset-x-0 bottom-0 z-[100] flex flex-col items-center gap-2 p-4 sm:items-end sm:right-4 sm:left-auto sm:bottom-4">
      <AnimatePresence>
        {toasts.map((t) => {
          const Icon = ICONS[t.variant ?? "default"];
          return (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 16, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.96 }}
              transition={{ duration: 0.2 }}
              className={cn(
                "flex w-full max-w-sm items-start gap-3 rounded-xl border bg-card p-4 shadow-raised sm:w-96",
                t.variant === "success" && "border-success/30",
                t.variant === "destructive" && "border-destructive/30",
                t.variant === "default" && "border-border",
              )}
            >
              <Icon
                className={cn(
                  "mt-0.5 h-5 w-5 shrink-0",
                  t.variant === "success" && "text-success",
                  t.variant === "destructive" && "text-destructive",
                  t.variant === "default" && "text-primary",
                )}
              />
              <div className="flex-1 space-y-0.5">
                <p className="text-sm font-medium text-foreground">{t.title}</p>
                {t.description && <p className="text-sm text-muted-foreground">{t.description}</p>}
              </div>
              <button
                onClick={() => dismiss(t.id)}
                className="shrink-0 rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                aria-label="Dismiss notification"
              >
                <X className="h-4 w-4" />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
