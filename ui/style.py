import streamlit as st


def apply_style() -> None:
    st.markdown(
        """
        <style>
        :root { --ink:#18343B; --teal:#0E8F92; --navy:#143D59; --mist:#EAF3F4; }
        .stApp { background: linear-gradient(180deg,#F8FBFC 0%,#F3F7F8 100%); }
        h1,h2,h3 { color:var(--ink); letter-spacing:-.02em; }
        [data-testid="stSidebar"] { background:#123844; }
        [data-testid="stSidebar"] * { color:#F3FBFC; }
        [data-testid="stSidebar"] .stButton button { width:100%; border-color:#3B6973; }
        div[data-testid="stMetric"] { background:white; border:1px solid #DCE9EB;
          border-radius:14px; padding:14px 16px; box-shadow:0 4px 18px rgba(20,61,89,.05); }
        div[data-testid="stForm"] { background:white; border:1px solid #DCE9EB;
          border-radius:16px; padding:18px; }
        .login-mark { width:64px;height:64px;border-radius:18px;background:#0E8F92;color:white;
          display:flex;align-items:center;justify-content:center;font-size:25px;font-weight:800;
          box-shadow:0 12px 28px rgba(14,143,146,.22); margin-top:10vh; }
        .section-note { color:#59747B; margin-top:-8px; margin-bottom:18px; }
        .status-chip { display:inline-block;padding:4px 9px;border-radius:999px;background:#E7F5F2;
          color:#176B64;font-weight:650;font-size:13px; }
        .danger-chip { display:inline-block;padding:4px 9px;border-radius:999px;background:#FDECEC;
          color:#A33B3B;font-weight:650;font-size:13px; }
        .block-container { max-width:1500px; padding-top:2rem; }
        @media (max-width: 720px) { .block-container { padding:1rem; } }
        </style>
        """,
        unsafe_allow_html=True,
    )

