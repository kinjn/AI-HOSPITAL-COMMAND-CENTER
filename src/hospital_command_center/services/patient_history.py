"""Build patient encounter history text for LLM context."""

from hospital_command_center.db.models.encounter import EncounterModel


def format_patient_history(encounters: list[EncounterModel], *, limit: int = 8) -> str:
    """Format prior encounters into a concise history block for triage."""
    if not encounters:
        return "No prior visits on record."

    lines: list[str] = []
    for enc in encounters[:limit]:
        date_str = enc.created_at.strftime("%Y-%m-%d") if enc.created_at else "unknown date"
        parts = [f"- Visit {date_str}: symptoms: {enc.symptoms or 'not recorded'}"]

        if enc.pathway:
            parts.append(f"pathway: {enc.pathway}")
        if enc.status:
            parts.append(f"status: {enc.status}")

        triage = enc.triage_result
        if triage:
            parts.append(f"urgency: {triage.urgency_level}")
            if triage.reasoning:
                parts.append(f"triage note: {triage.reasoning[:200]}")

        summary = enc.case_summary
        if summary and summary.summary_text:
            excerpt = summary.summary_text[:200].replace("\n", " ")
            parts.append(f"summary: {excerpt}")

        lines.append("; ".join(parts))

    return "\n".join(lines)
