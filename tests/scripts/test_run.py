"""
test_run.py — Artha Terminal Chat Client
=========================================
Run from the project root:
    python tests/scripts/test_run.py

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
import shutil
import uuid
from datetime import datetime

# ── Colorama ──────────────────────────────────────────────────────────────────
try:
    from colorama import init as _cinit, Fore, Back, Style
    _cinit(autoreset=True)
    _HAS_COLOR = True
except ImportError:
    class Fore:
        YELLOW = LIGHTYELLOW_EX = WHITE = LIGHTWHITE_EX = RED = CYAN = RESET = ""
    class Back:
        RESET = ""
    class Style:
        BRIGHT = DIM = RESET_ALL = NORMAL = ""
    _HAS_COLOR = False

# ── Palette ───────────────────────────────────────────────────────────────────
GOLD  = Style.BRIGHT + Fore.YELLOW   # bright gold  — headings, prompts, borders
AMBER = Fore.YELLOW                  # softer amber — labels, secondary chrome
DIM   = Style.DIM   + Fore.YELLOW    # dim gold     — hints, meta info
WHITE = Style.BRIGHT + Fore.WHITE    # bright white — body / response text
MUTED = Style.DIM   + Fore.WHITE     # dim white    — descriptions, padding
ERR   = Style.BRIGHT + Fore.RED      # red          — errors only
RESET = Style.RESET_ALL

W = 78  # terminal width

# ── Helpers ───────────────────────────────────────────────────────────────────

def _c(color: str, text: str) -> str:
    return f"{color}{text}{RESET}"

def _puts(text: str = ""):
    print(text)

def _blank():
    print()

def _rule():
    print(_c(DIM, "─" * W))

def _strip_ansi(s: str) -> str:
    import re
    return re.sub(r"\x1b\[[0-9;]*m", "", s)


# ── Box drawing ───────────────────────────────────────────────────────────────

def _box(lines: list[str], title: str = ""):
    inner = W - 2
    if title:
        head = f"┌─ {title} " + "─" * (inner - len(title) - 4) + "┐"
    else:
        head = "┌" + "─" * inner + "┐"
    print(_c(AMBER, head))
    for line in lines:
        visible = len(_strip_ansi(line))
        pad     = max(0, inner - 2 - visible)
        print(_c(AMBER, "│ ") + line + " " * pad + _c(AMBER, " │"))
    print(_c(AMBER, "└" + "─" * inner + "┘"))


# ── UI components ─────────────────────────────────────────────────────────────

def _banner(session_id: str):
    log_rel = os.path.join("tests", "logs", f"session_{session_id}.md")
    _blank()
    _box([
        _c(GOLD,  "  ⬡  A R T H A"),
        _c(MUTED, "  AI Financial Analyst"),
        _c(MUTED, "  Indian markets · Stocks · Documents · Forecasts"),
        "",
        _c(AMBER, "  Session : ") + _c(WHITE, session_id),
        _c(AMBER, "  Log     : ") + _c(MUTED, log_rel),
    ])
    _blank()


def _print_help():
    commands = [
        ("/upload",  "Upload a file (picker or type path)"),
        ("/context", "Inject raw text context"),
        ("/files",   "List uploaded files this session"),
        ("/clear",   "Reset session (files + history)"),
        ("/new",     "Start a brand-new session"),
        ("/session", "Show current session ID"),
        ("/help",    "Show this help"),
        ("/quit",    "Exit"),
    ]
    lines = [
        _c(GOLD, "  {:<12}".format(cmd)) + _c(MUTED, desc)
        for cmd, desc in commands
    ]
    _box(lines, title="Commands")
    _blank()


def _prompt_user() -> str:
    return input(_c(GOLD, "\n  ▶  ")).strip()


def _ok(msg: str):
    print(_c(GOLD,  "  ✔  ") + _c(WHITE, msg))

def _err(msg: str):
    print(_c(ERR,   "  ✖  ") + _c(WHITE, msg))

def _info(msg: str):
    print(_c(AMBER, "  ·  ") + _c(MUTED, msg))

def _thinking():
    print(_c(DIM, "\n  · · ·  thinking…\n"))


def _print_agent_reply(text: str, data: dict | None, logger: "SessionLogger"):
    logger.log_agent(text, data)
    import textwrap
    _blank()
    header = "┌─ Artha " + "─" * (W - 9) + "┐"
    footer = "└" + "─" * (W - 2) + "┘"
    print(_c(GOLD, header))
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            pad = W - 2
            print(_c(AMBER, "│") + " " * pad + _c(AMBER, "│"))
            continue
        for line in textwrap.wrap(paragraph, width=W - 4) or [""]:
            pad = W - 4 - len(line)
            print(_c(AMBER, "│ ") + _c(WHITE, line) + " " * pad + _c(AMBER, " │"))
    print(_c(GOLD, footer))
    if data:
        _blank()
        _print_data_summary(data)
    _blank()


def _print_data_summary(data: dict):
    chart_type = data.get("chart_type", "unknown")
    rows: list[tuple[str, str]] = []

    if chart_type == "candlestick":
        dates  = data.get("dates",  [])
        closes = data.get("close",  [])
        rows = [("Ticker", str(data.get("ticker", "n/a"))),
                ("Candles", str(len(dates)))]
        if dates:   rows.append(("Range",  f"{dates[0]}  →  {dates[-1]}"))
        if closes:  rows.append(("Close",  f"first={closes[0]}  last={closes[-1]}"))
    elif chart_type == "forecast":
        med  = data.get("forecast_median",  [])
        hist = data.get("historical_dates", [])
        rows = [("Symbol",  str(data.get("symbol", "n/a"))),
                ("Horizon", f"{data.get('horizon_days', 'n/a')} days")]
        if hist: rows.append(("Hist range", f"{hist[0]}  →  {hist[-1]}"))
        if med:  rows.append(("Forecast",   f"first={med[0]}  last={med[-1]}"))
    else:
        rows = [(str(k), str(v)[:60]) for k, v in list(data.items())[:6]]

    lines = [
        _c(AMBER, "  {:<14}".format(k)) + _c(MUTED, v)
        for k, v in rows
    ]
    _box(lines, title=f"Data · {chart_type.upper()}")


# ─────────────────────────────────────────────────────────────────────────────
# SESSION LOGGER
# ─────────────────────────────────────────────────────────────────────────────

class SessionLogger:
    def __init__(self, session_id: str):
        os.makedirs(_LOGS_DIR, exist_ok=True)
        self.path = os.path.join(_LOGS_DIR, f"session_{session_id}.md")
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
            import json
            self._write(
                f"\n**Data block ({data.get('chart_type', 'unknown')}):**\n"
                f"```json\n{json.dumps(data, indent=2)}\n```\n"
            )

    def log_event(self, event: str):
        self._write(f"\n> **{datetime.now().strftime('%H:%M:%S')}** — {event}\n")

    def close(self):
        self._write(f"\n---\n\n**Ended:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


# ─────────────────────────────────────────────────────────────────────────────
# LAZY PROJECT IMPORTS
# ─────────────────────────────────────────────────────────────────────────────

def _import_project() -> tuple:
    try:
        from agent import run_agent
        from utils.session_store import (
            append_message, get_history, add_file,
            get_files, clear_session,
        )
        from utils.doc_parser import parse_uploaded_file
        from config import settings
        return (
            run_agent, append_message, get_history,
            add_file, get_files, clear_session,
            parse_uploaded_file, settings,
        )
    except ImportError as e:
        _err(f"Import error: {e}")
        _err("Make sure venv is active and .env exists with API keys.")
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
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="Select a file to upload to Artha",
            filetypes=[
                ("Supported files", "*.pdf *.docx *.doc *.xlsx *.xls *.csv *.txt *.ppt *.pptx"),
                ("All files", "*.*"),
            ],
        )
        root.destroy()
        return path if path else None
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

def cmd_upload(session_id: str, add_file_fn, settings, logger: SessionLogger):
    _blank()
    _box([
        _c(GOLD,  "  1") + _c(MUTED, "  Open file picker"),
        _c(GOLD,  "  2") + _c(MUTED, "  Type path manually"),
        _c(AMBER, "  0") + _c(MUTED, "  Cancel"),
    ], title="Upload a file")
    choice = input(_c(AMBER, "  Choice: ")).strip()

    filepath = None
    if choice == "1":
        _info("Opening file picker…")
        filepath = _pick_file_tkinter()
        if not filepath:
            _info("No file selected.")
            return
    elif choice == "2":
        filepath = input(_c(AMBER, "  Path: ")).strip().strip('"').strip("'")
    else:
        _info("Cancelled.")
        return

    if not filepath or not os.path.isfile(filepath):
        _err(f"File not found: {filepath}")
        return

    ext     = os.path.splitext(filepath)[1].lower()
    allowed = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt", ".ppt", ".pptx"}
    if ext not in allowed:
        _err(f"Unsupported type '{ext}'.")
        return

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_id  = str(uuid.uuid4())
    filename = os.path.basename(filepath)
    dest     = os.path.join(settings.UPLOAD_DIR, f"{file_id}_{filename}")
    shutil.copy2(filepath, dest)
    add_file_fn(session_id, file_id, dest, filename)

    _ok(f"Uploaded  '{filename}'")
    _ok(f"File ID   {file_id}")
    logger.log_event(f"File uploaded: {filename} (id={file_id})")
    _info("You can now ask: 'What is my uploaded document about?'")


def cmd_context(session_id: str, append_message_fn, logger: SessionLogger):
    _blank()
    _info("Paste context below. Type END to finish, CANCEL to abort.")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip().upper() == "END":
            break
        if line.strip().upper() == "CANCEL":
            _info("Cancelled.")
            return
        lines.append(line)
    if not lines:
        _info("No context provided.")
        return
    text = "\n".join(lines)
    append_message_fn(session_id, "system", f"[User-provided context]:\n{text}")
    logger.log_event(f"Context injected ({len(text)} chars)")
    _ok(f"Context added ({len(text)} characters).")


def cmd_files(session_id: str, get_files_fn):
    files = get_files_fn(session_id)
    if not files:
        _info("No files uploaded yet.")
        return
    lines = []
    for i, f in enumerate(files, 1):
        exists   = _c(GOLD, "✔") if os.path.exists(f["filepath"]) else _c(ERR, "✖ MISSING")
        short_id = f["file_id"][:8] + "…"
        lines.append(
            _c(DIM,   f"  {i:<3}") +
            _c(WHITE, f"{f['filename']:<32}") +
            _c(MUTED, f"{short_id:<12}") +
            exists
        )
    _box(lines, title="Uploaded Files")


def cmd_clear(session_id: str, get_files_fn, clear_session_fn, logger: SessionLogger):
    confirm = input(_c(AMBER, "  Delete all files and history? (y/N): ")).strip().lower()
    if confirm != "y":
        _info("Cancelled.")
        return
    files   = get_files_fn(session_id)
    deleted = sum(
        1 for f in files
        if os.path.exists(f["filepath"]) and not os.remove(f["filepath"])
    )
    clear_session_fn(session_id)
    logger.log_event(f"Session cleared. {deleted} file(s) deleted.")
    _ok(f"Session cleared. {deleted} file(s) deleted.")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────────────────

async def _chat_loop():
    (
        run_agent, append_message, get_history, add_file,
        get_files, clear_session, parse_uploaded_file, settings
    ) = _import_project()

    session_id = f"cli_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    logger     = SessionLogger(session_id)

    _banner(session_id)
    _print_help()

    while True:
        try:
            user_input = _prompt_user()
        except (KeyboardInterrupt, EOFError):
            _blank()
            _info("Goodbye.")
            logger.close()
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd in ("/quit", "/exit", "/q"):
            _info("Goodbye.")
            logger.close()
            break
        elif cmd == "/help":
            _print_help()
        elif cmd == "/session":
            _info(f"Session ID: {session_id}")
        elif cmd == "/files":
            cmd_files(session_id, get_files)
        elif cmd == "/upload":
            cmd_upload(session_id, add_file, settings, logger)
        elif cmd == "/context":
            cmd_context(session_id, append_message, logger)
        elif cmd == "/clear":
            cmd_clear(session_id, get_files, clear_session, logger)
        elif cmd == "/new":
            confirm = input(_c(AMBER, "  Start new session? (y/N): ")).strip().lower()
            if confirm == "y":
                cmd_clear(session_id, get_files, clear_session, logger)
                logger.close()
                session_id = f"cli_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                logger     = SessionLogger(session_id)
                _ok(f"New session: {session_id}")
        elif cmd.startswith("/"):
            _err(f"Unknown command '{user_input}'. Type /help.")
        else:
            files   = get_files(session_id)
            message = user_input
            if files:
                file_names = ", ".join(f["filename"] for f in files)
                message = (
                    f"{user_input}\n\n"
                    f"[System note: session_id='{session_id}'. "
                    f"Files in session: {file_names}. "
                    f"Use parse_document_tool(session_id) or search_documents_tool(session_id, query).]"
                )

            logger.log_user(user_input)
            append_message(session_id, "user", user_input)
            _rule()
            _thinking()
            try:
                result = await run_agent(session_id, message)
                append_message(session_id, "assistant", result["text"])
                _print_agent_reply(result["text"], result.get("data"), logger)
            except Exception as e:
                _err(f"Agent error: {e}")
                logger.log_event(f"ERROR: {e}")
            _rule()


def main():
    try:
        asyncio.run(_chat_loop())
    except KeyboardInterrupt:
        print("\nInterrupted. Goodbye!")


if __name__ == "__main__":
    main()
