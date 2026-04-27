"""
components/chat_page.py — Main chat interface

Uses st.chat_message() as the bubble container — this is the only reliable
way to nest content inside a styled wrapper in Streamlit. Raw HTML divs
opened in one st.markdown call and closed in another do NOT nest; each call
renders in its own isolated container. st.chat_message() is a true context
manager that wraps all child elements correctly.

All visual styling (colors, fonts, borders, layout) lives in styles/main.css.
"""

import streamlit as st
from utils import api_client
from utils.formatters import format_timestamp

_SUGGESTIONS = [
    ("📈", "Analyse TCS stock for the past 6 months"),
    ("🔮", "Forecast Reliance Industries for the next 30 days"),
    ("📰", "Latest news about the Indian banking sector"),
    ("📄", "Summarise the document I just uploaded"),
    ("💡", "Explain P/E ratio and how to use it"),
    ("📊", "Compare Nifty 50 vs Sensex performance this year"),
]


def render(token: str, username: str, user_id: int):
    # Header
    st.markdown("""
    <div class="artha-header">
      <div class="artha-logo">⬡ Arth<span>a</span></div>
      <div class="artha-tagline">AI FINANCIAL ANALYST · INDIAN MARKETS</div>
    </div>
    """, unsafe_allow_html=True)

    messages = st.session_state.get("messages", [])

    if not messages:
        _render_welcome(username)
    else:
        _render_messages(messages)

    user_input = st.chat_input(
        "Ask Artha about stocks, fundamentals, forecasts, or your documents…",
        key="chat_input",
    )
    if user_input:
        _handle_input(token, user_input.strip())


# ─────────────────────────────────────────────────────────────────────────────
# WELCOME
# ─────────────────────────────────────────────────────────────────────────────

def _render_welcome(username: str):
    st.markdown(f"""
    <div class="welcome-banner">
      <div class="title">Good to see you, {username}.</div>
      <div class="sub">Your AI financial analyst is ready. What would you like to explore?</div>
      <div class="hint">try one of these to get started ↓</div>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(2)
    for i, (emoji, text) in enumerate(_SUGGESTIONS):
        with cols[i % 2]:
            if st.button(f"{emoji}  {text}", key=f"suggestion_{i}", use_container_width=True):
                _handle_input(st.session_state.token, text)


# ─────────────────────────────────────────────────────────────────────────────
# MESSAGE RENDERING
# ─────────────────────────────────────────────────────────────────────────────

def _render_messages(messages: list[dict]):
    for msg in messages:
        role    = msg.get("role", "")
        content = msg.get("content", "")
        ts      = format_timestamp(msg.get("created_at", ""))
        data    = msg.get("data")

        if role == "user":
            _user_bubble(content, ts)
        elif role == "assistant":
            _artha_bubble(content, ts)
            if data:
                _render_chart(data)


def _user_bubble(content: str, ts: str):
    """
    Right-aligned user message. st.chat_message("user") is a proper context
    manager — everything inside renders correctly inside its container.
    CSS targets [data-testid="stChatMessage"]:has(.user-label) to apply
    right-alignment and amber bubble styling.
    """
    with st.chat_message("user"):
        st.markdown('<span class="user-label"></span>', unsafe_allow_html=True)
        st.markdown(content)
        st.markdown(f'<div class="msg-ts msg-ts-user">{ts}</div>', unsafe_allow_html=True)


def _artha_bubble(content: str, ts: str):
    """
    Left-aligned agent message. Uses st.chat_message("assistant") so all
    child elements (markdown, code blocks, tables) render inside one container.
    CSS targets [data-testid="stChatMessage"]:has(.artha-label).
    """
    with st.chat_message("assistant"):
        st.markdown('<span class="artha-label"></span>', unsafe_allow_html=True)
        st.markdown(content)
        st.markdown(f'<div class="msg-ts msg-ts-artha">{ts}</div>', unsafe_allow_html=True)


def _thinking_bubble():
    with st.chat_message("assistant"):
        st.markdown("""
        <div class="thinking-dots">
          <span></span><span></span><span></span>
        </div>
        """, unsafe_allow_html=True)


def _render_chart(data: dict):
    # Deferred import — avoids circular import since chart_card imports from components
    from components import chart_card
    chart_card.render(data)


# ─────────────────────────────────────────────────────────────────────────────
# INPUT HANDLING
# ─────────────────────────────────────────────────────────────────────────────

def _handle_input(token: str, user_input: str):
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.session_state.messages.append({
        "role":       "user",
        "content":    user_input,
        "created_at": now_iso,
    })

    # Show existing messages + user bubble before the API call
    _render_messages(st.session_state.messages)

    placeholder = st.empty()
    with placeholder.container():
        _thinking_bubble()

    with st.spinner(""):
        response, err = api_client.send_message(token, user_input)

    placeholder.empty()

    if err:
        st.session_state.messages.append({
            "role":       "assistant",
            "content":    f"⚠️ **Error:** {err}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "data":       None,
        })
    else:
        st.session_state.messages.append({
            "role":       "assistant",
            "content":    response.get("text", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "data":       response.get("data"),
        })

    st.rerun()
