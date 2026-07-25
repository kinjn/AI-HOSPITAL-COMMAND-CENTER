import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { AlertTriangle, ArrowLeft } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { PatientInfoCard } from "@/components/results/PatientInfoCard";
import { MedicalSummaryCard } from "@/components/results/MedicalSummaryCard";
import { BillingCard } from "@/components/results/BillingCard";
import { FollowUpCard } from "@/components/results/FollowUpCard";
import { DietaryPreferenceForm } from "@/components/results/DietaryPreferenceForm";
import { ResultActions } from "@/components/results/ResultActions";
import { EmptyState } from "@/components/encounters/EmptyState";
import { useEncounterByTrackingId } from "@/hooks/useEncounters";
import { extractErrorMessage } from "@/api/client";

export default function EncounterDetail() {
  const { trackingId } = useParams<{ trackingId: string }>();
  const { data: encounter, isLoading, isError, error } = useEncounterByTrackingId(trackingId);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Button asChild variant="ghost" size="sm" className="-ml-2">
        <Link to="/">
          <ArrowLeft /> Back to home
        </Link>
      </Button>

      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-40 w-full rounded-xl" />
          <Skeleton className="h-56 w-full rounded-xl" />
          <Skeleton className="h-56 w-full rounded-xl" />
        </div>
      )}

      {isError && (
        <EmptyState
          icon={AlertTriangle}
          title="Couldn't find that encounter"
          description={extractErrorMessage(error)}
          actionLabel="Try a different Tracking ID"
          onAction={() => {
            window.location.href = "/encounter/lookup";
          }}
        />
      )}

      {!isLoading && !isError && encounter && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="space-y-6"
        >
          <PatientInfoCard encounter={encounter} />
          <MedicalSummaryCard summary={encounter.case_summary} />
          <BillingCard billing={encounter.billing_records[0] ?? null} trackingId={encounter.tracking_id} />
          {(() => {
            // `encounter.followups` is sorted oldest-first by the backend, and a
            // dietary update regenerates the plan as a brand-new followup row
            // rather than mutating the existing one — so the most recent
            // guidance (e.g. after saving a preference) is always the LAST
            // entry, not the first. Reading [0] here showed stale diet
            // guidance even after a successful save. Mirrors the Staff
            // Portal's `encounter.followups[encounter.followups.length - 1]`
            // (see frontend/src/pages/EncounterResult.tsx).
            const latestFollowup = encounter.followups[encounter.followups.length - 1] ?? null;
            return (
              <>
                {latestFollowup?.plan.diet_guidance &&
                  !latestFollowup.plan.diet_guidance.preferences_confirmed && (
                    <DietaryPreferenceForm trackingId={encounter.tracking_id} />
                  )}
                <FollowUpCard followup={latestFollowup} />
              </>
            );
          })()}
          <ResultActions encounter={encounter} />
        </motion.div>
      )}
    </div>
  );
}
