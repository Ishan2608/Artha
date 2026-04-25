"""
utils/session_store.py — Persistent, DB-backed session store

Drop-in replacement for the original in-memory session_store.
The public API is identical so agent.py and multi_agent.py require zero changes.

session_id is now str(user.id) — set by main.py after authentication.

Public API
----------
get_history(session_id)
    Returns list of {"role": str, "content": str} dicts in chronological order.
    `content` is the enriched version (with system notes) fed to the agent.

append_message(session_id, role, content, display_content=None)
    Persists a message.  display_content defaults to content when omitted
    (correct for "assistant" and "system" roles).

add_file(session_id, file_id, filepath, filename)
    Records an uploaded file for the session.

get_files(session_id)
    Returns list of {"file_id", "filepath", "filename"} dicts.

clear_session(session_id)
    Deletes all messages and file records for the session (does NOT delete
    the files from disk — that's the caller's responsibility).

get_display_history(session_id)
    Like get_history() but returns display_content + created_at timestamp.
    Used by GET /chat/history to return clean conversation to the frontend.
"""

from db import SessionLocal
from models.db_models import Message, UploadedFile


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _user_id(session_id: str) -> int:
    """Convert session_id string to int user_id."""
    return int(session_id)


# ---------------------------------------------------------------------------
# History (agent memory)
# ---------------------------------------------------------------------------

def get_history(session_id: str) -> list[dict]:
    """
    Return all messages for the session in chronological order.
    Each dict: {"role": str, "content": str}

    `content` is the enriched text (includes [System note: session_id=...])
    so the agent always has context about which session it's operating in.
    """
    uid = _user_id(session_id)
    db = SessionLocal()
    try:
        rows = (
            db.query(Message)
            .filter(Message.user_id == uid)
            .order_by(Message.id)
            .all()
        )
        return [{"role": r.role, "content": r.content} for r in rows]
    finally:
        db.close()


def append_message(
    session_id: str,
    role: str,
    content: str,
    display_content: str | None = None,
) -> None:
    """
    Persist a single message to the database.

    Parameters
    ----------
    session_id      : str(user.id)
    role            : "user" | "assistant" | "system"
    content         : Full text (may include session/file hints for the agent).
    display_content : Clean text shown to the user.
                      Defaults to `content` when omitted (correct for assistant/system).
    """
    uid = _user_id(session_id)
    db = SessionLocal()
    try:
        msg = Message(
            user_id=uid,
            role=role,
            content=content,
            display_content=display_content if display_content is not None else content,
        )
        db.add(msg)
        db.commit()
    finally:
        db.close()


def get_display_history(session_id: str) -> list[dict]:
    """
    Return conversation history formatted for frontend display.

    Each dict: {"role": str, "content": str, "created_at": str (ISO-8601)}

    Uses display_content (clean user text) rather than the enriched agent content.
    System-role messages (injected context) are excluded — they are internal.
    """
    uid = _user_id(session_id)
    db = SessionLocal()
    try:
        rows = (
            db.query(Message)
            .filter(Message.user_id == uid, Message.role != "system")
            .order_by(Message.id)
            .all()
        )
        return [
            {
                "role": r.role,
                "content": r.display_content,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# File tracking
# ---------------------------------------------------------------------------

def add_file(
    session_id: str,
    file_id: str,
    filepath: str,
    filename: str,
) -> None:
    """Record an uploaded file for the given session."""
    uid = _user_id(session_id)
    db = SessionLocal()
    try:
        record = UploadedFile(
            user_id=uid,
            file_id=file_id,
            filepath=filepath,
            filename=filename,
        )
        db.add(record)
        db.commit()
    finally:
        db.close()


def get_files(session_id: str) -> list[dict]:
    """
    Return all files uploaded in the session.
    Each dict: {"file_id": str, "filepath": str, "filename": str}
    """
    uid = _user_id(session_id)
    db = SessionLocal()
    try:
        rows = (
            db.query(UploadedFile)
            .filter(UploadedFile.user_id == uid)
            .all()
        )
        return [
            {
                "file_id": r.file_id,
                "filepath": r.filepath,
                "filename": r.filename,
            }
            for r in rows
        ]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Session cleanup
# ---------------------------------------------------------------------------

def clear_session(session_id: str) -> None:
    """
    Delete all messages and file records for the session from the database.

    IMPORTANT: This does NOT delete files from disk.
    The caller (main.py delete_session route) must delete disk files first,
    because this function removes the filepath metadata needed to find them.
    """
    uid = _user_id(session_id)
    db = SessionLocal()
    try:
        db.query(Message).filter(Message.user_id == uid).delete()
        db.query(UploadedFile).filter(UploadedFile.user_id == uid).delete()
        db.commit()
    finally:
        db.close()
