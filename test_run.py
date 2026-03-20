"""
test_run.py — Artha Terminal Chat Client

Beautiful terminal UI via `rich`. Every session is automatically saved
to logs/session_YYYYMMDD_HHMMSS.md — plain Markdown, readable in any editor.

pip install rich colorama

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

import asyncio
import os
import sys
import shutil
import uuid
from datetime import datetime

# ── Rich ──────────────────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.table import Table
    from rich.prompt import Prompt
    from rich.rule import Rule
    from rich import box
    _console = Console()
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False
    _console = None

# ── Colorama fallback when rich is absent ─────────────────────────────────────
if not _HAS_RICH:
    try:
        from colorama import init as _cinit, Fore, Style
        _cinit(autoreset=True)
    except ImportError:
        class Fore:
            CYAN = GREEN = YELLOW = RED = MAGENTA = BLUE = WHITE = ""
        class Style:
            BRIGHT = RESET_ALL = DIM = ""


# ─────────────────────────────────────────────────────────────────────────────
# SESSION LOGGER
# Writes a Markdown file per session to logs/
# Format is clean enough to read in Obsidian, VS Code, any Markdown viewer.
# ─────────────────────────────────────────────────────────────────────────────

class SessionLogger:
    def __init__(self, session_id: str):
        os.makedirs("logs", exist_ok=True)
        self.path = os.path.join("logs", f"session_{session_id}.md")
        self._write(f"# Artha Session — {session_id}\n\n"
                    f"**Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n")

    def _write(self, text: str):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(text)

    def log_user(self, message: str):
        self._write(f"\n### 🧑 You\n{message}\n")

    def log_agent(self, text: str, data: dict | None = None):
        self._write(f"\n### 🤖 Artha\n{text}\n")
        if data:
            import json
            self._write(f"\n**Data block ({data.get('chart_type', 'unknown')}):**\n"
                        f"```json\n{json.dumps(data, indent=2)}\n```\n")

    def log_event(self, event: str):
        self._write(f"\n> **{datetime.now().strftime('%H:%M:%S')}** — {event}\n")

    def log_separator(self):
        self._write("\n---\n")

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
        return run_agent, append_message, get_history, add_file, get_files, clear_session, parse_uploaded_file, settings
    except ImportError as e:
        _err(f"Import error: {e}")
        _err("Make sure venv is active and .env exists with API keys.")
        sys.exit(1)
    except Exception as e:
        _err(f"Startup error: {e}")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY HELPERS  (rich when available, colorama fallback otherwise)
# ─────────────────────────────────────────────────────────────────────────────

def _print(text: str = ""):
    if _HAS_RICH:
        _console.print(text)
    else:
        print(text)

def _err(msg: str):
    if _HAS_RICH:
        _console.print(f"[bold red]  ✖  {msg}[/]")
    else:
        print(f"  ✖  {msg}")

def _ok(msg: str):
    if _HAS_RICH:
        _console.print(f"[bold green]  ✔  {msg}[/]")
    else:
        print(f"  ✔  {msg}")

def _info(msg: str):
    if _HAS_RICH:
        _console.print(f"[yellow]  ▸  {msg}[/]")
    else:
        print(f"  ▸  {msg}")

def _rule(title: str = ""):
    if _HAS_RICH:
        _console.rule(f"[dim]{title}[/]" if title else "")
    else:
        print("─" * 60)

def _banner(session_id: str):
    if _HAS_RICH:
        _console.print(Panel.fit(
            "[bold cyan]⬡  A R T H A[/]  [dim]— AI Financial Analyst[/]\n"
            "[dim]Indian markets • Stocks • Documents • Forecasts[/]",
            border_style="cyan",
            padding=(1, 4),
        ))
        _console.print(f"  [dim]Session:[/] [yellow]{session_id}[/]")
        _console.print(f"  [dim]Log:[/]     [dim]logs/session_{session_id}.md[/]\n")
    else:
        print(f"\n  ARTHA — AI Financial Analyst")
        print(f"  Session: {session_id}\n")

def _print_help():
    if _HAS_RICH:
        t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        t.add_column(style="cyan bold", no_wrap=True)
        t.add_column(style="white")
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
        for cmd, desc in commands:
            t.add_row(cmd, desc)
        _console.print(Panel(t, title="[bold]Commands[/]", border_style="dim", padding=(0, 1)))
    else:
        print("\n  Commands: /upload /context /files /clear /new /session /help /quit\n")

def _print_agent_reply(text: str, data: dict | None, logger: SessionLogger):
    logger.log_agent(text, data)
    if _HAS_RICH:
        _console.print()
        _console.print(Panel(
            Markdown(text),
            title="[bold green]Artha[/]",
            border_style="green",
            padding=(1, 2),
        ))
        if data:
            _print_data_summary(data)
    else:
        print("\n  Artha:")
        for line in text.split("\n"):
            print(f"    {line}")
        print()

def _print_data_summary(data: dict):
    chart_type = data.get("chart_type", "unknown")
    if _HAS_RICH:
        t = Table(title=f"📊 Data Block — {chart_type.upper()}", box=box.SIMPLE,
                  show_header=False, border_style="magenta", padding=(0, 2))
        t.add_column(style="dim", no_wrap=True)
        t.add_column(style="white")
        if chart_type == "candlestick":
            dates  = data.get("dates",  [])
            closes = data.get("close",  [])
            t.add_row("Ticker",  str(data.get("ticker",   "n/a")))
            t.add_row("Candles", str(len(dates)))
            if dates:   t.add_row("Range",  f"{dates[0]}  →  {dates[-1]}")
            if closes:  t.add_row("Close",  f"first={closes[0]}  last={closes[-1]}")
        elif chart_type == "forecast":
            med  = data.get("forecast_median", [])
            hist = data.get("historical_dates", [])
            t.add_row("Symbol",   str(data.get("symbol", "n/a")))
            t.add_row("Horizon",  f"{data.get('horizon_days','n/a')} days")
            if hist: t.add_row("History", f"{len(hist)} points, last={hist[-1]}")
            if med:  t.add_row("Forecast", f"{len(med)} pts, range {min(med):.2f}–{max(med):.2f}")
        elif chart_type in ("line", "bar"):
            t.add_row("Label",  str(data.get("label", "n/a")))
            t.add_row("Points", str(len(data.get("values", []))))
        elif chart_type == "table":
            t.add_row("Columns", str(len(data.get("columns", []))))
            t.add_row("Rows",    str(len(data.get("rows", []))))
        else:
            keys = [k for k in data if k != "chart_type"]
            t.add_row("Keys", ", ".join(keys[:10]))
        _console.print(t)


# ─────────────────────────────────────────────────────────────────────────────
# TKINTER FILE PICKER
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
    _print()
    if _HAS_RICH:
        _console.print(Panel("[bold]Upload a file[/]\n"
                             "[cyan]1[/]  Open file picker\n"
                             "[cyan]2[/]  Type path manually\n"
                             "[cyan]0[/]  Cancel",
                             border_style="cyan", padding=(0, 2)))
        choice = Prompt.ask("  Choice", choices=["0", "1", "2"], default="1")
    else:
        print("  [1] Picker  [2] Manual  [0] Cancel")
        choice = input("  Choice: ").strip()

    filepath = None
    if choice == "1":
        _info("Opening file picker…")
        filepath = _pick_file_tkinter()
        if not filepath:
            _info("No file selected.")
            return
    elif choice == "2":
        filepath = input("  Path: ").strip().strip('"').strip("'")
    else:
        _info("Cancelled.")
        return

    if not filepath or not os.path.isfile(filepath):
        _err(f"File not found: {filepath}")
        return

    ext = os.path.splitext(filepath)[1].lower()
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

    _ok(f"Uploaded '{filename}'")
    _ok(f"File ID : {file_id}")
    logger.log_event(f"File uploaded: {filename} (id={file_id})")
    _print(f"  [dim]You can now ask: 'What is my uploaded document about?'[/]")


def cmd_context(session_id: str, append_message_fn, logger: SessionLogger):
    _print(f"\n[cyan]Paste context below. Type [bold]END[/bold] to finish, [bold]CANCEL[/bold] to abort.[/]")
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
    if _HAS_RICH:
        t = Table(box=box.SIMPLE, show_header=True, header_style="bold cyan")
        t.add_column("#",        style="dim",   width=3)
        t.add_column("Filename", style="white")
        t.add_column("File ID",  style="dim")
        t.add_column("On disk",  style="green")
        for i, f in enumerate(files, 1):
            exists = "✔" if os.path.exists(f["filepath"]) else "[red]✖ MISSING[/]"
            t.add_row(str(i), f["filename"], f["file_id"][:8] + "…", exists)
        _console.print(t)
    else:
        for i, f in enumerate(files, 1):
            print(f"  [{i}] {f['filename']}  |  {f['file_id']}")


def cmd_clear(session_id: str, get_files_fn, clear_session_fn, logger: SessionLogger):
    if _HAS_RICH:
        confirm = Prompt.ask("  [red]Delete all files and history?[/]", choices=["y", "n"], default="n")
    else:
        confirm = input("  Delete all? (y/N): ").strip().lower()
    if confirm != "y":
        _info("Cancelled.")
        return
    files = get_files_fn(session_id)
    deleted = sum(1 for f in files if os.path.exists(f["filepath"]) and not os.remove(f["filepath"]))
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
            if _HAS_RICH:
                user_input = Prompt.ask(f"\n[bold blue]You[/]").strip()
            else:
                user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            _print(f"\n[yellow]Goodbye![/]")
            logger.close()
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        if cmd in ("/quit", "/exit", "/q"):
            _print("[yellow]Goodbye![/]")
            logger.close()
            break
        elif cmd == "/help":
            _print_help()
        elif cmd == "/session":
            _print(f"  Session ID: [yellow]{session_id}[/]")
        elif cmd == "/files":
            cmd_files(session_id, get_files)
        elif cmd == "/upload":
            cmd_upload(session_id, add_file, settings, logger)
        elif cmd == "/context":
            cmd_context(session_id, append_message, logger)
        elif cmd == "/clear":
            cmd_clear(session_id, get_files, clear_session, logger)
        elif cmd == "/new":
            if _HAS_RICH:
                confirm = Prompt.ask("  [yellow]Start new session?[/]", choices=["y", "n"], default="n")
            else:
                confirm = input("  Start new session? (y/N): ").strip().lower()
            if confirm == "y":
                cmd_clear(session_id, get_files, clear_session, logger)
                logger.close()
                session_id = f"cli_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                logger     = SessionLogger(session_id)
                _print(f"  New session: [yellow]{session_id}[/]")
        elif cmd.startswith("/"):
            _err(f"Unknown command '{user_input}'. Type /help.")
        else:
            # Build message with session_id + file hints for document tools
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
            _info("Thinking…")
            try:
                result = await run_agent(session_id, message)
                append_message(session_id, "assistant", result["text"])
                _print_agent_reply(result["text"], result.get("data"), logger)
            except Exception as e:
                _err(f"Agent error: {e}")
                logger.log_event(f"ERROR: {e}")


def main():
    try:
        asyncio.run(_chat_loop())
    except KeyboardInterrupt:
        print("\nInterrupted. Goodbye!")


if __name__ == "__main__":
    main()
