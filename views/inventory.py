from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core.db import select_rows
from core.helpers import number, show_table
from ui.layout import page_header


def render(user: dict) -> None:
    page_header("Inventory", "Warehouse and hospital stock calculated from the movement ledger")
    try:
        available = select_rows("app_available_inventory", order="expiry_date")
        working = select_rows("inventory_working_days")
        expiry = select_rows("expiry_alerts", order="expiry_date")
        low_stock = select_rows("low_stock_alerts", order="item_name")
        movements = select_rows("inventory_movement_details", order="movement_date", desc=True, limit=200)
    except Exception as exc:
        st.error(f"Inventory data could not be loaded: {exc}")
        return

    total_batches = len({row.get("batch_id") for row in available})
    locations = len({row.get("location_id") for row in available})
    estimated_runs = sum(float(row.get("estimated_runs") or 0) for row in available)
    a, b, c, d = st.columns(4)
    a.metric("Available batches", total_batches)
    b.metric("Stock locations", locations)
    c.metric("Estimated runs", number(estimated_runs, 1))
    d.metric("Expiry / low-stock alerts", len(expiry) + len(low_stock))

    tabs = st.tabs([
        "📦 Available stock",
        "📅 Working days",
        "⏳ Expiry",
        "⚠️ Low stock",
        "↔️ Movement history",
    ])
    with tabs[0]:
        show_table(available, {
            "location_name": "Location", "item_name": "Item", "manufacturer_cat_number": "Manufacturer Cat #",
            "lot_number": "Lot", "quantity": "Available", "unit": "Unit",
            "expiry_date": "Expiry", "estimated_runs": "Estimated runs",
        })
    with tabs[1]:
        show_table(working, {
            "location_name": "Location", "item_name": "Item", "available_quantity": "Available",
            "quantity_used_last_30_days": "Used (30d)", "average_daily_usage": "Daily average",
            "estimated_working_days": "Working days",
        })
    with tabs[2]:
        show_table(expiry, {
            "location_name": "Location", "item_name": "Item", "lot_number": "Lot",
            "quantity": "Available", "expiry_date": "Expiry", "days_until_expiry": "Days left",
        })
    with tabs[3]:
        show_table(low_stock, {
            "location_name": "Location", "item_name": "Item", "available_quantity": "Available",
            "reorder_level": "Reorder level", "unit": "Unit",
        })
    with tabs[4]:
        show_table(movements, {
            "movement_number": "Movement", "movement_type": "Type", "movement_date": "Date",
            "slip_number": "Slip", "item_name": "Item", "lot_number": "Lot",
            "quantity": "Quantity", "unit": "Unit", "from_location": "From",
            "to_location": "To", "from_stock_state": "From state",
            "to_stock_state": "To state", "reason": "Reason",
        })
