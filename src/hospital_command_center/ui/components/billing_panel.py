"""Streamlit display for billing agent output."""

from typing import Any

import streamlit as st


def render_billing(billing: dict[str, Any]) -> None:
    st.subheader("Billing & insurance")
    if not billing:
        st.warning("No billing data available.")
        return

    breakdown = billing.get("cost_breakdown", {})
    cols = st.columns(4)
    cols[0].metric("Consultation", f"₹{breakdown.get('consultation_fee', 0)}")
    cols[1].metric("Tests", f"₹{breakdown.get('test_cost', 0)}")
    cols[2].metric("Medication", f"₹{breakdown.get('medication_cost', 0)}")
    cols[3].metric("Total", f"₹{billing.get('estimated_cost_inr', breakdown.get('total', 0))}")

    st.caption(
        f"Status: {billing.get('status', 'draft')} · Currency: {billing.get('currency', 'INR')}"
    )

    doc = billing.get("insurance_document")
    if doc:
        with st.expander("Insurance details"):
            st.write(f"**Reference:** {doc.get('reference_number', '—')}")
            st.write(f"**Type:** {doc.get('document_type', '—')}")
            st.write(f"**Clinical indication:** {doc.get('clinical_indication', '—')}")
            if doc.get("proposed_services"):
                st.write("**Proposed services:**")
                for service in doc["proposed_services"]:
                    st.write(f"- {service}")
            if doc.get("icd10_codes"):
                st.write("**ICD-10 Diagnosis Codes:**")
                for code in doc["icd10_codes"]:
                    st.write(f"- `{code}`")
            if doc.get("cpt_codes"):
                st.write("**CPT Procedure Codes:**")
                for code in doc["cpt_codes"]:
                    st.write(f"- `{code}`")

    if billing.get("insurance_documentation"):
        with st.expander("Pre-authorization document"):
            st.code(billing["insurance_documentation"], language=None)
