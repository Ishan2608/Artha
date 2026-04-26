"""
app.py — Artha Frontend Entry Point

Run with:
    cd frontend
    streamlit run app.py

Routing logic (all client-side via st.session_state):
  - No token  → auth_page.render()  (login / register)
  - Has token → sidebar.render() + chat_page.render()

State initialised on first load:
  st.session_state.token          : str | None
  st.session_state.user_id        : int | None
  st.session_state.username       : str | None
  st.session_state.messages       : list  — conversation history
  st.session_state.uploaded_files : list  — files for this session
  st.session_state.confirm_clear  : bool  — destructive action guard
"""

import streamlit as st
import os

from config import AppConfig
from components import auth_page, sidebar, chat_page
from utils import api_client


# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be the first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title=AppConfig.PAGE_TITLE,
    page_icon=AppConfig.PAGE_ICON,
    layout=AppConfig.LAYOUT,
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────────────────────────────────────
# CSS + FONTS
# ─────────────────────────────────────────────────────────────────────────────

def _inject_styles():
    """Load Google Fonts and inject the full CSS file."""
    # Google Fonts — Syne (display), JetBrains Mono (data), Nunito (body)
    st.markdown(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&'
        'family=JetBrains+Mono:wght@300;400;500&'
        'family=Nunito:wght@400;500;600;700&display=swap" rel="stylesheet">',
        unsafe_allow_html=True,
    )

    css_path = os.path.join(os.path.dirname(__file__), "styles", "main.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    else:
        st.warning("styles/main.css not found — running without custom theme.")


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE DEFAULTS
# ─────────────────────────────────────────────────────────────────────────────

def _init_state():
    defaults = {
        "token":          None,
        "user_id":        None,
        "username":       None,
        "messages":       [],
        "uploaded_files": [],
        "confirm_clear":  False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ─────────────────────────────────────────────────────────────────────────────
# TOKEN VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def _validate_token() -> bool:
    """
    Silently verify the stored JWT is still accepted by the backend.
    If it has expired (e.g. 24h default), clear state so the user is
    redirected to the login screen rather than hitting 401s on every call.

    Returns True if the token is valid, False if it has expired or is absent.
    """
    token = st.session_state.get("token")
    if not token:
        return False

    _, err = api_client.get_me(token)
    if err:
        # Token expired or invalid — wipe state
        for key in ("token", "user_id", "username", "messages", "uploaded_files"):
            st.session_state[key] = None if key not in ("messages", "uploaded_files") else []
        st.session_state.token = None
        return False

    return True


# ─────────────────────────────────────────────────────────────────────────────
# SYNC UPLOADED FILES FROM BACKEND
# ─────────────────────────────────────────────────────────────────────────────

def _sync_files(token: str):
    """
    On first load after login, pull the file list from the backend
    (the user may have uploaded files in a previous session).
    Only runs once per login; subsequent uploads update state locally.
    """
    if st.session_state.get("files_synced"):
        return
    data, err = api_client.get_files(token)
    if not err and data:
        st.session_state.uploaded_files = data.get("files", [])
    st.session_state.files_synced = True


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    _inject_styles()
    _init_state()

    authenticated = _validate_token()

    if not authenticated:
        # Show full-page auth screen (no sidebar)
        auth_page.render()
    else:
        token    = st.session_state.token
        username = st.session_state.username
        user_id  = st.session_state.user_id

        # Sync file list once per session
        _sync_files(token)

        # Left sidebar: user info, file upload, controls
        sidebar.render(token, username, user_id)

        # Main panel: chat
        chat_page.render(token, username, user_id)


if __name__ == "__main__":
    main()
