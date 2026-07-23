"""Streamlit main application entry - AI Hospital Command Center Dashboard."""

import asyncio

import streamlit as st

from hospital_command_center.core.config import get_settings
from hospital_command_center.ui.components.navbar import render_navbar
from hospital_command_center.ui.db_helper import fetch_dashboard_stats, fetch_encounters

settings = get_settings()

st.set_page_config(
    page_title=settings.app_name,
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

render_navbar("nav_home")

# Custom CSS for gorgeous styling
st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6;
    }
    .metric-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border-left: 5px solid #4F46E5;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px rgba(0, 0, 0, 0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1F2937;
        margin-bottom: 5px;
    }
    .metric-label {
        font-size: 0.875rem;
        font-weight: 500;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .status-badge {
        padding: 4px 8px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# App header
st.subheader("Executive Command Center Overview")

# Fetch dashboard stats
try:
    stats = asyncio.run(fetch_dashboard_stats())
except Exception as e:
    st.error(f"Error fetching database stats: {e}")
    stats = {
        "total_encounters": 0,
        "active_encounters": 0,
        "critical_cases": 0,
        "pathway_counts": {},
        "total_billing_est": 0.0
    }

# Top metrics row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f'<div class="metric-card" style="border-left-color: #4F46E5;">'
        f'<div class="metric-label">Total Submissions</div>'
        f'<div class="metric-value">{stats["total_encounters"]}</div>'
        f'<div style="font-size: 0.8rem; color: #10B981;">Processed by AI Workflow</div>'
        f'</div>',
        unsafe_allow_html=True
    )

with col2:
    # Use color alert (orange/red) for critical queue
    crit_color = "#EF4444" if stats["critical_cases"] > 0 else "#10B981"
    st.markdown(
        f'<div class="metric-card" style="border-left-color: {crit_color};">'
        f'<div class="metric-label">Critical / Urgent Queue</div>'
        f'<div class="metric-value" style="color: {crit_color};">{stats["critical_cases"]}</div>'
        f'<div style="font-size: 0.8rem; color: #6B7280;">Requires immediate attention</div>'
        f'</div>',
        unsafe_allow_html=True
    )

with col3:
    st.markdown(
        f'<div class="metric-card" style="border-left-color: #F59E0B;">'
        f'<div class="metric-label">Active / Open Cases</div>'
        f'<div class="metric-value" style="color: #F59E0B;">{stats["active_encounters"]}</div>'
        f'<div style="font-size: 0.8rem; color: #6B7280;">Pending discharge/follow-up</div>'
        f'</div>',
        unsafe_allow_html=True
    )

with col4:
    st.markdown(
        f'<div class="metric-card" style="border-left-color: #10B981;">'
        f'<div class="metric-label">AI Estimated Revenue</div>'
        f'<div class="metric-value">₹{stats["total_billing_est"]:,.2f}</div>'
        f'<div style="font-size: 0.8rem; color: #6B7280;">Pre-Auth & cost breakdowns</div>'
        f'</div>',
        unsafe_allow_html=True
    )

st.write("")
st.divider()

# Quick Actions & Guidance Section
st.subheader("Quick Launchpad")
la1, la2, la3 = st.columns(3)

with la1:
    st.info("**Intake Patient Symptoms**\n\nSimulate patient channels (Web, App, WhatsApp) and run the automated multi-agent workflow (Triage -> Routing -> Summarization -> Billing -> Follow-up).")
    if st.button("Open Intake Form", key="btn_intake"):
        st.switch_page("pages/intake.py")

with la2:
    st.success("**Operations Dashboard**\n\nMonitor patient lists, triage urgency levels, care pathways, and current statuses. Perform manual pathway overrides or review cases.")
    if st.button("Open Dashboard", key="btn_dashboard"):
        st.switch_page("pages/dashboard.py")

with la3:
    st.warning("**Encounter Detail Viewer**\n\nDrill down into any specific patient encounter to inspect LLM triage rationale, medical briefings, itemized bills, and automated reminders.")
    if st.button("Open Detail Viewer", key="btn_detail"):
        st.switch_page("pages/encounter_detail.py")

# Show recent active encounters
st.write("")
st.subheader("Recent Active Encounters Queue")

try:
    recent_encounters = asyncio.run(fetch_encounters(limit=5))
except Exception as e:
    recent_encounters = []
    st.error(f"Error loading queue: {e}")

if recent_encounters:
    # Build a clean dataframe or metric cards
    for idx, e in enumerate(recent_encounters):
        urg_color = "red" if e["urgency"] in ["critical", "high"] else "orange" if e["urgency"] == "medium" else "green"
        stat_color = "blue" if e["status"] != "closed" else "green"
        
        pathway_label = e["pathway"] or "Not routed"
        if pathway_label == "teleconsult":
            pathway_label = "Teleconsultation"
        elif pathway_label == "specialist":
            pathway_label = "Specialist Referral"
        else:
            pathway_label = pathway_label.upper()

        with st.container():
            col_info, col_status, col_btn = st.columns([6, 3, 2])
            with col_info:
                st.markdown(f"**Patient:** {e['patient_name']} ({e['patient_gender'].title()}) · **Urgency:** :{urg_color}[{e['urgency'].upper()}]")
                st.markdown(f"**Symptoms:** *{e['symptoms']}*")
            with col_status:
                st.markdown(f"**Pathway:** {pathway_label}")
                st.markdown(f"**Status:** :{stat_color}[{e['status'].upper()}] · Channel: `{e['source_channel']}`")
            with col_btn:
                # Add action to view details
                if st.button("View Detail", key=f"view_rec_{e['id']}"):
                    st.session_state["selected_encounter_id"] = e["id"]
                    # Also write it to session state last_workflow compatible if we need to
                    try:
                        detail = asyncio.run(fetch_encounter_by_id(e["id"]))
                        if detail:
                            st.session_state["last_workflow"] = detail["workflow_state"]
                            st.session_state["patient_info"] = detail["patient"]
                    except Exception:
                        pass
                    st.switch_page("pages/encounter_detail.py")
            st.divider()
else:
    st.info("No active encounters in database. Use the Symptom Intake Form to submit a patient.")
