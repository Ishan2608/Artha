"""
components/auth_page.py — Login / Register UI

render() displays the full-page auth screen.
On success it writes to st.session_state and calls st.rerun().

State written:
  st.session_state.token     : str   — Bearer JWT
  st.session_state.user_id   : int
  st.session_state.username  : str
  st.session_state.messages  : list  — pre-loaded history from API
"""

import streamlit as st
from utils import api_client
from utils.formatters import format_timestamp


def _load_history(token: str) -> list[dict]:
    """Fetch saved messages from the backend and return them."""
    data, err = api_client.get_history(token)
    if err or not data:
        return []
    return data.get("messages", [])


def render():
    # ── Centered auth card ─────────────────────────────────────────────────────
    # Three-column trick: empty | card | empty
    _, col, _ = st.columns([1, 1.1, 1])

    with col:
        st.markdown("""
        <div class="auth-brand">
          <h1>⬡ Arth<span>a</span></h1>
          <p>AI FINANCIAL ANALYST · INDIAN MARKETS</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="auth-card">', unsafe_allow_html=True)

        login_tab, register_tab = st.tabs(["  Sign In  ", "  Create Account  "])

        # ── LOGIN ──────────────────────────────────────────────────────────────
        with login_tab:
            st.markdown("<br>", unsafe_allow_html=True)
            email    = st.text_input("Email", key="login_email",
                                     placeholder="you@example.com")
            password = st.text_input("Password", type="password",
                                     key="login_password",
                                     placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)

            if st.session_state.get("login_error"):
                st.error(st.session_state.login_error)

            if st.button("Sign In →", key="login_btn", use_container_width=True):
                if not email or not password:
                    st.session_state.login_error = "Please fill in all fields."
                    st.rerun()
                else:
                    with st.spinner("Authenticating…"):
                        data, err = api_client.login(email, password)
                    if err:
                        st.session_state.login_error = err
                        st.rerun()
                    else:
                        _on_auth_success(data)

        # ── REGISTER ───────────────────────────────────────────────────────────
        with register_tab:
            st.markdown("<br>", unsafe_allow_html=True)
            username = st.text_input("Username", key="reg_username",
                                     placeholder="at least 3 characters")
            reg_email = st.text_input("Email", key="reg_email",
                                      placeholder="you@example.com")
            reg_pass  = st.text_input("Password", type="password",
                                      key="reg_password",
                                      placeholder="at least 8 characters")
            st.markdown("<br>", unsafe_allow_html=True)

            if st.session_state.get("reg_error"):
                st.error(st.session_state.reg_error)

            if st.button("Create Account →", key="reg_btn", use_container_width=True):
                error = _validate_register(username, reg_email, reg_pass)
                if error:
                    st.session_state.reg_error = error
                    st.rerun()
                else:
                    with st.spinner("Creating your account…"):
                        data, err = api_client.register(username, reg_email, reg_pass)
                    if err:
                        st.session_state.reg_error = err
                        st.rerun()
                    else:
                        _on_auth_success(data)

        st.markdown('</div>', unsafe_allow_html=True)  # close .auth-card

        # Backend status pill
        st.markdown("<br>", unsafe_allow_html=True)
        health, _ = api_client.health_check()
        if health:
            st.markdown(
                '<div style="text-align:center">'
                '<span class="stat-chip">● Backend online</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="text-align:center">'
                '<span class="stat-chip" style="color:var(--rose);border-color:#ff5e7d30">'
                '● Backend offline — start the server</span>'
                '</div>',
                unsafe_allow_html=True,
            )


def _validate_register(username: str, email: str, password: str) -> str | None:
    if not username or len(username) < 3:
        return "Username must be at least 3 characters."
    if not email or "@" not in email:
        return "Enter a valid email address."
    if not password or len(password) < 8:
        return "Password must be at least 8 characters."
    return None


def _on_auth_success(data: dict):
    """Write auth state and pre-load history, then rerun to chat page."""
    token    = data["access_token"]
    user_id  = data["user_id"]
    username = data["username"]

    st.session_state.token    = token
    st.session_state.user_id  = user_id
    st.session_state.username = username

    # Pre-load conversation history so the chat page renders immediately.
    st.session_state.messages = _load_history(token)

    # Clear any error state from previous attempts
    for key in ("login_error", "reg_error"):
        st.session_state.pop(key, None)

    st.rerun()
