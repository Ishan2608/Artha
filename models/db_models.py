"""
models/db_models.py — SQLAlchemy ORM models

Three tables:
  users          : Registered accounts (one user = one chat session)
  messages       : All conversation turns for every user
  uploaded_files : Files uploaded during a user's session

Design notes:
  - User.id is used as the session_id throughout the agent system.
    This means session_id = str(user.id) — no separate session table needed.
  - Message stores both `content` (enriched, sent to the agent) and
    `display_content` (clean original text, returned to the frontend).
    This lets the agent see document/session hints while users see clean history.
  - Cascade delete on all relationships: deleting a User wipes their messages
    and files automatically.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db import Base


def _utcnow() -> datetime:
    """Return timezone-aware UTC datetime (avoids deprecation warning in Python 3.12+)."""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships — cascade ensures child rows are deleted with the user.
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="user", cascade="all, delete-orphan", order_by="Message.id"
    )
    files: Mapped[list["UploadedFile"]] = relationship(
        "UploadedFile", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "user" | "assistant" | "system"

    # What the agent sees: may include enrichment like
    # "[System note: session_id='3'. Files uploaded: report.pdf ...]"
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # What the user sees: the raw message without any system-injected notes.
    # For "assistant" and "system" roles this is identical to `content`.
    display_content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship("User", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message id={self.id} user_id={self.user_id} role={self.role!r}>"


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_id: Mapped[str] = mapped_column(String(36), nullable=False)   # UUID4 string
    filepath: Mapped[str] = mapped_column(String(500), nullable=False)  # absolute path on disk
    filename: Mapped[str] = mapped_column(String(255), nullable=False)  # original filename
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship("User", back_populates="files")

    def __repr__(self) -> str:
        return f"<UploadedFile id={self.id} user_id={self.user_id} filename={self.filename!r}>"
