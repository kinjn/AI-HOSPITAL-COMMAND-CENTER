# AI Hospital Command Center — Frontend

A production-grade React operations dashboard for the AI Hospital Command Center. Replaces the
previous Streamlit UI. Talks only to the existing FastAPI backend — no business logic, LangGraph
workflow, or database models were touched (see `BACKEND_CHANGES.md` in the backend project for the
handful of additive, read-only endpoints/fields that were required).

## Stack

React 19 · Vite · TypeScript · Tailwind CSS · shadcn-style UI primitives · React Router ·
TanStack Query · Axios · Lucide icons

## Getting started

```bash
cd frontend
cp .env.example .env      # then edit VITE_API_KEY to match the backend's API_KEY
npm install
npm run dev
```

The app runs at `http://localhost:5173` and expects the backend at the URL configured in
`VITE_API_BASE_URL` (default `http://localhost:8000/api/v1`).

### Running the backend alongside it

From the backend project root:

```bash
uvicorn hospital_command_center.api.app:create_app --factory --reload --port 8000
```

(Use whatever command the backend README specifies if different — the important part is that it's
serving on the port referenced by `VITE_API_BASE_URL`.)

## Environment variables

| Variable              | Description                                                        |
|------------------------|----------------------------------------------------------------------|
| `VITE_API_BASE_URL`   | Base URL of the FastAPI backend, including the `/api/v1` prefix.    |
| `VITE_API_KEY`        | Sent as the `x-api-key` header on every request. Must match the backend's `API_KEY` setting. |

## Required backend change: CORS

The backend previously had no CORS middleware (it was only ever called from the same-origin
Streamlit process). Since the browser now calls the API from a different origin
(`http://localhost:5173` in dev), CORS middleware was added to the backend (see
`BACKEND_CHANGES.md`). If you deploy the frontend somewhere else, add that origin to the backend's
`CORS_ALLOW_ORIGINS` environment variable (comma-separated).

## Project structure

```
src/
  api/          Axios client + typed API functions (encounters, intake, triage, followup)
  components/
    ui/         Reusable shadcn-style primitives (button, card, badge, input, table, ...)
    layout/     Sidebar
    dashboard/  KPI tile
    encounter/  Encounter queue table, status/urgency badges
    intake/     Intake form, clarification form, workflow stepper
  context/      Theme provider (light/dark/system + localStorage persistence)
  hooks/        React Query hooks (encounters list w/ 15s auto-refresh, mutations)
  layouts/      Persistent app shell (sidebar + content)
  pages/        Welcome, Dashboard, New Patient, Active Encounters, Billing Queue, Follow-ups,
                Settings, Encounter Result
  routes/       Router config with lazy-loaded, code-split pages
  types/        TypeScript types mirroring backend response shapes
```

## Notes on the intake → result flow

1. **New Patient** submits the form via `POST /intake/web`. This call runs the whole backend
   workflow synchronously (triage → routing → summary → billing → follow-up), so the "processing"
   screen shows a visual step progression while waiting rather than polling a job status.
2. If the AI triage step needs more information, the backend returns
   `awaiting_triage_clarification: true` with a short list of questions. The UI shows those
   questions (`POST /triage/encounters/{id}/clarify` to answer) — this can repeat up to the
   backend's configured maximum.
3. Once complete, the UI navigates to `/dashboard/encounters/:id`, which loads the full record from
   `GET /encounters/{id}` — so refreshing the page, or coming back to it later from the queue,
   always shows the same data.
4. **Add New Patient** on the result page simply navigates to a fresh `/dashboard/new-patient`
   route, which mounts a brand-new form component with no leftover state.

## Accessibility & performance

- Semantic form elements with associated `<label>`s, `aria-invalid`/`aria-describedby` on errors.
- Visible focus rings (`:focus-visible`) throughout; keyboard-operable table rows.
- Routes are lazy-loaded (`React.lazy` + `Suspense`) for code splitting.
- The encounter queue table is written to avoid unnecessary re-renders (memoized filtering).
