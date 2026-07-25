import { Outlet } from "react-router-dom";
import { AppHeader } from "@/components/layout/AppHeader";
import { Toaster } from "@/components/ui/toaster";

export function AppLayout() {
  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <main className="mx-auto max-w-6xl px-4 pb-16 pt-6 sm:px-6 sm:pt-10">
        <Outlet />
      </main>
      <Toaster />
    </div>
  );
}
