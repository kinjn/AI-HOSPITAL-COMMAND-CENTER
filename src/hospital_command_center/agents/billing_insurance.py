"""Billing/insurance agent: rule-based cost estimates and LLM insurance documentation."""

import logging
import re
from decimal import Decimal
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from hospital_command_center.agents.base import BaseAgent
from hospital_command_center.agents.llm import get_chat_model
from hospital_command_center.agents.structured_output import invoke_structured
from hospital_command_center.core.exceptions import NotConfiguredError
from hospital_command_center.domain.billing import (
    BillingEstimate,
    BillingStatus,
    CostBreakdown,
    InsuranceDocument,
)
from hospital_command_center.domain.medical import MedicalSummary
from hospital_command_center.domain.triage import TriageResult, UrgencyLevel
from hospital_command_center.domain.workflow import CarePathway, RoutingDecision
from hospital_command_center.prompts import load_prompt

logger = logging.getLogger(__name__)


class _BillingLLMOutput(BaseModel):
    clinical_indication: str = Field(
        ...,
        description="Summarize the patient symptoms and diagnostic findings indicating the medical necessity for treatment.",
        min_length=10,
        max_length=2000,
    )
    coverage_notes: str = Field(
        ...,
        description="Detailed justification notes explaining why the treatment and tests are covered based on urgency and symptoms.",
        min_length=10,
        max_length=2000,
    )
    icd10_codes: list[str] = Field(
        default_factory=list,
        description="ICD-10 diagnosis codes only, no descriptions.",
    )
    cpt_codes: list[str] = Field(
        default_factory=list,
        description="CPT procedure/service codes only, no descriptions.",
    )



# Consultation/visit fees reflect typical Indian private-hospital rates
# (physician fee + basic facility component). Emergency includes the ED
# facility charge on top of the physician evaluation; teleconsultation is
# priced lower given the absence of a physical facility overhead.
_CONSULTATION_FEE_INR: dict[CarePathway, Decimal] = {
    CarePathway.OPD: Decimal("700.00"),
    CarePathway.TELECONSULTATION: Decimal("400.00"),
    CarePathway.EMERGENCY: Decimal("3000.00"),
    CarePathway.SPECIALIST_REFERRAL: Decimal("1800.00"),
}

# Diagnostic test unit costs, benchmarked against typical Indian private-
# hospital / diagnostic-lab price lists. Keys are canonical test names
# produced by ``_normalize_test_name`` — see ``_TEST_NAME_ALIASES`` below for
# the fuzzy-matching patterns that map free-text test names onto these keys.
_TEST_COST_INR: dict[str, Decimal] = {
    "cbc": Decimal("400.00"),
    "basic metabolic panel": Decimal("950.00"),
    "liver function test": Decimal("900.00"),
    "lipid profile": Decimal("700.00"),
    "thyroid function test": Decimal("900.00"),
    "hba1c": Decimal("650.00"),
    "blood glucose": Decimal("150.00"),
    "chest x-ray": Decimal("600.00"),
    "ecg": Decimal("400.00"),
    "echocardiogram": Decimal("2800.00"),
    "urinalysis": Decimal("250.00"),
    "stool routine": Decimal("300.00"),
    "blood culture": Decimal("1200.00"),
    "urine culture": Decimal("900.00"),
    "troponin": Decimal("1300.00"),
    "d-dimer": Decimal("1800.00"),
    "coagulation profile": Decimal("700.00"),
    "ct scan": Decimal("5500.00"),
    "mri": Decimal("8500.00"),
    "ultrasound abdomen": Decimal("1500.00"),
    "sputum test": Decimal("350.00"),
    "blood typing": Decimal("200.00"),
    "malaria test": Decimal("300.00"),
    "dengue test": Decimal("900.00"),
    "hiv test": Decimal("500.00"),
    "covid rt-pcr": Decimal("700.00"),
    "pregnancy test": Decimal("150.00"),
    "vitamin d": Decimal("1200.00"),
    "vitamin b12": Decimal("900.00"),
}

# Applied to any suggested test that doesn't match a known alias — set close
# to the median of the priced table above rather than an arbitrary low
# figure, so unmapped/novel tests don't understate the estimate.
_DEFAULT_TEST_COST_INR = Decimal("900.00")

# Medication estimate scales with acuity: critical patients typically require
# IV fluids/emergency drugs, high-urgency patients need broader empirical
# coverage, while low-urgency OPD visits are usually a short oral course.
_MEDICATION_COST_INR: dict[UrgencyLevel, Decimal] = {
    UrgencyLevel.LOW: Decimal("200.00"),
    UrgencyLevel.MEDIUM: Decimal("450.00"),
    UrgencyLevel.HIGH: Decimal("900.00"),
    UrgencyLevel.CRITICAL: Decimal("2200.00"),
}

# Miscellaneous/facility charges: registration, nursing, consumables.
# Emergency carries the largest component (triage nursing, monitoring,
# consumables, observation bay time) versus a light OPD registration fee.
_MISC_COST_INR: dict[CarePathway, Decimal] = {
    CarePathway.OPD: Decimal("150.00"),
    CarePathway.TELECONSULTATION: Decimal("75.00"),
    CarePathway.EMERGENCY: Decimal("1800.00"),
    CarePathway.SPECIALIST_REFERRAL: Decimal("400.00"),
}

# ---------------------------------------------------------------------------
# Deterministic fallback code lookup tables
# ---------------------------------------------------------------------------

_TEST_CPT_CODES: dict[str, str] = {
    "cbc": "85025",
    "basic metabolic panel": "80048",
    "liver function test": "80076",
    "lipid profile": "80061",
    "thyroid function test": "84443",
    "hba1c": "83036",
    "blood glucose": "82947",
    "chest x-ray": "71046",
    "ecg": "93000",
    "echocardiogram": "93306",
    "urinalysis": "81003",
    "stool routine": "82272",
    "blood culture": "87040",
    "urine culture": "87086",
    "troponin": "84484",
    "d-dimer": "85379",
    "coagulation profile": "85610",
    "ct scan": "70450",
    "mri": "70551",
    "ultrasound abdomen": "76700",
    "sputum test": "87116",
    "blood typing": "86900",
    "malaria test": "87207",
    "dengue test": "86790",
    "hiv test": "86703",
    "covid rt-pcr": "87635",
    "pregnancy test": "81025",
    "vitamin d": "82306",
    "vitamin b12": "82607",
}

_PATHWAY_CPT_CODES: dict[CarePathway, str] = {
    CarePathway.OPD: "99213",
    CarePathway.TELECONSULTATION: "99441",
    CarePathway.EMERGENCY: "99285",
    CarePathway.SPECIALIST_REFERRAL: "99214",
}

_URGENCY_ICD10_CODES: dict[UrgencyLevel, str] = {
    UrgencyLevel.LOW: "R69",
    UrgencyLevel.MEDIUM: "R69",
    UrgencyLevel.HIGH: "R68.89",
    UrgencyLevel.CRITICAL: "R68.89",
}

# CPT visit codes that are incompatible with an emergency encounter
_NON_EMERGENCY_VISIT_CPTS: frozenset[str] = frozenset({"99213", "99214", "99441"})

# ---------------------------------------------------------------------------
# Human-readable code descriptions — display-only.
#
# The structured `icd10_codes` / `cpt_codes` arrays returned to callers stay
# code-only (this matches how payers/TPAs actually expect a claims payload
# to look). These lookups are used *only* when rendering the printed
# pre-authorization letter in `_format_insurance_documentation`, so a human
# reviewer isn't left staring at a bare code with no clinical context. Codes
# not present here still render fine — the formatter falls back to the code
# alone.
# ---------------------------------------------------------------------------

_ICD10_DESCRIPTIONS: dict[str, str] = {
    "I21.9": "Acute myocardial infarction, unspecified",
    "R07.9": "Chest pain, unspecified",
    "R21": "Rash and other nonspecific skin eruption",
    "L40.9": "Psoriasis, unspecified",
    "T78.40XA": "Allergic reaction, unspecified, initial encounter",
    "G43.909": "Migraine, unspecified, not intractable",
    "R51.9": "Headache, unspecified",
    "R42": "Dizziness and giddiness",
    "R56.9": "Unspecified convulsions",
    "R55": "Syncope and collapse",
    "R20.2": "Paresthesia of skin",
    "R50.9": "Fever, unspecified",
    "R53.83": "Other fatigue",
    "R63.4": "Abnormal weight loss",
    "R68.83": "Chills (without fever)",
    "J06.9": "Acute upper respiratory infection, unspecified",
    "R06.02": "Shortness of breath",
    "R06.2": "Wheezing",
    "J45.909": "Unspecified asthma, uncomplicated",
    "J18.9": "Pneumonia, unspecified organism",
    "J01.90": "Acute sinusitis, unspecified",
    "H66.90": "Otitis media, unspecified, unspecified ear",
    "H10.9": "Unspecified conjunctivitis",
    "R10.9": "Unspecified abdominal pain",
    "R11.2": "Nausea with vomiting, unspecified",
    "R19.7": "Diarrhea, unspecified",
    "K59.00": "Constipation, unspecified",
    "K21.9": "Gastro-esophageal reflux disease without esophagitis",
    "N39.0": "Urinary tract infection, site not specified",
    "R35.0": "Frequency of micturition",
    "R31.9": "Hematuria, unspecified",
    "M54.9": "Dorsalgia, unspecified",
    "M54.2": "Cervicalgia",
    "M25.50": "Pain in joint, unspecified",
    "T14.8": "Other injury of unspecified body region",
    "R00.2": "Palpitations",
    "R60.9": "Edema, unspecified",
    "F41.9": "Anxiety disorder, unspecified",
    "F32.9": "Major depressive disorder, single episode, unspecified",
    "G47.00": "Insomnia, unspecified",
    "E66.9": "Obesity, unspecified",
    "E03.9": "Hypothyroidism, unspecified",
    "E05.90": "Thyrotoxicosis, unspecified without thyrotoxic crisis",
    "D64.9": "Anemia, unspecified",
    "N17.9": "Acute kidney failure, unspecified",
    "N18.9": "Chronic kidney disease, unspecified",
    "E11.9": "Type 2 diabetes mellitus without complications",
    "I10": "Essential (primary) hypertension",
    "I00.9": "Rheumatic fever without heart involvement",
    "R69": "Illness, unspecified",
    "R68.89": "Other general symptoms and signs",
}

_CPT_DESCRIPTIONS: dict[str, str] = {
    "99285": "ED visit, high severity",
    "99213": "Office/outpatient visit, established patient",
    "99441": "Telephone E/M service, 5-10 minutes",
    "99214": "Office/outpatient visit, established patient, moderate complexity",
    "85025": "Complete blood count (CBC), automated with differential",
    "80048": "Basic metabolic panel",
    "80076": "Hepatic function panel",
    "80061": "Lipid panel",
    "84443": "Thyroid stimulating hormone (TSH)",
    "83036": "Hemoglobin A1c",
    "82947": "Glucose, quantitative, blood",
    "71046": "Radiologic exam, chest, 2 views",
    "93000": "Electrocardiogram, routine ECG with interpretation",
    "93306": "Echocardiography, transthoracic, complete",
    "81003": "Urinalysis, automated, without microscopy",
    "82272": "Fecal occult blood test",
    "87040": "Blood culture, bacterial",
    "87086": "Urine culture, bacterial, quantitative",
    "84484": "Troponin, quantitative",
    "85379": "D-dimer, quantitative",
    "85610": "Prothrombin time (PT)",
    "70450": "CT scan, head/brain, without contrast",
    "70551": "MRI, brain, without contrast",
    "76700": "Ultrasound, abdomen, complete",
    "87116": "Culture, mycobacterial (AFB)",
    "86900": "Blood typing, ABO",
    "87207": "Blood smear, special stain (e.g. malaria)",
    "86790": "Dengue virus antibody",
    "86703": "HIV-1/HIV-2 antibody, single assay",
    "87635": "SARS-CoV-2, RT-PCR",
    "81025": "Urine pregnancy test, visual color comparison",
    "82306": "Vitamin D, 25-hydroxy",
    "82607": "Vitamin B-12 (cyanocobalamin)",
}

# Ordered list of (compiled_regex, icd10_code) pairs for broad, reusable symptom
# categories. Order matters: more-specific patterns (e.g. ACS composite, or a
# specific diagnosis like migraine) should appear *before* their constituent /
# generic patterns (e.g. plain chest pain, plain headache) so that the
# candidate list is populated correctly before promotion rules run.
#
# NOTE on coverage: this table intentionally covers a *broad* range of common
# outpatient/ED presentations (not just the handful of scenarios exercised by
# unit tests). A narrow table silently discards clinically valid, LLM-supplied
# codes whenever the presenting context doesn't happen to match one of a small
# number of hard-coded categories — this previously caused the agent to
# collapse to a single generic urgency-based fallback code (R69 / R68.89) for
# almost every real-world encounter, even when several distinct, well-
# supported diagnoses were documented. Adding more categories here directly
# reduces both false negatives (legitimate codes stripped for lack of a
# matching pattern) and reliance on the single-code fallback, without loosening
# the negation / hallucination checks that gate each match.
#
# Each tuple: (pattern_string, icd10_code)
_SYMPTOM_ICD10_MAP: list[tuple[str, str]] = [
    # Skin
    (r"\brash\b|\bskin\s+eruption\b", "R21"),
    (r"\bpsoriasis\b", "L40.9"),
    (r"\ballergic\s+reaction\b|\bhives\b|\burticaria\b", "T78.40XA"),
    # Neurological — migraine (specific) is checked before plain headache
    # (generic) so the promotion rule below can prefer the specific code.
    (r"\bmigraine\b", "G43.909"),
    (r"\bheadache\b", "R51.9"),
    (r"\bdizziness\b", "R42"),
    (r"\bseizure\b|\bconvulsion\b", "R56.9"),
    (r"\bsyncope\b|\bfainting\b|\bfainted\b|\bpassed\s+out\b", "R55"),
    (r"\bnumbness\b|\btingling\b|\bparesthesia\b", "R20.2"),
    # Constitutional
    (r"\bfever\b", "R50.9"),
    (r"\bfatigue\b|\btiredness\b", "R53.83"),
    (r"\bweight\s+loss\b", "R63.4"),
    (r"\bchills\b", "R68.83"),
    # Respiratory
    (r"\bcough\b|\buri\b|\bupper\s+respiratory\b|\bcold\b|\bsore\s+throat\b", "J06.9"),
    (r"\bshortness\s+of\s+breath\b|\bdyspnea\b", "R06.02"),
    (r"\bwheez(?:e|ing)\b", "R06.2"),
    (r"\basthma\b", "J45.909"),
    (r"\bpneumonia\b", "J18.9"),
    # ENT
    (r"\bsinusitis\b|\bsinus\s+infection\b", "J01.90"),
    (r"\bear\s+pain\b|\botitis\s+media\b|\bearache\b", "H66.90"),
    (r"\bconjunctivitis\b|\bpink\s+eye\b", "H10.9"),
    # Gastrointestinal
    (r"\babdominal\s+pain\b", "R10.9"),
    (r"\bvomiting\b|\bnausea\b", "R11.2"),
    (r"\bdiarrhea\b", "R19.7"),
    (r"\bconstipation\b", "K59.00"),
    (r"\bheartburn\b|\bacid\s+reflux\b|\bgerd\b", "K21.9"),
    # Genitourinary
    (r"\bdysuria\b|\bpainful\s+urination\b|\burinary\s+tract\s+infection\b|\bburning\s+urination\b", "N39.0"),
    (r"\burinary\s+frequency\b|\bfrequent\s+urination\b", "R35.0"),
    (r"\bhematuria\b|\bblood\s+in\s+(?:the\s+)?urine\b", "R31.9"),
    # Musculoskeletal
    (r"\bback\s+pain\b", "M54.9"),
    (r"\bneck\s+pain\b", "M54.2"),
    (r"\bjoint\s+pain\b|\barthralgia\b", "M25.50"),
    (r"\bfracture\b", "T14.8"),
    # Cardiac — only explicit chest pain complaint maps to R07.9.
    # Generic clinical labels like "cardiac", "heart attack", or "myocardial"
    # appear routinely in case summaries / history and must NOT by themselves
    # produce a chest-pain symptom code.  ACS / MI detection is handled
    # separately via the composite check in _allowed_icd10_candidates.
    (r"\bchest\s+pain\b", "R07.9"),
    (r"\bpalpitations\b", "R00.2"),
    (r"\bedema\b|\bswelling\s+in\s+(?:the\s+)?legs\b|\bswollen\s+ankles\b", "R60.9"),
    # Psychiatric
    (r"\banxiety\b|\banxious\b", "F41.9"),
    (r"\bdepression\b|\bdepressed\s+mood\b", "F32.9"),
    (r"\binsomnia\b|\btrouble\s+sleeping\b", "G47.00"),
    # Endocrine / metabolic
    (r"\bobesity\b", "E66.9"),
    (r"\bhypothyroidism\b", "E03.9"),
    (r"\bhyperthyroidism\b", "E05.90"),
    # Hematology / renal
    (r"\banemia\b", "D64.9"),
    (r"\bkidney\s+injury\b|\bacute\s+kidney\b", "N17.9"),
    (r"\bchronic\s+kidney\s+disease\b|\bckd\b", "N18.9"),
    # Chronic conditions
    (r"\bdiabetes\b", "E11.9"),
    (r"\bhypertension\b", "I10"),
    # Rheumatic fever — only present when explicitly documented
    (r"\brheumatic\s+fever\b|\brheumatic\b", "I00.9"),
]

# Pre-compile _SYMPTOM_ICD10_MAP patterns for performance
_COMPILED_SYMPTOM_MAP: list[tuple[re.Pattern, str]] = [
    (re.compile(pattern, re.IGNORECASE), code)
    for pattern, code in _SYMPTOM_ICD10_MAP
]

# ---------------------------------------------------------------------------
# Negation detection
# ---------------------------------------------------------------------------

# Phrase that, when appearing immediately before a clinical term, negate it.
# The regex matches the negation word/phrase followed by optional punctuation
# and whitespace up to (but not including) the clinical term.
_NEGATION_RE: re.Pattern = re.compile(
    r"\b(?:no|denies|without|negative\s+for|absent)\b"
    r"[^a-z]{0,30}",  # allow short gap of non-alpha chars (commas, spaces, …)
    re.IGNORECASE,
)


def _is_negated(ctx: str, match: re.Match) -> bool:
    """Return True when the regex *match* inside *ctx* is preceded by a
    negation phrase (no, denies, without, negative for, absent).

    Strategy: look at the 50 characters immediately before the match start;
    if a negation phrase ends at (or very near) that boundary, the symptom
    is considered negated.
    """
    window_start = max(0, match.start() - 50)
    prefix = ctx[window_start : match.start()]
    # A negation phrase must *end* at the boundary of the clinical term.
    # We anchor the search to the tail of the prefix string.
    return bool(re.search(
        r"\b(?:no|denies|without|negative\s+for|absent)\b[^a-z]*$",
        prefix,
        re.IGNORECASE,
    ))


# ---------------------------------------------------------------------------
# Deterministic code sanitizers
# ---------------------------------------------------------------------------


def _sanitize_cpt_codes(
    llm_codes: list[str],
    *,
    pathway: "CarePathway",
    suggested_tests: list[str],
) -> list[str]:
    """Enforce pathway-correct CPT codes and merge test CPT codes.

    Rules applied in order:
    1. If pathway is EMERGENCY, strip office/teleconsult visit codes
       (99213, 99214, 99441) from the LLM list — they are incompatible.
    2. Always ensure the pathway's canonical visit code is present.
    3. Add CPT codes for every mapped suggested test that is not already
       present in the list.
    4. Deduplicate while preserving insertion order.
    """
    seen: set[str] = set()
    result: list[str] = []

    # Step 1 – filter incompatible visit codes for emergency encounters
    filtered = (
        [c for c in llm_codes if c not in _NON_EMERGENCY_VISIT_CPTS]
        if pathway == CarePathway.EMERGENCY
        else list(llm_codes)
    )

    # Step 2 – ensure pathway visit code is present (prepend if missing)
    pathway_code = _PATHWAY_CPT_CODES[pathway]
    if pathway_code not in filtered:
        filtered.insert(0, pathway_code)

    # Collect deduplicated result so far
    for code in filtered:
        if code not in seen:
            seen.add(code)
            result.append(code)

    # Step 3 – merge test CPT codes
    for test in suggested_tests:
        normalized = _normalize_test_name(test)
        test_cpt = _TEST_CPT_CODES.get(normalized)
        if test_cpt and test_cpt not in seen:
            seen.add(test_cpt)
            result.append(test_cpt)

    return result


def _allowed_icd10_candidates(
    *,
    symptoms: str,
    case_summary: str = "",
    history_notes: str = "",
    pathway: "CarePathway",
    urgency: "UrgencyLevel",
) -> list[str]:
    """Generate the list of ICD-10 codes that are clinically plausible for this
    encounter based on a combined context string (symptoms + case summary +
    history notes).

    Algorithm
    ---------
    1. Combine symptoms, case_summary, and history_notes into one lowercased
       context string.
    2. Iterate ``_COMPILED_SYMPTOM_MAP`` and add matching codes.
    3. ACS composite check: pathway is EMERGENCY and context contains
       explicit (non-negated) chest pain *and* radiating pain (arm/jaw/shoulder)
       *and* at least one ACS-associated symptom (sweating/diaphoresis/
       nausea/shortness of breath) → add ``I21.9``.
       Alternatively, explicit documented MI confirmation (e.g. "confirmed
       myocardial infarction") alone is sufficient without chest pain text.
    4. Deduplicate while preserving insertion order.
    5. If no candidates found → add ``_URGENCY_ICD10_CODES[urgency]``.
    """
    ctx = " ".join([symptoms, case_summary, history_notes]).lower()

    # Check ACS composite pattern first so I21.9 can be added alongside R07.9;
    # promotion rules in _sanitize_icd10_codes will remove R07.9 when I21.9 is
    # in the allowed set.
    #
    # has_positive_chest_pain: at least one non-negated "chest pain" mention
    # in *any* of symptoms / case_summary / history_notes.
    # Generic clinical labels ("cardiac", "heart attack", "myocardial") that
    # appear in case summaries are intentionally excluded so that phrases like
    # "possible cardiac issue" do not produce chest-pain candidates.
    _chest_pain_pattern = re.compile(r"\bchest\s+pain\b", re.IGNORECASE)
    has_positive_chest_pain = any(
        not _is_negated(ctx, m) for m in _chest_pain_pattern.finditer(ctx)
    )
    has_radiating_pain = bool(
        re.search(r"radiating\b|\bleft\s+arm\b|\bjaw\b|\bshoulder\b", ctx)
    )
    has_acs_associated = bool(
        re.search(
            r"\bsweating\b|\bdiaphoresis\b|\bnausea\b|\bshortness\s+of\s+breath\b",
            ctx,
        )
    )
    # Explicit textual confirmation of MI (e.g. "confirmed myocardial infarction").
    # This path bypasses the chest-pain gate because a documented MI diagnosis
    # is itself authoritative evidence of cardiac involvement.
    is_confirmed_mi = bool(
        re.search(
            r"confirmed\s+(heart\s+attack|myocardial\s+infarction|mi)\b"
            r"|myocardial\s+infarction\s+confirmed",
            ctx,
        )
    )
    is_acs = pathway == CarePathway.EMERGENCY and (
        is_confirmed_mi  # confirmed MI text alone is authoritative
        or (has_positive_chest_pain and has_radiating_pain and has_acs_associated)
    )

    seen: set[str] = set()
    candidates: list[str] = []

    def _add(code: str) -> None:
        if code not in seen:
            seen.add(code)
            candidates.append(code)

    # ACS composite → I21.9 takes priority over generic R07.9
    if is_acs:
        _add("I21.9")

    # Iterate broad symptom map; skip any match that is syntactically negated.
    for pattern, code in _COMPILED_SYMPTOM_MAP:
        for m in pattern.finditer(ctx):
            if not _is_negated(ctx, m):
                _add(code)
                break  # one positive match is enough to add the code

    # Fallback when nothing matched
    if not candidates:
        _add(_URGENCY_ICD10_CODES[urgency])

    return candidates


def _sanitize_icd10_codes(
    llm_codes: list[str],
    *,
    symptoms: str,
    case_summary: str = "",
    history_notes: str = "",
    pathway: "CarePathway",
    urgency: "UrgencyLevel",
) -> list[str]:
    """Validate and correct LLM-generated ICD-10 codes using a candidate-list
    approach rather than growing one-off symptom guardrails.

    Algorithm
    ---------
    1. Build ``allowed`` via ``_allowed_icd10_candidates(...)``.
    2. Filter ``llm_codes``: keep only codes that appear in ``allowed``.
    3. Apply deterministic promotion rules:
       - I21.9 in allowed  → ensure I21.9 present; remove R07.9.
       - R21 in allowed and psoriasis NOT in context
           → ensure R21 present; remove L40.9.
       - G43.909 (migraine) in allowed → ensure G43.909 present; remove
           the generic R51.9 headache code.
       - R07.9 in allowed and I21.9 NOT in allowed
           → ensure R07.9 present; remove I21.9.
    4. If result still empty → use ``allowed[0]``.
    5. Deduplicate while preserving order.

    This naturally removes hallucinated codes such as:
    - I00.9 (rheumatic fever) when not supported by context.
    - J06.9 (upper respiratory) when no respiratory symptoms exist.
    - R51.9 (headache) when no headache is mentioned.
    - L40.9 (psoriasis) when psoriasis is not documented.
    """
    allowed = _allowed_icd10_candidates(
        symptoms=symptoms,
        case_summary=case_summary,
        history_notes=history_notes,
        pathway=pathway,
        urgency=urgency,
    )
    allowed_set: set[str] = set(allowed)

    # Build combined context for promotion-rule checks
    ctx = " ".join([symptoms, case_summary, history_notes]).lower()
    has_psoriasis = bool(re.search(r"\bpsoriasis\b", ctx))

    # Normalize LLM codes before filtering: strip inline descriptions that the
    # LLM sometimes appends (e.g. "R50.9 — Fever, unspecified" → "R50.9").
    # This mirrors the Pydantic field validator on InsuranceDocument but must
    # happen here too because _sanitize_icd10_codes sees the raw LLM output.
    _DESC_STRIP_RE = re.compile(r"([A-Z]\d[\w.]+)", re.IGNORECASE)

    def _extract_code(raw: str) -> str | None:
        m = _DESC_STRIP_RE.search(raw.strip())
        return m.group(1) if m else None

    normalized_llm: list[str] = [c for raw in llm_codes if (c := _extract_code(raw))]

    # Step 1: filter LLM codes to those in allowed
    result: list[str] = [code for code in normalized_llm if code in allowed_set]

    # Step 2: promotion rules
    # -- ACS / MI: I21.9 must be present; R07.9 is too non-specific.
    if "I21.9" in allowed_set:
        if "I21.9" not in result:
            result.insert(0, "I21.9")
        if "R07.9" in result:
            result.remove("R07.9")

    # -- Rash without psoriasis: ensure R21; strip L40.9.
    if "R21" in allowed_set and not has_psoriasis:
        if "R21" not in result:
            result.insert(0, "R21")
        if "L40.9" in result:
            result.remove("L40.9")

    # -- Migraine (specific) supersedes generic headache: when the context
    # supports a migraine diagnosis, prefer G43.909 over the non-specific
    # R51.9 so the same complaint isn't double-coded at two granularities.
    if "G43.909" in allowed_set:
        if "G43.909" not in result:
            result.insert(0, "G43.909")
        if "R51.9" in result:
            result.remove("R51.9")

    # -- Non-ACS chest pain: ensure R07.9; strip I21.9.
    if "R07.9" in allowed_set and "I21.9" not in allowed_set:
        if "R07.9" not in result:
            result.insert(0, "R07.9")
        if "I21.9" in result:
            result.remove("I21.9")

    # Step 3: final fallback
    if not result:
        result = [allowed[0]]

    # Step 4: deduplicate preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for code in result:
        if code not in seen:
            seen.add(code)
            deduped.append(code)

    # Observability: surface how much the guardrail is altering LLM output.
    # A high drop rate is the signal that the candidate table needs more
    # categories (rather than silently masking the issue), and codes the LLM
    # supplied but that got dropped are useful for auditing false negatives.
    if logger.isEnabledFor(logging.DEBUG):
        dropped = sorted(set(normalized_llm) - set(deduped))
        added = sorted(set(deduped) - set(normalized_llm))
        if dropped or added:
            logger.debug(
                "ICD-10 sanitizer adjusted LLM output: dropped=%s added=%s "
                "final=%s (allowed_candidates=%s)",
                dropped, added, deduped, allowed,
            )

    return deduped

# ---------------------------------------------------------------------------
# Test name normalization helpers
# ---------------------------------------------------------------------------

# Alias map: normalized canonical key → list of regex patterns (case-insensitive)
_TEST_NAME_ALIASES: list[tuple[str, list[str]]] = [
    (
        "cbc",
        [
            r"\bcbc\b",
            r"\bcomplete blood count\b",
        ],
    ),
    (
        "ecg",
        [
            r"\becg\b",
            r"\belectrocardiogram\b",
        ],
    ),
    (
        "chest x-ray",
        [
            r"\bchest\s+x[\s\-]?ray\b",
        ],
    ),
    (
        "basic metabolic panel",
        [
            r"\bbasic metabolic panel\b",
            r"\bbmp\b",
        ],
    ),
    (
        "echocardiogram",
        [
            r"\bechocardiogram\b",
            r"\becho\b",
            r"\btransthoracic\s+echocardiogram\b",
            r"\btte\b",
        ],
    ),
    (
        "urinalysis",
        [
            r"\burinalysis\b",
            r"\burine\s+test\b",
        ],
    ),
    (
        "liver function test",
        [r"\bliver\s+function\s+test\b", r"\blft\b"],
    ),
    (
        "lipid profile",
        [r"\blipid\s+profile\b", r"\blipid\s+panel\b"],
    ),
    (
        "thyroid function test",
        [
            r"\bthyroid\s+function\s+test\b",
            r"\btft\b",
            r"\bthyroid\s+profile\b",
            r"\btsh\b",
        ],
    ),
    (
        "hba1c",
        [
            r"\bhba1c\b",
            r"\bglycated\s+hemoglobin\b",
            r"\bhemoglobin\s+a1c\b",
        ],
    ),
    (
        "blood glucose",
        [
            r"\bblood\s+glucose\b",
            r"\bblood\s+sugar\b",
            r"\bfasting\s+blood\s+sugar\b",
            r"\bfbs\b",
            r"\brandom\s+blood\s+sugar\b",
        ],
    ),
    (
        "stool routine",
        [
            r"\bstool\s+(?:routine|exam|test|culture)\b",
            r"\bfecal\s+occult\s+blood\b",
        ],
    ),
    (
        "blood culture",
        [r"\bblood\s+culture\b"],
    ),
    (
        "urine culture",
        [r"\burine\s+culture\b"],
    ),
    (
        "troponin",
        [r"\btroponin\b"],
    ),
    (
        "d-dimer",
        [r"\bd[\s\-]?dimer\b"],
    ),
    (
        "coagulation profile",
        [
            r"\bcoagulation\s+profile\b",
            r"\bpt[\s/]?inr\b",
            r"\bprothrombin\s+time\b",
            r"\baptt\b",
        ],
    ),
    (
        "ct scan",
        [
            r"\bct\s+scan\b",
            r"\bcat\s+scan\b",
            r"\bcomputed\s+tomography\b",
        ],
    ),
    (
        "mri",
        [
            r"\bmri\b",
            r"\bmagnetic\s+resonance\s+imaging\b",
        ],
    ),
    (
        "ultrasound abdomen",
        [
            r"\bultrasound\b",
            r"\busg\b",
            r"\bsonography\b",
        ],
    ),
    (
        "sputum test",
        [r"\bsputum\s+(?:test|afb|culture|examination)\b"],
    ),
    (
        "blood typing",
        [
            r"\bblood\s+typing\b",
            r"\bblood\s+group(?:ing)?\b",
        ],
    ),
    (
        "malaria test",
        [
            r"\bmalaria\s+(?:test|smear|antigen)\b",
            r"\bmp\s+smear\b",
        ],
    ),
    (
        "dengue test",
        [r"\bdengue\b"],
    ),
    (
        "hiv test",
        [
            r"\bhiv\s+test\b",
            r"\bhiv\s+antibody\b",
        ],
    ),
    (
        "covid rt-pcr",
        [
            r"\bcovid.*\bpcr\b",
            r"\brt[\s\-]?pcr\b",
        ],
    ),
    (
        "pregnancy test",
        [
            r"\bpregnancy\s+test\b",
            r"\burine\s+hcg\b",
            r"\bbeta\s+hcg\b",
        ],
    ),
    (
        "vitamin d",
        [
            r"\bvitamin\s+d\b",
            r"25[\s\-]?oh\s+vitamin\s+d",
        ],
    ),
    (
        "vitamin b12",
        [
            r"\bvitamin\s+b12\b",
            r"\bb12\s+level\b",
        ],
    ),
]

# Pre-compile patterns for performance
_COMPILED_ALIASES: list[tuple[str, list[re.Pattern]]] = [
    (canonical, [re.compile(p, re.IGNORECASE) for p in patterns])
    for canonical, patterns in _TEST_NAME_ALIASES
]


def _normalize_test_name(test_name: str) -> str:
    """Return the canonical lookup key for a test name, or the lowercased input."""
    stripped = test_name.strip()
    for canonical, patterns in _COMPILED_ALIASES:
        for pattern in patterns:
            if pattern.search(stripped):
                return canonical
    return stripped.lower()


def _dedupe_tests(tests: list[str]) -> list[str]:
    """Deduplicate a list of suggested-test names using normalized-name
    comparison, preserving the first-seen display text.

    Guards against duplicate billing (the same test summed twice into
    ``test_cost``) and duplicate "Diagnostic: ..." lines in
    ``proposed_services`` whenever the same test appears twice under
    different aliases (e.g. "CBC" and "Complete Blood Count").
    """
    seen: set[str] = set()
    result: list[str] = []
    for test in tests:
        key = _normalize_test_name(test)
        if key not in seen:
            seen.add(key)
            result.append(test)
    return result


def _build_submission_instructions(*, pathway: CarePathway, urgency: UrgencyLevel) -> str:
    """Generate submission guidance tailored to urgency and care pathway.

    Emergency/critical encounters need an expedited concurrent-review
    channel since care typically starts before authorization is confirmed;
    routine OPD/teleconsultation/specialist referrals go through the
    standard pre-authorization channel with normal insurer turnaround
    times.
    """
    if pathway == CarePathway.EMERGENCY or urgency == UrgencyLevel.CRITICAL:
        return (
            "Submit as an EMERGENCY / concurrent authorization via the insurer's "
            "24x7 cashless desk or TPA helpline immediately, since treatment has "
            "already commenced or is clinically time-critical. Attach this "
            "document, the clinical summary, and photo ID/policy card. Insurers "
            "are generally required to respond to emergency cashless requests "
            "within 1 hour of receipt; do not delay treatment pending approval."
        )
    return (
        "Submit through the insurer's or TPA's standard pre-authorization "
        "portal at least 48-72 hours prior to a planned procedure, attaching "
        "this document, the clinical summary, the itemized cost breakdown, "
        "and the patient's policy card / photo ID. Standard-track requests are "
        "typically adjudicated within 24-48 business hours; follow up with the "
        "reference number above if no response is received."
    )


class BillingInsuranceAgent(BaseAgent):
    name = "billing_insurance"

    def run(self, *, encounter_id: UUID, **kwargs: Any) -> dict[str, Any]:
        estimate = self._build_estimate(encounter_id, **kwargs)
        return estimate.model_dump(mode="json")

    def _build_estimate(self, encounter_id: UUID, **kwargs: Any) -> BillingEstimate:
        triage = self._parse_triage(encounter_id, kwargs.get("triage"))
        routing = self._parse_routing(encounter_id, kwargs.get("routing"))
        medical_summary = self._parse_medical_summary(encounter_id, kwargs.get("medical_summary"))
        symptoms = str(kwargs.get("symptoms", ""))

        pathway = routing.pathway
        cost_breakdown = self._estimate_costs(
            pathway=pathway,
            urgency=triage.urgency,
            suggested_tests=medical_summary.suggested_tests,
        )
        insurance_document = self._build_insurance_document(
            encounter_id=encounter_id,
            pathway=pathway,
            urgency=triage.urgency,
            medical_summary=medical_summary,
            symptoms=symptoms,
            cost_breakdown=cost_breakdown,
        )
        insurance_documentation = self._format_insurance_documentation(
            insurance_document, cost_breakdown
        )

        return BillingEstimate(
            encounter_id=encounter_id,
            estimated_cost_inr=cost_breakdown.total,
            currency="INR",
            cost_breakdown=cost_breakdown,
            insurance_documentation=insurance_documentation,
            insurance_document=insurance_document,
            status=BillingStatus.DRAFT,
        )

    def _parse_triage(self, encounter_id: UUID, raw: Any) -> TriageResult:
        if isinstance(raw, dict) and raw:
            return TriageResult.model_validate(raw)
        return TriageResult(encounter_id=encounter_id)

    def _parse_routing(self, encounter_id: UUID, raw: Any) -> RoutingDecision:
        if isinstance(raw, dict) and raw:
            return RoutingDecision.model_validate(raw)
        return RoutingDecision(encounter_id=encounter_id)

    def _parse_medical_summary(self, encounter_id: UUID, raw: Any) -> MedicalSummary:
        if isinstance(raw, dict) and raw:
            return MedicalSummary.model_validate(raw)
        return MedicalSummary(encounter_id=encounter_id)

    def _estimate_costs(
        self,
        *,
        pathway: CarePathway,
        urgency: UrgencyLevel,
        suggested_tests: list[str],
    ) -> CostBreakdown:
        consultation_fee = _CONSULTATION_FEE_INR[pathway]
        # Dedupe before summing: a test listed twice under different aliases
        # (e.g. "CBC" and "Complete Blood Count") must be billed once, not
        # twice.
        deduped_tests = _dedupe_tests(suggested_tests)
        test_cost = sum(
            (self._test_unit_cost(test) for test in deduped_tests),
            Decimal("0.00"),
        )
        medication_cost = _MEDICATION_COST_INR[urgency]
        miscellaneous_cost = _MISC_COST_INR[pathway]

        return CostBreakdown(
            consultation_fee=consultation_fee,
            test_cost=test_cost,
            medication_cost=medication_cost,
            miscellaneous_cost=miscellaneous_cost,
        )

    def _test_unit_cost(self, test_name: str) -> Decimal:
        normalized = _normalize_test_name(test_name)
        return _TEST_COST_INR.get(normalized, _DEFAULT_TEST_COST_INR)

    def _build_insurance_document(
        self,
        *,
        encounter_id: UUID,
        pathway: CarePathway,
        urgency: UrgencyLevel,
        medical_summary: MedicalSummary,
        symptoms: str,
        cost_breakdown: CostBreakdown,
    ) -> InsuranceDocument:
        # Dedupe so the same test isn't listed (and later billed/coded) twice
        # under two different aliases (e.g. "CBC" and "Complete Blood Count").
        deduped_tests = _dedupe_tests(medical_summary.suggested_tests)

        proposed_services = [f"{pathway.value.replace('_', ' ').title()} consultation"]
        proposed_services.extend(f"Diagnostic: {test}" for test in deduped_tests)

        # Resolve CPT codes from our database for known tests; the LLM will
        # use its clinical knowledge to determine codes for any unmapped tests.
        known_mappings: dict[str, str] = {
            f"{pathway.value.replace('_', ' ').title()} consultation": _PATHWAY_CPT_CODES[pathway]
        }
        for test in deduped_tests:
            normalized = _normalize_test_name(test)
            if test_cpt := _TEST_CPT_CODES.get(normalized):
                known_mappings[test] = test_cpt

        user_lines = [
            f"Symptoms: {symptoms.strip() if symptoms else 'None provided'}",
            f"Urgency Level: {urgency.value}",
            f"Care Pathway: {pathway.value.replace('_', ' ').title()}",
            f"Clinical Summary: {medical_summary.case_summary}",
            f"Medical History: {medical_summary.history_notes}",
            f"Proposed Services: {', '.join(proposed_services)}",
            f"Known CPT Mappings: {known_mappings}",
            "CPT CODING INSTRUCTIONS: "
            "1. Use the exact CPT codes provided in 'Known CPT Mappings' for those services. "
            "2. For any service listed in 'Proposed Services' that does NOT appear in 'Known CPT Mappings', "
            "use your clinical knowledge to determine and output its correct CPT code. "
            "3. Do NOT include CPT codes for any tests or services that are not explicitly listed in 'Proposed Services'.",
        ]

        system_prompt = load_prompt("billing_insurance")
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="\n".join(user_lines)),
        ]

        clinical_indication: str | None = None
        coverage_notes: str | None = None
        icd10_codes: list[str] = []
        cpt_codes: list[str] = []

        try:
            output: _BillingLLMOutput = invoke_structured(_BillingLLMOutput, messages)
            clinical_indication = output.clinical_indication
            coverage_notes = output.coverage_notes
            icd10_codes = output.icd10_codes
            cpt_codes = output.cpt_codes
            logger.info("LLM billing document generated for encounter %s", encounter_id)
        except NotConfiguredError:
            raise
        except Exception as exc:
            logger.warning(
                "LLM billing document generation failed for encounter %s, "
                "falling back to rule-based defaults: %s",
                encounter_id,
                exc,
            )

        if not clinical_indication:
            if symptoms and symptoms.strip():
                clinical_indication = f"Presenting symptoms: {symptoms.strip()}"
            else:
                clinical_indication = medical_summary.case_summary

        if not coverage_notes:
            coverage_notes = (
                f"Urgency classified as {urgency.value}. "
                f"Pathway: {pathway.value.replace('_', ' ')}. "
                f"{medical_summary.history_notes}"
            )

        # Apply deterministic guardrails unconditionally — corrects LLM
        # hallucinations even when the LLM call succeeded, and provides
        # pathway/urgency-based fallbacks when the LLM call failed.
        icd10_codes = _sanitize_icd10_codes(
            icd10_codes,
            symptoms=symptoms,
            case_summary=medical_summary.case_summary,
            history_notes=medical_summary.history_notes,
            pathway=pathway,
            urgency=urgency,
        )

        cpt_codes = _sanitize_cpt_codes(
            cpt_codes,
            pathway=pathway,
            suggested_tests=deduped_tests,
        )

        return InsuranceDocument(
            encounter_id=encounter_id,
            reference_number=f"PREAUTH-{str(encounter_id)[:8].upper()}",
            clinical_indication=clinical_indication,
            proposed_services=proposed_services,
            estimated_amount_inr=cost_breakdown.total,
            coverage_notes=coverage_notes,
            icd10_codes=icd10_codes,
            cpt_codes=cpt_codes,
            submission_instructions=_build_submission_instructions(
                pathway=pathway, urgency=urgency
            ),
        )

    def _format_insurance_documentation(
        self,
        document: InsuranceDocument,
        cost_breakdown: CostBreakdown,
    ) -> str:
        def _money(value: Decimal) -> str:
            return f"Rs. {value:,.2f}"

        services = "\n".join(f"  - {service}" for service in document.proposed_services)

        icd10_lines = "\n".join(
            f"  {code:<10} {_ICD10_DESCRIPTIONS.get(code, '(description not coded — refer to ICD-10-CM index)')}"
            for code in document.icd10_codes
        )
        cpt_lines = "\n".join(
            f"  {code:<10} {_CPT_DESCRIPTIONS.get(code, '(description not coded — refer to CPT code book)')}"
            for code in document.cpt_codes
        )

        return "\n".join(
            [
                "=" * 72,
                "HOSPITAL COMMAND CENTER — BILLING & INSURANCE UNIT",
                "INSURANCE PRE-AUTHORIZATION REQUEST",
                "=" * 72,
                f"Reference Number:   {document.reference_number}",
                f"Encounter ID:       {document.encounter_id}",
                f"Document Type:      {document.document_type}",
                f"Generated At (UTC): {document.generated_at.isoformat()}Z",
                "Patient Name:       [As per hospital registration]",
                "Policy / Member ID: [To be completed by billing desk]",
                "Treating Facility:  [Facility name / network hospital ID]",
                "-" * 72,
                "CLINICAL INDICATION",
                "-" * 72,
                f"{document.clinical_indication}",
                "",
                "-" * 72,
                "PROPOSED SERVICES",
                "-" * 72,
                services if services else "  (none)",
                "",
                "-" * 72,
                "ICD-10 DIAGNOSIS CODES",
                "-" * 72,
                icd10_lines if icd10_lines else "  (none)",
                "",
                "-" * 72,
                "CPT PROCEDURE CODES",
                "-" * 72,
                cpt_lines if cpt_lines else "  (none)",
                "",
                "-" * 72,
                "ESTIMATED COST BREAKDOWN (INR)",
                "-" * 72,
                f"  {'Consultation / visit fee:':<32}{_money(cost_breakdown.consultation_fee):>15}",
                f"  {'Diagnostic tests:':<32}{_money(cost_breakdown.test_cost):>15}",
                f"  {'Medication (estimated):':<32}{_money(cost_breakdown.medication_cost):>15}",
                f"  {'Facility / miscellaneous:':<32}{_money(cost_breakdown.miscellaneous_cost):>15}",
                "  " + "-" * 47,
                f"  {'TOTAL ESTIMATED AMOUNT:':<32}{_money(cost_breakdown.total):>15}",
                "",
                "  Note: this is a good-faith clinical cost estimate for pre-",
                "  authorization purposes only, not a final invoice. Actual charges",
                "  may vary based on services rendered. The patient's final",
                "  out-of-pocket responsibility (co-pay, deductible, and any",
                "  non-covered items) is determined solely by the insurer/TPA under",
                "  the terms of the specific policy and is not calculated here.",
                "",
                "-" * 72,
                "COVERAGE NOTES / MEDICAL NECESSITY JUSTIFICATION",
                "-" * 72,
                f"{document.coverage_notes}",
                "",
                "-" * 72,
                "SUBMISSION INSTRUCTIONS",
                "-" * 72,
                f"{document.submission_instructions}",
                "",
                "=" * 72,
                "This document is system-generated by the Billing & Insurance agent",
                "and requires review and countersignature by an authorized hospital",
                "billing officer prior to submission to the insurer/TPA.",
                "=" * 72,
            ]
        )