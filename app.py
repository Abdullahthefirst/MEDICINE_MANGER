import streamlit as st

from core.auth import require_login
from ui.layout import navigation
from ui.style import apply_style
from views import admin, ai_analysis, customers, data_entry, downtime, finance, inventory, kits, overview


st.set_page_config(
    page_title="Medicine Manager",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_style()
user = require_login()
page = navigation(user)

PAGES = {
    "Overview": overview.render,
    "Customers": customers.render,
    "Inventory": inventory.render,
    "Data Entry": data_entry.render,
    "Finance": finance.render,
    "Downtime": downtime.render,
    "Kit Issues": kits.render,
    "AI Analysis": ai_analysis.render,
    "Administration": admin.render,
}

try:
    PAGES[page](user)
except Exception as exc:
    st.error(f"The page could not be displayed: {exc}")
