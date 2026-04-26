"""
components/sidebar.py — Left sidebar

render(token, username, user_id) draws the full sidebar:
  - User identity card with live status dot
  - File upload widget with instant backend POST
  - Uploaded files list
  - Context injection expander
  - Session controls (clear history, sign out)

All mutations (upload, clear) modify st.session_state directly so the
chat page refreshes without a full reload where possible.
"""

import streamlit as st
from utils import api_client
from utils.formatters import ext_icon
from config import AppConfig


def render(token: str, username: str, user_id: int):
    with st.sidebar:
        _user_card(username, user_id)
        _file_section(token)
        _context_section(token)
        _session_controls(token)


# ─────────────────────────────────────────────────────────────────────────────
# USER CARD
# ─────────────────────────────────────────────────────────────────────────────

def _user_card(username: str, user_id: int):
    st.markdown(f"""
    <div class="user-card">
      <div class="greeting">Logged in as</div>
      <div class="username">{username}</div>
      <div class="session-id">
        <span class="status-dot"></span>
        session · {user_id}
      </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# FILE UPLOAD
# ─────────────────────────────────────────────────────────────────────────────

def _file_section(token: str):
    st.markdown('<div class="sidebar-label">Documents</div>', unsafe_allow_html=True)

    # Upload widget
    uploaded = st.file_uploader(
        "Upload a file",
        type=AppConfig.ALLOWED_EXTENSIONS,
        key="file_uploader",
        label_visibility="collapsed",
        help="Supported: PDF, DOCX, XLSX, CSV, TXT, PPT",
    )

    if uploaded is not None:
        # Avoid re-uploading if this file was already sent this session
        already_sent = any(
            f["filename"] == uploaded.name
            for f in st.session_state.get("uploaded_files", [])
        )
        if not already_sent:
            with st.spinner(f"Uploading {uploaded.name}…"):
                data, err = api_client.upload_file(
                    token, uploaded.getvalue(), uploaded.name
                )
            if err:
                st.error(f"Upload failed: {err}")
            else:
                # Append to local file list without hitting /files again
                if "uploaded_files" not in st.session_state:
                    st.session_state.uploaded_files = []
                st.session_state.uploaded_files.append({
                    "file_id":  data["file_id"],
                    "filename": data["filename"],
                })
                st.success(f"✔ {uploaded.name} uploaded")

    # File list
    files = st.session_state.get("uploaded_files", [])
    if files:
        for f in files:
            icon = ext_icon(f["filename"])
            name = f["filename"]
            fid  = f["file_id"][:8]
            st.markdown(f"""
            <div class="file-pill">
              <div class="icon">{icon}</div>
              <div class="info">
                <div class="name" title="{name}">{name}</div>
                <div class="id">{fid}…</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="padding:4px 20px 8px">'
            '<span style="font-family:\'JetBrains Mono\',monospace;font-size:11px;'
            'color:var(--text-muted)">No files uploaded yet.</span>'
            '</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# CONTEXT INJECTION
# ─────────────────────────────────────────────────────────────────────────────

def _context_section(token: str):
    st.markdown('<div class="sidebar-label">Inject Context</div>', unsafe_allow_html=True)
    with st.expander("Paste raw context…", expanded=False):
        ctx_text = st.text_area(
            "Context",
            key="context_input",
            height=120,
            placeholder="Paste any text you want Artha to remember for this session…",
            label_visibility="collapsed",
        )
        if st.button("Inject →", key="inject_btn", use_container_width=True):
            if ctx_text.strip():
                with st.spinner("Injecting context…"):
                    _, err = api_client.inject_context(token, ctx_text.strip())
                if err:
                    st.error(f"Failed: {err}")
                else:
                    st.success(f"✔ {len(ctx_text):,} chars injected")
                    st.session_state.context_input = ""
            else:
                st.warning("Context is empty.")


# ─────────────────────────────────────────────────────────────────────────────
# SESSION CONTROLS
# ─────────────────────────────────────────────────────────────────────────────

def _session_controls(token: str):
    st.markdown('<div class="sidebar-label">Session</div>', unsafe_allow_html=True)
    st.markdown('<div style="padding: 0 12px; display:flex; flex-direction:column; gap:6px">', unsafe_allow_html=True)

    # Stats row
    msg_count  = len(st.session_state.get("messages", []))
    file_count = len(st.session_state.get("uploaded_files", []))
    st.markdown(
        f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px">'
        f'<span class="stat-chip">💬 {msg_count} messages</span>'
        f'<span class="stat-chip">📁 {file_count} files</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.button("🗑  Clear History", key="clear_btn", use_container_width=True):
        st.session_state.confirm_clear = True

    if st.session_state.get("confirm_clear"):
        st.warning("This will delete your entire conversation and all uploaded files. Are you sure?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Yes, clear", key="confirm_yes"):
                with st.spinner("Clearing…"):
                    _, err = api_client.clear_history(token)
                if err:
                    st.error(f"Failed: {err}")
                else:
                    st.session_state.messages       = []
                    st.session_state.uploaded_files = []
                    st.session_state.confirm_clear  = False
                    st.rerun()
        with c2:
            if st.button("Cancel", key="confirm_no"):
                st.session_state.confirm_clear = False
                st.rerun()

    # Sign out
    if st.button("⎋  Sign Out", key="signout_btn", use_container_width=True):
        _sign_out()

    st.markdown('</div>', unsafe_allow_html=True)


def _sign_out():
    """Clear all session state and return to auth screen."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
