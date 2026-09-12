from __future__ import annotations

import streamlit as st

from core.auth import sign_out


ROLE_NAV = {
    "admin": [
        "Overview", "Customers", "Inventory", "Data Entry", "Finance",
        "Downtime", "Kit Issues", "AI Analysis", "Administration",
    ],
    "management_viewer": [
        "Overview", "Customers", "Inventory", "Finance", "Downtime",
        "Kit Issues", "AI Analysis",
    ],
    "hospital_staff": [
        "Overview", "Customers", "Inventory", "Data Entry", "Finance",
        "Downtime", "Kit Issues", "AI Analysis",
    ],
    "warehouse_staff": [
        "Overview", "Inventory", "Data Entry", "Downtime",
        "Kit Issues", "AI Analysis",
    ],
}

PAGE_LABELS = {
    "Overview": "📊 Overview",
    "Customers": "🏥 Customers",
    "Inventory": "📦 Inventory",
    "Data Entry": "✍️ Data Entry",
    "Finance": "💳 Finance",
    "Downtime": "⏱️ Downtime",
    "Kit Issues": "🧩 Kit Issues",
    "AI Analysis": "✨ AI Analysis",
    "Administration": "⚙️ Administration",
}


def navigation(user: dict) -> str:
    with st.sidebar:
        st.markdown("## Medicine Manager")
        st.caption(user.get("full_name", "User"))

        role = user.get("role", "").replace("_", " ").title()
        st.markdown(
            f"<span class='role-badge'>🛡️ {role}</span>",
            unsafe_allow_html=True,
        )

        st.divider()

        pages = ROLE_NAV.get(user.get("role"), ["Overview"])
        page = st.radio(
            "Navigation",
            pages,
            format_func=lambda item: PAGE_LABELS.get(item, item),
            label_visibility="collapsed",
        )

        st.divider()

        if st.button("🚪 Sign out", use_container_width=True):
            sign_out()

    return page


def page_header(title: str, note: str = "") -> None:
    st.title(title)
    if note:
        st.markdown(f"<div class='section-note'>{note}</div>", unsafe_allow_html=True)
