from __future__ import annotations

import streamlit as st
from supabase import Client, create_client


def get_client() -> Client:
    if "supabase_client" not in st.session_state:
        supabase_url = st.secrets.get("SUPABASE_URL", "")
        supabase_key = st.secrets.get("SUPABASE_KEY", "")
        if not supabase_url or not supabase_key:
            st.error(
                "Supabase is not configured. Add SUPABASE_URL and SUPABASE_KEY "
                "to .streamlit/secrets.toml locally or to the Streamlit Cloud app secrets."
            )
            st.code(
                'SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"\n'
                'SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY"',
                language="toml",
            )
            st.stop()
        st.session_state.supabase_client = create_client(
            supabase_url, supabase_key
        )
    return st.session_state.supabase_client


def current_user() -> dict | None:
    return st.session_state.get("user")


def sign_in(email: str, password: str) -> tuple[bool, str]:
    try:
        client = get_client()
        result = client.auth.sign_in_with_password(
            {"email": email.strip(), "password": password}
        )
        profile_result = (
            client.table("profiles")
            .select("id,full_name,role,is_active")
            .eq("id", result.user.id)
            .single()
            .execute()
        )
        profile = profile_result.data
        if not profile or not profile.get("is_active"):
            client.auth.sign_out()
            return False, "Your account is inactive or has no application profile."
        st.session_state.user = {
            "id": result.user.id,
            "email": result.user.email,
            **profile,
        }
        return True, "Signed in"
    except Exception:
        return False, "Invalid credentials or missing user profile."


def sign_out() -> None:
    try:
        get_client().auth.sign_out()
    finally:
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


def require_login() -> dict:
    user = current_user()
    if user:
        return user

    left, center, right = st.columns([1, 1.15, 1])
    with center:
        st.markdown("<div class='login-mark'>MM</div>", unsafe_allow_html=True)
        st.title("Medicine Manager")
        st.caption("Secure operations and customer management")
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="name@company.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
        if submitted:
            if not email or not password:
                st.error("Enter both email and password.")
            else:
                ok, message = sign_in(email, password)
                if ok:
                    st.rerun()
                st.error(message)
    st.stop()
