from __future__ import annotations

import json

import streamlit as st
from google import genai

from core.db import select_rows
from ui.layout import page_header


def _safe_context() -> dict:
    return {
        "customer_overview": select_rows("customer_management_overview"),
        "quarterly_statistics": select_rows("customer_quarterly_statistics", order="quarter_start", desc=True, limit=100),
        "expiry_alerts": select_rows("expiry_alerts", order="expiry_date", limit=100),
        "monthly_downtime": select_rows("customer_monthly_downtime", order="month_start", desc=True, limit=100),
        "open_component_issues": [
            row for row in select_rows(
                "component_issues",
                "issue_number,customer_id,issue_type,severity,runs_affected,issue_details,status,reported_at",
                limit=100,
            ) if row.get("status") not in ("verified", "closed")
        ],
    }


def render(user: dict) -> None:
    page_header("AI analysis", "Operational summaries from authorized aggregate data")
    configured_key = st.secrets.get("GEMINI_API_KEY", "")
    if configured_key:
        api_key = configured_key
        st.caption("Using the organization Gemini configuration.")
    else:
        api_key = st.text_input(
            "Gemini API key", type="password",
            help="Used for this browser session only and never written to Supabase.",
        )
        if api_key:
            st.session_state.gemini_api_key = api_key
        api_key = st.session_state.get("gemini_api_key", "")

    model = st.secrets.get("GEMINI_MODEL", "gemini-2.5-flash")
    prompts = {
        "Quarterly performance": "Summarize quarterly sales, services and patient-count trends by hospital. Identify material changes and useful follow-up questions.",
        "Inventory risk": "Analyze expiry exposure, stock coverage and estimated working days. Prioritize operational actions without making clinical decisions.",
        "Downtime": "Analyze downtime frequency, duration, lost runs and affected services. Identify recurring operational causes.",
        "Component issues": "Summarize unresolved kit component issues by severity, runs affected and age. Suggest administrative follow-up actions only.",
        "Custom question": "",
    }
    analysis_type = st.selectbox("Analysis", list(prompts))
    question = st.text_area("Question", value=prompts[analysis_type], height=120)
    st.info("Only aggregate operational information is sent. Patient names and medical details are not stored or included.")
    if st.button("Generate analysis", type="primary"):
        if not api_key:
            st.error("Enter a Gemini API key.")
            return
        if not question.strip():
            st.error("Enter a question.")
            return
        try:
            context = _safe_context()
            instruction = (
                "You are analyzing a hospital customer and consumables management system. "
                "Use only the supplied data. Clearly distinguish facts from estimates. "
                "Do not provide diagnosis, treatment, clinical instructions, or automatic approvals. "
                "Return a concise management summary, key findings, risks, and recommended administrative actions.\n\n"
                f"Question: {question}\n\nData: {json.dumps(context, default=str)}"
            )
            response = genai.Client(api_key=api_key).models.generate_content(
                model=model, contents=instruction
            )
            st.markdown(response.text or "No response was returned.")
        except Exception as exc:
            st.error(f"AI analysis failed: {exc}")
