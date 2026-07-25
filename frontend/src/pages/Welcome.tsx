import { useNavigate } from "react-router-dom";
import { Activity, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";

export default function Welcome() {
  const navigate = useNavigate();

  return (
    <div className="relative flex min-h-screen flex-col bg-background">
      <div className="absolute right-5 top-5">
        <ThemeToggle />
      </div>

      <div className="flex flex-1 flex-col items-center justify-center px-6 py-16">
        <div className="flex w-full max-w-md flex-col items-center text-center">
          <div className="mb-7 flex size-16 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-panel">
            <Activity className="size-8" />
          </div>

          <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
            AI Hospital Command Center
          </h1>
          <p className="mt-3 max-w-sm text-balance text-sm text-muted-foreground sm:text-base">
            One operations view for patient intake, triage, care routing, billing, and follow-up —
            built for the teams who keep care moving.
          </p>

          <Button size="lg" className="mt-9 w-full sm:w-auto" onClick={() => navigate("/dashboard")}>
            Enter Hospital
            <ArrowRight className="size-4" />
          </Button>
        </div>
      </div>

      <footer className="pb-6 text-center text-xs text-muted-foreground">
        Internal operations tool — authorized staff only
      </footer>
    </div>
  );
}
