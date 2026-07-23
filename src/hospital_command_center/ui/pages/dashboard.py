"""Ops dashboard: active encounters, triage queues, routing overrides, and operational actions."""

import asyncio

import streamlit as st

from hospital_command_center.ui.components.billing_panel import render_billing
from hospital_command_center.ui.components.followup_panel import render_followup
from hospital_command_center.ui.components.navbar import render_navbar
from hospital_command_center.ui.components.routing_panel import render_routing
from hospital_command_center.ui.components.triage_panel import render_triage
from hospital_command_center.ui.db_helper import (
    add_doctor_notes,
    approve_billing_status,
    fetch_encounter_by_id,
    fetch_encounters,
    override_pathway,
    update_status,
)

st.set_page_config(
    page_title="Operations Dashboard | Hospital Command Center",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

render_navbar("nav_dashboard")

# Custom header
st.subheader("Operations Queue & Triage Management")

# Page Filters (horizontal design)
with st.container():
    f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns([1.8, 1.2, 1.2, 1.2, 1.0])
    with f_col1:
        search_query = st.text_input("Search Patient or Symptoms", placeholder="Name, phone, symptom...")
    with f_col2:
        status_filter = st.selectbox(
            "Encounter Status",
            ["All", "Intake", "Triaged", "Routed", "Summary_Ready", "Billing_Ready", "Closed"]
        )
    with f_col3:
        pathway_filter = st.selectbox(
            "Care Pathway",
            ["All", "Emergency", "OPD (in-person)", "Teleconsultation", "Specialist Referral"]
        )
    with f_col4:
        urgency_filter = st.selectbox(
            "Triage Urgency",
            ["All", "Critical", "High", "Medium", "Low"]
        )
    with f_col5:
        limit = st.slider("Max entries to load", 10, 200, 50)

# Run DB queries to get encounters list
try:
    # Map visual pathway options to search-compatible filters
    mapped_pathway = pathway_filter
    if pathway_filter == "OPD (in-person)":
        mapped_pathway = "OPD"
    elif pathway_filter == "Teleconsultation":
        mapped_pathway = "teleconsult"
    elif pathway_filter == "Specialist Referral":
        mapped_pathway = "specialist"

    encounters = asyncio.run(
        fetch_encounters(
            status_filter=status_filter,
            pathway_filter=mapped_pathway,
            urgency_filter=urgency_filter,
            search_query=search_query,
            limit=limit,
        )
    )
except Exception as e:
    st.error(f"Error loading encounters from database: {e}")
    encounters = []

# Layout: 2 Columns (Left: Master List, Right: Selected Encounter Details & Operations)
col_list, col_details = st.columns([5, 6])

with col_list:
    st.subheader(f"Encounters Queue ({len(encounters)})")
    
    if not encounters:
        st.info("No encounters match the current filter criteria.")
    else:
        for e in encounters:
            # Styled Card for each encounter
            urgency = e["urgency"].lower()
            urg_tag = urgency.upper()
            urg_color = (
                "#EF4444" if urgency == "critical"
                else "#F97316" if urgency == "high"
                else "#F59E0B" if urgency == "medium"
                else "#10B981"
            )
            
            # Highlight selected encounter card
            is_selected = st.session_state.get("selected_encounter_id") == e["id"]
            border_style = "border: 2px solid #4F46E5; background-color: #F5F3FF;" if is_selected else "border: 1px solid #E5E7EB;"
            
            pathway_label = e["pathway"] or "—"
            if pathway_label == "teleconsult":
                pathway_label = "Teleconsultation"
            elif pathway_label == "specialist":
                pathway_label = "Specialist Referral"
            else:
                pathway_label = pathway_label.upper()

            with st.container():
                st.markdown(
                    f'<div style="{border_style} border-radius: 8px; padding: 15px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">'
                    f'<strong>{e["patient_name"]}</strong> ({e["patient_gender"].title()})<br/>'
                    f'<small>Urgency: <span style="color: {urg_color}; font-weight: bold;">{urg_tag}</span> | Status: {e["status"].upper()} | Channel: {e["source_channel"].upper()}</small><br/>'
                    f'<span style="font-size: 0.9em; color: #4B5563;">Symptoms: <em>"{e["symptoms"]}"</em></span><br/>'
                    f'<span style="font-size: 0.85em; font-weight: 500; color: #6D28D9;">Pathway Recommendation: {pathway_label}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                
                # Small row of actions for this card
                c_sel, c_view = st.columns([3, 2])
                with c_sel:
                    if st.button("Select to Manage", key=f"sel_btn_{e['id']}"):
                        st.session_state["selected_encounter_id"] = e["id"]
                        # Set compatibility last_workflow
                        try:
                            det = asyncio.run(fetch_encounter_by_id(e["id"]))
                            if det:
                                st.session_state["last_workflow"] = det["workflow_state"]
                                st.session_state["patient_info"] = det["patient"]
                        except Exception:
                            pass
                        st.rerun()
                with c_view:
                    if st.button("Open Page", key=f"pg_btn_{e['id']}"):
                        st.session_state["selected_encounter_id"] = e["id"]
                        try:
                            det = asyncio.run(fetch_encounter_by_id(e["id"]))
                            if det:
                                st.session_state["last_workflow"] = det["workflow_state"]
                                st.session_state["patient_info"] = det["patient"]
                        except Exception:
                            pass
                        st.switch_page("pages/encounter_detail.py")
                
                st.write("")

# Right column: Details and management console
with col_details:
    selected_id = st.session_state.get("selected_encounter_id")
    if not selected_id:
        st.subheader("Encounter Management Console")
        st.info("Select a patient from the queue on the left to view metrics, read summaries, and manage their care workflow.")
        
        # Show general help instructions
        st.markdown("""
        ### Workflow Pipeline:
        1. **Intake**: Patient submits symptoms via Web/App/WhatsApp.
        2. **Triage (AI)**: Urgent cases are immediately flagged (CRITICAL/HIGH/MEDIUM/LOW).
        3. **Route (AI)**: Automated assignment of pathways (Emergency, OPD, Teleconsult, Specialist).
        4. **Summary (AI)**: Synthesizes symptoms, history and prints a SOAP doctor briefing.
        5. **Billing (AI)**: Itemizes billing and initiates pre-authorization request.
        6. **Follow-up (AI)**: Details reminders, medication timelines, and red flag warnings.
        """)
    else:
        # Load encounter detail from database
        try:
            detail = asyncio.run(fetch_encounter_by_id(selected_id))
        except Exception as e:
            st.error(f"Error reading details: {e}")
            detail = None

        if not detail:
            st.error("Encounter record not found in database.")
        else:
            patient = detail["patient"]
            encounter = detail["encounter"]
            state = detail["workflow_state"]

            col_title, col_clear = st.columns([3, 1])
            with col_title:
                st.subheader(f"Manage: {patient['full_name']}")
            with col_clear:
                if st.button("Clear Selection", key="btn_clear_selection", use_container_width=True):
                    if "selected_encounter_id" in st.session_state:
                        del st.session_state["selected_encounter_id"]
                    st.rerun()
            
            # Quick facts
            st.markdown(
                f"**Patient ID:** `{patient['id']}` · **Encounter ID:** `{encounter['id']}` · **Created:** {encounter['created_at'].strftime('%Y-%m-%d %H:%M:%S')}"
            )
            st.write(f"**Submitted Symptoms:** *\"{encounter['symptoms']}\"*")

            # Progress timeline visual
            st.write("**Workflow Pipeline Status:**")
            status_order = ["intake", "triaged", "routed", "summary_ready", "billing_ready", "closed"]
            current_status = encounter["status"]
            
            status_line = ""
            for idx, stat in enumerate(status_order):
                if stat == current_status:
                    status_line += f"**[{stat.upper()}]**"
                else:
                    status_line += f" {stat} "
                if idx < len(status_order) - 1:
                    status_line += " -> "
            st.markdown(status_line)
            st.write("")

            # Action tabs
            tab_ops, tab_summary, tab_billing, tab_followup = st.tabs([
                "Actions / Override",
                "Medical Summaries",
                "Billing & Insurance",
                "Follow-up plan"
            ])

            with tab_ops:
                st.markdown("#### Operations Control Board")
                
                # Urgency Triage summary
                urgency = state.get("triage", {}).get("urgency", "unknown").upper()
                st.write(f"**AI Urgency Assessment:** `{urgency}`")
                if state.get("triage", {}).get("rationale"):
                    st.caption(f"Rationale: {state['triage']['rationale']}")

                st.write("")
                st.divider()

                # Pathway override selector
                st.markdown("##### Care Pathway Override")
                current_pathway = encounter["pathway"]
                pathway_opts = {
                    "emergency": "Emergency",
                    "opd": "OPD (in-person)",
                    "teleconsult": "Teleconsultation",
                    "specialist": "Specialist referral"
                }
                
                pathway_list = list(pathway_opts.keys())
                try:
                    default_idx = pathway_list.index(current_pathway) if current_pathway in pathway_list else 1
                except ValueError:
                    default_idx = 1

                new_pathway = st.selectbox(
                    "Override Care Pathway to:",
                    options=pathway_list,
                    format_func=lambda x: pathway_opts.get(x, x.upper()),
                    index=default_idx
                )

                if st.button("Confirm Pathway Override"):
                    try:
                        success = asyncio.run(override_pathway(encounter["id"], new_pathway))
                        if success:
                            st.success(f"Pathway successfully changed to {pathway_opts[new_pathway]}.")
                            st.rerun()
                        else:
                            st.error("Failed to update care pathway in database.")
                    except Exception as err:
                        st.error(f"Error updating pathway: {err}")

                st.divider()

                # Status manual progression
                st.markdown("##### Manual Status Override")
                new_status = st.selectbox(
                    "Change Encounter Status to:",
                    ["intake", "triaged", "routed", "summary_ready", "billing_ready", "closed"],
                    index=status_order.index(current_status) if current_status in status_order else 0
                )

                if st.button("Confirm Status Override"):
                    try:
                        success = asyncio.run(update_status(encounter["id"], new_status))
                        if success:
                            st.success(f"Status successfully updated to {new_status.upper()}.")
                            st.rerun()
                        else:
                            st.error("Failed to update status.")
                    except Exception as err:
                        st.error(f"Error updating status: {err}")

            with tab_summary:
                render_triage(state.get("triage", {}))
                render_routing(state.get("routing", {}))

                st.divider()
                st.markdown("#### Medical Case Summary & Doctor Notes")
                summary = state.get("medical_summary", {})
                if not summary:
                    st.warning("No medical summary available yet.")
                else:
                    st.write(summary.get("case_summary", ""))
                    if summary.get("suggested_tests"):
                        st.write("**Suggested clinical tests:** " + ", ".join(summary["suggested_tests"]))
                    if summary.get("history_notes"):
                        st.write("**Extracted patient history:** " + summary["history_notes"])
                    
                    if summary.get("doctor_briefing"):
                        st.markdown("**Doctor Briefing (SOAP notes):**")
                        st.text_area("AI SOAP Note Briefing", value=summary["doctor_briefing"], height=180, disabled=True)
                    
                    st.divider()
                    st.markdown("##### Add/Edit Doctor Clinical Review Notes")
                    doc_notes = st.text_area(
                        "Doctor notes (prescriptions, diagnostic remarks, override notes)",
                        value=summary.get("doctor_briefing") or "",
                        help="Review notes saved to database case summaries table.",
                        height=100
                    )
                    
                    if st.button("Save Doctor Notes"):
                        try:
                            success = asyncio.run(add_doctor_notes(encounter["id"], doc_notes))
                            if success:
                                st.success("Doctor clinical review notes saved to SQLite.")
                                st.rerun()
                            else:
                                st.error("Failed to save doctor notes.")
                        except Exception as err:
                            st.error(f"Error saving notes: {err}")

            with tab_billing:
                render_billing(state.get("billing", {}))
                
                billing_record = state.get("billing", {})
                if billing_record:
                    st.divider()
                    st.markdown("##### Insurance Pre-Authorization Control")
                    current_bill_status = billing_record.get("status", "draft")
                    st.write(f"Current Pre-Authorization Status: **{current_bill_status.upper()}**")
                    
                    b_col1, b_col2, b_col3 = st.columns(3)
                    with b_col1:
                        if st.button("Approve Pre-Auth / Estimate", disabled=(current_bill_status == "approved")):
                            try:
                                if asyncio.run(approve_billing_status(encounter["id"], "approved")):
                                    st.success("Billing status approved. Encounter progresses to CLOSED.")
                                    st.rerun()
                                else:
                                    st.error("Failed to approve billing record.")
                            except Exception as err:
                                st.error(f"Error: {err}")
                    with b_col2:
                        if st.button("Mark as Submitted", disabled=(current_bill_status == "submitted")):
                            try:
                                if asyncio.run(approve_billing_status(encounter["id"], "submitted")):
                                    st.success("Billing status updated to submitted.")
                                    st.rerun()
                                else:
                                    st.error("Failed to submit billing.")
                            except Exception as err:
                                st.error(f"Error: {err}")
                    with b_col3:
                        if st.button("Dispute / Reject", disabled=(current_bill_status == "rejected")):
                            try:
                                if asyncio.run(approve_billing_status(encounter["id"], "rejected")):
                                    st.warning("Billing estimate rejected/disputed.")
                                    st.rerun()
                                else:
                                    st.error("Failed to reject billing.")
                            except Exception as err:
                                st.error(f"Error: {err}")

            with tab_followup:
                render_followup(state.get("followup", {}))
