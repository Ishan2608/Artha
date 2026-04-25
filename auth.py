"""
auth.py — Authentication utilities

Provides:
  hash_password(plain)            -> bcrypt hash string
  verify_password(plain, hashed)  -> bool
  create_access_token(user_id)    -> signed JWT string
  get_current_user(token, db)     -> User ORM object  [FastAPI Depends]

JWT payload: {"sub": "<user_id>", "exp": <unix timestamp>}

Token lifetime is controlled by config.settings.ACCESS_TOKEN_EXPIRE_HOURS (default 24).
The signing secret is config.settings.SECRET_KEY — set a strong random value in .env.

Dependency injection pattern:
    from auth import get_current_user
    from models.db_models import User

    @app.get("/protected")
    async def protected(current_user: User = Depends(get_current_user)):
        return {"user_id": current_user.id}
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from db import get_db
from config import settings

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the stored *hashed* password."""
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

_ALGORITHM = "HS256"

# FastAPI reads the Bearer token from the Authorization header automatically.
# tokenUrl is the login endpoint — used by Swagger UI's "Authorize" button.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_access_token(
    user_id: int,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a signed JWT for *user_id*.

    Default expiry: settings.ACCESS_TOKEN_EXPIRE_HOURS hours.
    Returns the encoded token string.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM)


def decode_token(token: str) -> int:
    """
    Decode *token* and return the user_id (int).
    Raises HTTPException 401 on any failure.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exc
        return int(sub)
    except (JWTError, ValueError, TypeError):
        raise credentials_exc


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    FastAPI dependency that validates the Bearer token and returns the User ORM object.

    Raises HTTP 401 if the token is missing, malformed, expired, or the user
    no longer exists in the database.

    Usage:
        from auth import get_current_user
        from models.db_models import User

        @app.post("/chat")
        async def chat(current_user: User = Depends(get_current_user)):
            session_id = str(current_user.id)
    """
    from models.db_models import User  # local import avoids circular dependency

    user_id = decode_token(token)
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
