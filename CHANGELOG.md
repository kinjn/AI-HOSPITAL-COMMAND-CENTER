# Fix changelog (frontend + backend)

If you're ever unsure whether your local project has all fixes applied, check this file exists
with all the entries below — if any are missing, you have a partial/stale copy and should
re-extract the full zip rather than patching individual files.

1. **CORS + real `/encounters` data + new `/encounters/{id}`** — see `BACKEND_CHANGES.md`.
2. **`/intake/web` and `/intake/app` no longer 500 on invalid input** — invalid patient
   name/phone now returns a clean 422 instead of crashing
   (`api/routes/intake.py`).
3. **`/triage/.../clarify` hardened the same way** — `api/routes/triage.py` now catches
   `IntakeError`/`TriageError`/`NotConfiguredError`/`ValidationError` locally instead of relying
   solely on the global handlers in `app.py`.
4. **Ollama latency fix** — `agents/llm.py` (`is_ollama_backend()`), `agents/structured_output.py`,
   and `agents/followup.py` skip the doomed `json_schema` attempt when talking to a local Ollama
   backend, instead of wasting a guaranteed-400 round-trip on every single agent call. Has no
   effect once you're on a real OpenAI-compatible cloud provider (e.g. Groq) — it auto-detects
   and gets out of the way.
5. **Dietary preference now actually reaches the backend** — `channels/web.py` and
   `channels/mobile_app.py` were silently dropping `dietary_preference`/`food_allergies` even
   though the domain model and follow-up agent both support them. Fixed in both adapters.
   `frontend/src/components/intake/intake-form.tsx` has a new optional "Dietary information"
   section (dropdown + free text) to actually collect it.
6. **Insurance pre-authorization document now exposed** — it was already being generated and
   stored (`insurance_doc_json`) but never returned by any endpoint. `api/routes/encounters.py`
   now unwraps and returns it; `frontend/src/pages/EncounterResult.tsx` renders it under
   "Billing & insurance".
7. **Frontend clarification-question robustness** — `frontend/src/pages/NewPatient.tsx` now
   derives which questions are still unanswered from the backend's own conversation state
   (`pendingQuestions()`), instead of trusting the raw LLM output, which avoids an answer-count
   mismatch if a smaller model ever re-lists an already-answered question on a later round.
8. **Pre-existing conditions field, fully wired** — `known_medical_conditions` existed on the
   intake domain model but was dropped before it ever reached `intake_context_json`, and no agent
   accepted it. Now: persisted in `intake_context_json`, threaded through
   `graphs/state.py`/`graphs/nodes.py`, and consumed by both `TriageAgent` and
   `MedicalSummarizerAgent` as informational context. Added as an optional field on the intake
   form.
9. **Update dietary preference after intake** — new `PATCH /encounters/{id}/dietary` endpoint
   updates the stored intake context and regenerates + persists a fresh follow-up plan, so the
   generic "please confirm dietary preference" placeholder isn't a dead end. Surfaced on the
   Encounter Result page (`components/encounter/dietary-update-form.tsx`), shown only when
   `diet_guidance.preferences_confirmed` is false.
10. **Insurance document formatting fixed** — the raw pre-authorization text is an ASCII-formatted
    plaintext document (meant for printing/faxing) with `====` separators; rendering it as a
    flowing `<p>` collapsed all the line breaks into a wall of text. Now the structured fields
    (reference number, clinical indication, proposed services, ICD-10/CPT codes, coverage notes,
    submission instructions) are the primary display, with the full raw text available in a
    collapsible, monospace, pre-formatted section for printing/submission.
11. **Encounter Result page was only rendering a fraction of the data the API already returned** —
    the backend was correctly generating and persisting extracted patient history, the AI's SOAP
    doctor briefing, diet recommended/avoid lists, hydration notes, special instructions, and
    escalation ("red flag") rules the whole time; the React page just never had UI for most of
    them (only summary text, tests, meds, labs, and a one-line diet summary were shown). Not a
    backend regression — added the missing sections to `EncounterResult.tsx`.

## Reminder about the triage prompt

`prompts/triage.md` explicitly tells the model to **skip** clarifying questions for obvious
emergencies (its own example is "chest pain"). Testing with something like "chest pain and
headache" is expected to go straight to a decision — that's not a bug. Use a genuinely vague
input (e.g. just "not feeling well") to exercise the clarification flow.
