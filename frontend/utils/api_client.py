"""
utils/api_client.py — Centralized backend API client

Every HTTP call to the Artha backend goes through this module.
No other file should import `requests` or construct URLs.

All functions return a (data, error) tuple:
  - On success: (response_dict_or_None, None)
  - On failure: (None, error_message_string)

The `token` parameter is the Bearer JWT string stored in st.session_state.
"""

from __future__ import annotations
import requests
from config import Endpoints, AppConfig

_TIMEOUT = AppConfig.REQUEST_TIMEOUT


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────────────────────

def register(username: str, email: str, password: str) -> tuple[dict | None, str | None]:
    """Create a new account. Returns (token_response, error)."""
    try:
        r = requests.post(
            Endpoints.REGISTER,
            json={"username": username, "email": email, "password": password},
            timeout=_TIMEOUT,
        )
        if r.status_code == 201:
            return r.json(), None
        return None, r.json().get("detail", "Registration failed.")
    except requests.ConnectionError:
        return None, "Cannot reach the backend. Is the server running?"
    except Exception as e:
        return None, str(e)


def login(email: str, password: str) -> tuple[dict | None, str | None]:
    """Authenticate. Returns (token_response, error)."""
    try:
        r = requests.post(
            Endpoints.LOGIN,
            json={"email": email, "password": password},
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            return r.json(), None
        return None, r.json().get("detail", "Login failed.")
    except requests.ConnectionError:
        return None, "Cannot reach the backend. Is the server running?"
    except Exception as e:
        return None, str(e)


def get_me(token: str) -> tuple[dict | None, str | None]:
    """Fetch current user profile."""
    try:
        r = requests.get(Endpoints.ME, headers=_headers(token), timeout=_TIMEOUT)
        if r.status_code == 200:
            return r.json(), None
        return None, r.json().get("detail", "Auth error.")
    except Exception as e:
        return None, str(e)


# ─────────────────────────────────────────────────────────────────────────────
# CHAT
# ─────────────────────────────────────────────────────────────────────────────

def send_message(token: str, message: str) -> tuple[dict | None, str | None]:
    """
    Send a chat message. Returns (chat_response, error).
    chat_response keys: session_id, text, data (may be None).
    """
    try:
        r = requests.post(
            Endpoints.CHAT,
            json={"message": message},
            headers=_headers(token),
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            return r.json(), None
        return None, r.json().get("detail", "Agent error.")
    except requests.ConnectionError:
        return None, "Cannot reach the backend. Is the server running?"
    except Exception as e:
        return None, str(e)


def get_history(token: str) -> tuple[dict | None, str | None]:
    """
    Fetch conversation history.
    Returns (history_response, error).
    history_response keys: session_id, message_count, messages[{role, content, created_at}].
    """
    try:
        r = requests.get(Endpoints.CHAT_HISTORY, headers=_headers(token), timeout=_TIMEOUT)
        if r.status_code == 200:
            return r.json(), None
        return None, r.json().get("detail", "Failed to load history.")
    except requests.ConnectionError:
        return None, "Cannot reach the backend. Is the server running?"
    except Exception as e:
        return None, str(e)


def clear_history(token: str) -> tuple[dict | None, str | None]:
    """Clear all chat history and uploaded files."""
    try:
        r = requests.delete(Endpoints.CHAT_HISTORY, headers=_headers(token), timeout=_TIMEOUT)
        if r.status_code == 200:
            return r.json(), None
        return None, r.json().get("detail", "Failed to clear history.")
    except Exception as e:
        return None, str(e)


# ─────────────────────────────────────────────────────────────────────────────
# FILES
# ─────────────────────────────────────────────────────────────────────────────

def upload_file(token: str, file_bytes: bytes, filename: str) -> tuple[dict | None, str | None]:
    """Upload a file to the session. Returns (upload_response, error)."""
    try:
        r = requests.post(
            Endpoints.UPLOAD,
            files={"file": (filename, file_bytes)},
            headers=_headers(token),
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            return r.json(), None
        return None, r.json().get("detail", "Upload failed.")
    except requests.ConnectionError:
        return None, "Cannot reach the backend. Is the server running?"
    except Exception as e:
        return None, str(e)


def get_files(token: str) -> tuple[dict | None, str | None]:
    """List uploaded files for the current session."""
    try:
        r = requests.get(Endpoints.FILES, headers=_headers(token), timeout=_TIMEOUT)
        if r.status_code == 200:
            return r.json(), None
        return None, r.json().get("detail", "Failed to list files.")
    except Exception as e:
        return None, str(e)


# ─────────────────────────────────────────────────────────────────────────────
# CONTEXT
# ─────────────────────────────────────────────────────────────────────────────

def inject_context(token: str, context: str) -> tuple[dict | None, str | None]:
    """Inject raw text context into the session."""
    try:
        r = requests.post(
            Endpoints.CONTEXT,
            json={"context": context},
            headers=_headers(token),
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            return r.json(), None
        return None, r.json().get("detail", "Failed to inject context.")
    except Exception as e:
        return None, str(e)


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH
# ─────────────────────────────────────────────────────────────────────────────

def health_check() -> tuple[dict | None, str | None]:
    """Ping the backend health endpoint."""
    try:
        r = requests.get(Endpoints.HEALTH, timeout=5)
        if r.status_code == 200:
            return r.json(), None
        return None, "Backend unhealthy."
    except Exception:
        return None, "Backend unreachable."
