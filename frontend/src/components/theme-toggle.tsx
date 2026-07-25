import { Moon, Sun, SunMoon } from "lucide-react";
import { useTheme } from "@/context/ThemeProvider";
import { Button } from "@/components/ui/button";

const ORDER: Array<"light" | "dark" | "system"> = ["light", "dark", "system"];

export function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();

  function cycle() {
    const next = ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length];
    setTheme(next);
  }

  const Icon = theme === "system" ? SunMoon : resolvedTheme === "dark" ? Moon : Sun;
  const label =
    theme === "system" ? "Theme: matching system" : theme === "dark" ? "Theme: dark" : "Theme: light";

  return (
    <Button variant="outline" size="icon" onClick={cycle} aria-label={`${label}. Click to change.`} title={label}>
      <Icon className="size-4" />
    </Button>
  );
}
