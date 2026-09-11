import streamlit as st
from supabase import Client, create_client

st.set_page_config(
    page_title="Medicine Manager",
    page_icon="🏥",
    layout="wide",
)

if "supabase" not in st.session_state:
    st.session_state.supabase = create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"],
    )

supabase: Client = st.session_state.supabase


def login() -> None:
    st.title("Medicine Manager")
    st.subheader("Sign in")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)

    if submitted:
        if not email or not password:
            st.error("Enter both email and password.")
            return

        try:
            response = supabase.auth.sign_in_with_password(
                {
                    "email": email.strip(),
                    "password": password,
                }
            )

            profile_response = (
                supabase.table("profiles")
                .select("id, full_name, role, is_active")
                .eq("id", response.user.id)
                .single()
                .execute()
            )

            profile = profile_response.data

            if not profile or not profile["is_active"]:
                supabase.auth.sign_out()
                st.error("This account is not active.")
                return

            st.session_state.user = {
                "id": response.user.id,
                "email": response.user.email,
                **profile,
            }

            st.rerun()

        except Exception:
            st.error("Invalid login or missing user profile.")


def logout() -> None:
    supabase.auth.sign_out()
    st.session_state.clear()
    st.rerun()


if "user" not in st.session_state:
    login()
    st.stop()

user = st.session_state.user

st.title("Medicine Manager")
st.success(f"Logged in as {user['full_name']}")
st.write(f"Role: `{user['role']}`")

if st.button("Log out"):
    logout()
