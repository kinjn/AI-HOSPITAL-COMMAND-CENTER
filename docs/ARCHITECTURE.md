# Architecture Overview

## System Layers

| Layer | Responsibility | Primary modules |
|-------|----------------|-----------------|
| Channels | Patient intake (WhatsApp, Web, App) | `hospital_command_center.channels.*` |
| API | HTTP surface for clients & webhooks | `hospital_command_center.api.*` |
| Orchestration | Multi-agent workflow (LangGraph) | `hospital_command_center.graphs.*` |
| Agents | LLM-backed domain tasks | `hospital_command_center.agents.*` |
| Services | Business logic orchestration | `hospital_command_center.services.*` |
| Domain | Pydantic schemas & enums | `hospital_command_center.domain.*` |
| Persistence | SQLite via SQLAlchemy | `hospital_command_center.db.*` |
| UI | Staff / ops dashboard | `hospital_command_center.ui.*` |

## Core Workflow (LangGraph)

```
[Intake] → [Triage] → [Route] → [Medical Summarizer] → [Billing/Insurance] → [Follow-up Scheduler]
                ↓
         emergency | opd | teleconsultation | specialist_referral
```

## Agent Responsibilities

1. **Triage** — Classify urgency from symptoms (WhatsApp/Web/App payload).
2. **Router** — Select care pathway (Emergency, OPD, Teleconsultation, Specialist).
3. **Medical Summarizer** — Case summary, suggested tests, history extraction.
4. **Billing/Insurance** — Insurance-compatible docs, cost estimates.
5. **Follow-up** — Medication/lab reminders, diet guidance, escalation rules.

## Data Flow

- Inbound messages normalized to `domain` intake models.
- Graph state persisted in `graphs/state` and optionally checkpointed.
- Repositories read/write patient, encounter, and follow-up records in SQLite.

## Deployment Surfaces

- **FastAPI** — REST API + channel webhooks (`scripts/run_api.py`).
- **Streamlit** — Internal command center UI (`scripts/run_ui.py`).
- **LangGraph** — Invoked from services or API route handlers.
