"""Unit tests for triage pause/resume persistence."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from hospital_command_center.db import models  # noqa: F401
from hospital_command_center.db.base import Base
from hospital_command_center.db.models.encounter import EncounterModel
from hospital_command_center.db.models.patient import PatientModel
from hospital_command_center.services.encounter_persistence import EncounterPersistenceService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture()
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_persist_triage_pause_stores_pending_questions(session: AsyncSession) -> None:
    patient = PatientModel(full_name="Test Patient", phone="+10000000001")
    session.add(patient)
    await session.commit()

    encounter = EncounterModel(
        patient_id=patient.id,
        symptoms="I feel unwell",
        status="intake",
        intake_context_json=json.dumps({"patient_name": "Test Patient", "age": 30}),
    )
    session.add(encounter)
    await session.commit()

    persistence = EncounterPersistenceService(session)
    state = {
        "triage": {
            "status": "needs_clarification",
            "clarifying_questions": ["How long have you felt unwell?", "Any fever?"],
            "rationale": "Too vague.",
        }
    }
    saved = await persistence.persist_triage_pause(encounter.id, state)

    assert saved.status == "awaiting_triage_clarification"
    conversation = json.loads(saved.triage_conversation_json)
    assert len(conversation) == 2
    assert conversation[0]["question"] == "How long have you felt unwell?"
    assert conversation[0]["answer"] is None


@pytest.mark.asyncio
async def test_apply_clarification_answers_pairs_answers(session: AsyncSession) -> None:
    encounter = EncounterModel(
        symptoms="stomach pain",
        status="awaiting_triage_clarification",
        triage_conversation_json=json.dumps(
            [{"question": "How severe is the pain?", "answer": None}]
        ),
    )
    session.add(encounter)
    await session.commit()

    persistence = EncounterPersistenceService(session)
    conversation = persistence.apply_clarification_answers(encounter, ["7/10"])

    assert conversation[0]["answer"] == "7/10"
