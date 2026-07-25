import { lazy, Suspense, type ReactNode } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { AppLayout } from "@/layouts/AppLayout";
import { Skeleton } from "@/components/ui/skeleton";

const Welcome = lazy(() => import("@/pages/Welcome"));
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const NewPatient = lazy(() => import("@/pages/NewPatient"));
const ActiveEncounters = lazy(() => import("@/pages/ActiveEncounters"));
const EncounterResult = lazy(() => import("@/pages/EncounterResult"));
const BillingQueue = lazy(() => import("@/pages/BillingQueue"));
const FollowUps = lazy(() => import("@/pages/FollowUps"));
const Settings = lazy(() => import("@/pages/Settings"));

function PageFallback() {
  return (
    <div className="space-y-4 p-2">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

function withSuspense(element: ReactNode) {
  return <Suspense fallback={<PageFallback />}>{element}</Suspense>;
}

export const router = createBrowserRouter([
  { path: "/", element: withSuspense(<Welcome />) },
  {
    path: "/dashboard",
    element: <AppLayout />,
    children: [
      { index: true, element: withSuspense(<Dashboard />) },
      { path: "new-patient", element: withSuspense(<NewPatient />) },
      { path: "encounters", element: withSuspense(<ActiveEncounters />) },
      { path: "encounters/:id", element: withSuspense(<EncounterResult />) },
      { path: "billing", element: withSuspense(<BillingQueue />) },
      { path: "follow-ups", element: withSuspense(<FollowUps />) },
      { path: "settings", element: withSuspense(<Settings />) },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
