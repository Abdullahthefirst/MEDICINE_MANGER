from __future__ import annotations

from datetime import date, datetime, time

import streamlit as st

from core.auth import get_client
from core.db import insert_row, select_rows, try_action
from core.helpers import clean_payload, options, reference
from ui.layout import page_header


def _post_movement(payload: dict) -> None:
    get_client().rpc("post_inventory_movement", payload).execute()


def _usage_entry(user: dict) -> None:
    customers = select_rows("customers", "id,customer_code,hospital_name,branch_name", order="hospital_name")
    if not customers:
        st.info("No accessible hospitals.")
        return
    customer_labels, customer_map = options(customers, ["hospital_name", "branch_name", "customer_code"])
    selected_customer = customer_map[st.selectbox("Hospital", customer_labels)]
    contracts = select_rows(
        "current_contracts", "id,contract_number,start_date,end_date,current_status",
        [("customer_id", "eq", selected_customer["id"]), ("current_status", "eq", "active")],
    )
    if not contracts:
        st.warning("This hospital has no active contract.")
        return
    contract_labels, contract_map = options(contracts, ["contract_number", "end_date"])
    selected_contract = contract_map[st.selectbox("Contract", contract_labels)]
    services = select_rows(
        "contract_services", "id,service_code,service_name,billing_unit,unit_price",
        [("contract_id", "eq", selected_contract["id"]), ("is_active", "eq", True)],
    )
    if not services:
        st.warning("Add services and prices to this contract first.")
        return
    service_labels, service_map = options(services, ["service_name", "service_code"])
    with st.form("usage_entry"):
        selected_service_label = st.selectbox("Service", service_labels)
        a, b, c = st.columns(3)
        usage_date = a.date_input("Usage date", value=date.today())
        quantity = b.number_input("Service quantity", min_value=0.001, value=1.0, step=1.0)
        patients = c.number_input("Patients served", min_value=0, value=0, step=1)
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Record usage")
    if submitted:
        service = service_map[selected_service_label]
        payload = clean_payload({
            "usage_number": reference("USE"), "customer_id": selected_customer["id"],
            "contract_id": selected_contract["id"], "contract_service_id": service["id"],
            "usage_date": usage_date, "service_quantity": quantity, "patients_served": patients,
            "unit_price": service["unit_price"], "notes": notes.strip(), "created_by": user["id"],
        })
        if try_action(lambda: insert_row("customer_usage", payload), "Usage recorded."):
            st.rerun()


def _receipt(user: dict) -> None:
    items = select_rows("inventory_items", "id,item_code,item_name,unit", [("is_active", "eq", True)], order="item_name")
    locations = select_rows("stock_locations", "id,location_name,location_type", [("location_type", "eq", "warehouse")], order="location_name")
    if not items or not locations:
        st.warning("Items and a warehouse location are required.")
        return
    item_labels, item_map = options(items, ["item_name", "item_code"])
    location_labels, location_map = options(locations, ["location_name"])
    with st.form("inventory_receipt"):
        item_label = st.selectbox("Item", item_labels)
        destination_label = st.selectbox("Receiving warehouse", location_labels)
        a, b = st.columns(2)
        lot = a.text_input("Lot number")
        manufacturer_cat = b.text_input("Manufacturer catalogue number")
        received = a.date_input("Received date", value=date.today())
        expiry = b.date_input("Expiry date", value=date.today(), min_value=date.today())
        supplier = a.text_input("Supplier")
        quantity = b.number_input("Quantity received", min_value=0.001, step=1.0)
        slip = st.text_input("Receiving slip", value=reference("GRN"))
        notes = st.text_area("Delivery condition / notes")
        submitted = st.form_submit_button("Receive inventory")
    if submitted:
        if not lot:
            st.error("Lot number is required.")
            return
        item = item_map[item_label]
        destination = location_map[destination_label]

        def save():
            if manufacturer_cat:
                get_client().table("inventory_items").update(
                    {"manufacturer_cat_number": manufacturer_cat.strip()}
                ).eq("id", item["id"]).execute()
            result = get_client().table("inventory_batches").upsert(
                clean_payload({
                    "item_id": item["id"], "lot_number": lot.strip(),
                    "catalogue_number": manufacturer_cat.strip(), "received_date": received,
                    "expiry_date": expiry, "supplier_name": supplier.strip(), "notes": notes.strip(),
                }), on_conflict="item_id,lot_number"
            ).execute()
            batch = result.data[0]
            _post_movement({
                "p_movement_number": reference("MOV"), "p_movement_type": "receipt",
                "p_movement_date": datetime.combine(received, time.min).isoformat(),
                "p_slip_number": slip.strip(), "p_reason": notes.strip() or None,
                "p_item_id": item["id"], "p_batch_id": batch["id"],
                "p_from_location_id": None, "p_to_location_id": destination["id"],
                "p_from_state": None, "p_to_state": "available", "p_quantity": quantity,
                "p_patients_served": 0, "p_customer_usage_id": None,
            })
        if try_action(save, "Inventory received and stock updated."):
            st.rerun()


def _transfer(user: dict) -> None:
    stock = select_rows("available_inventory", order="item_name")
    destinations = select_rows("stock_locations", "id,location_name,location_type", [("location_type", "eq", "hospital")], order="location_name")
    if not stock or not destinations:
        st.info("Available warehouse stock and hospital locations are required.")
        return
    stock = [row for row in stock if not row.get("customer_id")]
    if not stock:
        st.info("No warehouse stock is available.")
        return
    stock_labels, stock_map = options(stock, ["location_name", "item_name", "lot_number", "quantity"])
    destination_labels, destination_map = options(destinations, ["location_name"])
    with st.form("inventory_transfer"):
        stock_label = st.selectbox("Source batch", stock_labels)
        destination_label = st.selectbox("Destination hospital", destination_labels)
        quantity = st.number_input("Quantity", min_value=0.001, step=1.0)
        slip = st.text_input("Delivery slip", value=reference("DSL"))
        movement_date = st.date_input("Dispatch date", value=date.today())
        reason = st.text_area("Notes")
        submitted = st.form_submit_button("Dispatch inventory")
    if submitted:
        source = stock_map[stock_label]
        destination = destination_map[destination_label]
        payload = {
            "p_movement_number": reference("MOV"), "p_movement_type": "transfer",
            "p_movement_date": datetime.combine(movement_date, time.min).isoformat(),
            "p_slip_number": slip.strip(), "p_reason": reason.strip() or None,
            "p_item_id": source["item_id"], "p_batch_id": source["batch_id"],
            "p_from_location_id": source["location_id"], "p_to_location_id": destination["id"],
            "p_from_state": "available", "p_to_state": "available", "p_quantity": quantity,
            "p_patients_served": 0, "p_customer_usage_id": None,
        }
        if try_action(lambda: _post_movement(payload), "Inventory dispatched."):
            st.rerun()


def _consume(user: dict) -> None:
    stock = [row for row in select_rows("available_inventory", order="item_name") if row.get("customer_id")]
    usages = select_rows("customer_usage", "id,usage_number,customer_id,usage_date", order="usage_date", desc=True, limit=100)
    if not stock:
        st.info("No accessible hospital stock is available.")
        return
    stock_labels, stock_map = options(stock, ["location_name", "item_name", "lot_number", "quantity"])
    usage_labels, usage_map = options(usages, ["usage_number", "usage_date"])
    with st.form("inventory_usage"):
        stock_label = st.selectbox("Consumed batch", stock_labels)
        quantity = st.number_input("Quantity consumed", min_value=0.001, step=1.0)
        usage_label = st.selectbox("Related service usage (optional)", ["None", *usage_labels])
        movement_date = st.date_input("Usage date", value=date.today())
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Record consumption")
    if submitted:
        source = stock_map[stock_label]
        related = usage_map.get(usage_label)
        if related and related.get("customer_id") != source.get("customer_id"):
            st.error("The service usage belongs to a different hospital.")
            return
        payload = {
            "p_movement_number": reference("MOV"), "p_movement_type": "usage",
            "p_movement_date": datetime.combine(movement_date, time.min).isoformat(),
            "p_slip_number": None, "p_reason": notes.strip() or None,
            "p_item_id": source["item_id"], "p_batch_id": source["batch_id"],
            "p_from_location_id": source["location_id"], "p_to_location_id": None,
            "p_from_state": "available", "p_to_state": None, "p_quantity": quantity,
            "p_patients_served": 0, "p_customer_usage_id": related["id"] if related else None,
        }
        if try_action(lambda: _post_movement(payload), "Consumption recorded."):
            st.rerun()


def _stock_status(user: dict) -> None:
    balances = select_rows("inventory_balances")
    if not balances:
        st.info("No inventory balances are available.")
        return
    items = {row["id"]: row for row in select_rows("inventory_items", "id,item_name,item_code")}
    batches = {row["id"]: row for row in select_rows("inventory_batches", "id,lot_number")}
    locations = {row["id"]: row for row in select_rows("stock_locations", "id,location_name")}
    records = []
    for row in balances:
        if float(row.get("quantity") or 0) <= 0:
            continue
        records.append({**row, "label": f"{locations.get(row['location_id'],{}).get('location_name','')} — {items.get(row['item_id'],{}).get('item_name','')} — {batches.get(row['batch_id'],{}).get('lot_number','')} — {row['stock_state']} ({row['quantity']})"})
    labels = [row["label"] for row in records]
    mapping = {row["label"]: row for row in records}
    with st.form("stock_status_change"):
        selected_label = st.selectbox("Stock batch", labels)
        action = st.selectbox("Action", ["quarantine", "release", "expiry", "disposal"])
        quantity = st.number_input("Quantity", min_value=0.001, step=1.0)
        reason = st.text_area("Reason", help="Required for traceability.")
        submitted = st.form_submit_button("Post inventory change")
    if submitted:
        row = mapping[selected_label]
        if not reason.strip():
            st.error("A reason is required.")
            return
        if quantity > float(row.get("quantity") or 0):
            st.error("Quantity cannot exceed the current balance.")
            return
        if action == "quarantine" and row["stock_state"] != "available":
            st.error("Only available stock can be quarantined.")
            return
        if action == "release" and row["stock_state"] != "quarantine":
            st.error("Only quarantined stock can be released.")
            return
        from_state, to_state, to_location = row["stock_state"], None, None
        if action == "quarantine":
            to_state, to_location = "quarantine", row["location_id"]
        elif action == "release":
            to_state, to_location = "available", row["location_id"]
        payload = {
            "p_movement_number": reference("MOV"), "p_movement_type": action,
            "p_movement_date": datetime.now().isoformat(), "p_slip_number": None,
            "p_reason": reason.strip(), "p_item_id": row["item_id"], "p_batch_id": row["batch_id"],
            "p_from_location_id": row["location_id"], "p_to_location_id": to_location,
            "p_from_state": from_state, "p_to_state": to_state, "p_quantity": quantity,
            "p_patients_served": 0, "p_customer_usage_id": None,
        }
        if try_action(lambda: _post_movement(payload), "Inventory status updated."):
            st.rerun()


def render(user: dict) -> None:
    page_header("Data entry", "Choose one section and record the operational event")
    role_sections = {
        "admin": ["Customer usage", "Inventory receipt", "Warehouse transfer", "Inventory consumption", "Stock status"],
        "hospital_staff": ["Customer usage", "Inventory consumption", "Stock status"],
        "warehouse_staff": ["Inventory receipt", "Warehouse transfer", "Stock status"],
    }
    allowed = role_sections.get(user["role"], [])
    if not allowed:
        st.info("Your role has no data-entry permissions.")
        return
    section = st.selectbox("Section", allowed)
    st.divider()
    try:
        {
            "Customer usage": _usage_entry,
            "Inventory receipt": _receipt,
            "Warehouse transfer": _transfer,
            "Inventory consumption": _consume,
            "Stock status": _stock_status,
        }[section](user)
    except Exception as exc:
        st.error(f"This section could not be loaded: {exc}")
