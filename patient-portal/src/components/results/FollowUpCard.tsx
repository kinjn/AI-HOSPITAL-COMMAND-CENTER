import { CalendarClock, Pill, FlaskConical, Utensils, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { FollowUpPlanDetail } from "@/types/domain";

export function FollowUpCard({ followup }: { followup: FollowUpPlanDetail | null }) {
  if (!followup) return null;
  const { plan } = followup;
  const hasContent =
    (plan.medication_reminders?.length ?? 0) > 0 ||
    (plan.lab_reminders?.length ?? 0) > 0 ||
    plan.diet_guidance ||
    (plan.escalation_rules?.length ?? 0) > 0 ||
    plan.notes;

  if (!hasContent) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CalendarClock className="h-5 w-5 text-primary" />
          Follow-up instructions
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {plan.medication_reminders && plan.medication_reminders.length > 0 && (
          <section>
            <p className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <Pill className="h-3.5 w-3.5" /> Medication reminders
            </p>
            <div className="space-y-2">
              {plan.medication_reminders.map((med, i) => (
                <div key={i} className="rounded-lg border border-border p-3">
                  <p className="text-sm font-medium text-foreground">
                    {med.medication} — {med.dosage}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {med.frequency}
                    {med.duration_days ? ` · ${med.duration_days} days` : ""}
                    {med.times?.length ? ` · ${med.times.join(", ")}` : ""}
                  </p>
                  {med.notes && <p className="mt-1 text-xs text-muted-foreground">{med.notes}</p>}
                </div>
              ))}
            </div>
          </section>
        )}

        {plan.lab_reminders && plan.lab_reminders.length > 0 && (
          <section>
            <p className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <FlaskConical className="h-3.5 w-3.5" /> Lab reminders
            </p>
            <div className="space-y-2">
              {plan.lab_reminders.map((lab, i) => (
                <div key={i} className="rounded-lg border border-border p-3">
                  <p className="text-sm font-medium text-foreground">{lab.test}</p>
                  <p className="text-xs text-muted-foreground">
                    Due in {lab.due_in_days} day{lab.due_in_days === 1 ? "" : "s"}
                    {lab.fasting_required ? " · Fasting required" : ""}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">{lab.instructions}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {plan.diet_guidance && (
          <section>
            <p className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <Utensils className="h-3.5 w-3.5" /> Diet guidance
            </p>
            <p className="text-sm text-foreground">{plan.diet_guidance.summary}</p>
            <div className="mt-2 grid gap-3 sm:grid-cols-2">
              {plan.diet_guidance.recommended?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-success">Recommended</p>
                  <ul className="mt-1 space-y-0.5 text-xs text-muted-foreground">
                    {plan.diet_guidance.recommended.map((item) => (
                      <li key={item}>• {item}</li>
                    ))}
                  </ul>
                </div>
              )}
              {plan.diet_guidance.avoid?.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-destructive">Avoid</p>
                  <ul className="mt-1 space-y-0.5 text-xs text-muted-foreground">
                    {plan.diet_guidance.avoid.map((item) => (
                      <li key={item}>• {item}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </section>
        )}

        {plan.escalation_rules && plan.escalation_rules.length > 0 && (
          <section className="rounded-lg bg-warning/10 p-4">
            <p className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-warning">
              <AlertCircle className="h-3.5 w-3.5" /> When to seek help sooner
            </p>
            <ul className="space-y-1.5 text-sm text-foreground">
              {plan.escalation_rules.map((rule, i) => (
                <li key={i}>
                  <span className="font-medium">{rule.trigger}:</span> {rule.action}
                </li>
              ))}
            </ul>
          </section>
        )}

        {plan.notes && <p className="text-sm text-muted-foreground">{plan.notes}</p>}
      </CardContent>
    </Card>
  );
}
