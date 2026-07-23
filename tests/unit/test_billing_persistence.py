"""Unit tests for BillingRecordModel ORM persistence — normalized columns."""

from __future__ import annotations

from decimal import Decimal
import json
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from hospital_command_center.db import models  # noqa: F401 — registers all ORM classes
from hospital_command_center.db.base import Base
from hospital_command_center.db.models.billing_record import BillingRecordModel

# ---------------------------------------------------------------------------
# In-memory SQLite test engine/session fixture
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_billing_record(**overrides) -> BillingRecordModel:
    defaults = dict(
        encounter_id="enc-0001",
        estimated_cost=Decimal("3050.00"),
        currency="INR",
        consultation_fee=Decimal("500.00"),
        test_cost=Decimal("1050.00"),
        medication_cost=Decimal("350.00"),
        misc_cost=Decimal("100.00"),
        preauth_reference="PREAUTH-ENC00001",
        icd10_codes_json=json.dumps(["R51.9", "J06.9"]),
        cpt_codes_json=json.dumps(["99213", "85025", "93000"]),
        insurance_doc_json=json.dumps(
            {"documentation": "stub", "document": {}, "cost_breakdown": {}}
        ),
        status="draft",
    )
    defaults.update(overrides)
    return BillingRecordModel(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBillingRecordModelColumns:
    """Verify that the normalized columns are persisted and retrieved correctly."""

    @pytest.mark.asyncio
    async def test_itemized_costs_persisted(self, session: AsyncSession):
        record = _make_billing_record()
        session.add(record)
        await session.commit()
        await session.refresh(record)

        assert record.consultation_fee == Decimal("500.00")
        assert record.test_cost == Decimal("1050.00")
        assert record.medication_cost == Decimal("350.00")
        assert record.misc_cost == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_estimated_cost_matches_total(self, session: AsyncSession):
        record = _make_billing_record(estimated_cost=Decimal("2000.00"))
        session.add(record)
        await session.commit()
        await session.refresh(record)

        assert record.estimated_cost == Decimal("2000.00")

    @pytest.mark.asyncio
    async def test_preauth_reference_persisted(self, session: AsyncSession):
        record = _make_billing_record(preauth_reference="PREAUTH-ABCD1234")
        session.add(record)
        await session.commit()
        await session.refresh(record)

        assert record.preauth_reference == "PREAUTH-ABCD1234"

    @pytest.mark.asyncio
    async def test_preauth_reference_nullable(self, session: AsyncSession):
        """No unique constraint — two records for the same encounter are allowed."""
        r1 = _make_billing_record(encounter_id="enc-0002", preauth_reference="PREAUTH-SAME")
        r2 = _make_billing_record(encounter_id="enc-0002", preauth_reference="PREAUTH-SAME")
        session.add(r1)
        session.add(r2)
        await session.commit()  # Should not raise IntegrityError

    @pytest.mark.asyncio
    async def test_icd10_codes_json_roundtrip(self, session: AsyncSession):
        codes = ["R51.9", "I10", "R50.9"]
        record = _make_billing_record(icd10_codes_json=json.dumps(codes))
        session.add(record)
        await session.commit()
        await session.refresh(record)

        assert json.loads(record.icd10_codes_json) == codes

    @pytest.mark.asyncio
    async def test_cpt_codes_json_roundtrip(self, session: AsyncSession):
        codes = ["99285", "71046", "81003"]
        record = _make_billing_record(cpt_codes_json=json.dumps(codes))
        session.add(record)
        await session.commit()
        await session.refresh(record)

        assert json.loads(record.cpt_codes_json) == codes

    @pytest.mark.asyncio
    async def test_insurance_doc_json_backward_compat(self, session: AsyncSession):
        """The full blob column should still be present and readable."""
        blob = json.dumps(
            {"documentation": "stub text", "document": {"ref": "PREAUTH-X"}, "cost_breakdown": {}}
        )
        record = _make_billing_record(insurance_doc_json=blob)
        session.add(record)
        await session.commit()
        await session.refresh(record)

        loaded = json.loads(record.insurance_doc_json)
        assert loaded["documentation"] == "stub text"
        assert loaded["document"]["ref"] == "PREAUTH-X"

    @pytest.mark.asyncio
    async def test_defaults_for_new_columns(self, session: AsyncSession):
        """Records created without explicit costs should default to 0.0 / empty lists."""
        record = BillingRecordModel(encounter_id="enc-0003", status="draft")
        session.add(record)
        await session.commit()
        await session.refresh(record)

        assert record.consultation_fee == Decimal("0.00")
        assert record.test_cost == Decimal("0.00")
        assert record.medication_cost == Decimal("0.00")
        assert record.misc_cost == Decimal("0.00")
        assert record.preauth_reference is None
        assert json.loads(record.icd10_codes_json) == []
        assert json.loads(record.cpt_codes_json) == []


# ---------------------------------------------------------------------------
# Persistence service integration test
# ---------------------------------------------------------------------------


class TestPersistenceService:
    """Call EncounterPersistenceService.persist_workflow_state and verify new columns."""

    @pytest.mark.asyncio
    async def test_persist_workflow_state_populates_billing_columns(
        self, session: AsyncSession
    ):
        from sqlalchemy import select

        from hospital_command_center.db.models.encounter import EncounterModel
        from hospital_command_center.db.models.patient import PatientModel
        from hospital_command_center.services.encounter_persistence import (
            EncounterPersistenceService,
        )

        # --- Seed a minimal patient and encounter so FK constraints pass ---
        patient = PatientModel(
            full_name="Test Patient",
            phone="9999999999",
            source_channel="web",
        )
        session.add(patient)
        await session.flush()

        encounter = EncounterModel(
            patient_id=patient.id,
            symptoms="headache",
            source_channel="web",
            status="intake",
        )
        session.add(encounter)
        await session.commit()
        await session.refresh(encounter)

        # --- Build a realistic billing state dict (mirrors workflow output) ---
        billing_state = {
            "estimated_cost_inr": "2100.00",
            "currency": "INR",
            "status": "draft",
            "cost_breakdown": {
                "consultation_fee": "500.00",
                "test_cost": "1050.00",
                "medication_cost": "350.00",
                "miscellaneous_cost": "100.00",
                "total": "2000.00",
            },
            "insurance_document": {
                "reference_number": "PREAUTH-ABCD1234",
                "icd10_codes": ["R51.9", "J06.9"],
                "cpt_codes": ["99213", "85025"],
                "document_type": "pre_authorization_request",
                "clinical_indication": "Headache and mild fever.",
                "coverage_notes": "Low urgency, OPD pathway.",
            },
            "insurance_documentation": (
                "INSURANCE PRE-AUTHORIZATION REQUEST\nReference: PREAUTH-ABCD1234"
            ),
        }

        state = {
            "billing": billing_state,
        }

        svc = EncounterPersistenceService(session)
        await svc.persist_workflow_state(encounter.id, state)

        # --- Fetch the saved billing record and assert all 7 new columns ---
        from hospital_command_center.db.models.billing_record import BillingRecordModel

        result = await session.execute(
            select(BillingRecordModel).where(
                BillingRecordModel.encounter_id == encounter.id
            )
        )
        record = result.scalar_one()

        assert record.consultation_fee == Decimal("500.00")
        assert record.test_cost == Decimal("1050.00")
        assert record.medication_cost == Decimal("350.00")
        assert record.misc_cost == Decimal("100.00")
        assert record.preauth_reference == "PREAUTH-ABCD1234"
        assert json.loads(record.icd10_codes_json) == ["R51.9", "J06.9"]
        assert json.loads(record.cpt_codes_json) == ["99213", "85025"]
