"""Streamlit display for care pathway routing."""

from typing import Any

import streamlit as st

_PATHWAY_LABELS = {
    "emergency": "Emergency",
    "opd": "OPD (in-person)",
    "teleconsultation": "Teleconsultation",
    "specialist_referral": "Specialist referral",
}


def render_routing(routing: dict[str, Any]) -> None:
    st.subheader("Care pathway (Router)")
    if not routing:
        st.warning("No routing decision available.")
        return

    pathway = str(routing.get("pathway", "unknown"))
    label = _PATHWAY_LABELS.get(pathway, pathway.replace("_", " ").title())
    st.metric("Recommended pathway", label)
    if routing.get("notes"):
        st.write(routing["notes"])
