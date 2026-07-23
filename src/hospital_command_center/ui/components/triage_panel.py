"""Streamlit display for LLM triage output."""

from typing import Any

import streamlit as st

_URGENCY_COLORS = {
    "low": "green",
    "medium": "orange",
    "high": "red",
    "critical": "red",
}


def render_triage(triage: dict[str, Any]) -> None:
    st.subheader("Triage (LLM)")
    if not triage:
        st.warning("No triage result available.")
        return

    status = str(triage.get("status", "complete")).lower()
    if status == "needs_clarification":
        st.info("Additional detail needed before urgency can be classified.")
        questions = triage.get("clarifying_questions") or []
        if questions:
            st.markdown("**Clarifying questions:**")
            for idx, question in enumerate(questions, start=1):
                st.write(f"{idx}. {question}")
        if triage.get("rationale"):
            st.caption(triage["rationale"])
        return

    urgency = str(triage.get("urgency", "unknown")).lower()
    color = _URGENCY_COLORS.get(urgency, "gray")
    st.markdown(f"**Urgency:** :{color}[{urgency.upper()}]")
    if triage.get("rationale"):
        st.write(triage["rationale"])
