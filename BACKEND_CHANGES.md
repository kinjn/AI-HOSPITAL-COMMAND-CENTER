# Backend changes required for the React frontend

Per the brief, backend logic, LangGraph workflows, and database models were **not** touched. The
following read-only, additive changes were required and made:

## 1. CORS (necessary — browser cross-origin calls)

- `src/hospital_command_center/core/config.py`: added `cors_allow_origins_raw` /
  `cors_allow_origins` setting (env var `CORS_ALLOW_ORIGINS`, comma-separated, defaults to the
  local Vite dev server origins).
- `src/hospital_command_center/api/app.py`: added `CORSMiddleware` using that setting.

No existing settings or routes were changed.

## 2. `GET /encounters` — was a stub, now returns real data

The endpoint previously returned only `id`, `patient_id`, `status`, `pathway` and an explicit
`"stub": true` marker — not enough to render an operations dashboard (patient name, age, urgency,
billing, follow-up due dates). It now eager-loads and returns, per encounter: patient info, age
(from existing intake context), urgency (from the existing triage result row), latest billing
summary, and latest follow-up summary. All values are read from rows already written by the
existing workflow/persistence services — no new data is computed or stored.

## 3. `GET /encounters/{id}` — new endpoint (additive)

Needed for the Encounter Result page (and for reloading an encounter's full detail without
re-running the workflow). Returns the same fields as the list endpoint plus: triage detail, case
summary, all billing records, all follow-up plans, and a timeline derived from existing
`created_at` timestamps on those rows. This endpoint did not exist before; nothing else was
changed or removed.

## 4. Repository additions (additive only)

`src/hospital_command_center/db/repositories/encounter.py` gained two new read methods,
`list_all_with_relations` and `get_by_id_with_relations`, which eager-load the relationships above
via `selectinload`. The existing `list_all`, `get_by_status`, etc. are untouched.

## What was intentionally left alone

- LangGraph workflow graph, nodes, and agents: unchanged.
- `POST /intake`, `POST /intake/web`, `POST /intake/app`,
  `POST /triage/encounters/{id}/clarify`, `GET/POST /followup/*`, `/workflow/*`, `/webhooks/*`:
  unchanged.
- Database models/migrations: unchanged.
- Auth (`x-api-key` header, single shared API key): unchanged — the frontend just sends it.
