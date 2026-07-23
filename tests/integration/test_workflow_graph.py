"""Integration tests: LangGraph workflow — verifies the graph runs correctly."""

import pytest
from uuid import uuid4

from hospital_command_center.db.session import get_engine
from hospital_command_center.db.base import Base
from hospital_command_center.db import models  # noqa: F401
from hospital_command_center.graphs.patient_workflow import run_patient_workflow


@pytest.fixture(scope="module", autouse=True)
async def setup_db():
    """Create all tables before tests, drop after."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def test_workflow_returns_all_stages():
    """
    Calls run_patient_workflow() directly — bypasses HTTP layer entirely.
    Verifies all LangGraph nodes ran and populated state correctly.
    """
    result = run_patient_workflow(
        encounter_id=uuid4(),
        symptoms="Mild headache and fatigue for 1 day",
        patient_name="Graph Test Patient",
        age=25,
        gender="female",
        phone="9000000099",
        channel="web",
    )

    assert "triage" in result
    assert "routing" in result
    assert "medical_summary" in result
    assert "billing" in result
    assert "followup" in result


async def test_triage_urgency_is_valid():
    result = run_patient_workflow(
        encounter_id=uuid4(),
        symptoms="Severe chest pain and difficulty breathing",
        patient_name="Graph Test Patient 2",
        age=60,
        gender="male",
        phone="9000000098",
        channel="web",
    )
    assert result["triage"]["urgency"] in ("low", "medium", "high", "critical")


async def test_critical_symptoms_route_to_emergency():
    """Safety override: critical urgency must always go to emergency."""
    result = run_patient_workflow(
        encounter_id=uuid4(),
        symptoms="Unresponsive patient, no pulse, not breathing",
        patient_name="Graph Test Patient 3",
        age=70,
        gender="male",
        phone="9000000097",
        channel="web",
    )
    assert result["triage"]["urgency"] == "critical"
    assert result["routing"]["pathway"] == "emergency"


async def test_billing_cost_varies_by_pathway():
    """Emergency should cost more than teleconsultation."""
    emergency_result = run_patient_workflow(
        encounter_id=uuid4(),
        symptoms="Heart attack symptoms, crushing chest pain",
        patient_name="Billing Test Emergency",
        age=65,
        gender="male",
        phone="9000000096",
        channel="web",
    )

    tele_result = run_patient_workflow(
        encounter_id=uuid4(),
        symptoms="Mild cold, runny nose, no fever",
        patient_name="Billing Test Tele",
        age=25,
        gender="female",
        phone="9000000095",
        channel="web",
    )

    emergency_cost = float(emergency_result["billing"]["estimated_cost_inr"])
    tele_cost = float(tele_result["billing"]["estimated_cost_inr"])

    assert emergency_cost > tele_cost