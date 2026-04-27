"""
db.py — SQLAlchemy database setup

Provides:
  engine       : SQLAlchemy Engine (SQLite by default, swap DATABASE_URL for Postgres)
  SessionLocal : Session factory — used directly in session_store and via get_db() in routes
  Base         : DeclarativeBase — imported by all ORM models
  get_db()     : FastAPI dependency that yields a DB session with guaranteed close
  init_db()    : Creates all tables on startup (call from main.py lifespan)

SQLite is used out-of-the-box so no infrastructure is needed.
To switch to Postgres, change DATABASE_URL in .env:
  DATABASE_URL=postgresql+psycopg2://user:pass@localhost/artha
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config import settings
DATABASE_URL = settings.DATABASE_URL

# check_same_thread=False is required for SQLite when used with FastAPI's
# async request handling (multiple threads may share the same connection).
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


def get_db():
    """
    FastAPI dependency. Yields a DB session and guarantees it is closed
    after the request completes (even on exception).

    Usage:
        @app.post("/something")
        def route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Create all tables defined in ORM models.
    Safe to call multiple times — SQLAlchemy only creates tables that don't exist yet.
    Call this once at application startup.
    """
    # Import models here so Base.metadata knows about them before create_all().
    from models.db_models import User, Message, UploadedFile  # noqa: F401
    Base.metadata.create_all(bind=engine)
