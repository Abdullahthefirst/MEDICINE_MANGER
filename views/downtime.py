from __future__ import annotations

from datetime import date, datetime, time

import streamlit as st

from core.db import insert_row, select_rows, try_action, update_rows
from core.helpers import clean_payload, options, reference, show_table
from ui.layout import page_header


def _report(user: dict) -> None:
    if user["role"] == "management_viewer":
        return
    customers = select_rows("customers", "id,hospital_name,branch_name,customer_code", order="hospital_name")
    if not customers:
        return
    labels, mapping = options(customers, ["hospital_name", "branch_name", "customer_code"])
    with st.expander("Report downtime"):
        with st.form("report_downtime"):
            customer_label = st.selectbox("Hospital", labels)
            category = st.selectbox("Category", ["equipment", "kit_component", "inventory_shortage", "delivery_delay", "quality_issue", "maintenance", "other"])
            title = st.text_input("Title")
            cause = st.text_area("Cause details")
            impact = st.text_area("Impact details")
            a, b = st.columns(2)
            start_date = a.date_input("Started date", value=date.today())
            start_time = b.time_input("Started time", value=datetime.now().time().replace(second=0, microsecond=0))
            ended = st.checkbox("Downtime has ended")
            end_date = a.date_input("Ended date", value=date.today(), disabled=not ended)
            end_time = b.time_input("Ended time", value=datetime.now().time().replace(second=0, microsecond=0), disabled=not ended)
            c, d, e = st.columns(3)
            patients = c.number_input("Patients affected", min_value=0, step=1)
            runs = d.number_input("Runs lost", min_value=0, step=1)
            delayed = e.number_input("Services delayed", min_value=0, step=1)
            kit_id = st.text_input("Kit unique ID (optional)")
            component = st.text_input("Component name (optional)")
            is_backdated = st.checkbox("This is a backdated entry")
            backdate_reason = st.text_area("Reason for late entry", disabled=not is_backdated)
            submitted = st.form_submit_button("Report downtime")
        if submitted:
            if not title or not cause:
                st.error("Title and cause details are required.")
                return
            if is_backdated and not backdate_reason.strip():
                st.error("A reason is required for backdated downtime.")
                return
            start_at = datetime.combine(start_date, start_time)
            end_at = datetime.combine(end_date, end_time) if ended else None
            payload = clean_payload({
                "customer_id": mapping[customer_label]["id"], "event_number": reference("DWN"),
                "downtime_category": category, "title": title.strip(), "cause_details": cause.strip(),
                "impact_details": impact.strip(), "kit_unique_id": kit_id.strip(),
                "component_name": component.strip(), "started_at": start_at, "ended_at": end_at,
                "patients_affected": patients, "runs_lost": runs, "services_delayed": delayed,
                "status": "reported", "reported_by": user["id"], "is_backdated": is_backdated,
                "backdate_reason": backdate_reason.strip(), "admin_alerted": is_backdated,
            })
            if try_action(lambda: insert_row("downtime_events", payload), "Downtime reported."):
                st.rerun()


def _update(user: dict, events: list[dict]) -> None:
    if user["role"] not in ("admin", "hospital_staff", "warehouse_staff") or not events:
        return
    labels, mapping = options(events, ["event_number", "title", "status"])
    with st.expander("Update or resolve downtime"):
        with st.form("update_downtime"):
            label = st.selectbox("Event", labels)
            statuses = ["investigating", "action_required", "resolved", "reopened"]
            if user["role"] == "admin":
                statuses += ["verified", "closed"]
            status = st.selectbox("New status", statuses)
            resolution = st.text_area("Resolution details")
            corrective = st.text_area("Corrective action")
            preventive = st.text_area("Preventive action")
            mark_ended = st.checkbox("Set end time to now")
            submitted = st.form_submit_button("Update downtime")
        if submitted:
            event = mapping[label]
            payload = clean_payload({
                "status": status, "resolution_details": resolution.strip(),
                "corrective_action": corrective.strip(), "preventive_action": preventive.strip(),
            })
            if mark_ended:
                payload["ended_at"] = datetime.now().isoformat()
            if status == "resolved":
                payload.update({"resolved_by": user["id"], "resolved_at": datetime.now().isoformat()})
            if status in ("verified", "closed"):
                payload.update({"verified_by": user["id"], "verified_at": datetime.now().isoformat()})
            if try_action(lambda: update_rows("downtime_events", payload, [("id", "eq", event["id"])]), "Downtime updated."):
                st.rerun()


def render(user: dict) -> None:
    page_header("Downtime", "Each event retains its cause, duration, impact and resolution history")
    try:
        _report(user)
        events = select_rows("downtime_event_details", order="started_at", desc=True, limit=250)
        _update(user, events)
        monthly = select_rows("customer_monthly_downtime", order="month_start", desc=True)
    except Exception as exc:
        st.error(f"Downtime data could not be loaded: {exc}")
        return
    tabs = st.tabs(["Detailed events", "Monthly totals"])
    with tabs[0]:
        show_table(events, {
            "event_number": "Event", "title": "Title", "downtime_category": "Category",
            "cause_details": "Cause", "impact_details": "Impact", "started_at": "Started",
            "ended_at": "Ended", "duration_hours": "Hours", "patients_affected": "Patients",
            "runs_lost": "Runs lost", "services_delayed": "Services delayed", "status": "Status",
            "resolution_details": "Resolution", "corrective_action": "Corrective action",
            "preventive_action": "Preventive action", "is_backdated": "Backdated",
        })
    with tabs[1]:
        show_table(monthly, {
            "hospital_name": "Hospital", "branch_name": "Branch", "month_start": "Month",
            "downtime_events": "Events", "downtime_hours": "Hours",
        })
