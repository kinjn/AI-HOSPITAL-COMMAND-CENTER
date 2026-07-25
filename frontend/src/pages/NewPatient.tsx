import * as React from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorCallout } from "@/components/ui/error-callout";
import { IntakeForm } from "@/components/intake/intake-form";
import { ClarificationForm } from "@/components/intake/clarification-form";
import { WorkflowStepper, WORKFLOW_STEPS } from "@/components/intake/workflow-stepper";
import { useSubmitIntake, useSubmitTriageClarification } from "@/hooks/useIntake";
import { extractErrorMessage } from "@/api/client";
import type { IntakeFormValues, IntakeResponse } from "@/types/domain";

type Stage = "form" | "processing" | "clarifying" | "done";

/** Mirrors the backend's own "pending" computation (unanswered turns in the
 * stored conversation) instead of trusting the raw clarifying_questions list
 * from a single LLM call — avoids a submitted-answer-count mismatch if the
 * model ever re-lists an already-answered question on a later round. */
function pendingQuestions(response: IntakeResponse): string[] {
  const conversation = response.workflow_state.triage_conversation;
  if (conversation && conversation.length > 0) {
    const unanswered = conversation.filter((turn) => !turn.answer).map((turn) => turn.question);
    if (unanswered.length > 0) return unanswered;
  }
  return response.workflow_state.triage?.clarifying_questions ?? [];
}

export default function NewPatient() {
  const navigate = useNavigate();
  const [stage, setStage] = React.useState<Stage>("form");
  const [activeStep, setActiveStep] = React.useState(0);
  const [encounterId, setEncounterId] = React.useState<string | null>(null);
  const [questions, setQuestions] = React.useState<string[]>([]);

  const intakeMutation = useSubmitIntake();
  const clarificationMutation = useSubmitTriageClarification();

  const isProcessing = stage === "processing";

  // Simulated step progression while the backend runs the workflow
  // synchronously — advances through the visible steps but never reaches
  // the final one until the real response arrives.
  React.useEffect(() => {
    if (!isProcessing) return;
    setActiveStep(0);
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev < WORKFLOW_STEPS.length - 1 ? prev + 1 : prev));
    }, 900);
    return () => clearInterval(interval);
  }, [isProcessing]);

  function handleFormSubmit(values: IntakeFormValues) {
    setStage("processing");
    intakeMutation.mutate(values, {
      onSuccess: (response) => {
        setEncounterId(response.encounter.id);
        if (response.awaiting_triage_clarification) {
          setQuestions(pendingQuestions(response));
          setStage("clarifying");
        } else {
          setStage("done");
          navigate(`/dashboard/encounters/${response.encounter.id}`);
        }
      },
      onError: () => {
        setStage("form");
      },
    });
  }

  function handleClarificationSubmit(answers: string[]) {
    if (!encounterId) return;
    clarificationMutation.mutate(
      { encounterId, answers },
      {
        onSuccess: (response) => {
          if (response.awaiting_triage_clarification) {
            setQuestions(pendingQuestions(response));
          } else {
            setStage("processing");
            setTimeout(() => {
              setStage("done");
              navigate(`/dashboard/encounters/${encounterId}`);
            }, 700);
          }
        },
      },
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-foreground">New Patient</h1>
        <p className="text-sm text-muted-foreground">Start a new intake to triage and route a patient.</p>
      </div>

      {stage === "form" && (
        <Card className="max-w-3xl">
          <CardContent className="pt-6">
            {intakeMutation.isError && (
              <div className="mb-5">
                <ErrorCallout message={extractErrorMessage(intakeMutation.error)} />
              </div>
            )}
            <IntakeForm onSubmit={handleFormSubmit} disabled={intakeMutation.isPending} />
          </CardContent>
        </Card>
      )}

      {stage === "processing" && (
        <div className="flex justify-center py-10">
          <Card className="w-full max-w-md">
            <CardContent className="space-y-5 pt-6">
              <div className="text-center">
                <p className="text-base font-semibold text-foreground">Processing encounter…</p>
                <p className="text-sm text-muted-foreground">This usually takes a few moments.</p>
              </div>
              <WorkflowStepper activeIndex={activeStep} />
            </CardContent>
          </Card>
        </div>
      )}

      {stage === "clarifying" && (
        <div className="py-6">
          <ClarificationForm
            questions={questions}
            onSubmit={handleClarificationSubmit}
            submitting={clarificationMutation.isPending}
          />
          {clarificationMutation.isError && (
            <div className="mx-auto mt-4 max-w-lg">
              <ErrorCallout message={extractErrorMessage(clarificationMutation.error)} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
