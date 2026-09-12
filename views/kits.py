from __future__ import annotations

from datetime import datetime

import streamlit as st

from core.db import insert_row, select_rows, try_action, update_rows
from core.helpers import clean_payload, options, reference, show_table
from ui.layout import page_header


def _report_issue(user: dict) -> None:
    if user["role"] == "management_viewer":
        return
    kits = select_rows("individual_kits", "id,kit_identifier,kit_definition_id,status", order="created_at", desc=True)
    customers = select_rows("customers", "id,hospital_name,branch_name,customer_code", order="hospital_name")
    components = select_rows("inventory_items", "id,item_name,item_code,manufacturer_cat_number", [("item_type", "eq", "kit_component")], order="item_name")
    if not kits or not customers:
        return
    kit_labels, kit_map = options(kits, ["kit_identifier", "status"])
    customer_labels, customer_map = options(customers, ["hospital_name", "branch_name", "customer_code"])
    component_labels, component_map = options(components, ["item_name", "manufacturer_cat_number"])
    with st.expander("Report kit component issue"):
        with st.form("report_component_issue"):
            kit_label = st.selectbox("Unique kit", kit_labels)
            customer_label = st.selectbox("Affected hospital", customer_labels)
            component_label = st.selectbox("Component", ["Not specified", *component_labels])
            a, b, c = st.columns(3)
            issue_type = a.selectbox("Issue type", ["missing", "damaged", "defective", "expired", "insufficient_quantity", "incorrect_component", "other"])
            severity = b.selectbox("Severity", ["low", "medium", "high", "critical"], index=1)
            runs = c.number_input("Runs affected", min_value=0, step=1)
            details = st.text_area("Issue details")
            submitted = st.form_submit_button("Report issue")
        if submitted:
            if not details.strip():
                st.error("Issue details are required.")
                return
            component = component_map.get(component_label)
            payload = clean_payload({
                "issue_number": reference("ISS"), "individual_kit_id": kit_map[kit_label]["id"],
                "component_item_id": component["id"] if component else None,
                "customer_id": customer_map[customer_label]["id"], "issue_type": issue_type,
                "severity": severity, "runs_affected": runs, "issue_details": details.strip(),
                "status": "reported", "reported_by": user["id"],
            })
            if try_action(lambda: insert_row("component_issues", payload), "Component issue reported."):
                st.rerun()


def _action(user: dict, issues: list[dict]) -> None:
    if user["role"] not in ("admin", "hospital_staff", "warehouse_staff") or not issues:
        return
    labels, mapping = options(issues, ["issue_number", "issue_type", "status"])
    with st.expander("Add resolution action"):
        with st.form("issue_action"):
            label = st.selectbox("Issue", labels)
            action_type = st.selectbox("Action", ["investigation", "component_supplied", "component_transferred", "component_replaced", "kit_replaced", "kit_quarantined", "vendor_claim", "data_corrected", "other"])
            details = st.text_area("Action details")
            quantity = st.number_input("Quantity involved (optional)", min_value=0.0, step=1.0)
            evidence = st.text_input("Evidence URL (optional)")
            submitted = st.form_submit_button("Add action")
        if submitted:
            if not details.strip():
                st.error("Action details are required.")
                return
            payload = clean_payload({
                "component_issue_id": mapping[label]["id"], "action_type": action_type,
                "action_details": details.strip(), "quantity": quantity or None,
                "evidence_url": evidence.strip(), "performed_by": user["id"],
            })
            if try_action(lambda: insert_row("component_issue_actions", payload), "Action added to issue history."):
                st.rerun()


def _change_status(user: dict, issues: list[dict]) -> None:
    if user["role"] not in ("admin", "hospital_staff", "warehouse_staff") or not issues:
        return
    labels, mapping = options(issues, ["issue_number", "issue_type", "status"])
    with st.expander("Resolve or verify issue"):
        with st.form("issue_status"):
            label = st.selectbox("Issue", labels, key="status_issue")
            statuses = ["investigating", "action_required", "resolved", "reopened"]
            if user["role"] == "admin":
                statuses += ["verified", "closed"]
            status = st.selectbox("New status", statuses)
            resolution = st.text_area("Resolution details")
            submitted = st.form_submit_button("Update status")
        if submitted:
            payload = {"status": status, "resolution_details": resolution.strip() or None}
            if status == "resolved":
                payload.update({"resolved_by": user["id"], "resolved_at": datetime.now().isoformat()})
            if status in ("verified", "closed"):
                payload.update({"verified_by": user["id"], "verified_at": datetime.now().isoformat()})
            if try_action(lambda: update_rows("component_issues", payload, [("id", "eq", mapping[label]["id"])]), "Issue status updated."):
                st.rerun()


def _record_runs(user: dict) -> None:
    if user["role"] not in ("admin", "hospital_staff"):
        return
    kits = select_rows("kit_run_balances", filters=[("runs_remaining", "gt", 0)], order="kit_identifier")
    usage = select_rows("customer_usage", "id,usage_number,usage_date", order="usage_date", desc=True, limit=100)
    if not kits or not usage:
        return
    kit_labels, kit_map = options(kits, ["kit_identifier", "kit_name", "runs_remaining"])
    usage_labels, usage_map = options(usage, ["usage_number", "usage_date"])
    with st.expander("Record kit runs used"):
        with st.form("kit_usage"):
            kit_label = st.selectbox("Kit", kit_labels)
            usage_label = st.selectbox("Customer usage", usage_labels)
            runs = st.number_input("Runs used", min_value=1, step=1)
            submitted = st.form_submit_button("Record runs")
        if submitted:
            payload = {
                "individual_kit_id": kit_map[kit_label]["individual_kit_id"],
                "customer_usage_id": usage_map[usage_label]["id"],
                "runs_used": runs, "created_by": user["id"],
            }
            if try_action(lambda: insert_row("kit_usage", payload), "Kit runs recorded."):
                st.rerun()


def render(user: dict) -> None:
    page_header("Kit issues", "Unique-kit runs, component errors and verified resolution history")
    try:
        _report_issue(user)
        issues = select_rows("component_issues", order="reported_at", desc=True, limit=250)
        _action(user, issues)
        _change_status(user, issues)
        _record_runs(user)
        actions = select_rows("component_issue_actions", order="performed_at", desc=True, limit=250)
        balances = select_rows("kit_run_balances", order="kit_identifier")
    except Exception as exc:
        st.error(f"Kit data could not be loaded: {exc}")
        return
    tabs = st.tabs([
        "⚠️ Issues",
        "🛠️ Resolution history",
        "🧪 Kit run balances",
    ])
    with tabs[0]:
        show_table(issues, {
            "issue_number": "Issue", "issue_type": "Type", "severity": "Severity",
            "runs_affected": "Runs affected", "issue_details": "Details", "status": "Status",
            "resolution_details": "Resolution", "reported_at": "Reported", "resolved_at": "Resolved",
        })
    with tabs[1]:
        show_table(actions, {
            "component_issue_id": "Issue ID", "action_type": "Action", "action_details": "Details",
            "quantity": "Quantity", "performed_at": "Performed", "evidence_url": "Evidence",
        })
    with tabs[2]:
        show_table(balances, {
            "kit_identifier": "Unique kit", "kit_name": "Kit", "runs_per_kit": "Total runs",
            "runs_used": "Used", "runs_remaining": "Remaining", "status": "Status",
        })
