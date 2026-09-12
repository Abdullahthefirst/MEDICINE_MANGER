from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from core.db import insert_row, select_rows, try_action, update_rows
from core.helpers import clean_payload, money, options, reference, show_table
from ui.layout import page_header


def _customer_form(user: dict) -> None:
    if user["role"] != "admin":
        return
    with st.expander("Add hospital customer"):
        with st.form("add_customer"):
            a, b = st.columns(2)
            code = a.text_input("Customer code")
            name = b.text_input("Hospital name")
            branch = a.text_input("Branch label", help="Each branch remains a separate customer.")
            city = b.text_input("City", value="Karachi")
            address = st.text_area("Address")
            c, d = st.columns(2)
            contact = c.text_input("Contact person")
            phone = d.text_input("Phone")
            email = c.text_input("Email")
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Create customer")
        if submitted:
            if not code or not name or not address:
                st.error("Customer code, hospital name and address are required.")
            else:
                payload = clean_payload({
                    "customer_code": code.strip().upper(), "hospital_name": name.strip(),
                    "branch_name": branch.strip(), "city": city.strip(), "address": address.strip(),
                    "contact_person": contact.strip(), "phone": phone.strip(), "email": email.strip(),
                    "notes": notes.strip(), "created_by": user["id"],
                })
                if try_action(lambda: insert_row("customers", payload), "Customer created."):
                    st.rerun()


def _contract_form(user: dict, customer: dict) -> None:
    if user["role"] != "admin":
        return
    with st.expander("Add fixed-duration contract"):
        with st.form(f"contract_{customer['id']}"):
            number = st.text_input("Contract number", value=reference("CTR"))
            a, b = st.columns(2)
            start = a.date_input("Start date", value=date.today())
            end = b.date_input("End date", value=date.today() + timedelta(days=365))
            value = a.number_input("Contract value (optional)", min_value=0.0, step=1000.0)
            status = b.selectbox("Status", ["draft", "active", "terminated", "renewed"])
            document = st.text_input("Contract document URL")
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Save contract")
        if submitted:
            if end < start:
                st.error("End date must be after the start date.")
            else:
                payload = clean_payload({
                    "customer_id": customer["id"], "contract_number": number.strip(),
                    "start_date": start, "end_date": end, "contract_value": value or None,
                    "status": status, "document_url": document.strip(), "notes": notes.strip(),
                    "created_by": user["id"],
                })
                if try_action(lambda: insert_row("contracts", payload), "Contract created."):
                    st.rerun()


def render(user: dict) -> None:
    page_header("Customer management", "Hospitals, contracts, stock, usage and operational impact")
    _customer_form(user)
    try:
        customers = select_rows("customers", order="hospital_name")
    except Exception as exc:
        st.error(f"Customers could not be loaded: {exc}")
        return
    if not customers:
        st.info("No hospital customers are available.")
        return

    labels, mapping = options(customers, ["hospital_name", "branch_name", "customer_code"])
    selected = mapping[st.selectbox("Hospital", labels)]
    st.markdown(f"### {selected['hospital_name']}")
    st.caption(f"{selected.get('branch_name') or ''} · {selected.get('city') or ''} · {selected['customer_code']}")
    _contract_form(user, selected)

    try:
        overview = select_rows("customer_management_overview", filters=[("customer_id", "eq", selected["id"])])
        contracts = select_rows("current_contracts", filters=[("customer_id", "eq", selected["id"])], order="start_date", desc=True)
        inventory = select_rows("available_inventory", filters=[("customer_id", "eq", selected["id"])], order="expiry_date")
        usage = select_rows("customer_usage", filters=[("customer_id", "eq", selected["id"])], order="usage_date", desc=True, limit=100)
        deliveries = select_rows("customer_delivery_history", filters=[("customer_id", "eq", selected["id"])], order="movement_date", desc=True, limit=100)
        downtime = select_rows("downtime_event_details", filters=[("customer_id", "eq", selected["id"])], order="started_at", desc=True, limit=100)
        quarterly = select_rows("customer_quarterly_statistics", filters=[("customer_id", "eq", selected["id"])], order="quarter_start", desc=True)
        invoices = select_rows("invoice_balances", filters=[("customer_id", "eq", selected["id"])], order="issue_date", desc=True)
    except Exception as exc:
        st.error(f"Customer details could not be loaded: {exc}")
        return

    if overview:
        row = overview[0]
        a, b, c, d = st.columns(4)
        a.metric("Quarter sales", money(row.get("quarter_sales")))
        b.metric("Patients served", row.get("quarter_patients", 0))
        c.metric("Available batches", row.get("available_batches", 0))
        d.metric("Downtime", f"{row.get('quarter_downtime_hours', 0)} hrs")

    tabs = st.tabs([
        "📄 Contracts",
        "📊 Quarterly",
        "📦 Inventory",
        "🧾 Usage",
        "🚚 Deliveries",
        "⏱️ Downtime",
        "💳 Invoices",
    ])
    with tabs[0]:
        show_table(contracts, {
            "contract_number": "Contract", "start_date": "Start", "end_date": "End",
            "current_status": "Status", "days_remaining": "Days remaining", "contract_value": "Value",
        })
    with tabs[1]:
        show_table(quarterly, {
            "quarter_start": "Quarter", "services_provided": "Services",
            "patients_served": "Patients", "sales_value": "Sales",
            "downtime_hours": "Downtime hours", "runs_lost": "Runs lost",
        })
    with tabs[2]:
        show_table(inventory, {
            "item_name": "Item", "manufacturer_cat_number": "Manufacturer Cat #",
            "lot_number": "Lot", "quantity": "Available", "unit": "Unit",
            "expiry_date": "Expiry", "estimated_runs": "Estimated runs",
        })
    with tabs[3]:
        show_table(usage, {
            "usage_number": "Usage", "usage_date": "Date", "service_quantity": "Services",
            "patients_served": "Patients", "unit_price": "Unit price", "total_amount": "Value",
        })
    with tabs[4]:
        show_table(deliveries, {
            "movement_date": "Date", "slip_number": "Slip", "warehouse_name": "From",
            "item_name": "Item", "lot_number": "Lot", "quantity": "Quantity", "expiry_date": "Expiry",
        })
    with tabs[5]:
        show_table(downtime, {
            "event_number": "Event", "downtime_category": "Category", "title": "Title",
            "started_at": "Started", "ended_at": "Ended", "duration_hours": "Hours",
            "runs_lost": "Runs lost", "patients_affected": "Patients affected", "status": "Status",
        })
    with tabs[6]:
        show_table(invoices, {
            "invoice_number": "Invoice", "issue_date": "Issued", "due_date": "Due",
            "invoice_total": "Total", "amount_paid": "Paid",
            "outstanding_amount": "Outstanding", "calculated_status": "Status",
        })
