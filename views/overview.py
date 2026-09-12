from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from core.db import select_rows
from core.helpers import money, number, show_table
from ui.layout import page_header


def render(user: dict) -> None:
    page_header("Operations overview", "Current customer, inventory and service position")
    try:
        customers = select_rows("customer_management_overview")
        expiry = select_rows("expiry_alerts", order="expiry_date", limit=30)
        issues = select_rows(
            "component_issues",
            "issue_number,customer_id,issue_type,severity,status,runs_affected,reported_at",
            order="reported_at", desc=True, limit=50,
        )
        issues = [row for row in issues if row.get("status") not in ("verified", "closed")][:20]
        notifications = select_rows(
            "notifications", "id,title,message,created_at,is_read",
            [("user_id", "eq", user["id"]), ("is_read", "eq", False)],
            order="created_at", desc=True, limit=8,
        )
    except Exception as exc:
        st.error(f"Dashboard data could not be loaded: {exc}")
        return

    total_sales = sum(float(row.get("quarter_sales") or 0) for row in customers)
    patients = sum(int(row.get("quarter_patients") or 0) for row in customers)
    downtime = sum(float(row.get("quarter_downtime_hours") or 0) for row in customers)
    open_issues = sum(int(row.get("open_component_issues") or 0) for row in customers)

    a, b, c, d = st.columns(4)
    a.metric("Quarter sales", money(total_sales))
    b.metric("Patients served", number(patients))
    c.metric("Downtime", f"{number(downtime, 1)} hrs")
    d.metric("Open kit issues", number(open_issues))

    if customers:
        frame = pd.DataFrame(customers)
        frame["customer"] = frame["hospital_name"].fillna("") + frame["branch_name"].fillna("").map(lambda x: f" — {x}" if x else "")
        left, right = st.columns([1.25, 1])
        with left:
            st.subheader("Quarterly sales by hospital")
            fig = px.bar(
                frame, x="customer", y="quarter_sales", color="quarter_sales",
                color_continuous_scale=["#DDF3F1", "#0E8F92"], labels={"quarter_sales": "Sales", "customer": ""},
            )
            fig.update_layout(coloraxis_showscale=False, margin=dict(l=5, r=5, t=10, b=5), height=330)
            st.plotly_chart(fig, use_container_width=True)
        with right:
            st.subheader("Operational impact")
            impact = frame[["customer", "quarter_downtime_hours", "quarter_runs_lost"]].melt(
                "customer", var_name="Measure", value_name="Value"
            )
            fig = px.bar(impact, x="customer", y="Value", color="Measure", barmode="group",
                         color_discrete_sequence=["#E07A5F", "#143D59"])
            fig.update_layout(margin=dict(l=5, r=5, t=10, b=5), height=330, legend_title_text="")
            st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Expiry alerts")
        show_table(expiry, {
            "location_name": "Location", "item_name": "Item", "lot_number": "Lot",
            "quantity": "Available", "expiry_date": "Expiry", "days_until_expiry": "Days left",
        })
    with right:
        st.subheader("Open component issues")
        show_table(issues, {
            "issue_number": "Issue", "issue_type": "Type", "severity": "Severity",
            "status": "Status", "runs_affected": "Runs affected", "reported_at": "Reported",
        })

    if notifications:
        st.subheader("Notifications")
        for note in notifications:
            st.info(f"**{note['title']}** — {note['message']}")
