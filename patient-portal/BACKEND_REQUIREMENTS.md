# Backend requirements for the Patient Portal

> **Status: implemented.** See `backend-tracking-id-changes.zip` /
> `CHANGES.md` for the actual endpoint code, applied against this exact
> spec. This file is kept below as the reference contract the
> implementation follows.

The Patient Portal is built entirely against the **existing** backend — FastAPI,
LangGraph, SQLite, unchanged business logic. This file lists the gaps between
what exists today and what the Tracking-ID identification model needs, so
they can be added without the frontend having to guess at (or fake) backend
behavior.

---

## Security model

There are no patient accounts and no login. Instead, submitting a
consultation returns a **Tracking ID** — a short, human-friendly, unguessable
code (e.g. `HCC-83AF92`) — that acts as a bearer token for that one
encounter. Anyone who presents the correct Tracking ID can view that
encounter; nobody can browse, list, or guess their way to any other
encounter. The frontend never handles, stores, or displays raw internal
database ids (`encounter.id`, `patient.id`) anywhere — the Tracking ID is
the only identifier it ever works with.

## Required new endpoints

All three are thin wrappers around logic that already exists — no changes to
`hospital_command_center/workflow/*`, LangGraph, or the AI pipeline.

### 1. `POST /patient/intake`

Same request body as the existing `POST /intake/web`:

```json
{ "patient_name": "...", "age": 34, "gender": "female", "phone": "...", "symptoms": "..." }
```

Internally: call the exact same `workflow.start_from_intake` logic that
`POST /intake/web` already calls. The only difference is the response —
instead of returning the raw `encounter.id` / `patient.id`, generate (or
look up) a short Tracking ID for the new encounter and return that instead:

```json
{
  "tracking_id": "HCC-83AF92",
  "status": "triaged",
  "pathway": "opd",
  "workflow_state": { "...": "same shape as today's IntakeResponse.workflow_state" },
  "awaiting_triage_clarification": false
}
```

Minimal schema change: add a `tracking_id` column to the `encounters` table
(unique, indexed, generated at creation — e.g. `"HCC-" + secrets.token_hex(3).upper()`,
regenerated on collision), or a small separate `encounter_tracking_codes`
mapping table if the team prefers not to touch the existing schema.

### 2. `POST /patient/encounter/{tracking_id}/clarify`

Tracking-ID-addressed counterpart to the existing
`POST /triage/encounters/{encounter_id}/clarify`. Same
`TriageClarificationSubmission` body (`{ "answers": ["...", "..."] }`) and
`workflow.continue_triage` logic underneath — the backend just resolves
`tracking_id -> encounter_id` first instead of trusting an internal id from
the client. Returns the same shape as endpoint #1.

### 3. `GET /patient/encounter/{tracking_id}`

Resolves the Tracking ID to an encounter and returns its detail — same
underlying data as today's `GET /encounters/{id}` (status, urgency,
pathway, symptoms, medical summary, recommended tests, billing record(s),
follow-up plan(s), timeline), but:

- Addressed by `tracking_id`, not internal id.
- Response omits raw internal ids (`encounter.id`, `patient.id`,
  `billing.id`, `followup.id`) — the frontend's `PatientEncounterDetail`
  type has no `id` field, only `tracking_id`.
- Returns `404` if the Tracking ID doesn't resolve to anything, so an
  invalid or mistyped code can't be distinguished from "exists but you're
  not allowed to see it" — both should look identical to the caller.

```json
{
  "tracking_id": "HCC-83AF92",
  "patient": { "full_name": "...", "phone": "...", "gender": "..." },
  "age": 34,
  "symptoms": "...",
  "status": "billing_ready",
  "pathway": "opd",
  "urgency": "medium",
  "created_at": "...",
  "updated_at": "...",
  "triage": { "...": "..." },
  "case_summary": { "...": "..." },
  "billing_records": [ { "...": "..." } ],
  "followups": [ { "...": "..." } ],
  "timeline": [ { "...": "..." } ]
}
```

## Existing endpoints — used unmodified, or not used at all

- The existing `POST /intake/web`, `POST /triage/encounters/{id}/clarify`,
  `GET /encounters/{id}`, and `GET /followup/{id}` remain exactly as they
  are today for the Staff Portal's use. The Patient Portal calls none of
  them directly (see the three new endpoints above) precisely because they
  all key off the internal id, which this app never has.
- `GET /encounters` (the unscoped, hospital-wide list used by the Staff
  Portal) is never called anywhere in this app. There is no page, route, or
  API call in the Patient Portal that could return more than one encounter.

## Generating the Tracking ID

Any scheme is fine as long as it's not sequential/guessable. A reasonable
default: `"HCC-" + secrets.token_hex(3).upper()` (6 hex chars → 16.7M
possibilities, regenerate on the rare collision). Treat it the same way
you'd treat a password-reset token: don't log it in plaintext anywhere
easily accessible, and don't return it from any endpoint other than the
`POST /patient/intake` call that creates it and the `GET` call that's
already authenticated by possessing it.
