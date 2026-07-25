import * as React from "react";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { HelpCircle } from "lucide-react";

interface ClarificationFormProps {
  questions: string[];
  onSubmit: (answers: string[]) => void;
  submitting?: boolean;
}

export function ClarificationForm({ questions, onSubmit, submitting }: ClarificationFormProps) {
  const [answers, setAnswers] = React.useState<string[]>(() => questions.map(() => ""));

  React.useEffect(() => {
    setAnswers(questions.map(() => ""));
  }, [questions]);

  const canSubmit = answers.every((a) => a.trim().length > 0);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (canSubmit) onSubmit(answers);
  }

  return (
    <div className="mx-auto w-full max-w-lg space-y-5 rounded-lg border border-border bg-card p-6 shadow-panel">
      <div className="flex items-start gap-3">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
          <HelpCircle className="size-5" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-foreground">A couple more details</h2>
          <p className="text-sm text-muted-foreground">
            To route this patient accurately, please answer the following.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {questions.map((question, index) => (
          <div key={question} className="space-y-1.5">
            <Label htmlFor={`answer-${index}`}>{question}</Label>
            <Textarea
              id={`answer-${index}`}
              rows={3}
              value={answers[index]}
              onChange={(e) =>
                setAnswers((prev) => prev.map((a, i) => (i === index ? e.target.value : a)))
              }
              disabled={submitting}
            />
          </div>
        ))}
        <Button type="submit" className="w-full" disabled={!canSubmit || submitting}>
          {submitting ? "Submitting…" : "Continue"}
        </Button>
      </form>
    </div>
  );
}
