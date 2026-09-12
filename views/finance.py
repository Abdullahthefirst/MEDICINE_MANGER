from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from core.db import insert_row, select_rows, try_action, update_rows
from core.helpers import clean_payload, money, options, reference, show_table
from ui.layout import page_header


def _create_invoice(user: dict) -> None:
    if user["role"] not in ("admin", "hospital_staff"):
        return
    customers = select_rows("customers", "id,hospital_name,branch_name,customer_code", order="hospital_name")
    if not customers:
        return
    customer_labels, customer_map = options(customers, ["hospital_name", "branch_name", "customer_code"])
    with st.expander("Create invoice"):
        customer_label = st.selectbox("Hospital", customer_labels, key="invoice_customer")
        customer = customer_map[customer_label]
        contracts = select_rows("contracts", "id,contract_number", [("customer_id", "eq", customer["id"])])
        if not contracts:
            st.warning("No contract is available for this hospital.")
            return
        contract_labels, contract_map = options(contracts, ["contract_number"])
        with st.form("create_invoice"):
            contract_label = st.selectbox("Contract", contract_labels)
            a, b = st.columns(2)
            period_start = a.date_input("Billing period start", value=date.today().replace(day=1))
            period_end = b.date_input("Billing period end", value=date.today())
            issue_date = a.date_input("Issue date", value=date.today())
            due_date = b.date_input("Due date", value=date.today())
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Create draft invoice")
        if submitted:
            payload = clean_payload({
                "invoice_number": reference("INV"), "customer_id": customer["id"],
                "contract_id": contract_map[contract_label]["id"],
                "billing_period_start": period_start, "billing_period_end": period_end,
                "issue_date": issue_date, "due_date": due_date, "status": "draft",
                "notes": notes.strip(), "created_by": user["id"],
            })
            if try_action(lambda: insert_row("invoices", payload), "Draft invoice created."):
                st.rerun()


def _add_invoice_item(user: dict) -> None:
    if user["role"] not in ("admin", "hospital_staff"):
        return
    invoices = select_rows("invoices", "id,invoice_number,customer_id,contract_id,status", [("status", "eq", "draft")], order="created_at", desc=True)
    if not invoices:
        return
    invoice_labels, invoice_map = options(invoices, ["invoice_number"])
    with st.expander("Add usage to an invoice"):
        invoice_label = st.selectbox("Draft invoice", invoice_labels)
        invoice = invoice_map[invoice_label]
        usages = select_rows(
            "customer_usage", "id,usage_number,usage_date,service_quantity,unit_price,total_amount",
            [("customer_id", "eq", invoice["customer_id"]), ("contract_id", "eq", invoice["contract_id"])],
            order="usage_date", desc=True,
        )
        billed = select_rows("invoice_items", "customer_usage_id", [("is_void", "eq", False)])
        billed_ids = {row["customer_usage_id"] for row in billed}
        usages = [row for row in usages if row["id"] not in billed_ids]
        if not usages:
            st.info("No unbilled usage is available for this invoice.")
            return
        usage_labels, usage_map = options(usages, ["usage_number", "usage_date", "total_amount"])
        with st.form("add_invoice_item"):
            usage_label = st.selectbox("Usage", usage_labels)
            submitted = st.form_submit_button("Add to invoice")
        if submitted:
            usage = usage_map[usage_label]
            payload = {
                "invoice_id": invoice["id"], "customer_usage_id": usage["id"],
                "description": "Contract service", "quantity": usage["service_quantity"],
                "unit_price": usage["unit_price"],
            }
            if try_action(lambda: insert_row("invoice_items", payload), "Usage added to invoice."):
                st.rerun()


def _record_payment(user: dict) -> None:
    if user["role"] not in ("admin", "hospital_staff"):
        return
    invoices = select_rows(
        "invoice_balances",
        filters=[("calculated_status", "in_", ["issued", "partially_paid", "overdue"])],
        order="issue_date",
        desc=True,
    )
    if not invoices:
        return
    labels, mapping = options(invoices, ["invoice_number", "outstanding_amount"])
    with st.expander("Record payment"):
        with st.form("record_payment"):
            label = st.selectbox("Invoice", labels)
            amount = st.number_input("Amount received", min_value=0.01, step=1000.0)
            method = st.selectbox("Method", ["bank_transfer", "cheque", "cash", "online", "other"])
            ref = st.text_input("Payment reference")
            payment_date = st.date_input("Payment date", value=date.today())
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Record payment")
        if submitted:
            invoice = mapping[label]
            if amount > float(invoice.get("outstanding_amount") or 0):
                st.error("Payment cannot exceed the outstanding amount.")
                return
            payload = clean_payload({
                "payment_number": reference("PAY"), "invoice_id": invoice["invoice_id"],
                "payment_date": payment_date, "amount": amount, "payment_method": method,
                "reference_number": ref.strip(), "status": "recorded", "notes": notes.strip(),
                "created_by": user["id"],
            })
            if try_action(lambda: insert_row("payments", payload), "Payment recorded."):
                st.rerun()


def _change_invoice_status(user: dict) -> None:
    if user["role"] != "admin":
        return
    invoices = select_rows(
        "invoices", "id,invoice_number,status,issue_date,due_date",
        [("status", "in_", ["draft", "issued"])], order="created_at", desc=True,
    )
    if not invoices:
        return
    labels, mapping = options(invoices, ["invoice_number", "status"])
    with st.expander("Issue or cancel an invoice"):
        with st.form("change_invoice_status"):
            label = st.selectbox("Invoice", labels)
            status = st.selectbox("New status", ["issued", "cancelled"])
            submitted = st.form_submit_button("Update invoice")
        if submitted:
            if try_action(
                lambda: update_rows("invoices", {"status": status}, [("id", "eq", mapping[label]["id"])]),
                "Invoice status updated.",
            ):
                st.rerun()


def render(user: dict) -> None:
    page_header("Finance", "Contract usage, invoices and customer balances")
    try:
        _create_invoice(user)
        _add_invoice_item(user)
        _change_invoice_status(user)
        _record_payment(user)
        balances = select_rows("invoice_balances", order="issue_date", desc=True)
        quarter = select_rows("customer_quarterly_statistics", order="quarter_start", desc=True)
    except Exception as exc:
        st.error(f"Finance data could not be loaded: {exc}")
        return
    total = sum(float(row.get("invoice_total") or 0) for row in balances)
    paid = sum(float(row.get("amount_paid") or 0) for row in balances)
    outstanding = sum(float(row.get("outstanding_amount") or 0) for row in balances)
    overdue = sum(1 for row in balances if row.get("calculated_status") == "overdue")
    a, b, c, d = st.columns(4)
    a.metric("Total invoiced", money(total))
    b.metric("Paid", money(paid))
    c.metric("Outstanding", money(outstanding))
    d.metric("Overdue invoices", overdue)
    tabs = st.tabs(["Invoice balances", "Quarterly performance"])
    with tabs[0]:
        show_table(balances, {
            "invoice_number": "Invoice", "issue_date": "Issued", "due_date": "Due",
            "invoice_total": "Total", "amount_paid": "Paid", "outstanding_amount": "Outstanding",
            "calculated_status": "Status",
        })
    with tabs[1]:
        show_table(quarter, {
            "hospital_name": "Hospital", "branch_name": "Branch", "quarter_start": "Quarter",
            "services_provided": "Services", "patients_served": "Patients", "sales_value": "Sales",
            "downtime_hours": "Downtime hours", "runs_lost": "Runs lost",
        })
