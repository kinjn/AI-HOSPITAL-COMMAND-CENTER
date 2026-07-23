# Database Design — AI Hospital Command Center

## Overview

The database has **8 tables** covering all workflows: patient intake, triage,
case summarization, doctor routing, appointments, billing/insurance, and follow-up automation.

Each table maps to one agent or domain in the system. All foreign keys are enforced
at the ORM level via SQLAlchemy `ForeignKey` and navigable via `relationship()`.

---

## Entity Relationship Diagram

```
patients ──────────────────────────────────────────┐
   │                                               │
   │ (1 to many)                                   │ (1 to many)
   ▼                                               ▼
encounters                                    appointments
   │                                               ▲
   ├──(1 to 1)──► triage_results                   │
   │                                               │
   ├──(1 to 1)──► case_summaries              doctors
   │              (1 to many)
   ├──(1 to many)─► billing_records
   │
   ├──(1 to many)─► appointments
   │
   └──(1 to many)─► followups
```

**Key relationships:**
- A `patient` has many `encounters` (one per visit/submission)
- An `encounter` is the root — all agent outputs hang off it
- `triage_results` and `case_summaries` are 1-to-1 with an encounter
- `billing_records`, `appointments`, `followups` are 1-to-many with an encounter
- A `patient` also links directly to `appointments` (for walk-ins with no encounter)
- A `doctor` links to many `appointments`

---

## Tables

### 1. `patients`
Stores identity and demographics. Created once on first contact.

| Column         | Type        | Nullable | Default    | Notes                        |
|----------------|-------------|----------|------------|------------------------------|
| id             | String(36)  | No       | UUID4      | Primary key                  |
| full_name      | String(255) | No       | —          | Required                     |
| phone          | String(32)  | Yes      | —          |                              |
| email          | String(255) | Yes      | —          |                              |
| date_of_birth  | String(16)  | Yes      | —          | Format: `YYYY-MM-DD`         |
| gender         | String(16)  | Yes      | —          | `male` / `female` / `other`  |
| source_channel | String(32)  | No       | `web`      | `whatsapp` / `web` / `app`   |
| created_at     | DateTime    | No       | utcnow     | Auto-set on insert           |

**Relationships:**
- `encounters` → list of `EncounterModel`
- `appointments` → list of `AppointmentModel`

---

### 2. `encounters`
One row = one patient visit or symptom submission.
This is the **root/central table** — every agent writes its output to a table linked here.

| Column         | Type        | Nullable | Default    | Notes                                              |
|----------------|-------------|----------|------------|----------------------------------------------------|
| id             | String(36)  | No       | UUID4      | Primary key                                        |
| patient_id     | String(36)  | Yes      | —          | FK → patients.id (nullable for anonymous intake)  |
| symptoms       | Text        | No       | `""`       | Raw symptom text submitted by patient              |
| source_channel | String(32)  | No       | `web`      | `whatsapp` / `web` / `app`                        |
| status         | String(32)  | No       | `intake`   | Workflow stage (see lifecycle below)               |
| pathway        | String(32)  | Yes      | —          | Set after triage (see values below)                |
| created_at     | DateTime    | No       | utcnow     | Auto-set on insert                                 |
| updated_at     | DateTime    | Yes      | —          | Auto-updated on any change                         |

**`status` lifecycle:**
```
intake → triaged → routed → summary_ready → billing_ready → closed
```

**`pathway` values:** `emergency` / `opd` / `teleconsult` / `specialist`

**Relationships:**
- `patient` → `PatientModel`
- `triage_result` → `TriageResultModel` (single object, uselist=False)
- `case_summary` → `CaseSummaryModel` (single object, uselist=False)
- `billing_records` → list of `BillingRecordModel`
- `appointments` → list of `AppointmentModel`
- `followups` → list of `FollowUpModel`

---

### 3. `triage_results`
Output of the **Triage LLM agent**. One row per encounter (1-to-1).

| Column            | Type       | Nullable | Default | Notes                                              |
|-------------------|------------|----------|---------|----------------------------------------------------|
| id                | String(36) | No       | UUID4   | Primary key                                        |
| encounter_id      | String(36) | No       | —       | FK → encounters.id                                 |
| urgency_level     | String(32) | No       | —       | `low` / `medium` / `high` / `critical`             |
| suggested_pathway | String(32) | No       | —       | `emergency` / `opd` / `teleconsult` / `specialist` |
| reasoning         | Text       | Yes      | —       | LLM's explanation for the classification           |
| raw_llm_response  | Text       | Yes      | —       | Full LLM output stored for audit/debugging         |
| created_at        | DateTime   | No       | utcnow  | Auto-set on insert                                 |

**Relationships:**
- `encounter` → `EncounterModel`

---

### 4. `case_summaries`
Output of the **Medical Summarizer agent**. One row per encounter (1-to-1).

| Column               | Type       | Nullable | Default | Notes                                     |
|----------------------|------------|----------|---------|-------------------------------------------|
| id                   | String(36) | No       | UUID4   | Primary key                               |
| encounter_id         | String(36) | No       | —       | FK → encounters.id                        |
| summary_text         | Text       | No       | `""`    | Generated case summary                    |
| suggested_tests_json | Text       | No       | `"[]"`  | JSON array e.g. `["CBC", "ECG"]`          |
| extracted_history    | Text       | Yes      | —       | Past history pulled from patient records  |
| doctor_notes         | Text       | Yes      | —       | Optional notes added by reviewing doctor  |
| created_at           | DateTime   | No       | utcnow  | Auto-set on insert                        |

**Relationships:**
- `encounter` → `EncounterModel`

---

### 5. `doctors`
Doctor registry. Independent table — seeded by hospital admin, not created by agents.

| Column         | Type        | Nullable | Default | Notes                                  |
|----------------|-------------|----------|---------|----------------------------------------|
| id             | String(36)  | No       | UUID4   | Primary key                            |
| full_name      | String(255) | No       | —       | Required                               |
| specialization | String(128) | No       | —       | e.g. `Cardiology` / `General` / `ENT` |
| contact_phone  | String(32)  | Yes      | —       |                                        |
| contact_email  | String(255) | Yes      | —       |                                        |
| is_available   | Boolean     | No       | `True`  | Quick availability flag                |
| created_at     | DateTime    | No       | utcnow  | Auto-set on insert                     |

**Relationships:**
- `appointments` → list of `AppointmentModel`

---

### 6. `appointments`
Links a patient, doctor, and (optionally) an encounter.
One encounter can have multiple appointments — e.g. initial OPD + specialist referral.

| Column           | Type       | Nullable | Default      | Notes                                                |
|------------------|------------|----------|--------------|------------------------------------------------------|
| id               | String(36) | No       | UUID4        | Primary key                                          |
| patient_id       | String(36) | No       | —            | FK → patients.id                                     |
| doctor_id        | String(36) | No       | —            | FK → doctors.id                                      |
| encounter_id     | String(36) | Yes      | —            | FK → encounters.id (nullable for walk-ins)           |
| appointment_type | String(32) | No       | —            | `opd` / `teleconsult` / `specialist`                 |
| scheduled_at     | DateTime   | No       | —            | Appointment date and time                            |
| status           | String(32) | No       | `scheduled`  | `scheduled` / `completed` / `cancelled` / `no_show` |
| notes            | Text       | Yes      | —            | Optional notes                                       |
| created_at       | DateTime   | No       | utcnow       | Auto-set on insert                                   |

> **Why `patient_id` is kept here directly:**
> `encounter_id` is nullable because walk-in or direct teleconsult appointments
> can be booked before any encounter is created. In those cases,
> `encounter.patient` is not reachable, so `patient_id` must stay as a direct FK.

**Relationships:**
- `patient` → `PatientModel`
- `doctor` → `DoctorModel`
- `encounter` → `EncounterModel` (can be None)

---

### 7. `billing_records`
Output of the **Billing/Insurance agent**.
**1-to-many with encounters** — one encounter can produce multiple billing entries:
initial estimate → revised after tests → insurance claim → final invoice.

| Column             | Type          | Nullable | Default   | Notes                                            |
|--------------------|---------------|----------|-----------|--------------------------------------------------|
| id                 | String(36)    | No       | UUID4     | Primary key                                      |
| encounter_id       | String(36)    | No       | —         | FK → encounters.id                               |
| estimated_cost     | Numeric(10,2) | Yes      | —         | Nullable until estimate is generated             |
| currency           | String(8)     | No       | `INR`     |                                                  |
| consultation_fee   | Numeric(10,2) | No       | `0.00`    | Itemized consultation cost                       |
| test_cost          | Numeric(10,2) | No       | `0.00`    | Itemized diagnostics/test cost                   |
| medication_cost    | Numeric(10,2) | No       | `0.00`    | Itemized medication cost                         |
| misc_cost          | Numeric(10,2) | No       | `0.00`    | Itemized miscellaneous cost                      |
| preauth_reference  | String(64)    | Yes      | —         | Indexed insurance pre-authorization reference    |
| icd10_codes_json   | Text          | No       | `"[]"`    | Serialized ICD-10 diagnosis code list            |
| cpt_codes_json     | Text          | No       | `"[]"`    | Serialized CPT procedure/service code list       |
| insurance_provider | String(128)   | Yes      | —         |                                                  |
| insurance_doc_json | Text          | No       | `"{}"`    | Generated insurance-compatible document as JSON  |
| status             | String(32)    | No       | `draft`   | `draft` / `submitted` / `approved` / `rejected` |
| created_at         | DateTime      | No       | utcnow    | Auto-set on insert                               |

> **Note:** `patient_id` is intentionally not stored here.
> Reach the patient via `billing_record.encounter.patient` to avoid redundancy.
> `insurance_doc_json` is retained for full-document compatibility; normalized columns support direct SQL querying and reporting.

**Relationships:**
- `encounter` → `EncounterModel`

---

### 8. `followups`
One encounter produces **multiple follow-up rows** — one per reminder cycle.
Covers medication reminders, lab reminders, diet guidance, and escalation checks.

| Column        | Type       | Nullable | Default       | Notes                                                        |
|---------------|------------|----------|---------------|--------------------------------------------------------------|
| id            | String(36) | No       | UUID4         | Primary key                                                  |
| encounter_id  | String(36) | No       | —             | FK → encounters.id                                           |
| followup_type | String(32) | No       | `medication`  | `medication` / `lab` / `diet` / `escalation`                |
| plan_json     | Text       | No       | `"{}"`        | Reminder details (see structure below)                       |
| status        | String(32) | No       | `pending`     | `pending` / `sent` / `acknowledged` / `escalated` / `done`  |
| scheduled_at  | DateTime   | Yes      | —             | When this reminder fires                                     |
| created_at    | DateTime   | No       | utcnow        | Auto-set on insert                                           |

**`plan_json` structure:**
```json
{
  "type": "medication",
  "items": ["Metformin 500mg twice daily", "Aspirin 75mg once daily"],
  "message": "Hello, this is a reminder to take your medications.",
  "channel": "whatsapp"
}
```

**`channel` values:** `whatsapp` / `sms` / `email`

**Relationships:**
- `encounter` → `EncounterModel`

---

## Workflow → Table Mapping

| Project Workflow Step                  | Table(s) Written                                        |
|----------------------------------------|---------------------------------------------------------|
| Patient submits symptoms               | `patients` (created), `encounters` (created)            |
| Triage LLM classifies urgency          | `triage_results` (created), `encounters.status` updated |
| Route to OPD / Emergency / etc.        | `encounters.pathway` updated, `appointments` (created)  |
| Medical summarizer agent runs          | `case_summaries` (created)                              |
| Billing / insurance agent runs         | `billing_records` (created or updated)                  |
| Follow-up automation triggers          | `followups` (created per reminder cycle)                |

---

## ORM Navigation Examples

```python
# Load a patient's full encounter history
patient.encounters  # list[EncounterModel]

# From an encounter, get all agent outputs
encounter.triage_result        # TriageResultModel | None
encounter.case_summary         # CaseSummaryModel | None
encounter.billing_records      # list[BillingRecordModel]
encounter.appointments         # list[AppointmentModel]
encounter.followups            # list[FollowUpModel]

# From a billing record, get back to the patient
billing_record.encounter.patient  # PatientModel

# Get all appointments for a doctor
doctor.appointments  # list[AppointmentModel]
```

---

## Tech Stack

| Component   | Choice                                                                 |
|-------------|------------------------------------------------------------------------|
| ORM         | SQLAlchemy 2.x async (`mapped_column` style)                          |
| Session     | `sqlalchemy.ext.asyncio` — `AsyncSession` via `async_sessionmaker`    |
| ID strategy | UUID4 strings (`String(36)`) — portable across all databases          |
| Database    | Configured via `settings.database_url` — PostgreSQL for production, SQLite for local dev |
| Migrations  | Alembic — run `alembic init` then `alembic revision --autogenerate`   |

---

