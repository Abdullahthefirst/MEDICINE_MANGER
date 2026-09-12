import plotly.io as pio
import streamlit as st


def apply_style() -> None:
    dark_mode = st.session_state.get("dark_mode", False)
    pio.templates.default = "plotly_dark" if dark_mode else "plotly_white"

    if dark_mode:
        colors = {
            "app_top": "#10191F",
            "app_bottom": "#0B1217",
            "surface": "#162229",
            "surface_soft": "#1B2A32",
            "ink": "#EAF4F5",
            "muted": "#9FB4BA",
            "border": "#2A3D46",
            "shadow": "rgba(0,0,0,.24)",
            "input": "#111C22",
        }
    else:
        colors = {
            "app_top": "#F8FBFC",
            "app_bottom": "#F3F7F8",
            "surface": "#FFFFFF",
            "surface_soft": "#F5F9FA",
            "ink": "#18343B",
            "muted": "#59747B",
            "border": "#DCE9EB",
            "shadow": "rgba(20,61,89,.05)",
            "input": "#FFFFFF",
        }

    st.markdown(
        f"""
        <style>
        :root {{
          --ink:{colors['ink']};
          --muted:{colors['muted']};
          --surface:{colors['surface']};
          --surface-soft:{colors['surface_soft']};
          --border:{colors['border']};
          --input:{colors['input']};
        }}

        html, body, [data-testid="stAppViewContainer"], .stApp {{
          color:var(--ink);
          background:linear-gradient(
            180deg,
            {colors['app_top']} 0%,
            {colors['app_bottom']} 100%
          );
        }}

        [data-testid="stHeader"] {{
          background:transparent;
        }}

        h1,h2,h3,h4,h5,h6,p,label,span {{
          color:var(--ink);
        }}

        [data-testid="stSidebar"] {{
          background:#123D48;
          border-right:1px solid #285563;
        }}

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span {{
          color:#F3FBFC !important;
        }}

        [data-testid="stSidebar"]
        [data-testid="stCaptionContainer"] p {{
          color:#AFC9CE !important;
        }}

        [data-testid="stSidebar"] hr {{
          border-color:#315A64;
        }}

        [data-testid="stSidebar"] .stRadio label {{
          padding:.16rem 0;
        }}

        [data-testid="stSidebar"] .stButton button {{
          width:100%;
          min-height:2.8rem;
          background:#F5FAFB !important;
          border:1px solid #F5FAFB !important;
          color:#123D48 !important;
          font-weight:700;
        }}

        [data-testid="stSidebar"] .stButton button * {{
          color:#123D48 !important;
        }}

        [data-testid="stSidebar"] .stButton button:hover {{
          background:#DFF3F3 !important;
          border-color:#19B7B5 !important;
        }}

        [data-testid="stSidebar"] .role-badge {{
          display:inline-flex;
          align-items:center;
          padding:5px 10px;
          margin-top:4px;
          border-radius:999px;
          background:#DFF3F3;
          color:#123D48 !important;
          font-size:12px;
          font-weight:750;
        }}

        .theme-label {{
          color:#AFC9CE !important;
          font-size:12px;
          margin-top:8px;
        }}

        div[data-testid="stMetric"] {{
          background:var(--surface);
          border:1px solid var(--border);
          border-radius:14px;
          padding:14px 16px;
          box-shadow:0 4px 18px {colors['shadow']};
        }}

        div[data-testid="stForm"] {{
          background:var(--surface);
          border:1px solid var(--border);
          border-radius:16px;
          padding:18px;
        }}

        [data-testid="stExpander"] {{
          background:var(--surface);
          border-color:var(--border);
        }}

        [data-baseweb="tab-list"] {{
          gap:.25rem;
        }}

        [data-baseweb="tab"] {{
          background:var(--surface-soft);
          border-radius:9px 9px 0 0;
          padding-left:.85rem;
          padding-right:.85rem;
        }}

        [data-baseweb="tab"][aria-selected="true"] {{
          background:var(--surface);
        }}

        [data-baseweb="select"] > div,
        [data-baseweb="base-input"],
        [data-testid="stTextArea"] textarea,
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input,
        [data-testid="stTimeInput"] input {{
          background:var(--input) !important;
          color:var(--ink) !important;
          border-color:var(--border) !important;
        }}

        [data-testid="stDataFrame"],
        [data-testid="stTable"] {{
          border:1px solid var(--border);
          border-radius:10px;
          overflow:hidden;
        }}

        .section-note {{
          color:var(--muted);
          margin-top:-8px;
          margin-bottom:18px;
        }}

        .login-mark {{
          width:64px;
          height:64px;
          border-radius:18px;
          background:#0E8F92;
          color:white;
          display:flex;
          align-items:center;
          justify-content:center;
          font-size:25px;
          font-weight:800;
          margin-top:10vh;
        }}

        .block-container {{
          max-width:1500px;
          padding-top:2rem;
        }}

        @media (max-width:720px) {{
          .block-container {{
            padding:1rem;
          }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

