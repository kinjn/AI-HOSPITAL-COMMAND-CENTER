"""Single encounter viewer: complete summary, triage results, routing decision, billing breakdown, and follow-up plan."""

import asyncio

import streamlit as st

from hospital_command_center.core.exceptions import HospitalCommandCenterError
from hospital_command_center.services.workflow_service import WorkflowService
from hospital_command_center.ui.components.billing_panel import render_billing
from hospital_command_center.ui.components.followup_panel import render_followup
from hospital_command_center.ui.components.navbar import render_navbar
from hospital_command_center.ui.components.routing_panel import render_routing
from hospital_command_center.ui.components.triage_panel import render_triage
from hospital_command_center.ui.db_helper import (
    add_doctor_notes,
    approve_billing_status,
    fetch_dietary_context,
    fetch_encounter_by_id,
    fetch_encounters,
    override_pathway,
    update_dietary_context_and_regenerate_followup,
    update_status,
)

st.set_page_config(
    page_title="Encounter Detail Viewer | Hospital Command Center",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

render_navbar("nav_detail")

st.subheader("Encounter Detail & Case Insights")

# Retrieve all encounters for selection dropdown
try:
    all_enc = asyncio.run(fetch_encounters(limit=150))
except Exception as e:
    all_enc = []
    st.error(f"Error fetching patient encounter list: {e}")

# Determine currently selected encounter ID
selected_id = st.session_state.get("selected_encounter_id")

# Header Selector Panel
if all_enc:
    enc_options = {e["id"]: f"{e['patient_name']} — Urgency: {e['urgency'].upper()} ({e['created_at'].strftime('%b %d, %H:%M')})" for e in all_enc}
    enc_ids = list(enc_options.keys())
    
    try:
        default_index = enc_ids.index(selected_id) if selected_id in enc_ids else 0
    except ValueError:
        default_index = 0
        
    chosen_id = st.selectbox(
        "Select patient encounter to inspect:",
        options=enc_ids,
        format_func=lambda x: enc_options.get(x, x),
        index=default_index
    )
    
    if chosen_id != selected_id:
        st.session_state["selected_encounter_id"] = chosen_id
        st.rerun()
else:
    chosen_id = selected_id

# If we have a selected encounter, load and render it
if chosen_id:
    with st.spinner("Fetching full encounter information..."):
        try:
            detail = asyncio.run(fetch_encounter_by_id(chosen_id))
        except Exception as e:
            st.error(f"Failed to fetch details: {e}")
            detail = None

    if detail:
        patient = detail["patient"]
        encounter = detail["encounter"]
        state = detail["workflow_state"]

        # Clean visual cards for Patient Identity
        st.write("")
        c1, c2, c3 = st.columns([5, 3, 3])
        with c1:
            st.markdown(
                f'<div style="background-color: #F3F4F6; border-radius: 8px; padding: 15px; border-left: 4px solid #1F2937;">'
                f'<strong>Patient:</strong> {patient["full_name"]} · age {patient.get("age", "—")} · {patient["gender"].title()}<br/>'
                f'<strong>Mobile:</strong> {patient["phone"]} | <strong>Email:</strong> {patient["email"]}<br/>'
                f'<strong>Symptoms:</strong> <em>"{encounter["symptoms"]}"</em>'
                f'</div>',
                unsafe_allow_html=True
            )
        with c2:
            st.markdown(
                f'<div style="background-color: #F3F4F6; border-radius: 8px; padding: 15px; border-left: 4px solid #4F46E5;">'
                f'<strong>Encounter ID:</strong> <code>{encounter["id"]}</code><br/>'
                f'<strong>Patient ID:</strong> <code>{patient["id"]}</code><br/>'
                f'<strong>Channel:</strong> {encounter["source_channel"].upper()}'
                f'</div>',
                unsafe_allow_html=True
            )
        with c3:
            pathway_label = encounter["pathway"] or "—"
            if pathway_label == "teleconsult":
                pathway_label = "Teleconsultation"
            elif pathway_label == "specialist":
                pathway_label = "Specialist Referral"
            else:
                pathway_label = pathway_label.upper()

            st.markdown(
                f'<div style="background-color: #F3F4F6; border-radius: 8px; padding: 15px; border-left: 4px solid #10B981;">'
                f'<strong>Status:</strong> <span style="color: #2563EB; font-weight: bold;">{encounter["status"].upper()}</span><br/>'
                f'<strong>Pathway:</strong> <span style="color: #059669; font-weight: bold;">{pathway_label}</span><br/>'
                f'<strong>Created:</strong> {encounter["created_at"].strftime("%Y-%m-%d %H:%M")}'
                f'</div>',
                unsafe_allow_html=True
            )

        st.divider()

        # Detailed breakdown in visual panels
        st.subheader("Automated Agent Workflow Diagnostics")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            # 1. Triage Panel
            render_triage(state.get("triage", {}))
            
            # 2. Care Routing
            render_routing(state.get("routing", {}))
            
            # Action: Override Care Pathway
            with st.expander("Manual Actions & Care Pathway Override"):
                current_pathway = encounter["pathway"]
                pathway_opts = {
                    "emergency": "Emergency",
                    "opd": "OPD (in-person)",
                    "teleconsult": "Teleconsultation",
                    "specialist": "Specialist referral"
                }
                pathway_keys = list(pathway_opts.keys())
                try:
                    default_idx = pathway_keys.index(current_pathway) if current_pathway in pathway_keys else 1
                except ValueError:
                    default_idx = 1
                
                overridden_pathway = st.selectbox(
                    "Override Care Pathway:",
                    options=pathway_keys,
                    format_func=lambda x: pathway_opts.get(x, x.upper()),
                    index=default_idx,
                    key="override_pathway_detail"
                )
                if st.button("Apply Pathway Override", key="btn_apply_override"):
                    if asyncio.run(override_pathway(encounter["id"], overridden_pathway)):
                        st.success("Pathway overridden successfully.")
                        st.rerun()
                    else:
                        st.error("Failed to override care pathway.")
                
                st.write("")
                new_status = st.selectbox(
                    "Change Status state:",
                    ["intake", "triaged", "routed", "summary_ready", "billing_ready", "closed"],
                    index=["intake", "triaged", "routed", "summary_ready", "billing_ready", "closed"].index(encounter["status"]) if encounter["status"] in ["intake", "triaged", "routed", "summary_ready", "billing_ready", "closed"] else 0,
                    key="override_status_detail"
                )
                if st.button("Apply Status Override", key="btn_apply_status"):
                    if asyncio.run(update_status(encounter["id"], new_status)):
                        st.success("Status updated successfully.")
                        st.rerun()
                    else:
                        st.error("Failed to update status.")

        with col_right:
            # 3. Medical Summary & SOAP Note
            st.subheader("Medical Summarizer & SOAP Note")
            summary = state.get("medical_summary", {})
            if not summary:
                st.warning("No medical summaries generated yet.")
            else:
                st.write(summary.get("case_summary", ""))
                if summary.get("suggested_tests"):
                    st.markdown("**Suggested Tests:** " + ", ".join(summary["suggested_tests"]))
                if summary.get("history_notes"):
                    st.markdown("**Extracted History:** " + summary["history_notes"])
                if summary.get("doctor_briefing"):
                    st.markdown("**Doctor Briefing (SOAP Note):**")
                    st.text_area("SOAP Note Contents", value=summary["doctor_briefing"], height=160, disabled=True, key="soap_notes_detail")

                # Review editor
                st.markdown("##### Reviews and Custom Instructions")
                review_notes = st.text_area(
                    "Input clinical review notes or specific physician instructions:",
                    value=summary.get("doctor_briefing") or "",
                    height=80,
                    key="review_notes_input"
                )
                if st.button("Save Doctor Briefing Notes", key="btn_save_notes"):
                    if asyncio.run(add_doctor_notes(encounter["id"], review_notes)):
                        st.success("Briefing notes updated successfully.")
                        st.rerun()
                    else:
                        st.error("Failed to save notes.")

        st.divider()

        # Billing and Followups row
        col_billing, col_followups = st.columns(2)
        with col_billing:
            render_billing(state.get("billing", {}))
            
            billing = state.get("billing", {})
            if billing:
                st.write("")
                st.markdown("**Insurance Pre-Auth Status Control:**")
                current_bill_status = billing.get("status", "draft").upper()
                st.info(f"Current Pre-Authorization Status: **{current_bill_status}**")
                
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("Approve Billing & Close Case", disabled=(current_bill_status == "APPROVED"), key="approve_bill_det"):
                        if asyncio.run(approve_billing_status(encounter["id"], "approved")):
                            st.success("Estimate approved. Patient record marked closed.")
                            st.rerun()
                with b2:
                    if st.button("Dispute Estimate / File Dispute", disabled=(current_bill_status == "REJECTED"), key="dispute_bill_det"):
                        if asyncio.run(approve_billing_status(encounter["id"], "rejected")):
                            st.warning("Pre-authorization disputed.")
                            st.rerun()
                            
        with col_followups:
            render_followup(state.get("followup", {}))

            with st.expander("Update Dietary Preference / Allergies / Conditions", expanded=False):
                st.caption(
                    "Fill this in to (re)generate the diet & hydration guidance for "
                    "*this same encounter* — this updates the existing record instead "
                    "of creating a new patient/encounter."
                )
                try:
                    current_diet_ctx = asyncio.run(fetch_dietary_context(encounter["id"]))
                except Exception:
                    current_diet_ctx = {}

                diet_options = ["Not specified", "Vegetarian", "Non-vegetarian", "Vegan", "Eggetarian", "Other"]
                current_pref = current_diet_ctx.get("dietary_preference") or "Not specified"
                pref_index = diet_options.index(current_pref) if current_pref in diet_options else 0

                d1, d2 = st.columns(2)
                with d1:
                    updated_pref = st.selectbox(
                        "Dietary Preference",
                        diet_options,
                        index=pref_index,
                        key="update_dietary_pref",
                    )
                with d2:
                    updated_allergies = st.text_input(
                        "Known Food Allergies",
                        value=current_diet_ctx.get("food_allergies") or "",
                        placeholder="e.g. peanuts, shellfish",
                        key="update_food_allergies",
                    )
                updated_conditions = st.text_input(
                    "Pre-existing Medical Conditions",
                    value=current_diet_ctx.get("known_medical_conditions") or "",
                    placeholder="e.g. Type 2 diabetes, hypertension",
                    key="update_medical_conditions",
                )

                if st.button("Update & Regenerate Follow-up Plan", key="btn_update_dietary"):
                    with st.spinner("Updating record and regenerating the follow-up plan..."):
                        ok = asyncio.run(
                            update_dietary_context_and_regenerate_followup(
                                encounter["id"],
                                dietary_preference=(
                                    updated_pref if updated_pref != "Not specified" else None
                                ),
                                food_allergies=updated_allergies.strip() or None,
                                known_medical_conditions=updated_conditions.strip() or None,
                            )
                        )
                    if ok:
                        st.success("Follow-up plan regenerated with the updated dietary info.")
                        st.rerun()
                    else:
                        st.error("Could not find this encounter to update.")
            
else:
    # No encounter pre-selected and none found in DB
    st.info("No active encounters found. Submit the intake form first or execute a demo workflow below.")
    
    if st.button("Run Demo Workflow (using standard symptoms)"):
        try:
            with st.spinner("Running agent workflow pipeline... (Requires OpenAI API Key)"):
                state = WorkflowService().run_stub(symptoms="patient has high fever and severe stomach ache since yesterday")
                # Store resulting stub
                st.session_state["selected_encounter_id"] = str(state.get("encounter_id"))
                st.session_state["last_workflow"] = {
                    "encounter": {
                        "id": str(state.get("encounter_id")),
                        "symptoms": state.get("symptoms", "demo FEVER"),
                    },
                    "workflow_state": state,
                }
            st.success("Demo workflow processed!")
            st.rerun()
        except HospitalCommandCenterError as exc:
            st.error(f"Workflow execution failed: {exc}")