from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from core.auth import get_client
from core.db import insert_row, select_rows, try_action, update_rows
from core.helpers import clean_payload, options, show_table
from ui.layout import page_header


def _contract_services(user: dict) -> None:
    contracts = select_rows("contracts", "id,contract_number,customer_id", order="start_date", desc=True)
    if not contracts:
        return
    labels, mapping = options(contracts, ["contract_number"])
    with st.form("add_contract_service"):
        contract_label = st.selectbox("Contract", labels)
        a, b = st.columns(2)
        code = a.text_input("Service code")
        name = b.text_input("Service name")
        unit = a.text_input("Billing unit", value="service")
        price = b.number_input("Unit price", min_value=0.0, step=1000.0)
        submitted = st.form_submit_button("Add contract service")
    if submitted:
        payload = {
            "contract_id": mapping[contract_label]["id"], "service_code": code.strip().upper(),
            "service_name": name.strip(), "billing_unit": unit.strip(), "unit_price": price,
        }
        if try_action(lambda: insert_row("contract_services", payload), "Contract service added."):
            st.rerun()


def _inventory_item(user: dict) -> None:
    with st.form("add_inventory_item"):
        a, b = st.columns(2)
        code = a.text_input("Internal item code")
        name = b.text_input("Item name")
        item_type = a.selectbox("Type", ["consumable", "kit", "kit_component", "material"])
        unit = b.text_input("Unit", value="piece")
        manufacturer = a.text_input("Manufacturer catalogue number (optional)")
        origin = b.selectbox("Origin", ["Unknown", "local", "international", "both"])
        runs = a.number_input("Runs per unit (optional)", min_value=0.0, step=0.1)
        reorder = b.number_input("Reorder level", min_value=0.0, step=1.0)
        submitted = st.form_submit_button("Add inventory item")
    if submitted:
        payload = clean_payload({
            "item_code": code.strip().upper(), "item_name": name.strip(), "item_type": item_type,
            "unit": unit.strip(), "manufacturer_cat_number": manufacturer.strip(),
            "origin": None if origin == "Unknown" else origin, "runs_per_unit": runs or None,
            "reorder_level": reorder,
        })
        if try_action(lambda: insert_row("inventory_items", payload), "Inventory item added."):
            st.rerun()

    items = select_rows("inventory_items", "id,item_code,item_name,manufacturer_cat_number", order="item_name")
    if items:
        labels, mapping = options(items, ["item_name", "item_code"])
        with st.form("update_cat_number"):
            label = st.selectbox("Item to update", labels)
            number = st.text_input("Manufacturer catalogue number")
            submitted = st.form_submit_button("Update catalogue number")
        if submitted:
            if try_action(
                lambda: update_rows("inventory_items", {"manufacturer_cat_number": number.strip() or None}, [("id", "eq", mapping[label]["id"])]),
                "Manufacturer catalogue number updated.",
            ):
                st.rerun()


def _kits(user: dict) -> None:
    left, right = st.columns(2)
    with left:
        with st.form("kit_definition"):
            name = st.text_input("Kit definition name")
            runs = st.number_input("Runs per kit", min_value=1, step=1)
            submitted = st.form_submit_button("Add kit definition")
        if submitted:
            if try_action(lambda: insert_row("kit_definitions", {"kit_name": name.strip().upper(), "runs_per_kit": runs}), "Kit definition added."):
                st.rerun()
    definitions = select_rows("kit_definitions", "id,kit_name,runs_per_kit", order="kit_name")
    batches = select_rows("inventory_batches", "id,item_id,lot_number,expiry_date", order="created_at", desc=True)
    if definitions:
        labels, mapping = options(definitions, ["kit_name", "runs_per_kit"])
        with right:
            with st.form("individual_kit"):
                identifier = st.text_input("Unique kit identifier")
                definition_label = st.selectbox("Kit definition", labels)
                batch_labels, batch_map = options(batches, ["lot_number", "expiry_date"]) if batches else ([], {})
                batch_label = st.selectbox("Inventory batch (recommended)", ["Not linked", *batch_labels])
                received = st.date_input("Received date", value=date.today())
                expiry = st.date_input("Expiry date", value=date.today())
                submitted = st.form_submit_button("Register unique kit")
            if submitted:
                payload = clean_payload({
                    "kit_identifier": identifier.strip(), "kit_definition_id": mapping[definition_label]["id"],
                    "inventory_batch_id": batch_map.get(batch_label, {}).get("id"),
                    "received_date": received, "expiry_date": expiry, "status": "available",
                })
                if try_action(lambda: insert_row("individual_kits", payload), "Unique kit registered."):
                    st.rerun()

    components = select_rows(
        "inventory_items", "id,item_code,item_name,manufacturer_cat_number,unit",
        [("item_type", "eq", "kit_component")], order="item_name",
    )
    if definitions and components:
        definition_labels, definition_map = options(definitions, ["kit_name"])
        component_labels, component_map = options(components, ["item_name", "manufacturer_cat_number"])
        with st.expander("Add or update a kit component requirement"):
            with st.form("kit_component_requirement"):
                definition_label = st.selectbox("Kit", definition_labels)
                component_label = st.selectbox("Component", component_labels)
                has_quantity = st.checkbox("Quantity is confirmed")
                quantity = st.number_input("Required quantity", min_value=0.001, step=1.0, disabled=not has_quantity)
                notes = st.text_input("Notes", value="Quantity to be confirmed")
                submitted = st.form_submit_button("Save component requirement")
            if submitted:
                payload = {
                    "kit_definition_id": definition_map[definition_label]["id"],
                    "component_item_id": component_map[component_label]["id"],
                    "quantity_required": quantity if has_quantity else None,
                    "notes": notes.strip() or None,
                }
                if try_action(
                    lambda: get_client().table("kit_component_requirements").upsert(
                        payload, on_conflict="kit_definition_id,component_item_id"
                    ).execute(),
                    "Kit component requirement saved.",
                ):
                    st.rerun()


def _users(user: dict) -> None:
    profiles = select_rows("profiles", "id,full_name,role,is_active", order="full_name")
    locations = select_rows("stock_locations", "id,location_name,location_type", order="location_name")
    with st.expander("Register an existing Supabase Auth user"):
        with st.form("register_profile"):
            auth_id = st.text_input("Auth user UUID")
            full_name = st.text_input("Full name")
            role = st.selectbox("Role", ["hospital_staff", "warehouse_staff", "management_viewer", "admin"])
            submitted = st.form_submit_button("Create application profile")
        if submitted:
            payload = {"id": auth_id.strip(), "full_name": full_name.strip(), "role": role, "is_active": True}
            if try_action(lambda: insert_row("profiles", payload), "Application profile created."):
                st.rerun()
    show_table(profiles, {"full_name": "Name", "role": "Role", "is_active": "Active", "id": "Auth user UUID"})
    st.caption("Create authentication users in Supabase first, then insert their profile with the same UUID.")
    if profiles and locations:
        profile_labels, profile_map = options(profiles, ["full_name", "role"])
        location_labels, location_map = options(locations, ["location_name", "location_type"])
        with st.form("assign_location"):
            profile_label = st.selectbox("User", profile_labels)
            location_label = st.selectbox("Location", location_labels)
            submitted = st.form_submit_button("Assign location")
        if submitted:
            payload = {"user_id": profile_map[profile_label]["id"], "location_id": location_map[location_label]["id"]}
            if try_action(lambda: get_client().table("user_location_access").upsert(payload, on_conflict="user_id,location_id").execute(), "Location assigned."):
                st.rerun()


def _backdates(user: dict) -> None:
    requests = select_rows("backdate_requests", order="requested_at", desc=True)
    show_table(requests, {"request_type": "Type", "requested_event_date": "Event date", "reason": "Reason", "status": "Status", "requested_at": "Requested"})
    pending = [row for row in requests if row["status"] == "pending"]
    if pending:
        labels, mapping = options(pending, ["request_type", "requested_event_date", "reason"])
        with st.form("review_backdate"):
            label = st.selectbox("Pending request", labels)
            decision = st.selectbox("Decision", ["approved", "rejected"])
            notes = st.text_area("Review notes")
            submitted = st.form_submit_button("Save decision")
        if submitted:
            payload = {"status": decision, "reviewed_by": user["id"], "reviewed_at": pd.Timestamp.now().isoformat(), "review_notes": notes.strip() or None}
            if try_action(lambda: update_rows("backdate_requests", payload, [("id", "eq", mapping[label]["id"])]), "Request reviewed."):
                st.rerun()


def _exports() -> None:
    export_tables = {
        "Customers": "customers", "Customer overview": "customer_management_overview",
        "Inventory": "app_available_inventory", "Expiry alerts": "expiry_alerts",
        "Quarterly statistics": "customer_quarterly_statistics", "Downtime": "downtime_event_details",
        "Component issues": "component_issues", "Invoices": "invoice_balances",
    }
    selected = st.selectbox("Export dataset", list(export_tables))
    rows = select_rows(export_tables[selected])
    csv = pd.DataFrame(rows).to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, file_name=f"{export_tables[selected]}.csv", mime="text/csv")


def render(user: dict) -> None:
    page_header("Administration", "Master data, assignments, approvals and exports")
    tabs = st.tabs(["Contract services", "Inventory items", "Kits", "Users & locations", "Backdated entries", "Exports"])
    try:
        with tabs[0]: _contract_services(user)
        with tabs[1]: _inventory_item(user)
        with tabs[2]: _kits(user)
        with tabs[3]: _users(user)
        with tabs[4]: _backdates(user)
        with tabs[5]: _exports()
    except Exception as exc:
        st.error(f"Administration data could not be loaded: {exc}")
