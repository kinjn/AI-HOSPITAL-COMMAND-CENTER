import { Navigate, Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { CheckCircle2, Eye, PlusCircle, ShieldAlert } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CopyableCode } from "@/components/tracking/CopyableCode";

interface SubmittedState {
  trackingId: string;
}

export default function ConsultationSubmitted() {
  const location = useLocation();
  const state = location.state as SubmittedState | null;

  // This screen only makes sense right after a real submission — if someone
  // lands here directly (refresh, back button, shared link) there's no
  // tracking id to show, so send them back to start a consultation instead.
  if (!state?.trackingId) {
    return <Navigate to="/consult/new" replace />;
  }

  return (
    <div className="mx-auto max-w-lg">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
        <Card>
          <CardContent className="flex flex-col items-center gap-5 p-8 text-center sm:p-10">
            <motion.span
              initial={{ scale: 0.6, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", stiffness: 260, damping: 18, delay: 0.1 }}
              className="flex h-16 w-16 items-center justify-center rounded-full bg-success/10 text-success"
            >
              <CheckCircle2 className="h-8 w-8" />
            </motion.span>

            <div>
              <h1 className="font-display text-2xl font-semibold text-foreground">Consultation submitted</h1>
              <p className="mt-1.5 text-sm text-muted-foreground">
                Your care team is on it. Save this Tracking ID — it's the only way to check back in.
              </p>
            </div>

            <CopyableCode value={state.trackingId} className="text-lg" />

            <div className="flex items-start gap-2 rounded-lg bg-warning/10 p-3.5 text-left text-xs text-warning">
              <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
              <p>
                We can't recover this ID if you lose it and don't have another way to verify who you are. Write it
                down, screenshot it, or copy it somewhere safe before you leave this page.
              </p>
            </div>

            <div className="flex w-full flex-col gap-3 sm:flex-row">
              <Button asChild variant="outline" className="flex-1">
                <Link to="/consult/new">
                  <PlusCircle /> Start new consultation
                </Link>
              </Button>
              <Button asChild className="flex-1">
                <Link to={`/encounter/${encodeURIComponent(state.trackingId)}`}>
                  <Eye /> View encounter
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
