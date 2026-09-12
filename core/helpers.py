from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pandas as pd
import streamlit as st


def reference(prefix: str) -> str:
    return f"{prefix}-{datetime.now():%Y%m%d}-{uuid4().hex[:6].upper()}"


def money(value) -> str:
    try:
        return f"PKR {float(value or 0):,.0f}"
    except (TypeError, ValueError):
        return "PKR 0"


def number(value, digits: int = 0) -> str:
    try:
        return f"{float(value or 0):,.{digits}f}"
    except (TypeError, ValueError):
        return "0"


def clean_payload(data: dict) -> dict:
    cleaned = {}
    for key, value in data.items():
        if value == "":
            cleaned[key] = None
        elif isinstance(value, (date, datetime)):
            cleaned[key] = value.isoformat()
        elif isinstance(value, Decimal):
            cleaned[key] = float(value)
        else:
            cleaned[key] = value
    return cleaned


def options(rows: list[dict], label_fields: list[str]) -> tuple[list[str], dict]:
    mapping = {}
    labels = []
    for row in rows:
        label = " — ".join(str(row.get(field) or "") for field in label_fields)
        label = label.strip(" —")
        if label in mapping:
            label = f"{label} ({str(row['id'])[:6]})"
        labels.append(label)
        mapping[label] = row
    return labels, mapping


def show_table(rows: list[dict], columns: dict[str, str] | None = None) -> None:
    if not rows:
        st.info("No records found.")
        return
    frame = pd.DataFrame(rows)
    if columns:
        selected = [column for column in columns if column in frame.columns]
        frame = frame[selected].rename(columns=columns)
    st.dataframe(frame, use_container_width=True, hide_index=True)
