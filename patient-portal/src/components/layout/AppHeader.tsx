import { Link } from "react-router-dom";
import { PlusCircle, Search } from "lucide-react";
import { Wordmark } from "@/components/wordmark";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";

export function AppHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link to="/">
          <Wordmark />
        </Link>
        <div className="flex items-center gap-2">
          <Button asChild variant="ghost" size="sm">
            <Link to="/encounter/lookup">
              <Search /> <span className="hidden sm:inline">Find My Encounter</span>
            </Link>
          </Button>
          <Button asChild size="sm">
            <Link to="/consult/new">
              <PlusCircle /> <span className="hidden sm:inline">Start Consultation</span>
            </Link>
          </Button>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
