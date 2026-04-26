"""
components/chat_page.py — Main chat interface

render(token, username, user_id) draws:
  - Top header bar with Artha branding
  - Message history (loaded from st.session_state.messages on login)
  - Welcome / suggestion screen when history is empty
  - st.chat_input at the bottom
  - Charts embedded immediately below agent replies that carry data

State used:
  st.session_state.messages       : list[{role, content, created_at}]
  st.session_state.uploaded_files : list[{file_id, filename}]

State written on each agent turn:
  - Two new dicts appended to st.session_state.messages
    (the user message and the assistant reply)
"""

import streamlit as st
from utils import api_client
from utils.formatters import format_timestamp
from components import chart_card
from config import AppConfig

# ─── Suggestion prompts shown on an empty chat ─────────────────────────────────
_SUGGESTIONS = [
    ("📈", "Analyse TCS stock for the past 6 months"),
    ("🔮", "Forecast Reliance Industries for the next 30 days"),
    ("📰", "Latest news about the Indian banking sector"),
    ("📄", "Summarise the document I just uploaded"),
    ("💡", "Explain P/E ratio and how to use it"),
    ("📊", "Compare Nifty 50 vs Sensex performance this year"),
]


def render(token: str, username: str, user_id: int):
    # ── Header ─────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="artha-header">
      <div class="artha-logo">⬡ Arth<span>a</span></div>
      <div class="artha-tagline">AI FINANCIAL ANALYST · INDIAN MARKETS</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Message container ───────────────────────────────────────────────────────
    messages = st.session_state.get("messages", [])

    if not messages:
        _render_welcome(username)
    else:
        _render_messages(messages)

    # ── Chat input (always pinned to bottom) ────────────────────────────────────
    user_input = st.chat_input(
        "Ask Artha about stocks, fundamentals, forecasts, or your documents…",
        key="chat_input",
    )

    if user_input:
        _handle_input(token, user_input.strip())


# ─────────────────────────────────────────────────────────────────────────────
# WELCOME SCREEN
# ─────────────────────────────────────────────────────────────────────────────

def _render_welcome(username: str):
    st.markdown(f"""
    <div class="welcome-banner">
      <div class="title">Good to see you, {username}.</div>
      <div class="sub">Your AI financial analyst is ready. What would you like to explore?</div>
      <div class="hint">try one of these to get started ↓</div>
    </div>
    """, unsafe_allow_html=True)

    # Suggestion chips rendered as clickable buttons in a 2-column grid
    cols = st.columns(2)
    for i, (emoji, text) in enumerate(_SUGGESTIONS):
        with cols[i % 2]:
            # Use a unique key per suggestion
            if st.button(
                f"{emoji}  {text}",
                key=f"suggestion_{i}",
                use_container_width=True,
            ):
                _handle_input(st.session_state.token, text)


# ─────────────────────────────────────────────────────────────────────────────
# MESSAGE RENDERING
# ─────────────────────────────────────────────────────────────────────────────

def _render_messages(messages: list[dict]):
    """
    Render all messages from session state.
    Messages with role "user" are right-aligned (amber).
    Messages with role "assistant" are left-aligned (teal, Artha avatar).
    Each assistant message is followed by chart_card.render() if data exists.
    """
    for msg in messages:
        role    = msg.get("role", "")
        content = msg.get("content", "")
        ts      = format_timestamp(msg.get("created_at", ""))
        data    = msg.get("data")    # only present on in-session agent replies

        if role == "user":
            _user_bubble(content, ts)
        elif role == "assistant":
            _artha_bubble(content, ts)
            chart_card.render(data)


def _user_bubble(content: str, ts: str):
    st.markdown(f"""
    <div class="msg-user">
      <div>
        <div class="bubble">{_escape(content)}</div>
        <div class="ts">{ts}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def _artha_bubble(content: str, ts: str):
    # Use st.markdown for the bubble frame, then render content with st.markdown
    # so that markdown inside agent replies (bold, code, tables) is processed.
    st.markdown("""
    <div class="msg-artha">
      <div class="avatar">⬡</div>
      <div class="bubble-wrap">
        <div class="bubble">
    """, unsafe_allow_html=True)

    # Render the agent's reply as proper Markdown (handles code blocks, tables, etc.)
    st.markdown(content)

    st.markdown(f"""
        </div>
        <div class="ts">{ts}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def _thinking_bubble():
    st.markdown("""
    <div class="msg-artha">
      <div class="avatar">⬡</div>
      <div class="bubble-wrap">
        <div class="bubble">
          <div class="thinking-dots">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# MESSAGE HANDLING
# ─────────────────────────────────────────────────────────────────────────────

def _handle_input(token: str, user_input: str):
    """
    1. Append the user message to session state immediately.
    2. Show a thinking indicator.
    3. Call the backend.
    4. Append the assistant reply (with optional data) to session state.
    5. Rerun so the full page re-renders with the new messages.
    """
    from datetime import datetime, timezone

    now_iso = datetime.now(timezone.utc).isoformat()

    # Optimistically append user message so it shows right away
    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.session_state.messages.append({
        "role":       "user",
        "content":    user_input,
        "created_at": now_iso,
    })

    # Re-render messages so the user bubble appears, then show thinking
    _render_messages(st.session_state.messages)
    placeholder = st.empty()
    with placeholder.container():
        _thinking_bubble()

    # Send to backend
    with st.spinner(""):
        response, err = api_client.send_message(token, user_input)

    placeholder.empty()

    if err:
        st.session_state.messages.append({
            "role":       "assistant",
            "content":    f"⚠ {err}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "data":       None,
        })
    else:
        st.session_state.messages.append({
            "role":       "assistant",
            "content":    response.get("text", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "data":       response.get("data"),   # stored for this session's render
        })

    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _escape(text: str) -> str:
    """Minimal HTML escaping for user text rendered inside raw HTML div."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )
