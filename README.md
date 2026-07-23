# AI-Powered Hospital Command Center

Multi-agent workflow platform for hospital automation: patient flow, OPD coordination, discharge summaries, insurance communication, and doctor assistance.

**Stack:** LangGraph · FastAPI · SQLite · Streamlit · Pydantic

## Quick start

```powershell
cd ai-hospital-command-center
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
copy .env.example .env
python scripts\init_db.py
```

### Streamlit UI (command center)

```powershell
python scripts\run_ui.py
```

Open http://localhost:8501 — you should see **Welcome to Hospital command center**.

### FastAPI backend

```powershell
python scripts\run_api.py
```

- Root: http://localhost:8000/ — same welcome message (JSON)
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

## Project layout

```
src/hospital_command_center/
├── agents/          # Stub LLM agents (deterministic outputs)
├── api/             # FastAPI routes
├── channels/        # WhatsApp, Web, App intake adapters
├── core/            # Config, logging, exceptions
├── db/              # SQLAlchemy models & repositories
├── domain/          # Pydantic models
├── graphs/          # LangGraph patient workflow (linear stub)
├── services/        # Service layer
└── ui/              # Streamlit app
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/MODULE_MAP.md](docs/MODULE_MAP.md).

## Intake channels (API)

| Channel | Endpoint |
|---------|----------|
| Web | `POST /api/v1/intake/web` |
| Mobile app | `POST /api/v1/intake/app` |
| WhatsApp (stub) | `POST /api/v1/webhooks/whatsapp` |

Set `OPENAI_API_KEY` in `.env` for LLM triage. Without it, intake returns an error (no fallback).

## Status

LLM triage is live; routing/billing/follow-up agents remain rule-based stubs.
