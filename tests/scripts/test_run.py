"""
test_run.py — Artha Terminal Chat Client
=========================================
Run from the project root:
    python tests/scripts/test_run.py

Gives the same conversational experience as a frontend would.
Every session is saved to tests/logs/session_YYYYMMDD_HHMMSS.md

Commands
--------
  /upload   Upload a file (Tkinter picker or manual path)
  /context  Paste multi-line text context into the session
  /files    List uploaded files this session
  /clear    Reset session (clears files + history)
  /new      Start a brand-new session
  /session  Show current session ID
  /help     Show this help
  /quit     Exit
"""

import sys
import os

# ── Path bootstrap ─────────────────────────────────────────────────────────────
_HERE         = os.path.dirname(os.path.abspath(__file__))
_TESTS_DIR    = os.path.dirname(_HERE)
_PROJECT_ROOT = os.path.dirname(_TESTS_DIR)
sys.path.insert(0, _PROJECT_ROOT)
_LOGS_DIR = os.path.join(_TESTS_DIR, "logs")
# ──────────────────────────────────────────────────────────────────────────────

import asyncio
import json
import shutil
import uuid
import textwrap
import re as _re
from datetime import datetime

# ── Colorama ──────────────────────────────────────────────────────────────────
try:
    from colorama import init as _cinit, Fore, Back, Style
    _cinit(autoreset=True)
    _HAS_COLOR = True
except ImportError:
    class Fore:
        CYAN=MAGENTA=WHITE=RED=GREEN=YELLOW=BLUE=LIGHTCYAN_EX=LIGHTMAGENTA_EX=\
        LIGHTWHITE_EX=LIGHTYELLOW_EX=LIGHTGREEN_EX=LIGHTBLUE_EX=LIGHTRED_EX=\
        BLACK=RESET=""
    class Back:
        CYAN=MAGENTA=RED=GREEN=BLUE=BLACK=LIGHTBLACK_EX=YELLOW=RESET=""
    class Style:
        BRIGHT=DIM=RESET_ALL=NORMAL=""
    _HAS_COLOR = False

# ── Theme: Neon Dusk ─────────────────────────────────────────────────────────
# Dark gray terminal. Light, comfortable, colorful.
TEAL       = Style.BRIGHT + Fore.CYAN
SOFT_TEAL  = Fore.CYAN
DIM_TEAL   = Style.DIM   + Fore.CYAN
LIME       = Style.BRIGHT + Fore.LIGHTGREEN_EX
SOFT_LIME  = Fore.LIGHTGREEN_EX
CORAL      = Style.BRIGHT + Fore.LIGHTYELLOW_EX
SOFT_CORAL = Fore.LIGHTYELLOW_EX
PINK       = Style.BRIGHT + Fore.LIGHTMAGENTA_EX
SOFT_PINK  = Fore.MAGENTA
WHITE      = Style.BRIGHT + Fore.WHITE
MUTED      = Style.DIM   + Fore.WHITE
ERR_FG     = Style.BRIGHT + Fore.LIGHTRED_EX

# Badges
BG_ARTHA   = Back.CYAN    + Style.BRIGHT + Fore.BLACK
BG_USER    = Back.MAGENTA + Style.BRIGHT + Fore.WHITE
BG_OK      = Back.GREEN   + Style.BRIGHT + Fore.BLACK
BG_ERR     = Back.RED     + Style.BRIGHT + Fore.WHITE
BG_INFO    = Back.BLACK   + Style.DIM    + Fore.CYAN
BG_DATA    = Back.CYAN    + Style.BRIGHT + Fore.BLACK
BG_CMD     = Back.MAGENTA + Style.BRIGHT + Fore.WHITE

RESET = Style.RESET_ALL
W     = 82  # terminal width — all layout derived from this


# ── Primitives ────────────────────────────────────────────────────────────────

def _c(color: str, text: str) -> str:
    return f"{color}{text}{RESET}"

def _strip_ansi(s: str) -> str:
    return _re.sub(r"\x1b\[[0-9;]*m", "", s)

def _vlen(s: str) -> int:
    return len(_strip_ansi(s))

def _blank():
    print()

def _thin():
    print(_c(DIM_TEAL, "─" * W))

def _thick():
    print(_c(TEAL, "━" * W))


# ── Box ───────────────────────────────────────────────────────────────────────

def _box(lines: list[str], title: str = "", color=None):
    color  = color or SOFT_TEAL
    inner  = W - 2
    border = _c(color, "│")
    if title:
        t     = f"─ {title} "
        head  = "┌" + t + "─" * max(0, inner - len(t)) + "┐"
    else:
        head  = "┌" + "─" * inner + "┐"
    print(_c(color, head))
    for line in lines:
        vis = _vlen(line)
        pad = max(0, inner - 2 - vis)
        print(border + " " + line + " " * pad + " " + border)
    print(_c(color, "└" + "─" * inner + "┘"))


# ── Components ────────────────────────────────────────────────────────────────

def _banner(session_id: str):
    log_rel = os.path.join("tests", "logs", f"session_{session_id[:20]}.md")
    _blank()
    _thick()
    # Logo row
    print(f"  {_c(BG_ARTHA, '  ⬡  ARTHA  ')}  {_c(WHITE, 'AI Financial Analyst')}  "
          f"{_c(MUTED, '· Indian markets · Stocks · Forecasts · Docs')}")
    _thin()
    print(f"  {_c(CORAL, 'Session')}  {_c(SOFT_PINK, '·')}  {_c(WHITE, session_id)}")
    print(f"  {_c(CORAL, 'Log    ')}  {_c(SOFT_PINK, '·')}  {_c(MUTED,  log_rel)}")
    _thick()
    _blank()


def _print_help():
    commands = [
        ("/upload",   "Upload a file  (PDF · DOCX · XLSX · CSV · TXT · PPT)"),
        ("/context",  "Inject plain-text context or instructions"),
        ("/files",    "List uploaded files in this session"),
        ("/history",  "Print conversation history (clean display view)"),
        ("/clear",    "Clear session  (history + files)"),
        ("/new",      "Start a brand-new session"),
        ("/session",  "Show current session ID"),
        ("/help",     "Show this help"),
        ("/quit",     "Exit"),
    ]
    lines = []
    for cmd, desc in commands:
        lines.append(
            _c(BG_CMD, f" {cmd:<10}")
            + "  "
            + _c(MUTED, desc)
        )
    _box(lines, title="Commands", color=SOFT_PINK)
    _blank()


def _prompt() -> str:
    try:
        return input(_c(CORAL, "\n  ▶  ")).strip()
    except EOFError:
        return "/quit"


def _ok(msg: str):
    print(f"  {_c(BG_OK, ' ✔ ')}  {_c(WHITE, msg)}")

def _err(msg: str):
    print(f"  {_c(BG_ERR, ' ✖ ')}  {_c(ERR_FG, msg)}")

def _info(msg: str):
    print(f"  {_c(BG_INFO, ' · ')}  {_c(MUTED, msg)}")

def _thinking():
    print(_c(DIM_TEAL, f"\n  {'· ' * 18}\n  Thinking…\n"))


def _print_user(text: str):
    _blank()
    badge  = _c(BG_USER, "  You  ")
    prefix = f"  {badge}  "
    indent = " " * (_vlen(prefix))
    for i, line in enumerate(textwrap.wrap(text, width=W - _vlen(prefix)) or [""]):
        if i == 0:
            print(prefix + _c(WHITE, line))
        else:
            print(indent + _c(WHITE, line))


def _print_agent(text: str, data: dict | None, logger: "SessionLogger"):
    logger.log_agent(text, data)
    _blank()
    # Header
    header = _c(TEAL, "┌") + _c(TEAL, "─ ") + _c(BG_ARTHA, "  Artha  ") + \
             _c(TEAL, " " + "─" * (W - 14) + "┐")
    footer = _c(TEAL, "└" + "─" * (W - 2) + "┘")
    b      = _c(TEAL, "│")
    print(header)
    for para in text.split("\n"):
        if not para.strip():
            print(b + " " * (W - 2) + b)
            continue
        for line in textwrap.wrap(para, width=W - 4) or [""]:
            pad = W - 4 - len(line)
            print(b + " " + _c(WHITE, line) + " " * pad + " " + b)
    print(footer)
    if data:
        _blank()
        _print_data_card(data)
    _blank()


def _print_data_card(data: dict):
    ct   = data.get("chart_type", "unknown")
    rows: list[tuple[str, str]] = []

    if ct == "candlestick":
        dates  = data.get("dates",  [])
        closes = data.get("close",  [])
        rows = [
            ("Type",    "Candlestick Chart"),
            ("Symbol",  str(data.get("symbol", "n/a"))),
            ("Candles", str(len(dates))),
        ]
        if dates:   rows.append(("Range",  f"{dates[0]}  →  {dates[-1]}"))
        if closes:  rows.append(("Close",  f"open={closes[0]}  close={closes[-1]}"))

    elif ct == "forecast":
        med  = data.get("forecast_median",  [])
        hist = data.get("historical_dates", [])
        rows = [
            ("Type",    "Forecast Chart"),
            ("Symbol",  str(data.get("symbol", "n/a"))),
            ("Horizon", f"{data.get('horizon_days', '?')} days"),
        ]
        if hist: rows.append(("Hist range",    f"{hist[0]}  →  {hist[-1]}"))
        if med:  rows.append(("Forecast range", f"₹ {med[0]}  →  ₹ {med[-1]}"))

    else:
        rows = [(str(k), str(v)[:60]) for k, v in list(data.items())[:6]]

    # Compact two-column card
    W2     = W - 4
    col1_w = min(max(len(r[0]) for r in rows) + 1, W2 // 3)
    col2_w = W2 - col1_w - 3
    seg1   = "─" * (col1_w + 2)
    seg2   = "─" * (col2_w + 2)
    mg     = "  "
    b      = _c(SOFT_TEAL, "│")

    title_txt = f"─ Chart Data · {ct.upper()} "
    title_bar = mg + _c(TEAL, "┌" + title_txt + "─" * max(0, W2 - len(title_txt)) + "┐")
    print(title_bar)
    print(mg + _c(SOFT_TEAL, "┌" + seg1 + "┬" + seg2 + "┐"))
    for i, (k, v) in enumerate(rows):
        kc = f" {k[:col1_w]:<{col1_w}} "
        vc = f" {str(v)[:col2_w]:<{col2_w}} "
        print(mg + b + _c(CORAL, kc) + b + _c(WHITE, vc) + b)
        if i < len(rows) - 1:
            print(mg + _c(SOFT_TEAL, "├" + seg1 + "┼" + seg2 + "┤"))
    print(mg + _c(SOFT_TEAL, "└" + seg1 + "┴" + seg2 + "┘"))


# ─────────────────────────────────────────────────────────────────────────────
# SESSION LOGGER
# ─────────────────────────────────────────────────────────────────────────────

class SessionLogger:
    def __init__(self, session_id: str):
        os.makedirs(_LOGS_DIR, exist_ok=True)
        fname     = f"session_{session_id[:40]}.md"
        self.path = os.path.join(_LOGS_DIR, fname)
        self._write(
            f"# Artha Session — {session_id}\n\n"
            f"**Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n"
        )

    def _write(self, text: str):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(text)

    def log_user(self, message: str):
        self._write(f"\n### 🧑 You\n{message}\n")

    def log_agent(self, text: str, data: dict | None = None):
        self._write(f"\n### 🤖 Artha\n{text}\n")
        if data:
            self._write(
                f"\n**Data block ({data.get('chart_type', 'unknown')}):**\n"
                f"```json\n{json.dumps(data, indent=2, default=str)}\n```\n"
            )

    def log_event(self, event: str):
        self._write(f"\n> **{datetime.now().strftime('%H:%M:%S')}** — {event}\n")

    def close(self):
        self._write(f"\n---\n\n**Ended:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        _info(f"Session log saved → {os.path.relpath(self.path)}")


# ─────────────────────────────────────────────────────────────────────────────
# LAZY PROJECT IMPORTS
# ─────────────────────────────────────────────────────────────────────────────

def _import_project():
    try:
        from agent import run_agent
        from utils.session_store import (
            append_message, get_history, get_display_history,
            add_file, get_files, clear_session,
        )
        from config import settings
        from db import init_db
        return (
            run_agent, append_message, get_history, get_display_history,
            add_file, get_files, clear_session, settings, init_db,
        )
    except ImportError as e:
        _err(f"Import error: {e}")
        _err("Activate your venv and ensure .env has API keys.")
        sys.exit(1)
    except Exception as e:
        _err(f"Startup error: {e}")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# FILE PICKER
# ─────────────────────────────────────────────────────────────────────────────

def _pick_file_tkinter() -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="Select a file for Artha",
            filetypes=[
                ("Supported", "*.pdf *.docx *.doc *.xlsx *.xls *.csv *.txt *.ppt *.pptx"),
                ("All files", "*.*"),
            ],
        )
        root.destroy()
        return path or None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

ALLOWED_EXT = {".pdf",".docx",".doc",".xlsx",".xls",".csv",".txt",".ppt",".pptx"}


def cmd_upload(session_id: str, add_file_fn, settings, logger: SessionLogger):
    _blank()
    _box([
        _c(CORAL, "  1") + "  " + _c(MUTED, "Open file picker  (GUI)"),
        _c(CORAL, "  2") + "  " + _c(MUTED, "Type path manually"),
        _c(MUTED, "  0") + "  " + _c(MUTED, "Cancel"),
    ], title="Upload a File", color=SOFT_CORAL)

    choice = input(_c(CORAL, "  Choice: ")).strip()
    filepath = None

    if choice == "1":
        _info("Opening file picker…")
        filepath = _pick_file_tkinter()
        if not filepath:
            _info("No file selected."); return
    elif choice == "2":
        filepath = input(_c(CORAL, "  Path: ")).strip().strip('"').strip("'")
    else:
        _info("Cancelled."); return

    if not filepath or not os.path.isfile(filepath):
        _err(f"File not found: {filepath}"); return

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in ALLOWED_EXT:
        _err(f"Unsupported type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXT))}"); return

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_id  = str(uuid.uuid4())
    filename = os.path.basename(filepath)
    dest     = os.path.join(settings.UPLOAD_DIR, f"{file_id}_{filename}")
    shutil.copy2(filepath, dest)
    add_file_fn(session_id, file_id, dest, filename)

    _ok(f"Uploaded   '{filename}'")
    _ok(f"File ID    {file_id[:8]}…")
    logger.log_event(f"File uploaded: {filename}  (id={file_id})")
    _info("Try: 'Summarise my uploaded document' or 'What does section 3 say?'")


def cmd_context(session_id: str, append_message_fn, logger: SessionLogger):
    _blank()
    _info("Paste your context below.")
    _info("Type  END   on its own line to finish.")
    _info("Type  CANCEL  to abort.")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip().upper() == "END":
            break
        if line.strip().upper() == "CANCEL":
            _info("Cancelled."); return
        lines.append(line)
    if not lines:
        _info("No context provided."); return
    text = "\n".join(lines)
    append_message_fn(session_id, "system", f"[User-provided context]:\n{text}")
    logger.log_event(f"Context injected ({len(text)} chars)")
    _ok(f"Context added  ({len(text):,} characters)")


def cmd_files(session_id: str, get_files_fn):
    files = get_files_fn(session_id)
    if not files:
        _info("No files uploaded yet."); return
    lines = []
    for i, f in enumerate(files, 1):
        exists = _c(LIME, "✔ on disk") if os.path.exists(f["filepath"]) else _c(ERR_FG, "✖ missing")
        lines.append(
            _c(MUTED,  f"  {i:<3}")
            + _c(WHITE, f"{f['filename']:<34}")
            + _c(MUTED, f"{f['file_id'][:8]}…  ")
            + exists
        )
    _box(lines, title="Uploaded Files", color=SOFT_LIME)


def cmd_clear(session_id: str, get_files_fn, clear_session_fn, logger: SessionLogger):
    confirm = input(_c(ERR_FG, "  Delete all history and files? (y/N): ")).strip().lower()
    if confirm != "y":
        _info("Cancelled."); return
    files   = get_files_fn(session_id)
    deleted = 0
    for f in files:
        if os.path.exists(f["filepath"]):
            os.remove(f["filepath"])
            deleted += 1
    clear_session_fn(session_id)
    logger.log_event(f"Session cleared. {deleted} file(s) deleted.")
    _ok(f"Session cleared. {deleted} file(s) deleted from disk.")


def cmd_history(session_id: str, get_display_history_fn):
    """
    Print the clean conversation history — same view as GET /chat/history.

    Uses get_display_history() which:
      - Returns only 'user' and 'assistant' turns (system context injections excluded)
      - Returns display_content for user messages (clean original text, not the
        enriched version with [System note:] appended by the agent turn)
      - Includes created_at timestamps
    """
    history = get_display_history_fn(session_id)
    if not history:
        _info("No conversation history yet."); return

    _blank()
    _thick()
    print(f"  {_c(BG_INFO, '  History  ')}  {_c(MUTED, f'{len(history)} message(s) · session {session_id}')}")
    _thin()
    for m in history:
        role = m["role"]
        text = m["content"]
        ts   = m.get("created_at", "")
        ts_str = f"  {_c(MUTED, str(ts)[:19])}" if ts else ""

        if role == "user":
            badge = _c(BG_USER, "  You  ")
            _blank()
            print(f"  {badge}{ts_str}")
            for line in textwrap.wrap(text, width=W - 6) or [""]:
                print(f"      {_c(WHITE, line)}")
        elif role == "assistant":
            badge = _c(BG_ARTHA, "  Artha  ")
            _blank()
            print(f"  {badge}{ts_str}")
            for para in text.split("\n"):
                if not para.strip():
                    continue
                for line in textwrap.wrap(para, width=W - 6) or [""]:
                    print(f"      {_c(MUTED, line)}")
    _blank()
    _thick()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────────────────

async def _chat_loop():
    (
        run_agent, append_message, get_history, get_display_history,
        add_file, get_files, clear_session, settings, init_db,
    ) = _import_project()

    # Ensure all DB tables exist before any session_store call.
    # Safe to call every run — SQLAlchemy only creates tables that don't exist.
    init_db()

    session_id = f"cli_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    logger     = SessionLogger(session_id)

    _banner(session_id)
    _print_help()

    try:
        while True:
            try:
                user_input = _prompt()
            except KeyboardInterrupt:
                _blank(); _info("Use /quit to exit gracefully."); continue

            if not user_input:
                continue

            cmd = user_input.lower()

            # ── Commands ──────────────────────────────────────────────────────
            if cmd in ("/quit", "/exit", "/q"):
                _info("Goodbye.")
                logger.close()
                break

            elif cmd == "/help":
                _print_help()

            elif cmd == "/session":
                _info(f"Session ID : {session_id}")
                _info(f"Log file   : {os.path.relpath(logger.path)}")

            elif cmd == "/files":
                cmd_files(session_id, get_files)

            elif cmd == "/history":
                cmd_history(session_id, get_display_history)

            elif cmd == "/upload":
                cmd_upload(session_id, add_file, settings, logger)

            elif cmd == "/context":
                cmd_context(session_id, append_message, logger)

            elif cmd == "/clear":
                cmd_clear(session_id, get_files, clear_session, logger)

            elif cmd == "/new":
                confirm = input(_c(ERR_FG, "  Start a new session? (y/N): ")).strip().lower()
                if confirm == "y":
                    cmd_clear(session_id, get_files, clear_session, logger)
                    logger.close()
                    session_id = f"cli_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    logger     = SessionLogger(session_id)
                    _blank()
                    _ok(f"New session started: {session_id}")
                    _info(f"Log → {os.path.relpath(logger.path)}")

            elif cmd.startswith("/"):
                _err(f"Unknown command '{user_input}'. Type /help.")

            # ── Agent turn ────────────────────────────────────────────────────
            else:
                files = get_files(session_id)

                # Build the enriched message that carries session_id to doc tools.
                # Mirrors the exact enrichment logic in main.py /chat so that
                # session_id context persists on follow-up turns without the user
                # having to repeat themselves.
                if files:
                    file_names = ", ".join(f["filename"] for f in files)
                    enriched = (
                        f"{user_input}\n\n"
                        f"[System note: session_id='{session_id}'. "
                        f"Files in session: {file_names}. "
                        f"Use parse_document_tool(session_id) or "
                        f"search_documents_tool(session_id, query).]"
                    )
                else:
                    enriched = (
                        f"{user_input}\n\n"
                        f"[System note: session_id='{session_id}'. No files uploaded yet.]"
                    )

                logger.log_user(user_input)
                _print_user(user_input)
                _thin()
                _thinking()

                try:
                    result = await run_agent(session_id, enriched)

                    # Store enriched content for agent memory, but pass the
                    # original clean text as display_content so /history and
                    # GET /chat/history never expose the [System note:] injection.
                    # This mirrors the append_message calls in main.py /chat.
                    append_message(
                        session_id, "user",
                        content=enriched,
                        display_content=user_input,
                    )
                    append_message(session_id, "assistant", result["text"])

                    _print_agent(result["text"], result.get("data"), logger)

                except Exception as e:
                    _err(f"Agent error: {e}")
                    logger.log_event(f"ERROR: {type(e).__name__}: {e}")

                _thin()

    except Exception as e:
        _err(f"Unexpected crash: {e}")
        logger.log_event(f"CRASH: {e}")
    finally:
        logger.close()


def main():
    try:
        asyncio.run(_chat_loop())
    except KeyboardInterrupt:
        print("\n  Interrupted. Goodbye!")


if __name__ == "__main__":
    main()
