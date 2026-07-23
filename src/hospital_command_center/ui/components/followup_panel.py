"""Streamlit display for follow-up agent output."""

from typing import Any

import streamlit as st


def render_followup(followup: dict[str, Any]) -> None:
    st.subheader("Follow-up Plan")
    if not followup:
        st.warning("No follow-up data available.")
        return

    if followup.get("notes"):
        st.info(followup["notes"])

    meds = followup.get("medication_reminders", [])
    if meds:
        st.markdown("#### Medication Reminders")
        for med in meds:
            priority_tag = ""
            if med.get("priority") == "high":
                priority_tag = "[High Priority] "
            elif med.get("priority") == "medium":
                priority_tag = "[Medium Priority] "
            
            times = ", ".join(med.get("times", []))
            st.write(
                f"{priority_tag}**{med.get('medication')}** — {med.get('dosage')}, "
                f"{med.get('frequency')} ({times})"
            )
            if med.get("notes"):
                st.caption(f"Note: {med['notes']}")

    labs = followup.get("lab_reminders", [])
    if labs:
        st.markdown("#### Lab Reminders")
        for lab in labs:
            fasting = "Fasting required" if lab.get("fasting_required") else "No fasting required"
            st.write(
                f"- **{lab.get('test')}** — due in {lab.get('due_in_days')} day(s). "
                f"{lab.get('instructions', '')}"
            )
            st.caption(fasting)

    diet = followup.get("diet_guidance")
    if diet:
        with st.expander("Diet & Hydration Guidance", expanded=True):
            if not diet.get("preferences_confirmed", False):
                st.warning(
                    "Dietary preference (veg/non-veg/vegan) and food allergies have not "
                    "been confirmed yet — meal-specific guidance is withheld until then."
                )
            st.write(diet.get("summary", ""))
            col1, col2 = st.columns(2)
            with col1:
                if diet.get("recommended"):
                    st.write("**Recommended:**")
                    for item in diet["recommended"]:
                        st.write(f"- {item}")
            with col2:
                if diet.get("avoid"):
                    st.write("**Avoid:**")
                    for item in diet["avoid"]:
                        st.write(f"- {item}")
            
            if diet.get("hydration_notes"):
                st.write(f"**Hydration:** {diet['hydration_notes']}")
            if diet.get("special_instructions"):
                st.info(f"Note: {diet['special_instructions']}")

    rules = followup.get("escalation_rules", [])
    if rules:
        st.markdown("#### Red Flags (Escalation)")
        for rule in rules:
            severity = rule.get("severity", "medium").upper()
            color = "red" if severity == "CRITICAL" else "orange" if severity == "HIGH" else "blue"
            line = (
                f":{color}[**{severity}**] — {rule.get('trigger')}  \n"
                f"**Action:** {rule.get('action')}"
            )
            if rule.get("notify_within"):
                line += f"  \n**Notify:** {rule['notify_within']}"
            if rule.get("notify_channels"):
                line += f" via {', '.join(rule['notify_channels'])}"
            st.markdown(line)

    schedule = followup.get("schedule", [])
    if schedule:
        with st.expander("Automated Care Timeline"):
            for task in schedule:
                status_label = "[Pending]" if task.get("status") == "pending" else "[Completed]"
                st.write(
                    f"{status_label} **{task.get('task_type').replace('_', ' ').title()}** via {task.get('channel')} "
                    f"— {task.get('note', '')}"
                )
