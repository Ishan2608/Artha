"""
main.py — FastAPI Application

All HTTP routes for the Artha backend.
Entry point for uvicorn: `uvicorn main:app --reload`

Auth routes (no token required)
--------------------------------
POST   /auth/register              -> Create account, returns JWT
POST   /auth/login                 -> Verify credentials, returns JWT
GET    /auth/me                    -> Returns current user profile (token required)

Chat routes  [all require Bearer token]
---------------------------------------
POST   /chat                       -> Send a message to Artha, get reply
GET    /chat/history               -> Full conversation history (clean, display-ready)
DELETE /chat/history               -> Clear conversation + delete uploaded files from disk

File routes  [all require Bearer token]
----------------------------------------
POST   /upload                     -> Upload a file (PDF, DOCX, Excel, CSV, TXT, PPT)
GET    /files                      -> List files uploaded in this session
POST   /context                    -> Inject raw text context into the session

Misc
----
GET    /health                     -> Health check (no auth)

Session / memory contract
--------------------------
  session_id = str(user.id)  — derived from the JWT, never sent by the client.
  run_agent() reads session history BEFORE the current message is appended.
  Both the enriched user message (with session_id note) and the assistant reply
  are appended AFTER run_agent() returns — never before.
  GET /chat/history returns display_content (clean text), not the enriched version.
"""

import os
import uuid
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from config import settings
from db import get_db, init_db
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from models.db_models import User
from models.schemas import (
    # auth
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    # chat
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
    ChatMessageItem,
    # upload
    UploadResponse,
    # misc
    ContextRequest,
    ClearSessionResponse,
)
from utils.session_store import (
    append_message,
    add_file,
    get_files,
    clear_session,
    get_display_history,
)
from multi_agent import run_agent


# ─────────────────────────────────────────────────────────────────────────────
# APP LIFESPAN — creates DB tables once on startup
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup tasks before yielding, shutdown tasks after."""
    init_db()   # creates tables if they don't exist — safe to call every boot
    yield
    # (add shutdown cleanup here if needed in future)


# ─────────────────────────────────────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Artha Backend",
    description=(
        "AI Financial Analyst API for Indian retail investors. "
        "Powered by LangGraph + Gemini / Groq."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # tighten to specific origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".doc",
    ".xlsx", ".xls", ".csv",
    ".txt", ".ppt", ".pptx",
}


# ─────────────────────────────────────────────────────────────────────────────
# AUTH ROUTES  (no token required)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Create a new user account and return a JWT.

    Fails with 409 if the username or email is already taken.
    Password is bcrypt-hashed before storage — never stored in plain text.
    """
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    if db.query(User).filter(User.username == request.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username is already taken.",
        )

    user = User(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
    )


@app.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate with email + password. Returns a JWT on success.

    Always returns the same generic 401 for wrong email or wrong password —
    intentionally vague to avoid leaking whether an email is registered.
    """
    user = db.query(User).filter(User.email == request.email, User.is_active == True).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
    )


@app.get("/auth/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return UserResponse(
        user_id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at.isoformat(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# CHAT ROUTES  [require Bearer token]
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Main conversational endpoint.

    session_id is derived from the authenticated user's id — the client does
    not send it. This enforces the one-user → one-chat design.

    Flow:
      1. Build enriched message: append session_id + file hints so the agent
         can invoke document tools on any turn, even after page refresh.
      2. Call run_agent() — it reads history, runs tools, returns text + optional data.
      3. Append ENRICHED user message to DB history (agent memory).
         Also store the CLEAN original message as display_content for the history UI.
      4. Append the assistant reply.
      5. Return ChatResponse.

    The 'data' field is None for plain text replies and populated with chart-ready
    JSON when the agent includes a ```data ...``` block in its response.
    """
    session_id = str(current_user.id)
    files = get_files(session_id)

    # Enrich the message so the agent always knows the session_id and what
    # files are available, regardless of which turn it is in the conversation.
    if files:
        file_names = ", ".join(f["filename"] for f in files)
        enriched_message = (
            f"{request.message}\n\n"
            f"[System note: session_id='{session_id}'. "
            f"Files uploaded in this session: {file_names}. "
            f"Use parse_document_tool(session_id) or "
            f"search_documents_tool(session_id, query) to access them.]"
        )
    else:
        enriched_message = (
            f"{request.message}\n\n"
            f"[System note: session_id='{session_id}'. "
            f"No files uploaded in this session yet.]"
        )

    try:
        result = await run_agent(session_id, enriched_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    # Store enriched version for agent memory, clean version for display.
    append_message(
        session_id,
        "user",
        content=enriched_message,
        display_content=request.message,   # ← what the frontend shows
    )
    append_message(session_id, "assistant", result["text"])

    return ChatResponse(
        session_id=session_id,
        text=result["text"],
        data=result.get("data"),
    )


@app.get("/chat/history", response_model=ChatHistoryResponse)
async def chat_history(current_user: User = Depends(get_current_user)):
    """
    Return the full conversation history for the authenticated user.

    Only user and assistant turns are returned (system context injections are
    omitted). User messages show the clean original text, not the enriched
    version with session notes.
    """
    session_id = str(current_user.id)
    raw = get_display_history(session_id)
    messages = [
        ChatMessageItem(
            role=m["role"],
            content=m["content"],
            created_at=m["created_at"],
        )
        for m in raw
    ]
    return ChatHistoryResponse(
        session_id=session_id,
        message_count=len(messages),
        messages=messages,
    )


@app.delete("/chat/history", response_model=ClearSessionResponse)
async def clear_chat_history(current_user: User = Depends(get_current_user)):
    """
    Clear the conversation history and delete all uploaded files for the user.

    File deletion happens before clear_session() because clear_session() removes
    the filepath metadata — we'd lose track of what to delete if order were reversed.
    """
    session_id = str(current_user.id)
    files = get_files(session_id)
    deleted_count = 0
    for f in files:
        if os.path.exists(f["filepath"]):
            os.remove(f["filepath"])
            deleted_count += 1

    clear_session(session_id)

    return ClearSessionResponse(
        message=(
            f"Conversation history cleared. "
            f"{deleted_count} uploaded file(s) deleted from disk."
        )
    )


# ─────────────────────────────────────────────────────────────────────────────
# FILE ROUTES  [require Bearer token]
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    File upload endpoint.

    Saves the file to UPLOAD_DIR with a UUID prefix to avoid name collisions.
    Registers the file in the DB so document tools can locate it on any future turn.
    Supported: PDF, DOCX, DOC, XLSX, XLS, CSV, TXT, PPT, PPTX.
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type '{ext}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    session_id = str(current_user.id)
    file_id    = str(uuid.uuid4())
    safe_name  = f"{file_id}_{file.filename or 'upload'}"
    dest       = os.path.join(settings.UPLOAD_DIR, safe_name)

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(dest, "wb") as out:
        shutil.copyfileobj(file.file, out)

    add_file(session_id, file_id, dest, file.filename or safe_name)

    return UploadResponse(
        file_id=file_id,
        filename=file.filename or safe_name,
        message=(
            f"'{file.filename}' uploaded successfully. "
            "You can now ask questions about it."
        ),
    )


@app.get("/files")
async def list_files(current_user: User = Depends(get_current_user)):
    """List files registered for the authenticated user's session."""
    session_id = str(current_user.id)
    files = get_files(session_id)
    return {
        "session_id": session_id,
        "file_count": len(files),
        "files": [
            {"file_id": f["file_id"], "filename": f["filename"]}
            for f in files
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# CONTEXT ROUTE  [requires Bearer token]
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/context")
async def add_text_context(
    request: ContextRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Text context injection endpoint.

    Stores raw text as a 'system' role message in session history.
    agent.py folds 'system' messages into labelled HumanMessages so Groq/Llama
    sees the context correctly despite not supporting multiple SystemMessages.

    This message is stored in DB but excluded from GET /chat/history (UI display).
    """
    session_id = str(current_user.id)
    content    = f"[User-provided context]:\n{request.context}"
    append_message(session_id, "system", content)
    return {
        "message":    "Context added to your session.",
        "char_count": len(request.context),
    }


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK  (no auth)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0", "agent": "artha"}
