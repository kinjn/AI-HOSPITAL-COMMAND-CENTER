import { createBrowserRouter } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";

import Landing from "@/pages/Landing";
import NewConsultation from "@/pages/NewConsultation";
import ConsultationSubmitted from "@/pages/ConsultationSubmitted";
import EncounterLookup from "@/pages/EncounterLookup";
import EncounterDetail from "@/pages/EncounterDetail";
import NotFound from "@/pages/NotFound";

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: "/", element: <Landing /> },
      { path: "/consult/new", element: <NewConsultation /> },
      { path: "/consult/submitted", element: <ConsultationSubmitted /> },
      { path: "/encounter/lookup", element: <EncounterLookup /> },
      { path: "/encounter/:trackingId", element: <EncounterDetail /> },
      { path: "*", element: <NotFound /> },
    ],
  },
]);
