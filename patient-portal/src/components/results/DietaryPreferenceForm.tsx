import * as React from "react";
import { Check, Utensils } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { useUpdateDietaryPreference } from "@/hooks/useEncounters";
import { useToast } from "@/context/ToastContext";
import { extractErrorMessage } from "@/api/client";

export function DietaryPreferenceForm({ trackingId }: { trackingId: string }) {
  const [dietaryPreference, setDietaryPreference] = React.useState("");
  const [foodAllergies, setFoodAllergies] = React.useState("");
  const { toast } = useToast();
  const mutation = useUpdateDietaryPreference(trackingId);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutation.mutate(
      {
        dietary_preference: dietaryPreference || undefined,
        food_allergies: foodAllergies.trim() || undefined,
      },
      {
        onSuccess: () => {
          toast({ title: "Preferences saved", description: "Your diet guidance has been updated.", variant: "success" });
        },
        onError: (err) => {
          toast({ title: "Couldn't save that", description: extractErrorMessage(err), variant: "destructive" });
        },
      },
    );
  }

  return (
    <Card className="border-primary/30">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Utensils className="h-5 w-5 text-primary" />
          Confirm your dietary preference
        </CardTitle>
        <CardDescription>
          We need this to give you specific meal guidance instead of general advice.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="dietary_preference">Dietary preference</Label>
              <Select
                id="dietary_preference"
                value={dietaryPreference}
                onChange={(e) => setDietaryPreference(e.target.value)}
              >
                <option value="">Select…</option>
                <option value="vegetarian">Vegetarian</option>
                <option value="non-vegetarian">Non-vegetarian</option>
                <option value="vegan">Vegan</option>
                <option value="other">Other</option>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="food_allergies">Known food allergies</Label>
              <Input
                id="food_allergies"
                value={foodAllergies}
                onChange={(e) => setFoodAllergies(e.target.value)}
                placeholder="None, or e.g. peanuts, shellfish"
              />
            </div>
          </div>
          <Button type="submit" disabled={mutation.isPending || !dietaryPreference}>
            {mutation.isPending ? (
              <Spinner />
            ) : (
              <>
                <Check /> Save preferences
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
