"""
main.py — FastAPI Application

All HTTP routes for the Artha backend.
Entry point for uvicorn: `uvicorn main:app --reload`

Routes
------
POST   /chat                       -> Send a message to the agent
POST   /upload?session_id=...      -> Upload a file (PDF, DOCX, Excel, CSV, TXT, PPT)
POST   /context                    -> Inject raw text context into a session
DELETE /session/{session_id}       -> Delete a session and all its uploaded files
GET    /session/{session_id}/files -> List files uploaded in a session
GET    /health                     -> Health check

Memory contract:
  run_agent() reads session history BEFORE the current message is appended.
  This route stores the ENRICHED message (with session_id note) in history so
  that on follow-up turns, document tools still receive the session_id hint.
  Both the enriched user message and the assistant reply are appended AFTER
  run_agent() returns — never before.
"""

import os
import uuid
import shutil

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from models.schemas import (
    ChatRequest,
    ChatResponse,
    UploadResponse,
    ContextRequest,
    ClearSessionResponse,
)
from utils.session_store import append_message, add_file, get_files, clear_session
from agent import run_agent


# ─────────────────────────────────────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Shree Backend",
    description=(
        "AI Financial Analyst API for Indian retail investors. "
        "Powered by LangGraph + Gemini and Groq (Llama 3.3 70B) + direct tool binding."
    ),
    version="1.0.0",
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
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main conversational endpoint.

    Flow:
      1. Build the enriched message: append session_id + file hints if files exist.
         This enriched form is what gets stored in history so follow-up turns
         still carry the session_id context for document tools.
      2. Call run_agent() — reads history, runs tools, returns text + optional data.
      3. Append ENRICHED user message to history (not the raw message).
      4. Append the assistant reply to history.
      5. Return ChatResponse.

    The 'data' field is None for plain text replies and populated with chart-ready
    JSON when the agent includes a ```data ...``` block in its response.
    """
    files   = get_files(request.session_id)

    # Always embed session_id so document tools can locate uploads on any turn.
    if files:
        file_names = ", ".join(f["filename"] for f in files)
        enriched_message = (
            f"{request.message}\n\n"
            f"[System note: session_id='{request.session_id}'. "
            f"Files uploaded in this session: {file_names}. "
            f"Use parse_document_tool(session_id) or "
            f"search_documents_tool(session_id, query) to access them.]"
        )
    else:
        # Still embed session_id even with no files — keeps history consistent
        # and allows tools to give a clean 'no files uploaded' message.
        enriched_message = (
            f"{request.message}\n\n"
            f"[System note: session_id='{request.session_id}'. "
            f"No files uploaded in this session yet.]"
        )

    try:
        result = await run_agent(request.session_id, enriched_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    # Store the ENRICHED message so subsequent turns retain the session_id note.
    # The frontend only ever sends/receives request.message (clean) and result["text"].
    append_message(request.session_id, "user",      enriched_message)
    append_message(request.session_id, "assistant", result["text"])

    return ChatResponse(
        session_id=request.session_id,
        text=result["text"],
        data=result.get("data"),
    )


@app.post("/upload", response_model=UploadResponse)
async def upload_file(
    session_id: str = Query(...),
    file: UploadFile = File(...),
):
    """
    File upload endpoint.

    Saves the file to the uploads/ directory with a UUID prefix to avoid collisions.
    Registers the file in session_store so document tools can access it.
    Supported: PDF, DOCX, DOC, XLSX, XLS, CSV, TXT, PPT, PPTX.
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type '{ext}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    file_id   = str(uuid.uuid4())
    safe_name = f"{file_id}_{file.filename or 'upload'}"
    dest      = os.path.join(settings.UPLOAD_DIR, safe_name)

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


@app.post("/context")
async def add_text_context(request: ContextRequest):
    """
    Text context injection endpoint.

    Stores raw text as a 'system' role message in session history.
    agent.py folds 'system' messages into labelled HumanMessages so Groq/Llama
    sees the context correctly despite not supporting multiple SystemMessages.
    """
    content = f"[User-provided context]:\n{request.context}"
    append_message(request.session_id, "system", content)
    return {
        "message":    "Context added to your session.",
        "char_count": len(request.context),
    }


@app.delete("/session/{session_id}", response_model=ClearSessionResponse)
async def delete_session(session_id: str):
    """
    Session cleanup endpoint.

    Deletes all uploaded files from disk, then clears the session from the
    in-memory store. File deletion happens first because clear_session() removes
    the file list — we'd lose track of what to delete if order were reversed.
    """
    files         = get_files(session_id)
    deleted_count = 0
    for f in files:
        if os.path.exists(f["filepath"]):
            os.remove(f["filepath"])
            deleted_count += 1

    clear_session(session_id)

    return ClearSessionResponse(
        message=(
            f"Session '{session_id}' cleared. "
            f"{deleted_count} uploaded file(s) deleted from disk."
        )
    )


@app.get("/session/{session_id}/files")
async def list_session_files(session_id: str):
    """
    List files registered for a session.
    Does NOT expose filepaths — internal server detail.
    """
    files = get_files(session_id)
    return {
        "session_id": session_id,
        "file_count": len(files),
        "files": [
            {"file_id": f["file_id"], "filename": f["filename"]}
            for f in files
        ],
    }


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0", "agent": "artha"}
