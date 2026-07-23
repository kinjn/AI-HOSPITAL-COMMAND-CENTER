"""Patient symptom intake form simulation: runs LLM triage and routing workflows."""

import asyncio
from uuid import UUID

import streamlit as st

from hospital_command_center.core.exceptions import HospitalCommandCenterError
from hospital_command_center.core.validation import validate_patient_name, validate_phone
from hospital_command_center.db.session import get_session_factory
from hospital_command_center.domain.intake import IntakeChannel, IntakeSubmission
from hospital_command_center.domain.triage import TriageClarificationSubmission
from hospital_command_center.services.workflow_service import WorkflowService
from hospital_command_center.ui.components.billing_panel import render_billing
from hospital_command_center.ui.components.followup_panel import render_followup
from hospital_command_center.ui.components.navbar import render_navbar
from hospital_command_center.ui.components.routing_panel import render_routing
from hospital_command_center.ui.components.triage_panel import render_triage

st.set_page_config(
    page_title="Symptom Intake Simulator | Hospital Command Center",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

render_navbar("nav_intake")


async def _submit_intake(payload: IntakeSubmission) -> dict:
    factory = get_session_factory()
    async with factory() as session:
        return await WorkflowService().start_from_intake(session, payload)


async def _continue_triage(encounter_id: str, answers: list[str]) -> dict:
    factory = get_session_factory()
    async with factory() as session:
        return await WorkflowService().continue_triage(
            session,
            UUID(encounter_id),
            TriageClarificationSubmission(answers=answers),
        )


def _store_workflow_result(result: dict, *, name: str, age: int, gender: str, phone: str) -> None:
    st.session_state["last_workflow"] = result
    st.session_state["patient_info"] = {
        "name": name,
        "age": age,
        "gender": gender,
        "mobile": phone,
    }
    st.session_state["selected_encounter_id"] = result["encounter"]["id"]

    triage = (result.get("workflow_state") or {}).get("triage") or {}
    if result.get("awaiting_triage_clarification"):
        st.session_state["triage_pending"] = {
            "encounter_id": result["encounter"]["id"],
            "questions": triage.get("clarifying_questions", []),
        }
    else:
        st.session_state.pop("triage_pending", None)

st.subheader("Patient Intake & AI Workflow Simulator")

# Test Templates to click and populate fields immediately
st.subheader("Load Test Templates")
template_col1, template_col2, template_col3, template_col4, template_col5 = st.columns(5)

with template_col1:
    if st.button("Critical: Chest Pain"):
        st.session_state["tmp_name"] = "John Miller"
        st.session_state["tmp_age"] = 62
        st.session_state["tmp_gender"] = "Male"
        st.session_state["tmp_phone"] = "9876543210"
        st.session_state["tmp_symptoms"] = "Sudden severe squeezing chest pain spreading to left shoulder and jaw, cold sweat, short of breath for 20 minutes."
        st.session_state["tmp_channel"] = "mobile_app"
        st.rerun()

with template_col2:
    if st.button("Low: Mild Cough"):
        st.session_state["tmp_name"] = "Emma Watson"
        st.session_state["tmp_age"] = 28
        st.session_state["tmp_gender"] = "Female"
        st.session_state["tmp_phone"] = "9123456789"
        st.session_state["tmp_symptoms"] = "Slight dry cough and tickly throat for 2 days. No fever, no body ache, breathing is normal. Just need advice on cough syrup."
        st.session_state["tmp_channel"] = "whatsapp"
        st.rerun()

with template_col3:
    if st.button("Medium: Stomach Ache"):
        st.session_state["tmp_name"] = "Raj Patel"
        st.session_state["tmp_age"] = 45
        st.session_state["tmp_gender"] = "Male"
        st.session_state["tmp_phone"] = "9876543210"
        st.session_state["tmp_symptoms"] = "Dull abdominal pain around the belly button, mild nausea. Started last night after having seafood dinner. Pain scale 4/10."
        st.session_state["tmp_channel"] = "web"
        st.rerun()

with template_col4:
    if st.button("High: Fever & Rash"):
        st.session_state["tmp_name"] = "Alice Smith"
        st.session_state["tmp_age"] = 9
        st.session_state["tmp_gender"] = "Female"
        st.session_state["tmp_phone"] = "9988776655"
        st.session_state["tmp_symptoms"] = "High fever (102.5F) for 24 hours, red spotty rash spreading on the chest, lethargy, complains of sore throat and earache."
        st.session_state["tmp_channel"] = "web"
        st.rerun()

with template_col5:
    if st.button("Vague: Not feeling well"):
        st.session_state["tmp_name"] = "Sam Lee"
        st.session_state["tmp_age"] = 34
        st.session_state["tmp_gender"] = "Other"
        st.session_state["tmp_phone"] = "9012345678"
        st.session_state["tmp_symptoms"] = "I don't feel well."
        st.session_state["tmp_channel"] = "web"
        st.rerun()

st.divider()

# Input Form
col_form, col_guidelines = st.columns([7, 4])

with col_form:
    st.subheader("Patient Admission Intake Form")
    
    # Retrieve template data or set defaults
    d_name = st.session_state.get("tmp_name", "")
    d_age = st.session_state.get("tmp_age", 35)
    d_gender = st.session_state.get("tmp_gender", "Male")
    d_phone = st.session_state.get("tmp_phone", "")
    d_symptoms = st.session_state.get("tmp_symptoms", "")
    d_channel_val = st.session_state.get("tmp_channel", "web")
    
    # Render input fields
    name = st.text_input(
        "Patient Full Name *",
        value=d_name,
        placeholder="e.g. Ravi Kumar",
        help="Enter first and last name using letters only.",
    )
    
    col_a, col_g = st.columns(2)
    with col_a:
        age = st.slider("Patient Age", 1, 110, int(d_age))
    with col_g:
        gender = st.selectbox("Gender", ["Male", "Female", "Other"], index=["Male", "Female", "Other"].index(d_gender))
        
    phone = st.text_input(
        "Mobile Number *",
        value=d_phone,
        placeholder="10-digit number, e.g. 9876543210",
        help="Enter a valid 10-digit mobile number. Optional +91 prefix is accepted.",
    )

    st.markdown("**Dietary & Clinical Background** _(optional, but needed before diet guidance can be given)_")
    col_diet, col_allergy = st.columns(2)
    with col_diet:
        dietary_preference = st.selectbox(
            "Dietary Preference",
            ["Not specified", "Vegetarian", "Non-vegetarian", "Vegan", "Eggetarian", "Other"],
            help="Used by the follow-up agent to give safe, relevant meal guidance.",
        )
    with col_allergy:
        food_allergies = st.text_input(
            "Known Food Allergies",
            placeholder="e.g. peanuts, shellfish (leave blank if none)",
        )
    known_medical_conditions = st.text_input(
        "Pre-existing Medical Conditions",
        placeholder="e.g. Type 2 diabetes, hypertension (leave blank if none)",
        help="Passed to the medical summarizer as prior clinical context.",
    )

    # Channel selection
    channel_opts = {
        "web": "Web Portal Intake",
        "mobile_app": "Mobile Health App Simulation",
        "whatsapp": "WhatsApp Webhook Simulation"
    }
    channel_list = list(channel_opts.keys())
    channel = st.selectbox(
        "Simulation Channel / Adapter *",
        options=channel_list,
        format_func=lambda x: channel_opts[x],
        index=channel_list.index(d_channel_val)
    )
    
    symptoms = st.text_area("Describe Symptoms / Clinical Complaint *", value=d_symptoms, height=120)
    
    if st.button("Submit to CommandCenter Workflow", use_container_width=True):
        validation_errors: list[str] = []

        if not symptoms.strip():
            validation_errors.append("Please describe symptoms before submitting.")

        try:
            validated_name = validate_patient_name(name)
        except ValueError as exc:
            validation_errors.append(str(exc))

        try:
            validated_phone = validate_phone(phone)
        except ValueError as exc:
            validation_errors.append(str(exc))

        if validation_errors:
            for message in validation_errors:
                st.error(message)
        else:
            try:
                with st.spinner("Initializing workflow (loading histories, running AI agents triage/routing/billing/reminders)..."):
                    payload = IntakeSubmission(
                        channel=IntakeChannel(channel),
                        symptoms=symptoms.strip(),
                        patient_name=validated_name,
                        age=age,
                        gender=gender,
                        phone=validated_phone,
                        dietary_preference=(
                            dietary_preference if dietary_preference != "Not specified" else None
                        ),
                        food_allergies=food_allergies.strip() or None,
                        known_medical_conditions=known_medical_conditions.strip() or None,
                    )
                    result = asyncio.run(_submit_intake(payload))
                    _store_workflow_result(
                        result,
                        name=validated_name,
                        age=age,
                        gender=gender,
                        phone=validated_phone,
                    )

                if result.get("awaiting_triage_clarification"):
                    st.warning(
                        "Triage needs more detail. Answer the clarifying questions below "
                        "(up to 2) to continue the workflow."
                    )
                else:
                    st.success("Intake successfully logged to SQLite and AI processing is complete.")
            except HospitalCommandCenterError as exc:
                st.error(f"Execution Error: {exc}")
            except Exception as e:
                st.error(f"Unexpected Database / API Error: {e}")

with col_guidelines:
    st.subheader("Simulated Agent Pipeline")
    st.markdown("""
    When you submit symptoms:
    - **Load patient history**: Looks up any previous records for this phone number and name, building past patient clinical history.
    - **Triage LLM**: Analyzes severity and may ask up to 2 clarifying questions when symptoms are vague.
    - **Pathway Router**: Chooses care pathways based on urgency.
    - **Medical Summarizer**: Synthesizes the clinical file and creates doctor briefings in SOAP notes format.
    - **Billing & Pre-Auth Agent**: Formulates CPT/ICD-10 clinical codes and requests insurance estimates.
    - **Follow-up Reminders**: Creates medication reminders, red flags warnings, and follow-up schedules.
    """)

triage_pending = st.session_state.get("triage_pending")
if triage_pending:
    st.divider()
    st.subheader("Triage clarifying questions")
    st.caption("The triage agent needs a bit more detail before routing and billing can run.")

    questions = triage_pending.get("questions") or []
    answers: list[str] = []
    for idx, question in enumerate(questions):
        st.markdown(f"**{idx + 1}. {question}**")
        answers.append(
            st.text_input(f"Your answer #{idx + 1}", key=f"triage_answer_{idx}")
        )

    if st.button("Submit answers and continue workflow", use_container_width=True):
        if not all(a.strip() for a in answers):
            st.error("Please answer all clarifying questions.")
        else:
            try:
                patient_info = st.session_state.get("patient_info", {})
                with st.spinner("Re-running triage and completing the workflow..."):
                    result = asyncio.run(
                        _continue_triage(
                            triage_pending["encounter_id"],
                            [a.strip() for a in answers],
                        )
                    )
                    _store_workflow_result(
                        result,
                        name=patient_info.get("name", ""),
                        age=patient_info.get("age", 0),
                        gender=patient_info.get("gender", ""),
                        phone=patient_info.get("mobile", ""),
                    )
                if result.get("awaiting_triage_clarification"):
                    st.warning("Triage still needs more detail. Please answer the new questions.")
                else:
                    st.success("Triage complete — workflow finished.")
                st.rerun()
            except HospitalCommandCenterError as exc:
                st.error(f"Execution Error: {exc}")
            except Exception as e:
                st.error(f"Unexpected Database / API Error: {e}")

# Output displays
workflow = st.session_state.get("last_workflow")
if workflow:
    patient_data = st.session_state.get("patient_info", {})
    encounter = workflow.get("encounter", {})
    state = workflow.get("workflow_state", {})
    db_patient = workflow.get("patient", {})

    st.write("")
    st.divider()
    
    st.subheader("Live Workflow Result Summary")
    
    # Navigation shortcuts
    nav_col1, nav_col2 = st.columns(2)
    with nav_col1:
        if st.button("View this Encounter on Dashboard"):
            st.switch_page("pages/dashboard.py")
    with nav_col2:
        if st.button("View full Diagnostics detail"):
            st.switch_page("pages/encounter_detail.py")
            
    st.write("")

    col_res1, col_res2 = st.columns(2)
    
    with col_res1:
        st.markdown("#### Patient Identity & Encounter info")
        st.write(f"**Patient Name:** {patient_data.get('name')} · **Age/Gender:** {patient_data.get('age')} · {patient_data.get('gender')}")
        st.write(f"**Patient DB ID:** `{db_patient.get('id', '—')}`")
        st.write(f"**Encounter ID:** `{encounter.get('id', '—')}`")
        st.write(f"**Encounter DB Status:** `{encounter.get('status', '—')}`")
        st.write(f"**Symptoms Details:** *{encounter.get('symptoms', '—')}*")

        history = workflow.get("patient_history_used")
        if history:
            with st.expander("Extracted Patient History used in LLM Triage"):
                st.text(history)
                
        # 3. Medical summary
        summary = state.get("medical_summary", {})
        if summary:
            with st.expander("AI Case Summary & SOAP Notes", expanded=True):
                st.write(summary.get("case_summary", ""))
                if summary.get("suggested_tests"):
                    st.write("**Suggested Tests:** " + ", ".join(summary["suggested_tests"]))
                if summary.get("doctor_briefing"):
                    st.markdown("**Doctor SOAP Briefing:**")
                    st.text(summary["doctor_briefing"])

    with col_res2:
        # Render panel visuals
        render_triage(state.get("triage", {}))
        render_routing(state.get("routing", {}))
        render_billing(state.get("billing", {}))
        render_followup(state.get("followup", {}))
