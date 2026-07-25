import * as React from "react";
import { useNavigate } from "react-router-dom";
import { KeyRound, Search } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";

export default function EncounterLookup() {
  const [trackingId, setTrackingId] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);
  const navigate = useNavigate();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const cleaned = trackingId.trim();
    if (!cleaned) {
      setError("Enter the Tracking ID from your consultation.");
      return;
    }
    setError(null);
    setSubmitting(true);
    // Navigation itself triggers the lookup on the detail page — the tracking
    // ID never gets validated here, only there, against the real backend.
    navigate(`/encounter/${encodeURIComponent(cleaned)}`);
  }

  return (
    <div className="mx-auto max-w-md">
      <Card>
        <CardHeader className="items-center text-center">
          <span className="mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-accent text-accent-foreground">
            <KeyRound className="h-5 w-5" />
          </span>
          <CardTitle>Find your encounter</CardTitle>
          <CardDescription>
            Enter the Tracking ID you received after submitting your consultation.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="trackingId">Tracking ID</Label>
              <Input
                id="trackingId"
                value={trackingId}
                onChange={(e) => {
                  setTrackingId(e.target.value);
                  setError(null);
                }}
                placeholder="HCC-83AF92"
                className="text-center font-mono uppercase tracking-wide"
                autoFocus
                autoComplete="off"
                autoCapitalize="characters"
                invalid={!!error}
              />
              {error && <p className="text-xs text-destructive">{error}</p>}
            </div>
            <Button type="submit" size="lg" className="w-full" disabled={submitting}>
              {submitting ? (
                <Spinner />
              ) : (
                <>
                  <Search /> Find encounter
                </>
              )}
            </Button>
          </form>
          <p className="mt-5 text-center text-xs text-muted-foreground">
            Your Tracking ID was shown right after you submitted your consultation. We can't recover it for you if
            it's lost — please start a new consultation instead.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
