# Repository Design — AI Hospital Command Center

## What is the Repository Layer?

The repository layer is the **only place in the codebase that talks to the database**.

Every database read and write goes through a repository. Agents, services, and API
handlers never import SQLAlchemy sessions or write queries directly — they call
repository methods instead.

```
Agent / Service
      │
      ▼
  Repository         ← only layer that touches the DB
      │
      ▼
 SQLAlchemy (ORM)
      │
      ▼
  Database (PostgreSQL / SQLite)
```

---

## Why This Pattern?

- **Single responsibility** — each repository owns exactly one model/table
- **Easy to test** — you can mock a repository in tests without touching the DB
- **No scattered queries** — if a query needs to change, there is exactly one place to change it
- **Clean agents** — agents focus on AI logic, not SQL


If a task involves more than one repository (e.g. create encounter + create triage result
together), that belongs in a **service**, not a repository.

---

## Repositories

### `PatientRepository`
Owns the `patients` table.

| Method | Description |
|---|---|
| `create(patient)` | Insert a new patient record |
| `get_by_id(patient_id)` | Fetch a patient by UUID |
| `get_by_phone(phone)` | Look up patient by phone — used at intake to avoid duplicates |
| `get_by_email(email)` | Look up patient by email |
| `update(patient)` | Commit changes to an existing patient |
| `delete(patient)` | Remove a patient record |

---

### `EncounterRepository`
Owns the `encounters` table. This is the most-used repository — every agent reads/updates encounters.

| Method | Description |
|---|---|
| `create(encounter)` | Insert a new encounter |
| `get_by_id(encounter_id)` | Fetch a single encounter by UUID |
| `get_by_patient_id(patient_id)` | All encounters for a patient, newest first |
| `get_by_status(status)` | All encounters at a given workflow stage — used by the command center dashboard |
| `get_by_pathway(pathway)` | All encounters routed to a given pathway (e.g. all `emergency`) |
| `update(encounter)` | Commit status/pathway changes after each agent step |
| `delete(encounter)` | Remove an encounter |

---

### `TriageResultRepository`
Owns the `triage_results` table. Written to by the Triage LLM agent.

| Method | Description |
|---|---|
| `create(triage_result)` | Save triage agent output after classification |
| `get_by_id(triage_result_id)` | Fetch by UUID |
| `get_by_encounter_id(encounter_id)` | Fetch the triage result for a specific encounter (1-to-1) |
| `get_by_urgency_level(urgency_level)` | All results at a given urgency — useful for monitoring/dashboards |
| `update(triage_result)` | Update if triage is re-run |
| `delete(triage_result)` | Remove a triage result |

---

### `CaseSummaryRepository`
Owns the `case_summaries` table. Written to by the Medical Summarizer agent.

| Method | Description |
|---|---|
| `create(case_summary)` | Save summarizer agent output |
| `get_by_id(case_summary_id)` | Fetch by UUID |
| `get_by_encounter_id(encounter_id)` | Fetch the summary for a specific encounter (1-to-1) |
| `update(case_summary)` | Update if doctor adds notes or summary is regenerated |
| `delete(case_summary)` | Remove a summary |

---

### `DoctorRepository`
Owns the `doctors` table. This table is seeded by hospital admin, not by agents.

| Method | Description |
|---|---|
| `create(doctor)` | Add a new doctor to the registry |
| `get_by_id(doctor_id)` | Fetch a doctor by UUID |
| `get_all()` | All doctors, ordered by name |
| `get_available()` | All doctors with `is_available=True` — used by routing agent to assign appointments |
| `get_by_specialization(specialization)` | Doctors filtered by specialty — used for specialist referrals |
| `update(doctor)` | Update availability or contact info |
| `delete(doctor)` | Remove a doctor |

---

### `AppointmentRepository`
Owns the `appointments` table. Written to by the routing agent after triage.

| Method | Description |
|---|---|
| `create(appointment)` | Book a new appointment |
| `get_by_id(appointment_id)` | Fetch by UUID |
| `get_by_patient_id(patient_id)` | All appointments for a patient, newest first |
| `get_by_encounter_id(encounter_id)` | All appointments linked to an encounter |
| `get_by_doctor_id(doctor_id)` | All appointments for a doctor — used for doctor's schedule view |
| `get_by_status(status)` | Filter by status (e.g. all `scheduled` appointments) |
| `update(appointment)` | Update status (e.g. `scheduled` → `completed`) |
| `delete(appointment)` | Cancel/remove an appointment |

---

### `BillingRecordRepository`
Owns the `billing_records` table. Written to by the Billing/Insurance agent.
Multiple records per encounter are expected (initial estimate → revised → final invoice).

| Method | Description |
|---|---|
| `create(billing_record)` | Save a new billing entry |
| `get_by_id(billing_record_id)` | Fetch by UUID |
| `get_by_encounter_id(encounter_id)` | All billing records for an encounter, newest first |
| `get_by_status(status)` | All records at a given billing stage (e.g. all `submitted`) |
| `update(billing_record)` | Update cost estimate or status |
| `delete(billing_record)` | Remove a billing record |

---

### `FollowUpRepository`
Owns the `followups` table. Written to and polled by the Follow-up Automation agent.
Multiple follow-ups per encounter — one per reminder cycle.

| Method | Description |
|---|---|
| `create(followup)` | Schedule a new follow-up reminder |
| `get_by_id(followup_id)` | Fetch by UUID |
| `get_by_encounter_id(encounter_id)` | All follow-ups for an encounter, ordered by `scheduled_at` |
| `get_by_status(status)` | All follow-ups at a given stage |
| `get_by_type(followup_type)` | Filter by type (e.g. all `medication` reminders) |
| `get_pending()` | All follow-ups with `status=pending` ordered by `scheduled_at` — primary method used by the automation agent to find what needs to be sent next |
| `update(followup)` | Update status after reminder is sent or escalated |
| `delete(followup)` | Remove a follow-up |

---

## How to Use a Repository

Repositories take an `AsyncSession` injected at construction time.
Never instantiate a session inside a repository.

```python
# In a service or agent
async def run_triage(encounter_id: str, session: AsyncSession) -> None:
    encounter_repo = EncounterRepository(session)
    triage_repo = TriageResultRepository(session)

    encounter = await encounter_repo.get_by_id(encounter_id)

    # ... run LLM triage logic ...

    triage_result = TriageResultModel(
        encounter_id=encounter.id,
        urgency_level="high",
        suggested_pathway="emergency",
        reasoning="Chest pain with shortness of breath...",
    )
    await triage_repo.create(triage_result)

    encounter.status = "triaged"
    encounter.pathway = "emergency"
    await encounter_repo.update(encounter)
```

