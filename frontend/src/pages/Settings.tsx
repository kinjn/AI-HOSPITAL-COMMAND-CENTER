import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ThemeToggle } from "@/components/theme-toggle";

export default function Settings() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground">Preferences for this workstation.</p>
      </div>

      <Card className="max-w-lg">
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
          <CardDescription>Switch between light, dark, or match your system.</CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-between">
          <span className="text-sm text-foreground">Theme</span>
          <ThemeToggle />
        </CardContent>
      </Card>

      <Card className="max-w-lg">
        <CardHeader>
          <CardTitle>About</CardTitle>
          <CardDescription>AI Hospital Command Center — operations dashboard.</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          For access issues or data corrections, contact your hospital IT administrator.
        </CardContent>
      </Card>
    </div>
  );
}
