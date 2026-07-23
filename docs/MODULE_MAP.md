# Module Map

Maps each workflow step to packages and files.

## 1. Patient intake (WhatsApp / Web / App)

| Component | Path |
|-----------|------|
| Channel adapters | `channels/whatsapp.py`, `channels/web.py`, `channels/mobile_app.py` |
| Intake API | `api/routes/intake.py`, `api/routes/webhooks.py` |
| Domain models | `domain/intake.py`, `domain/patient.py` |
| Service | `services/intake_service.py` |

## 2. Triage LLM

| Component | Path |
|-----------|------|
| Agent | `agents/triage.py` |
| Prompt | `prompts/triage.md` |
| Domain | `domain/triage.py` |
| Service | `services/triage_service.py` |
| Graph node | `graphs/nodes.py` (triage node) |

## 3. Workflow routing

| Pathways | `domain/workflow.py` (Emergency, OPD, Teleconsultation, Specialist) |
| Agent | `agents/router.py` |
| Service | `services/routing_service.py` |
| Conditional edges | `graphs/edges.py` |

## 4. Medical summarizer

| Agent | `agents/medical_summarizer.py` |
| Domain | `domain/medical.py` |
| Service | `services/summarization_service.py` |

## 5. Billing / insurance

| Agent | `agents/billing_insurance.py` |
| Domain | `domain/billing.py` |
| Service | `services/billing_service.py` |

## 6. Follow-up automation

| Agent | `agents/followup.py` |
| Domain | `domain/followup.py` |
| Service | `services/followup_service.py` |
| Persistence | `db/models/followup.py`, `db/repositories/followup.py` |

## Orchestration

| Piece | Path |
|-------|------|
| Full graph | `graphs/patient_workflow.py` |
| State | `graphs/state.py` |
| Runner | `services/workflow_service.py` |

## Surfaces

| Surface | Path |
|---------|------|
| REST API | `api/app.py`, `api/routes/*` |
| Staff UI | `ui/app.py`, `ui/pages/*` |
| DB | `db/session.py`, `db/models/*` |
