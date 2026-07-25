# MyCare — Patient Portal

An independent, patient-facing frontend for the AI Hospital Command Center.
Talks to the same FastAPI backend as the Staff Portal, but is a completely
separate application: separate codebase, separate identification model,
separate audience, separate visual identity. **No files in `backend/` or
`frontend/` (the Staff Portal) were modified to build this.**

## Identification model: Tracking ID, not accounts

There is no login, no password, no OTP, and no patient account. Submitting a
consultation returns a **Tracking ID** (e.g. `HCC-83AF92`) — a private code
the patient saves and later re-enters to view that one consultation. Nothing
in this app can list, browse, or enumerate encounters; the only way in is
knowing the exact Tracking ID for the encounter you want.

| | Staff Portal (`../frontend`) | Patient Portal (this app) |
|---|---|---|
| Audience | Doctors, nurses, billing, admins | Individual patients |
| Identification | None (internal tool) | Tracking ID per consultation |
| Data visibility | All encounters, hospital-wide | Only the one encounter matching the Tracking ID entered |
| Vibe | Operations dashboard | Consumer healthcare app (Practo / MyChart-style) |

## Stack

React 19 · Vite · TypeScript · Tailwind CSS · shadcn-style local components ·
React Router 6 · TanStack Query · Axios · Lucide icons · Framer Motion.

## Getting started

```bash
cd patient-portal
npm install
cp .env.example .env   # point VITE_API_BASE_URL / VITE_API_KEY at your backend
npm run dev             # http://localhost:5174
```

The dev server runs on **5174** (the Staff Portal's Vite dev server uses
5173), so both apps can run side by side without a port clash.

## Before this works end-to-end

The backend doesn't yet have a concept of a Tracking ID, or endpoints keyed
by one. This app is built against the exact contract it expects — see
[`BACKEND_REQUIREMENTS.md`](./BACKEND_REQUIREMENTS.md) for the three
endpoints to add (`POST /patient/intake`, `POST
/patient/encounter/{tracking_id}/clarify`, `GET
/patient/encounter/{tracking_id}`), their request/response shapes, and the
one schema addition needed (a `tracking_id` column). All three are thin
wrappers around logic that already exists — no AI workflow, LangGraph, or
FastAPI business logic changes required.

## Structure

```
src/
  api/            Axios calls — one file per backend resource
  components/
    ui/           Local shadcn-style primitives (button, card, input, ...)
    layout/       App-wide header + layout shell (no auth branching)
    tracking/     Tracking ID display / copy component
    consultation/ Intake form, processing timeline
    encounters/   Status/urgency badges, empty states
    results/      Encounter detail sections
  context/        Theme + toast providers
  hooks/          React Query hooks (submit consultation, fetch by Tracking ID)
  pages/          Route-level screens
  routes/         Router config
  types/          Types mirroring the Tracking-ID backend contract
  styles/         Tailwind theme tokens (light + dark)
```

## Application flow

```
Landing
  ├─ Start New Consultation → Submit Symptoms → Processing → Consultation Submitted
  │                                                              (shows Tracking ID)
  │                                                                    ↓
  │                                                            View Encounter
  └─ View Existing Encounter → Enter Tracking ID → View ONLY that encounter
```

There is no dashboard, no "my encounters" list, and no route anywhere that
returns more than one encounter. `src/api/encounters.ts` has exactly one
function, `getEncounterByTrackingId`, and every encounter fetch in the app
goes through it.

## Design notes

- Palette, type pairing (Lexend/Inter), and component styling are
  deliberately different from the Staff Portal so the two never read as the
  same product to a patient.
- No agent, graph, or workflow-engine names ever appear in copy — the
  processing screen only ever describes the clinical steps (analyzing
  symptoms, determining urgency, etc.), never "LangGraph," "agent," or
  similar. No raw JSON or internal database ids are ever rendered.
- Light and dark mode are both fully themed via CSS variables in
  `src/styles/index.css`; toggle lives in the header.
- The Consultation Submitted screen treats the Tracking ID as something the
  patient could genuinely lose — it's shown with a copy button and an
  explicit "we can't recover this for you" warning, not just printed once
  and forgotten.
