from pydantic import BaseModel, Field
from typing import Optional, Any

"""
models/schemas.py — Pydantic request / response schemas
 
All schemas used by FastAPI route handlers live here.
ORM models live in models/db_models.py — kept separate intentionally.
"""
 
from typing import Any
from pydantic import BaseModel, EmailStr, Field
 
 
# ─────────────────────────────────────────────────────────────────────────────
# AUTH SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────
 
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
 
 
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
 
 
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
 
 
class UserResponse(BaseModel):
    user_id: int
    username: str
    email: str
    created_at: str   # ISO-8601 string; avoids datetime serialisation edge cases
    
# ─────────────────────────────────────────────────────────────────────────────
# CHAT SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────
 
class ChatRequest(BaseModel):
    """
    Body for POST /chat.
    session_id is NO LONGER sent by the client — it is derived from the JWT.
    """
    message: str = Field(..., min_length=1, description="User's message to Artha")
 
 
class ChatMessageItem(BaseModel):
    """A single message in the conversation history (frontend-friendly)."""
    role: str            # "user" | "assistant"
    content: str         # Clean display text
    created_at: str      # ISO-8601
 
 
class ChatHistoryResponse(BaseModel):
    """Response for GET /chat/history."""
    session_id: str
    message_count: int
    messages: list[ChatMessageItem]
 
 
class ChatResponse(BaseModel):
    session_id: str
    text: str
    data: Any | None = None   # Chart-ready JSON when the agent emits a ```data``` block
 
 
# ─────────────────────────────────────────────────────────────────────────────
# UPLOAD / FILE SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────
 
class UploadResponse(BaseModel):
    file_id: str
    filename: str
    message: str
 
 
# ─────────────────────────────────────────────────────────────────────────────
# CONTEXT SCHEMA
# ─────────────────────────────────────────────────────────────────────────────
 
class ContextRequest(BaseModel):
    context: str = Field(..., min_length=1)
 
 
# ─────────────────────────────────────────────────────────────────────────────
# SESSION SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────
 
class ClearSessionResponse(BaseModel):
    message: str
