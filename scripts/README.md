# Scripts

| Script | Purpose |
|--------|---------|
| `init_db.py` | Create SQLite schema for a new database; does not migrate existing tables |
| `run_api.py` | Start FastAPI with uvicorn |
| `run_ui.py` | Start Streamlit command center |

## Schema updates (existing databases)

If you see errors about missing columns (e.g. `consultation_fee`, `triage_conversation_json`), either delete `data/hospital_command_center.db` and run `init_db.py`, or apply:

```sql
ALTER TABLE encounters ADD COLUMN triage_conversation_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE encounters ADD COLUMN intake_context_json TEXT NOT NULL DEFAULT '{}';
```
