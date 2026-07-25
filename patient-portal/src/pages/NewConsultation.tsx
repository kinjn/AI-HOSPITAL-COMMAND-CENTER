import * as React from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { AlertTriangle, MessageCircleQuestion, RotateCcw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { IntakeForm } from "@/components/consultation/IntakeForm";
import { CONSULTATION_STEPS, ProcessingTimeline } from "@/components/consultation/ProcessingTimeline";
import { useSubmitConsultation } from "@/hooks/useIntake";
import { submitTriageClarification } from "@/api/triage";
import { extractErrorMessage } from "@/api/client";
import type { IntakeFormValues, TrackingSubmissionResult } from "@/types/domain";

type Stage = "form" | "processing" | "clarify" | "error";

const CLARIFY_STEP_INDEX = 2; // "Determining urgency" — where clarification pauses the pipeline
const LAST_STEP_INDEX = CONSULTATION_STEPS.length - 1;

const EMPTY_VALUES: IntakeFormValues = {
  patient_name: "",
  age: "",
  gender: "",
  phone: "",
  symptoms: "",
  known_medical_conditions: "",
};

export default function NewConsultation() {
  const navigate = useNavigate();
  const [stage, setStage] = React.useState<Stage>("form");
  const [activeStep, setActiveStep] = React.useState(0);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);
  const [pendingResult, setPendingResult] = React.useState<TrackingSubmissionResult | null>(null);
  const [answers, setAnswers] = React.useState<string[]>([]);
  const timerRef = React.useRef<number | null>(null);

  const submitMutation = useSubmitConsultation();
  const clarifyMutation = useMutation({
    mutationFn: ({ trackingId, answers }: { trackingId: string; answers: string[] }) =>
      submitTriageClarification(trackingId, answers),
  });

  function startAutoAdvance(stopAt: number) {
    stopAutoAdvance();
    timerRef.current = window.setInterval(() => {
      setActiveStep((step) => (step < stopAt ? step + 1 : step));
    }, 1400);
  }

  function stopAutoAdvance() {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }

  React.useEffect(() => () => stopAutoAdvance(), []);

  function handleResult(result: TrackingSubmissionResult) {
    stopAutoAdvance();
    if (result.awaiting_triage_clarification) {
      const questions = result.workflow_state.triage?.clarifying_questions ?? [];
      setAnswers(questions.map(() => ""));
      setPendingResult(result);
      setActiveStep(CLARIFY_STEP_INDEX);
      setStage("clarify");
      return;
    }
    setActiveStep(LAST_STEP_INDEX);
    window.setTimeout(
      () => navigate("/consult/submitted", { state: { trackingId: result.tracking_id }, replace: true }),
      500,
    );
  }

  function handleSubmitIntake(values: IntakeFormValues) {
    setStage("processing");
    setActiveStep(0);
    setErrorMessage(null);
    startAutoAdvance(LAST_STEP_INDEX - 1);
    submitMutation.mutate(values, {
      onSuccess: handleResult,
      onError: (err) => {
        stopAutoAdvance();
        setErrorMessage(extractErrorMessage(err));
        setStage("error");
      },
    });
  }

  function handleSubmitClarification(e: React.FormEvent) {
    e.preventDefault();
    if (!pendingResult) return;
    setStage("processing");
    startAutoAdvance(LAST_STEP_INDEX - 1);
    clarifyMutation.mutate(
      { trackingId: pendingResult.tracking_id, answers },
      {
        onSuccess: handleResult,
        onError: (err) => {
          stopAutoAdvance();
          setErrorMessage(extractErrorMessage(err));
          setStage("error");
        },
      },
    );
  }

  function handleRetry() {
    stopAutoAdvance();
    setStage("form");
    setActiveStep(0);
    setErrorMessage(null);
  }

  const questions = pendingResult?.workflow_state.triage?.clarifying_questions ?? [];

  return (
    <div className="mx-auto max-w-2xl">
      {stage === "form" && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <Card>
            <CardHeader>
              <CardTitle>Start a consultation</CardTitle>
              <CardDescription>
                Tell us a bit about yourself and what you're experiencing. This takes about two minutes. At the end
                you'll get a private Tracking ID — no account needed.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <IntakeForm initialValues={EMPTY_VALUES} onSubmit={handleSubmitIntake} isSubmitting={false} />
            </CardContent>
          </Card>
        </motion.div>
      )}

      {stage === "processing" && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <Card>
            <CardHeader>
              <CardTitle>Processing your consultation</CardTitle>
              <CardDescription>Please stay on this page — this only takes a moment.</CardDescription>
            </CardHeader>
            <CardContent>
              <ProcessingTimeline activeIndex={activeStep} />
            </CardContent>
          </Card>
        </motion.div>
      )}

      {stage === "clarify" && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageCircleQuestion className="h-5 w-5 text-primary" />
                A couple of quick questions
              </CardTitle>
              <CardDescription>
                Your answers help us determine the right level of care for you.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmitClarification} className="space-y-5">
                {questions.map((q, i) => (
                  <div key={i} className="space-y-1.5">
                    <label className="text-sm font-medium text-foreground">{q}</label>
                    <Textarea
                      value={answers[i] ?? ""}
                      onChange={(e) => {
                        const next = [...answers];
                        next[i] = e.target.value;
                        setAnswers(next);
                      }}
                      rows={3}
                      required
                    />
                  </div>
                ))}
                <Button type="submit" size="lg" className="w-full">
                  Continue
                </Button>
              </form>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {stage === "error" && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <Card>
            <CardContent className="flex flex-col items-center gap-3 p-10 text-center">
              <span className="flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10 text-destructive">
                <AlertTriangle className="h-6 w-6" />
              </span>
              <h2 className="font-display text-lg font-semibold text-foreground">Something went wrong</h2>
              <p className="max-w-sm text-sm text-muted-foreground">{errorMessage}</p>
              <Button onClick={handleRetry} className="mt-2">
                <RotateCcw /> Try again
              </Button>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
}
