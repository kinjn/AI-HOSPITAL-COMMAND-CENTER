"""Unit tests for the billing/insurance agent's clinical coding support."""

from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest

from hospital_command_center.agents.billing_insurance import (
    _PATHWAY_CPT_CODES,
    _TEST_CPT_CODES,
    _URGENCY_ICD10_CODES,
    BillingInsuranceAgent,
    _allowed_icd10_candidates,
    _dedupe_tests,
    _normalize_test_name,
    _sanitize_cpt_codes,
    _sanitize_icd10_codes,
)
from hospital_command_center.domain.billing import InsuranceDocument
from hospital_command_center.domain.triage import UrgencyLevel
from hospital_command_center.domain.workflow import CarePathway

# ---------------------------------------------------------------------------
# Fallback lookup table sanity checks
# ---------------------------------------------------------------------------


class TestFallbackLookupTables:
    """Verify the deterministic fallback code dictionaries are well-formed."""

    def test_test_cpt_codes_all_strings(self):
        for test_name, code in _TEST_CPT_CODES.items():
            assert isinstance(test_name, str)
            assert isinstance(code, str) and len(code) > 0

    def test_pathway_cpt_codes_cover_all_pathways(self):
        for pathway in CarePathway:
            assert pathway in _PATHWAY_CPT_CODES, f"Missing CPT code for pathway {pathway}"

    def test_urgency_icd10_codes_cover_all_levels(self):
        for level in UrgencyLevel:
            assert level in _URGENCY_ICD10_CODES, f"Missing ICD-10 code for urgency {level}"


# ---------------------------------------------------------------------------
# InsuranceDocument domain model
# ---------------------------------------------------------------------------


class TestInsuranceDocumentCodes:
    """Verify the InsuranceDocument accepts and serializes clinical codes."""

    def test_default_empty_codes(self):
        doc = InsuranceDocument(
            encounter_id=uuid4(),
            reference_number="PREAUTH-TEST",
            clinical_indication="Test indication",
            estimated_amount_inr=Decimal("1000.00"),
        )
        assert doc.icd10_codes == []
        assert doc.cpt_codes == []

    def test_codes_roundtrip_via_json(self):
        doc = InsuranceDocument(
            encounter_id=uuid4(),
            reference_number="PREAUTH-TEST",
            clinical_indication="Test indication",
            estimated_amount_inr=Decimal("1000.00"),
            icd10_codes=["R51.9", "J06.9"],
            cpt_codes=["99213", "85025"],
        )
        data = doc.model_dump(mode="json")
        assert data["icd10_codes"] == ["R51.9", "J06.9"]
        assert data["cpt_codes"] == ["99213", "85025"]

        restored = InsuranceDocument.model_validate(data)
        assert restored.icd10_codes == ["R51.9", "J06.9"]
        assert restored.cpt_codes == ["99213", "85025"]


# ---------------------------------------------------------------------------
# InsuranceDocument field-validator normalization
# ---------------------------------------------------------------------------


def _make_doc(**overrides):
    """Helper: build an InsuranceDocument with sensible defaults."""
    defaults = dict(
        encounter_id=uuid4(),
        reference_number="PREAUTH-TEST",
        clinical_indication="Test indication",
        estimated_amount_inr=Decimal("1000.00"),
        icd10_codes=[],
        cpt_codes=[],
    )
    defaults.update(overrides)
    return InsuranceDocument(**defaults)


class TestInsuranceDocumentNormalization:
    """Pydantic validators strip descriptions, dedup, and drop invalid codes."""

    # ------------------------------------------------------------------
    # ICD-10 normalization
    # ------------------------------------------------------------------

    def test_icd10_code_only_unchanged(self):
        """Plain code strings must pass through unchanged."""
        doc = _make_doc(icd10_codes=["R51.9", "J06.9", "I10"])
        assert doc.icd10_codes == ["R51.9", "J06.9", "I10"]

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("R51.9 — Headache, unspecified", "R51.9"),
            ("J06.9 — Acute upper respiratory infection, unspecified", "J06.9"),
            ("I10 — Essential hypertension", "I10"),
            ("E11.9 — Type 2 diabetes mellitus without complications", "E11.9"),
            ("R68.89 — Other general symptoms and signs", "R68.89"),
        ],
    )
    def test_icd10_strips_description(self, raw, expected):
        """Codes with em-dash descriptions are reduced to the bare code."""
        doc = _make_doc(icd10_codes=[raw])
        assert doc.icd10_codes == [expected]

    def test_icd10_removes_duplicates_preserves_order(self):
        """Duplicate codes are removed; first occurrence is kept."""
        doc = _make_doc(icd10_codes=["R51.9", "J06.9", "R51.9", "I10", "J06.9"])
        assert doc.icd10_codes == ["R51.9", "J06.9", "I10"]

    def test_icd10_ignores_invalid_entries(self):
        """Entries with no recognisable ICD-10 code are silently dropped."""
        doc = _make_doc(icd10_codes=["not a code", "   ", "12345", "R51.9"])
        assert doc.icd10_codes == ["R51.9"]

    def test_icd10_empty_list_stays_empty(self):
        doc = _make_doc(icd10_codes=[])
        assert doc.icd10_codes == []

    # ------------------------------------------------------------------
    # CPT normalization
    # ------------------------------------------------------------------

    def test_cpt_code_only_unchanged(self):
        """Plain 5-digit CPT strings must pass through unchanged."""
        doc = _make_doc(cpt_codes=["99213", "85025", "93000"])
        assert doc.cpt_codes == ["99213", "85025", "93000"]

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("99213 — Office/outpatient visit, established patient, low complexity", "99213"),
            ("85025 — Complete blood count (CBC) with differential", "85025"),
            ("93000 — Electrocardiogram (ECG), routine", "93000"),
            ("71046 — Chest X-ray, 2 views", "71046"),
            ("80048 — Basic metabolic panel", "80048"),
        ],
    )
    def test_cpt_strips_description(self, raw, expected):
        """Codes with em-dash descriptions are reduced to the bare code."""
        doc = _make_doc(cpt_codes=[raw])
        assert doc.cpt_codes == [expected]

    def test_cpt_removes_duplicates_preserves_order(self):
        """Duplicate CPT codes are removed; first occurrence is kept."""
        doc = _make_doc(cpt_codes=["99213", "85025", "99213", "93000", "85025"])
        assert doc.cpt_codes == ["99213", "85025", "93000"]

    def test_cpt_ignores_invalid_entries(self):
        """Entries with no 5-digit sequence are silently dropped."""
        doc = _make_doc(cpt_codes=["not a code", "1234", "123456", "99213"])
        assert doc.cpt_codes == ["99213"]

    def test_cpt_empty_list_stays_empty(self):
        doc = _make_doc(cpt_codes=[])
        assert doc.cpt_codes == []

    # ------------------------------------------------------------------
    # Mixed / combined
    # ------------------------------------------------------------------

    def test_mixed_raw_and_clean_codes_normalized(self):
        """A realistic mix of clean and description-bearing codes is handled correctly."""
        doc = _make_doc(
            icd10_codes=[
                "R51.9 — Headache, unspecified",
                "J06.9",
                "R51.9",          # duplicate of first after stripping
            ],
            cpt_codes=[
                "99213 — Office visit",
                "85025",
                "99213",          # duplicate
                "no valid code",  # invalid
            ],
        )
        assert doc.icd10_codes == ["R51.9", "J06.9"]
        assert doc.cpt_codes == ["99213", "85025"]


# ---------------------------------------------------------------------------
# Agent output: LLM returning descriptions is still normalized
# ---------------------------------------------------------------------------


class TestBillingAgentLLMCodeNormalization:
    """When the mocked LLM returns codes WITH descriptions, the stored
    InsuranceDocument must contain bare codes only."""

    @pytest.fixture()
    def agent(self):
        return BillingInsuranceAgent()

    def _make_kwargs(self, tests=None):
        eid = uuid4()
        return dict(
            encounter_id=eid,
            symptoms="headache and fever",
            triage={"encounter_id": str(eid), "urgency": "medium"},
            routing={"encounter_id": str(eid), "pathway": "opd"},
            medical_summary={
                "encounter_id": str(eid),
                "suggested_tests": tests or ["cbc"],
                "case_summary": "Patient presents with headache.",
                "history_notes": "No significant history.",
            },
        )

    @patch("hospital_command_center.agents.billing_insurance.invoke_structured")
    def test_llm_description_codes_normalized_in_document(self, mock_invoke, agent):
        """LLM output with descriptions should be stored as bare codes."""
        from unittest.mock import MagicMock

        mock_output = MagicMock()
        mock_output.clinical_indication = "Patient presents with headache and fever."
        mock_output.coverage_notes = "Urgency medium; OPD pathway appropriate."
        mock_output.icd10_codes = [
            "R51.9 — Headache, unspecified",
            "R50.9 — Fever, unspecified",
        ]
        mock_output.cpt_codes = [
            "99213 — Office/outpatient visit, established patient, low complexity",
            "85025 — Complete blood count (CBC) with differential",
        ]

        mock_invoke.return_value = mock_output

        result = agent.run(**self._make_kwargs())
        doc = result["insurance_document"]

        assert doc["icd10_codes"] == ["R51.9", "R50.9"]
        assert doc["cpt_codes"] == ["99213", "85025"]


# ---------------------------------------------------------------------------
# Agent fallback path (LLM unavailable)
# ---------------------------------------------------------------------------


class TestBillingAgentFallbackCodes:
    """When the LLM call fails, the agent should populate codes deterministically."""

    @pytest.fixture()
    def agent(self):
        return BillingInsuranceAgent()

    def _make_kwargs(self, urgency="medium", pathway="opd", tests=None):
        eid = uuid4()
        return dict(
            encounter_id=eid,
            # Use a neutral symptom string that does not trigger any ICD guardrail
            # so that urgency-based fallback codes are exercised.
            symptoms="general malaise",
            triage={"encounter_id": str(eid), "urgency": urgency},
            routing={"encounter_id": str(eid), "pathway": pathway},
            medical_summary={
                "encounter_id": str(eid),
                "suggested_tests": tests or ["cbc", "ecg"],
                "case_summary": "Patient presents with general malaise.",
                "history_notes": "No significant history.",
            },
        )

    @patch(
        "hospital_command_center.agents.billing_insurance.invoke_structured",
        side_effect=Exception("LLM unavailable"),
    )
    def test_fallback_icd10_codes_populated(self, _mock_invoke, agent):
        kwargs = self._make_kwargs(urgency="medium")
        result = agent.run(**kwargs)
        doc = result["insurance_document"]
        assert len(doc["icd10_codes"]) >= 1
        assert "R69" in doc["icd10_codes"]  # medium urgency fallback code must be present

    @patch(
        "hospital_command_center.agents.billing_insurance.invoke_structured",
        side_effect=Exception("LLM unavailable"),
    )
    def test_fallback_cpt_codes_include_pathway_and_tests(self, _mock_invoke, agent):
        kwargs = self._make_kwargs(pathway="opd", tests=["cbc", "ecg"])
        result = agent.run(**kwargs)
        doc = result["insurance_document"]
        # Should contain the OPD consultation code and both test codes
        assert "99213" in doc["cpt_codes"]   # OPD
        assert "85025" in doc["cpt_codes"]   # CBC
        assert "93000" in doc["cpt_codes"]   # ECG

    @patch(
        "hospital_command_center.agents.billing_insurance.invoke_structured",
        side_effect=Exception("LLM unavailable"),
    )
    def test_fallback_cpt_unknown_test_skipped(self, _mock_invoke, agent):
        kwargs = self._make_kwargs(tests=["some_exotic_test"])
        result = agent.run(**kwargs)
        doc = result["insurance_document"]
        # Only pathway code should be present; unknown test has no mapping
        assert len(doc["cpt_codes"]) == 1
        assert doc["cpt_codes"][0] == "99213"

    @patch(
        "hospital_command_center.agents.billing_insurance.invoke_structured",
        side_effect=Exception("LLM unavailable"),
    )
    def test_emergency_pathway_uses_correct_codes(self, _mock_invoke, agent):
        kwargs = self._make_kwargs(urgency="critical", pathway="emergency", tests=["chest x-ray"])
        result = agent.run(**kwargs)
        doc = result["insurance_document"]
        assert "R68.89" in doc["icd10_codes"]  # critical urgency fallback code must be present
        assert "99285" in doc["cpt_codes"]   # Emergency
        assert "71046" in doc["cpt_codes"]   # Chest X-ray

    @patch(
        "hospital_command_center.agents.billing_insurance.invoke_structured",
        side_effect=Exception("LLM unavailable"),
    )
    def test_documentation_text_includes_codes(self, _mock_invoke, agent):
        kwargs = self._make_kwargs(tests=["cbc"])
        result = agent.run(**kwargs)
        text = result["insurance_documentation"]
        assert "ICD-10 DIAGNOSIS CODES" in text
        assert "CPT PROCEDURE CODES" in text

class TestBillingAgentFuzzyMatching:
    """Verify that test names are normalized for unit cost and fallback CPT lookup."""

    @pytest.fixture()
    def agent(self):
        return BillingInsuranceAgent()

    @pytest.mark.parametrize(
        "test_name,expected_cost",
        [
            ("cbc", Decimal("450.00")),
            ("CBC", Decimal("450.00")),
            ("CBC Test", Decimal("450.00")),
            ("Complete Blood Count", Decimal("450.00")),
            ("Complete Blood Count (CBC)", Decimal("450.00")),
            ("ecg", Decimal("600.00")),
            ("ECG", Decimal("600.00")),
            ("Electrocardiogram", Decimal("600.00")),
            ("Chest Xray", Decimal("800.00")),
            ("Chest X-Ray", Decimal("800.00")),
            ("Chest X Ray", Decimal("800.00")),
            ("Chest X-ray", Decimal("800.00")),
            ("Some Unknown Test", Decimal("750.00")),  # default
        ],
    )
    def test_fuzzy_matching_costs(self, agent, test_name, expected_cost):
        cost = agent._test_unit_cost(test_name)
        assert cost == expected_cost

    @patch(
        "hospital_command_center.agents.billing_insurance.invoke_structured",
        side_effect=Exception("LLM unavailable"),
    )
    @pytest.mark.parametrize(
        "test_name,expected_cpt",
        [
            ("CBC Test", "85025"),
            ("Electrocardiogram", "93000"),
            ("Chest X-Ray", "71046"),
        ],
    )
    def test_fuzzy_matching_cpt_codes(self, _mock_invoke, agent, test_name, expected_cpt):
        eid = uuid4()
        kwargs = dict(
            encounter_id=eid,
            symptoms="test symptoms",
            triage={"encounter_id": str(eid), "urgency": "medium"},
            routing={"encounter_id": str(eid), "pathway": "opd"},
            medical_summary={
                "encounter_id": str(eid),
                "suggested_tests": [test_name],
                "case_summary": "Summary",
                "history_notes": "History",
            },
        )
        result = agent.run(**kwargs)
        cpt_codes = result["insurance_document"]["cpt_codes"]
        assert expected_cpt in cpt_codes


# ---------------------------------------------------------------------------
# Clinical code guardrails
# ---------------------------------------------------------------------------


def _make_agent_kwargs(
    *,
    symptoms: str,
    urgency: str = "high",
    pathway: str = "emergency",
    tests: list[str] | None = None,
    case_summary: str = "Patient presents with symptoms.",
) -> dict:
    """Build a full agent.run() kwargs dict for guardrail tests."""
    eid = uuid4()
    return dict(
        encounter_id=eid,
        symptoms=symptoms,
        triage={"encounter_id": str(eid), "urgency": urgency},
        routing={"encounter_id": str(eid), "pathway": pathway},
        medical_summary={
            "encounter_id": str(eid),
            "suggested_tests": tests or [],
            "case_summary": case_summary,
            "history_notes": "No significant history.",
        },
    )


class TestClinicalCodeGuardrails:
    """Verify that deterministic sanitizers override / supplement LLM codes."""

    # ------------------------------------------------------------------
    # _sanitize_cpt_codes – unit tests
    # ------------------------------------------------------------------

    def test_emergency_always_has_99285(self):
        """Emergency pathway must always include 99285."""
        result = _sanitize_cpt_codes(
            [],
            pathway=CarePathway.EMERGENCY,
            suggested_tests=[],
        )
        assert "99285" in result

    def test_emergency_removes_office_codes(self):
        """99213, 99214, 99441 are incompatible with emergency and must be stripped."""
        result = _sanitize_cpt_codes(
            ["99213", "99214", "99441", "85025"],
            pathway=CarePathway.EMERGENCY,
            suggested_tests=[],
        )
        assert "99285" in result
        assert "99213" not in result
        assert "99214" not in result
        assert "99441" not in result
        # Unrelated test code should be kept
        assert "85025" in result

    def test_non_emergency_office_codes_kept(self):
        """For OPD pathway, 99213 from LLM must be preserved (not stripped)."""
        result = _sanitize_cpt_codes(
            ["99213", "85025"],
            pathway=CarePathway.OPD,
            suggested_tests=[],
        )
        assert "99213" in result

    def test_test_cpt_codes_merged(self):
        """CPT codes for suggested tests are always added."""
        result = _sanitize_cpt_codes(
            [],
            pathway=CarePathway.OPD,
            suggested_tests=["cbc", "ecg"],
        )
        assert "85025" in result  # CBC
        assert "93000" in result  # ECG

    # ------------------------------------------------------------------
    # _sanitize_icd10_codes – unit tests
    # ------------------------------------------------------------------

    def test_rash_maps_to_R21_not_L40_9(self):
        """Rash without psoriasis: R21 must be present, L40.9 must be removed."""
        result = _sanitize_icd10_codes(
            ["L40.9"],
            symptoms="patient has a rash on arms",
            case_summary="",
            history_notes="",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert "R21" in result
        assert "L40.9" not in result

    def test_rash_keeps_L40_9_if_psoriasis_mentioned(self):
        """If psoriasis is explicitly in symptoms, L40.9 must be retained."""
        result = _sanitize_icd10_codes(
            ["L40.9"],
            symptoms="patient has psoriasis with rash",
            case_summary="",
            history_notes="",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert "L40.9" in result

    def test_cardiac_emergency_no_unrelated_respiratory_icd(self):
        """Cardiac emergency without cough/headache symptoms must not carry J06.9 or R51.9."""
        result = _sanitize_icd10_codes(
            ["J06.9", "R51.9", "I21.9"],
            symptoms="chest pain and cardiac emergency",
            case_summary="",
            history_notes="",
            pathway=CarePathway.EMERGENCY,
            urgency=UrgencyLevel.CRITICAL,
        )
        assert "J06.9" not in result
        assert "R51.9" not in result
        # Non-confirmed MI → I21.9 should be removed, R07.9 added
        assert "I21.9" not in result
        assert "R07.9" in result

    def test_chest_pain_non_confirmed_uses_R07_9_not_I21_9(self):
        """Unconfirmed cardiac case prefers R07.9 (chest pain) over I21.9 (MI)."""
        result = _sanitize_icd10_codes(
            ["I21.9"],
            symptoms="patient presenting with chest pain, suspected cardiac event",
            case_summary="",
            history_notes="",
            pathway=CarePathway.EMERGENCY,
            urgency=UrgencyLevel.CRITICAL,
        )
        assert "R07.9" in result
        assert "I21.9" not in result

    def test_confirmed_MI_keeps_I21_9(self):
        """When myocardial infarction is explicitly confirmed, I21.9 must be kept."""
        result = _sanitize_icd10_codes(
            ["I21.9"],
            symptoms="confirmed myocardial infarction, patient in cardiac arrest",
            case_summary="",
            history_notes="",
            pathway=CarePathway.EMERGENCY,
            urgency=UrgencyLevel.CRITICAL,
        )
        assert "I21.9" in result

    def test_llm_hallucinated_codes_overridden_via_agent(self):
        """Full agent run: LLM hallucinating J06.9/R51.9 for cardiac emergency is corrected."""
        from unittest.mock import MagicMock, patch

        agent = BillingInsuranceAgent()

        mock_output = MagicMock()
        mock_output.clinical_indication = "Cardiac emergency."
        mock_output.coverage_notes = "Emergency pathway."
        # LLM hallucinates unrelated respiratory / headache codes
        mock_output.icd10_codes = ["J06.9", "R51.9"]
        mock_output.cpt_codes = ["99213"]  # wrong visit code for emergency

        with patch(
            "hospital_command_center.agents.billing_insurance.invoke_structured",
            return_value=mock_output,
        ):
            result = agent.run(
                **_make_agent_kwargs(
                    symptoms="chest pain and cardiac emergency",
                    urgency="critical",
                    pathway="emergency",
                )
            )

        doc = result["insurance_document"]
        # Hallucinated visit code must be replaced by 99285
        assert "99285" in doc["cpt_codes"]
        assert "99213" not in doc["cpt_codes"]
        # Hallucinated unrelated ICD codes must be removed
        assert "J06.9" not in doc["icd10_codes"]
        assert "R51.9" not in doc["icd10_codes"]
        # Chest pain code should be injected
        assert "R07.9" in doc["icd10_codes"]

    def test_urgency_fallback_when_sanitized_list_empty(self):
        """If no symptom keywords match and LLM returns nothing, urgency fallback applies."""
        result = _sanitize_icd10_codes(
            [],
            symptoms="",
            case_summary="",
            history_notes="",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        # medium → R69
        assert result == ["R69"]


# ---------------------------------------------------------------------------
# ACS presentation guardrails (new tests)
# ---------------------------------------------------------------------------


class TestACSPresentationGuardrails:
    """Verify correct ICD-10 coding for acute coronary syndrome presentations.

    These tests cover the three key improvements from the Ramesh Verma bug report:
      1. I21.9 is KEPT (not stripped) for ACS presentations.
      2. I00.9 (rheumatic fever) is REMOVED when not explicitly documented.
      3. I00.9 is KEPT when rheumatic fever is explicitly in symptoms.
    """

    # ------------------------------------------------------------------
    # 1.  ACS presentation → I21.9 must be preserved / injected
    # ------------------------------------------------------------------

    def test_acs_presentation_keeps_I21_9(self):
        """Classic ACS symptoms (radiating pain + sweating/nausea/SOB) must keep I21.9."""
        result = _sanitize_icd10_codes(
            ["I21.9"],
            symptoms=(
                "Sudden severe chest pain radiating to left arm, sweating, "
                "nausea, shortness of breath"
            ),
            case_summary="",
            history_notes="",
            pathway=CarePathway.EMERGENCY,
            urgency=UrgencyLevel.CRITICAL,
        )
        assert "I21.9" in result, "I21.9 must be preserved for ACS presentations"
        assert "R07.9" not in result, "R07.9 must NOT be injected when I21.9 is kept"

    def test_acs_presentation_injects_I21_9_when_missing(self):
        """If LLM omits I21.9 for an ACS presentation, the guardrail must add it."""
        result = _sanitize_icd10_codes(
            [],
            symptoms=(
                "Sudden severe chest pain radiating to left arm, sweating, "
                "nausea, shortness of breath"
            ),
            case_summary="",
            history_notes="",
            pathway=CarePathway.EMERGENCY,
            urgency=UrgencyLevel.CRITICAL,
        )
        assert "I21.9" in result, "I21.9 must be injected for ACS presentations"

    def test_acs_jaw_radiation_triggers_I21_9(self):
        """Chest pain radiating to jaw + sweating is also an ACS presentation."""
        result = _sanitize_icd10_codes(
            ["I21.9"],
            symptoms="chest pain radiating to jaw, profuse sweating, shortness of breath",
            case_summary="",
            history_notes="",
            pathway=CarePathway.EMERGENCY,
            urgency=UrgencyLevel.CRITICAL,
        )
        assert "I21.9" in result

    def test_acs_shoulder_radiation_triggers_I21_9(self):
        """Chest pain radiating to shoulder + nausea is also an ACS presentation."""
        result = _sanitize_icd10_codes(
            ["I21.9"],
            symptoms="chest pain radiating to shoulder with nausea and shortness of breath",
            case_summary="",
            history_notes="",
            pathway=CarePathway.EMERGENCY,
            urgency=UrgencyLevel.CRITICAL,
        )
        assert "I21.9" in result

    def test_chest_pain_alone_without_acs_features_uses_R07_9(self):
        """Plain chest pain without ACS features: R07.9 is the correct code."""
        result = _sanitize_icd10_codes(
            ["I21.9"],
            symptoms="mild chest pain",
            case_summary="",
            history_notes="",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.LOW,
        )
        assert "R07.9" in result
        assert "I21.9" not in result

    # ------------------------------------------------------------------
    # 2.  I00.9 (rheumatic fever) removal
    # ------------------------------------------------------------------

    def test_rheumatic_fever_code_removed_in_cardiac_emergency(self):
        """I00.9 must be stripped in a cardiac emergency without explicit rheumatic history."""
        result = _sanitize_icd10_codes(
            ["I00.9", "I21.9"],
            symptoms=(
                "Sudden severe chest pain radiating to left arm, sweating, "
                "nausea, shortness of breath"
            ),
            case_summary="",
            history_notes="",
            pathway=CarePathway.EMERGENCY,
            urgency=UrgencyLevel.CRITICAL,
        )
        assert "I00.9" not in result, "I00.9 must be stripped in a cardiac emergency"
        assert "I21.9" in result, "I21.9 must still be present after I00.9 removal"

    def test_I00_9_removed_even_when_llm_insists(self):
        """Full agent run: LLM hallucinating I00.9 for an ACS emergency must be corrected."""
        from unittest.mock import MagicMock, patch

        agent = BillingInsuranceAgent()

        mock_output = MagicMock()
        mock_output.clinical_indication = "Cardiac emergency with ACS."
        mock_output.coverage_notes = "Emergency pathway."
        # LLM incorrectly assigns rheumatic fever code
        mock_output.icd10_codes = ["I00.9", "R07.9"]
        mock_output.cpt_codes = ["99285"]

        with patch(
            "hospital_command_center.agents.billing_insurance.invoke_structured",
            return_value=mock_output,
        ):
            result = agent.run(
                **_make_agent_kwargs(
                    symptoms=(
                        "Sudden severe chest pain radiating to left arm, sweating, "
                        "nausea, shortness of breath"
                    ),
                    urgency="critical",
                    pathway="emergency",
                )
            )

        doc = result["insurance_document"]
        assert "I00.9" not in doc["icd10_codes"], "Rheumatic fever code must be stripped"
        assert "I21.9" in doc["icd10_codes"], "Acute MI code must be injected"

    # ------------------------------------------------------------------
    # 3.  I00.9 kept when rheumatic fever IS explicitly documented
    # ------------------------------------------------------------------

    def test_rheumatic_fever_code_kept_when_documented(self):
        """I00.9 must NOT be stripped if rheumatic fever is explicitly in the symptoms."""
        result = _sanitize_icd10_codes(
            ["I00.9"],
            symptoms=(
                "chest pain radiating to left arm, sweating; known history of rheumatic fever"
            ),
            case_summary="",
            history_notes="",
            pathway=CarePathway.EMERGENCY,
            urgency=UrgencyLevel.CRITICAL,
        )
        assert "I00.9" in result, "I00.9 must be kept when rheumatic fever is documented"

    # ------------------------------------------------------------------
    # 4.  Ramesh Verma exact scenario
    # ------------------------------------------------------------------

    def test_ramesh_verma_scenario_end_to_end(self):
        """Regression test: the exact symptom set from the logged Ramesh Verma case.

        Expected outcome:
        - I21.9 (acute MI) present — NOT stripped.
        - I00.9 (rheumatic fever) absent — hallucinated code removed.
        - R07.9 (chest pain unspecified) absent — too generic for a confirmed ACS.
        - 99285 (emergency visit) present.
        """
        from unittest.mock import MagicMock, patch

        agent = BillingInsuranceAgent()

        mock_output = MagicMock()
        mock_output.clinical_indication = (
            "67-year-old male presenting with sudden severe chest pain radiating "
            "to left arm, sweating, nausea, and shortness of breath."
        )
        mock_output.coverage_notes = "Critical urgency; emergency pathway appropriate."
        # Simulate the previously observed wrong LLM output
        mock_output.icd10_codes = ["R07.9", "I00.9"]
        mock_output.cpt_codes = ["99285", "93000", "85025"]

        with patch(
            "hospital_command_center.agents.billing_insurance.invoke_structured",
            return_value=mock_output,
        ):
            eid = __import__("uuid").uuid4()
            result = agent.run(
                encounter_id=eid,
                symptoms=(
                    "Sudden severe chest pain radiating to left arm, sweating, "
                    "nausea, shortness of breath"
                ),
                triage={"encounter_id": str(eid), "urgency": "critical"},
                routing={"encounter_id": str(eid), "pathway": "emergency"},
                medical_summary={
                    "encounter_id": str(eid),
                    "suggested_tests": ["ecg", "cbc", "chest x-ray"],
                    "case_summary": (
                        "67-year-old male, Ramesh Verma, presenting with acute "
                        "chest pain radiating to left arm."
                    ),
                    "history_notes": "No prior cardiac history documented.",
                },
            )

        doc = result["insurance_document"]
        # Core assertions
        assert "I21.9" in doc["icd10_codes"], "I21.9 must be present for ACS presentation"
        assert "I00.9" not in doc["icd10_codes"], "I00.9 must not appear — not documented"
        assert "R07.9" not in doc["icd10_codes"], "R07.9 is too non-specific for ACS"
        # CPT codes
        assert "99285" in doc["cpt_codes"], "Emergency visit code 99285 must be present"
        assert "93000" in doc["cpt_codes"], "ECG CPT code 93000 must be present"


# ---------------------------------------------------------------------------
# General candidate-list validation (new tests)
# ---------------------------------------------------------------------------


class TestCandidateListValidation:
    """Verify the candidate-list approach to ICD-10 filtering."""

    # ------------------------------------------------------------------
    # _allowed_icd10_candidates unit tests
    # ------------------------------------------------------------------

    def test_abdominal_pain_candidate_present(self):
        """Abdominal pain in symptoms should produce R10.9 as a candidate."""
        candidates = _allowed_icd10_candidates(
            symptoms="abdominal pain",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.LOW,
        )
        assert "R10.9" in candidates

    def test_dizziness_candidate_present(self):
        """Dizziness should produce R42 as a candidate."""
        candidates = _allowed_icd10_candidates(
            symptoms="patient is experiencing dizziness",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.LOW,
        )
        assert "R42" in candidates

    def test_shortness_of_breath_candidate_present(self):
        """Shortness of breath should produce R06.02 as a candidate."""
        candidates = _allowed_icd10_candidates(
            symptoms="shortness of breath",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert "R06.02" in candidates

    def test_no_symptom_match_falls_back_to_urgency_code(self):
        """When no symptom keyword matches, the urgency fallback code should be the candidate."""
        candidates = _allowed_icd10_candidates(
            symptoms="",
            case_summary="",
            history_notes="",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        # medium urgency → R69
        assert "R69" in candidates
        assert len(candidates) == 1

    def test_case_summary_contributes_candidates(self):
        """Abdominal pain mentioned only in case_summary must still produce R10.9."""
        candidates = _allowed_icd10_candidates(
            symptoms="",
            case_summary="Patient presents with abdominal pain.",
            history_notes="",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.LOW,
        )
        assert "R10.9" in candidates

    def test_history_notes_contributes_candidates(self):
        """Diabetes mentioned only in history_notes must still produce E11.9."""
        candidates = _allowed_icd10_candidates(
            symptoms="",
            case_summary="",
            history_notes="Patient has a known history of diabetes.",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.LOW,
        )
        assert "E11.9" in candidates

    def test_acs_candidate_requires_emergency_pathway(self):
        """ACS (I21.9) should NOT be in candidates when pathway is OPD, even with ACS symptoms."""
        candidates = _allowed_icd10_candidates(
            symptoms=(
                "chest pain radiating to left arm, sweating, nausea, shortness of breath"
            ),
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.HIGH,
        )
        assert "I21.9" not in candidates
        assert "R07.9" in candidates  # plain chest pain code is still correct for OPD

    # ------------------------------------------------------------------
    # _sanitize_icd10_codes filtering tests
    # ------------------------------------------------------------------

    def test_unrelated_icd_filtered_out(self):
        """A hallucinated ICD code not in allowed candidates must be removed."""
        result = _sanitize_icd10_codes(
            ["I99.9"],  # not a real useful code; not in any symptom map for headache
            symptoms="headache",
            case_summary="",
            history_notes="",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.LOW,
        )
        assert "I99.9" not in result
        assert "R51.9" in result  # headache candidate must be promoted

    def test_abdominal_pain_keeps_R10_9_rejects_respiratory_headache(self):
        """Abdominal pain: R10.9 kept; J06.9 and R51.9 are not candidates and must be removed."""
        result = _sanitize_icd10_codes(
            ["R10.9", "J06.9", "R51.9"],
            symptoms="abdominal pain",
            case_summary="",
            history_notes="",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.LOW,
        )
        assert "R10.9" in result
        assert "J06.9" not in result
        assert "R51.9" not in result

    def test_dizziness_keeps_R42_rejects_cardiac(self):
        """Dizziness: R42 kept; I21.9 is not a candidate and must be removed."""
        result = _sanitize_icd10_codes(
            ["R42", "I21.9"],
            symptoms="dizziness",
            case_summary="",
            history_notes="",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.LOW,
        )
        assert "R42" in result
        assert "I21.9" not in result

    def test_shortness_of_breath_allows_R06_02(self):
        """Shortness of breath symptoms must allow R06.02 to pass through."""
        result = _sanitize_icd10_codes(
            ["R06.02"],
            symptoms="shortness of breath",
            case_summary="",
            history_notes="",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert "R06.02" in result

    def test_empty_symptoms_falls_back_to_urgency_code(self):
        """Empty symptoms and empty LLM codes should fall back to urgency-based ICD."""
        result = _sanitize_icd10_codes(
            [],
            symptoms="",
            case_summary="",
            history_notes="",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.HIGH,
        )
        # high urgency → R68.89
        assert result == ["R68.89"]

    def test_respiratory_emergency_uses_J06_9_and_99285(self):
        """Respiratory emergency (cough + fever) must keep J06.9 and use CPT 99285."""
        from unittest.mock import MagicMock, patch

        agent = BillingInsuranceAgent()

        mock_output = MagicMock()
        mock_output.clinical_indication = "Respiratory emergency."
        mock_output.coverage_notes = "Emergency pathway."
        mock_output.icd10_codes = ["J06.9", "R50.9"]
        mock_output.cpt_codes = ["99285", "85025"]

        with patch(
            "hospital_command_center.agents.billing_insurance.invoke_structured",
            return_value=mock_output,
        ):
            result = agent.run(
                **_make_agent_kwargs(
                    symptoms="high fever, cough, sore throat",
                    urgency="high",
                    pathway="emergency",
                    tests=["cbc"],
                )
            )

        doc = result["insurance_document"]
        assert "J06.9" in doc["icd10_codes"], "Respiratory code J06.9 must be kept"
        assert "R50.9" in doc["icd10_codes"], "Fever code R50.9 must be kept"
        assert "99285" in doc["cpt_codes"], "Emergency visit code 99285 must be present"
        assert "99213" not in doc["cpt_codes"], "OPD code must not appear in emergency"

    def test_cardiac_keywords_map_to_cardiac_icd_not_respiratory(self):
        """Cardiac emergency keywords should yield cardiac I-range codes, not respiratory J codes."""
        result = _sanitize_icd10_codes(
            ["J06.9", "R51.9"],  # LLM hallucinations
            symptoms="chest pain, cardiac distress",
            case_summary="",
            history_notes="",
            pathway=CarePathway.EMERGENCY,
            urgency=UrgencyLevel.CRITICAL,
        )
        assert "J06.9" not in result, "J06.9 must not appear without respiratory symptoms"
        assert "R51.9" not in result, "R51.9 must not appear without headache"
        assert "R07.9" in result, "Chest pain code R07.9 should be present"


# ---------------------------------------------------------------------------
# Echocardiogram CPT mapping (CPT 93306)
# ---------------------------------------------------------------------------


class TestEchocardiogramCPTMapping:
    """Verify that echocardiogram and its aliases resolve to CPT 93306."""

    # ------------------------------------------------------------------
    # Direct normalization + lookup-table assertions
    # ------------------------------------------------------------------

    def test_echocardiogram_maps_to_93306(self):
        """'Echocardiogram' (exact canonical form) must map to CPT 93306."""
        assert _normalize_test_name("Echocardiogram") == "echocardiogram"
        assert _TEST_CPT_CODES["echocardiogram"] == "93306"

    def test_echo_alias_maps_to_93306(self):
        """'echo' shorthand must normalise to 'echocardiogram' and yield CPT 93306."""
        assert _normalize_test_name("echo") == "echocardiogram"
        assert _TEST_CPT_CODES[_normalize_test_name("echo")] == "93306"

    def test_tte_alias_maps_to_93306(self):
        """'TTE' abbreviation must normalise to 'echocardiogram' and yield CPT 93306."""
        assert _normalize_test_name("TTE") == "echocardiogram"
        assert _TEST_CPT_CODES[_normalize_test_name("TTE")] == "93306"

    # ------------------------------------------------------------------
    # End-to-end: billing output includes 93306 for suggested_tests=["Echocardiogram"]
    # ------------------------------------------------------------------

    @patch(
        "hospital_command_center.agents.billing_insurance.invoke_structured",
        side_effect=Exception("LLM unavailable"),
    )
    def test_billing_output_includes_93306_for_echocardiogram(self, _mock_invoke):
        """Full agent run: suggested_tests=['Echocardiogram'] must surface CPT 93306."""
        agent = BillingInsuranceAgent()
        eid = uuid4()
        result = agent.run(
            encounter_id=eid,
            symptoms="chest pain and shortness of breath",
            triage={"encounter_id": str(eid), "urgency": "critical"},
            routing={"encounter_id": str(eid), "pathway": "emergency"},
            medical_summary={
                "encounter_id": str(eid),
                "suggested_tests": ["Echocardiogram"],
                "case_summary": "Patient presents with chest pain.",
                "history_notes": "No significant history.",
            },
        )
        cpt_codes = result["insurance_document"]["cpt_codes"]
        assert "93306" in cpt_codes, (
            f"CPT 93306 (echocardiogram) must appear in billing output; got {cpt_codes}"
        )


# ---------------------------------------------------------------------------
# Negated-symptom guard tests
# ---------------------------------------------------------------------------


class TestNegatedSymptoms:
    """Verify that negation phrases (no, denies, without, negative for, absent)
    prevent ICD-10 candidate generation for the negated symptom term.
    """

    # ------------------------------------------------------------------
    # Sunita case: "Shortness of breath after climbing stairs, no chest
    # pain, no cough"
    # ------------------------------------------------------------------

    def test_sunita_sob_includes_R06_02(self):
        """Positive SOB must still generate R06.02 despite other negations."""
        candidates = _allowed_icd10_candidates(
            symptoms="Shortness of breath after climbing stairs, no chest pain, no cough",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert "R06.02" in candidates, f"R06.02 expected; got {candidates}"

    def test_sunita_no_chest_pain_excludes_R07_9(self):
        """'no chest pain' must NOT generate R07.9 candidate."""
        candidates = _allowed_icd10_candidates(
            symptoms="Shortness of breath after climbing stairs, no chest pain, no cough",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert "R07.9" not in candidates, f"R07.9 must be absent; got {candidates}"

    def test_sunita_no_cough_excludes_J06_9(self):
        """'no cough' must NOT generate J06.9 candidate."""
        candidates = _allowed_icd10_candidates(
            symptoms="Shortness of breath after climbing stairs, no chest pain, no cough",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert "J06.9" not in candidates, f"J06.9 must be absent; got {candidates}"

    def test_sunita_no_acs_candidate(self):
        """No ACS (I21.9) when 'no chest pain' and not an emergency pathway."""
        candidates = _allowed_icd10_candidates(
            symptoms="Shortness of breath after climbing stairs, no chest pain, no cough",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert "I21.9" not in candidates, f"I21.9 must be absent; got {candidates}"

    # Full sanitize pass for Sunita
    def test_sunita_sanitize_includes_R06_02_excludes_R07_9_J06_9_I21_9(self):
        """_sanitize_icd10_codes must keep R06.02 and strip R07.9, J06.9, I21.9."""
        result = _sanitize_icd10_codes(
            ["R06.02", "R07.9", "J06.9", "I21.9"],  # simulated LLM over-generation
            symptoms="Shortness of breath after climbing stairs, no chest pain, no cough",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert "R06.02" in result, f"R06.02 expected in result; got {result}"
        assert "R07.9" not in result, f"R07.9 must be absent; got {result}"
        assert "J06.9" not in result, f"J06.9 must be absent; got {result}"
        assert "I21.9" not in result, f"I21.9 must be absent; got {result}"

    # ------------------------------------------------------------------
    # Various negation phrases
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "symptoms",
        [
            "no chest pain",
            "denies chest pain",
            "without chest pain",
            "negative for chest pain",
            "absent chest pain",
        ],
    )
    def test_negation_phrases_exclude_R07_9(self, symptoms: str):
        """All standard negation phrases before 'chest pain' must suppress R07.9."""
        candidates = _allowed_icd10_candidates(
            symptoms=symptoms,
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.LOW,
        )
        assert "R07.9" not in candidates, (
            f"R07.9 must be absent for '{symptoms}'; got {candidates}"
        )

    def test_no_headache_excludes_R51_9(self):
        """'no headache' must NOT generate R51.9."""
        candidates = _allowed_icd10_candidates(
            symptoms="no headache",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.LOW,
        )
        assert "R51.9" not in candidates, f"R51.9 must be absent; got {candidates}"

    def test_no_fever_excludes_R50_9(self):
        """'no fever' must NOT generate R50.9."""
        candidates = _allowed_icd10_candidates(
            symptoms="no fever",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.LOW,
        )
        assert "R50.9" not in candidates, f"R50.9 must be absent; got {candidates}"

    # ------------------------------------------------------------------
    # "denies chest pain, has dizziness" → R42 included, R07.9 excluded
    # ------------------------------------------------------------------

    def test_denies_chest_pain_has_dizziness_includes_R42(self):
        """Positive dizziness must generate R42."""
        candidates = _allowed_icd10_candidates(
            symptoms="denies chest pain, has dizziness",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.LOW,
        )
        assert "R42" in candidates, f"R42 expected; got {candidates}"

    def test_denies_chest_pain_has_dizziness_excludes_R07_9(self):
        """'denies chest pain' must NOT generate R07.9."""
        candidates = _allowed_icd10_candidates(
            symptoms="denies chest pain, has dizziness",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.LOW,
        )
        assert "R07.9" not in candidates, f"R07.9 must be absent; got {candidates}"

    # Sanitize pass
    def test_denies_chest_pain_dizziness_sanitize(self):
        """_sanitize_icd10_codes must keep R42 and strip R07.9."""
        result = _sanitize_icd10_codes(
            ["R42", "R07.9"],
            symptoms="denies chest pain, has dizziness",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.LOW,
        )
        assert "R42" in result, f"R42 expected in result; got {result}"
        assert "R07.9" not in result, f"R07.9 must be absent; got {result}"

    # ------------------------------------------------------------------
    # "fever and cough, no headache" → R50.9 & J06.9 included, R51.9 excluded
    # ------------------------------------------------------------------

    def test_fever_cough_no_headache_includes_R50_9(self):
        """Positive 'fever' must still generate R50.9."""
        candidates = _allowed_icd10_candidates(
            symptoms="fever and cough, no headache",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert "R50.9" in candidates, f"R50.9 expected; got {candidates}"

    def test_fever_cough_no_headache_includes_J06_9(self):
        """Positive 'cough' must still generate J06.9."""
        candidates = _allowed_icd10_candidates(
            symptoms="fever and cough, no headache",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert "J06.9" in candidates, f"J06.9 expected; got {candidates}"

    def test_fever_cough_no_headache_excludes_R51_9(self):
        """'no headache' must NOT generate R51.9."""
        candidates = _allowed_icd10_candidates(
            symptoms="fever and cough, no headache",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert "R51.9" not in candidates, f"R51.9 must be absent; got {candidates}"

    # Sanitize pass
    def test_fever_cough_no_headache_sanitize(self):
        """_sanitize_icd10_codes must keep R50.9 + J06.9 and strip R51.9."""
        result = _sanitize_icd10_codes(
            ["R50.9", "J06.9", "R51.9"],
            symptoms="fever and cough, no headache",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert "R50.9" in result, f"R50.9 expected; got {result}"
        assert "J06.9" in result, f"J06.9 expected; got {result}"
        assert "R51.9" not in result, f"R51.9 must be absent; got {result}"


# ---------------------------------------------------------------------------
# Generic cardiac words in case_summary must NOT create R07.9
# ---------------------------------------------------------------------------


class TestGenericCardiacWordsNotChestPain:
    """Generic clinical labels like 'cardiac', 'heart attack', 'myocardial'
    appearing in case_summary / history_notes must NOT generate R07.9 when
    the patient's symptoms lack explicit chest pain.
    """

    # ------------------------------------------------------------------
    # Sunita with case_summary that mentions "cardiac"
    # ------------------------------------------------------------------

    def test_sunita_with_cardiac_case_summary_excludes_R07_9_candidates(self):
        """'possible cardiac or respiratory issue' in case_summary must NOT add R07.9."""
        candidates = _allowed_icd10_candidates(
            symptoms="Shortness of breath after climbing stairs, no chest pain, no cough",
            case_summary="possible cardiac or respiratory issue requiring further evaluation",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert "R07.9" not in candidates, f"R07.9 must be absent; got {candidates}"

    def test_sunita_with_cardiac_case_summary_includes_R06_02(self):
        """Positive SOB must still produce R06.02 even with a cardiac case_summary."""
        candidates = _allowed_icd10_candidates(
            symptoms="Shortness of breath after climbing stairs, no chest pain, no cough",
            case_summary="possible cardiac or respiratory issue requiring further evaluation",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert "R06.02" in candidates, f"R06.02 expected; got {candidates}"

    def test_sunita_full_sanitize_with_cardiac_case_summary(self):
        """_sanitize_icd10_codes must keep R06.02 and strip R07.9, J06.9, I21.9
        even when case_summary contains 'cardiac'."""
        result = _sanitize_icd10_codes(
            ["R06.02", "R07.9", "J06.9", "I21.9"],
            symptoms="Shortness of breath after climbing stairs, no chest pain, no cough",
            case_summary="possible cardiac or respiratory issue requiring further evaluation",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert "R06.02" in result, f"R06.02 expected; got {result}"
        assert "R07.9" not in result, f"R07.9 must be absent; got {result}"
        assert "J06.9" not in result, f"J06.9 must be absent; got {result}"
        assert "I21.9" not in result, f"I21.9 must be absent; got {result}"

    # ------------------------------------------------------------------
    # Standalone generic cardiac phrases must NOT generate R07.9
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "phrase",
        [
            "cardiac evaluation required",
            "possible cardiac issue",
            "cardiac or respiratory issue",
            "heart disease evaluation",
            "myocardial perfusion study",
        ],
    )
    def test_generic_cardiac_phrase_no_R07_9(self, phrase: str):
        """Generic cardiac/heart/myocardial labels in case_summary alone
        must not produce R07.9 when symptoms do not mention chest pain."""
        candidates = _allowed_icd10_candidates(
            symptoms="shortness of breath",
            case_summary=phrase,
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert "R07.9" not in candidates, (
            f"R07.9 must be absent for case_summary='{phrase}'; got {candidates}"
        )

    # ------------------------------------------------------------------
    # Positive chest pain still generates R07.9
    # ------------------------------------------------------------------

    def test_explicit_chest_pain_symptom_generates_R07_9(self):
        """Explicit 'chest pain after exertion' in symptoms must produce R07.9."""
        candidates = _allowed_icd10_candidates(
            symptoms="chest pain after exertion",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert "R07.9" in candidates, f"R07.9 expected; got {candidates}"

    def test_chest_pain_after_exertion_sanitize_keeps_R07_9(self):
        """_sanitize_icd10_codes must keep R07.9 for explicit chest pain."""
        result = _sanitize_icd10_codes(
            ["R07.9"],
            symptoms="chest pain after exertion",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert "R07.9" in result, f"R07.9 expected; got {result}"

    # ------------------------------------------------------------------
    # ACS / MI presentation still produces I21.9 and excludes R07.9
    # ------------------------------------------------------------------

    def test_acs_sob_radiation_includes_I21_9(self):
        """Sudden severe chest pain + radiation + sweating/nausea/SOB (emergency)
        must produce I21.9."""
        candidates = _allowed_icd10_candidates(
            symptoms=(
                "Sudden severe chest pain radiating to left arm, sweating, "
                "nausea, shortness of breath"
            ),
            pathway=CarePathway.EMERGENCY,
            urgency=UrgencyLevel.CRITICAL,
        )
        assert "I21.9" in candidates, f"I21.9 expected; got {candidates}"

    def test_acs_sob_radiation_sanitize_excludes_R07_9(self):
        """_sanitize_icd10_codes must inject I21.9 and strip R07.9 for ACS."""
        result = _sanitize_icd10_codes(
            ["R07.9", "I21.9"],
            symptoms=(
                "Sudden severe chest pain radiating to left arm, sweating, "
                "nausea, shortness of breath"
            ),
            pathway=CarePathway.EMERGENCY,
            urgency=UrgencyLevel.CRITICAL,
        )
        assert "I21.9" in result, f"I21.9 expected; got {result}"
        assert "R07.9" not in result, f"R07.9 must be absent for ACS; got {result}"


# ---------------------------------------------------------------------------
# Expanded symptom-map coverage (multi-code, non-collapsing) — new tests
# ---------------------------------------------------------------------------


class TestExpandedSymptomMapCoverage:
    """The candidate table must cover a broad range of common presentations
    so that legitimate, distinct diagnoses are not collapsed into a single
    generic urgency-based fallback code.
    """

    def test_multi_symptom_case_yields_multiple_distinct_codes(self):
        """Back pain, fatigue, dizziness, insomnia, and two documented
        comorbidities should all surface as separate candidates rather than
        collapsing to one fallback code.
        """
        candidates = _allowed_icd10_candidates(
            symptoms="patient reports back pain, fatigue, and occasional dizziness",
            case_summary="Patient also notes trouble sleeping recently.",
            history_notes="Known history of hypertension and type 2 diabetes.",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.LOW,
        )
        for expected in ("R42", "R53.83", "M54.9", "G47.00", "E11.9", "I10"):
            assert expected in candidates, f"{expected} expected; got {candidates}"
        assert len(candidates) >= 6

    @pytest.mark.parametrize(
        "symptom,expected_code",
        [
            ("asthma", "J45.909"),
            ("urinary tract infection", "N39.0"),
            ("anxiety", "F41.9"),
            ("depression", "F32.9"),
            ("anemia", "D64.9"),
            ("seizure", "R56.9"),
            ("syncope", "R55"),
            ("obesity", "E66.9"),
        ],
    )
    def test_new_symptom_categories_present(self, symptom, expected_code):
        candidates = _allowed_icd10_candidates(
            symptoms=f"patient presents with {symptom}",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.LOW,
        )
        assert expected_code in candidates, f"{expected_code} expected; got {candidates}"

    def test_negation_still_works_for_new_categories(self):
        """Negation handling must still suppress newly-added categories."""
        candidates = _allowed_icd10_candidates(
            symptoms="denies anxiety, has fatigue",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.LOW,
        )
        assert "F41.9" not in candidates
        assert "R53.83" in candidates

    def test_migraine_promotes_over_generic_headache(self):
        """Migraine (specific) should be kept; generic headache code stripped."""
        result = _sanitize_icd10_codes(
            ["R51.9"],
            symptoms="patient reports a migraine with light sensitivity",
            case_summary="",
            history_notes="",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.LOW,
        )
        assert "G43.909" in result
        assert "R51.9" not in result

    def test_neutral_malaise_symptom_still_falls_back(self):
        """Regression guard: 'general malaise' must remain a neutral phrase
        that does not match any category, preserving the urgency fallback
        behavior other tests rely on."""
        candidates = _allowed_icd10_candidates(
            symptoms="general malaise",
            case_summary="Patient presents with general malaise.",
            history_notes="No significant history.",
            pathway=CarePathway.OPD,
            urgency=UrgencyLevel.MEDIUM,
        )
        assert candidates == ["R69"]


# ---------------------------------------------------------------------------
# Duplicate-test billing guard — new tests
# ---------------------------------------------------------------------------


class TestDuplicateTestBillingGuard:
    """Verify the same diagnostic test is never billed or coded twice when
    it appears under two different aliases in suggested_tests.
    """

    def test_dedupe_tests_collapses_aliases(self):
        result = _dedupe_tests(["CBC", "Complete Blood Count", "ECG"])
        assert result == ["CBC", "ECG"]

    def test_dedupe_tests_preserves_unique_order(self):
        result = _dedupe_tests(["ecg", "cbc", "ECG"])
        assert result == ["ecg", "cbc"]

    @patch(
        "hospital_command_center.agents.billing_insurance.invoke_structured",
        side_effect=Exception("LLM unavailable"),
    )
    def test_duplicate_test_aliases_billed_once(self, _mock_invoke):
        """'CBC' and 'Complete Blood Count' are the same test and must only
        contribute one test_cost line item, not two."""
        agent = BillingInsuranceAgent()
        eid = uuid4()
        result = agent.run(
            encounter_id=eid,
            symptoms="fatigue",
            triage={"encounter_id": str(eid), "urgency": "low"},
            routing={"encounter_id": str(eid), "pathway": "opd"},
            medical_summary={
                "encounter_id": str(eid),
                "suggested_tests": ["CBC", "Complete Blood Count"],
                "case_summary": "Patient presents with fatigue.",
                "history_notes": "No significant history.",
            },
        )
        cost_breakdown = result["cost_breakdown"]
        # Single CBC unit cost (450.00), not double (900.00).
        assert Decimal(cost_breakdown["test_cost"]) == Decimal("450.00")
        # CPT code for CBC must appear exactly once.
        assert result["insurance_document"]["cpt_codes"].count("85025") == 1
        # proposed_services must list the diagnostic once, not twice.
        diagnostic_lines = [
            s for s in result["insurance_document"]["proposed_services"]
            if "Diagnostic" in s
        ]
        assert len(diagnostic_lines) == 1
