import * as React from "react";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ErrorCallout } from "@/components/ui/error-callout";
import { useUpdateDietaryPreference } from "@/hooks/useEncounters";
import { extractErrorMessage } from "@/api/client";

interface DietaryUpdateFormProps {
  encounterId: string;
  onSaved?: () => void;
}

export function DietaryUpdateForm({ encounterId, onSaved }: DietaryUpdateFormProps) {
  const [preference, setPreference] = React.useState("");
  const [allergies, setAllergies] = React.useState("");
  const mutation = useUpdateDietaryPreference(encounterId);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!preference) return;
    mutation.mutate(
      { dietary_preference: preference, food_allergies: allergies || null },
      { onSuccess: () => onSaved?.() },
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-md border border-border bg-muted/30 p-4">
      <p className="text-xs font-medium text-foreground">
        Dietary preference wasn't provided at intake — add it now to get specific meal guidance.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="dietary-update-pref">Dietary preference</Label>
          <Select
            id="dietary-update-pref"
            value={preference}
            onChange={(e) => setPreference(e.target.value)}
            disabled={mutation.isPending}
          >
            <option value="">Select…</option>
            <option value="vegetarian">Vegetarian</option>
            <option value="non-vegetarian">Non-vegetarian</option>
            <option value="vegan">Vegan</option>
            <option value="other">Other</option>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="dietary-update-allergies">Known food allergies</Label>
          <Input
            id="dietary-update-allergies"
            placeholder="e.g. peanuts, shellfish"
            value={allergies}
            onChange={(e) => setAllergies(e.target.value)}
            disabled={mutation.isPending}
          />
        </div>
      </div>
      {mutation.isError && <ErrorCallout message={extractErrorMessage(mutation.error)} />}
      <Button type="submit" size="sm" disabled={!preference || mutation.isPending}>
        {mutation.isPending ? "Saving…" : "Save & regenerate guidance"}
      </Button>
    </form>
  );
}
