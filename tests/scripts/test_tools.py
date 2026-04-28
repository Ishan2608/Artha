"""
test_tools.py — Artha Tool Test Suite
======================================
Run from the project root:
    python tests/scripts/test_tools.py

Tests every tool with realistic Indian-market data.
Results are saved to tests/logs/test_tools_YYYYMMDD_HHMMSS.log
"""

import sys
import os
import json
import textwrap
import re as _re
from datetime import datetime

# ── Path bootstrap ─────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_TESTS_DIR = os.path.dirname(_HERE)
_PROJECT_ROOT = os.path.dirname(_TESTS_DIR)
sys.path.insert(0, _PROJECT_ROOT)
_LOGS_DIR = os.path.join(_TESTS_DIR, "logs")
# ──────────────────────────────────────────────────────────────────────────────

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

# ── Theme: Neon Dusk ──────────────────────────────────────────────────────────
# Deep dark-gray terminal. Light, comfortable, colorful FG+BG labels.
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

# Badges — BG + FG
BG_PASS    = Back.GREEN   + Style.BRIGHT + Fore.BLACK
BG_FAIL    = Back.RED     + Style.BRIGHT + Fore.WHITE
BG_SKIP    = Back.YELLOW  + Style.BRIGHT + Fore.BLACK
BG_JSON    = Back.CYAN    + Style.BRIGHT + Fore.BLACK
BG_SECTION = Back.MAGENTA + Style.BRIGHT + Fore.WHITE
BG_TOOL    = Back.CYAN    + Style.DIM    + Fore.BLACK
BG_IDX     = Back.GREEN   + Style.DIM    + Fore.BLACK
BG_HEADER  = Back.BLACK   + Style.BRIGHT + Fore.CYAN

RESET = Style.RESET_ALL
W = 82


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


# ── Structure ─────────────────────────────────────────────────────────────────

def _header(num: int, title: str):
    _blank()
    _thick()
    badge = _c(BG_SECTION, f"  TEST {num:02d}  ")
    print(f"  {badge}  {_c(WHITE, title)}")
    _thin()

def _section(label: str):
    _blank()
    badge = _c(BG_TOOL, f" {label} ")
    print(f"  {badge}")

def _kv(key: str, value, indent: int = 4):
    val_str = str(value)
    prefix  = " " * indent
    dot     = _c(SOFT_PINK, " · ")
    line    = prefix + _c(CORAL, key) + dot + _c(WHITE, val_str)
    if _vlen(line) > W:
        wrapped = textwrap.fill(
            val_str,
            width=W - indent - 2,
            initial_indent=prefix + _c(CORAL, key) + dot,
            subsequent_indent=prefix + " " * (len(key) + 3),
        )
        print(wrapped)
    else:
        print(line)

def _preview(label: str, text: str, chars: int = 200, indent: int = 4):
    prefix  = " " * indent
    clean   = str(text).replace("\n", " ").strip()
    snippet = clean[:chars] + (_c(MUTED, " …") if len(clean) > chars else "")
    dot     = _c(SOFT_PINK, " · ")
    print(textwrap.fill(
        snippet,
        width=W - indent,
        initial_indent=prefix + _c(CORAL, label) + dot,
        subsequent_indent=prefix + " " * (len(label) + 3),
    ))


# ── Table ─────────────────────────────────────────────────────────────────────

def _table(rows: list[tuple], title: str = ""):
    if not rows:
        print(_c(MUTED, "    (no rows)"))
        return
    MARGIN, PADDING, DIVIDER = 2, 2, 1
    STRUCTURE = MARGIN + 2 + PADDING * 2 + DIVIDER  # 9
    usable  = W - STRUCTURE
    col1_w  = min(max(len(str(r[0])) for r in rows) + 1, usable // 3)
    col2_w  = usable - col1_w
    seg1    = "─" * (col1_w + 2)
    seg2    = "─" * (col2_w + 2)
    mg      = " " * MARGIN
    b       = _c(SOFT_TEAL, "│")
    if title:
        inner = W - MARGIN - 2
        t_txt = f"─ {title} "
        t_bar = mg + _c(TEAL, "┌" + t_txt + "─" * max(0, inner - len(t_txt)) + "┐")
        print(t_bar)
    print(mg + _c(SOFT_TEAL, "┌" + seg1 + "┬" + seg2 + "┐"))
    for i, (k, v) in enumerate(rows):
        k_cell = f" {str(k)[:col1_w]:<{col1_w}} "
        v_cell = f" {str(v)[:col2_w]:<{col2_w}} "
        print(mg + b + _c(CORAL, k_cell) + b + _c(WHITE, v_cell) + b)
        if i < len(rows) - 1:
            print(mg + _c(SOFT_TEAL, "├" + seg1 + "┼" + seg2 + "┤"))
    print(mg + _c(SOFT_TEAL, "└" + seg1 + "┴" + seg2 + "┘"))


# ── Badges ────────────────────────────────────────────────────────────────────

def _pass(label: str = ""):
    badge = _c(BG_PASS, " ✔ PASS ")
    print(f"  {badge}" + (_c(MUTED, f"  {label}") if label else ""))

def _fail(label: str, reason: str = ""):
    badge = _c(BG_FAIL, " ✖ FAIL ")
    print(f"  {badge}  {_c(ERR_FG, label)}" + (_c(MUTED, f"  ·  {reason}") if reason else ""))

def _skip(reason: str):
    badge = _c(BG_SKIP, " ◌ SKIP ")
    print(f"  {badge}  {_c(MUTED, reason)}")

def _json_check(obj, label: str) -> bool:
    try:
        json.dumps(obj)
        print(f"  {_c(BG_JSON, ' ✔ JSON ')}  {_c(MUTED, label)}")
        return True
    except (TypeError, ValueError) as e:
        print(f"  {_c(BG_FAIL, ' ✖ JSON ')}  {_c(ERR_FG, label)}  {_c(MUTED, str(e))}")
        return False


# ── Logger ────────────────────────────────────────────────────────────────────

class TestLogger:
    def __init__(self):
        os.makedirs(_LOGS_DIR, exist_ok=True)
        ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = os.path.join(_LOGS_DIR, f"test_tools_{ts}.log")
        self._buf: list[str] = []
        self._write(f"Artha Tool Test Suite\nRun: {datetime.now()}\n{'='*60}\n")

    def _write(self, text: str):
        self._buf.append(text)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(text)

    def log(self, text: str):
        self._write(_strip_ansi(text) + "\n")

    def log_result(self, test_name: str, passed: bool, detail: str = ""):
        status = "PASS" if passed else "FAIL"
        self._write(f"[{status}] {test_name}" + (f"  —  {detail}" if detail else "") + "\n")

    def log_json(self, label: str, obj):
        try:
            self._write(f"\n--- {label} ---\n{json.dumps(obj, indent=2, default=str)}\n")
        except Exception as e:
            self._write(f"\n--- {label} (not serializable) ---\n{e}\n")

    def close(self, passed: int, failed: int):
        self._write(f"\n{'='*60}\nTotal: {passed} passed, {failed} failed\n")
        print(_c(MUTED, f"\n  Log saved → {os.path.relpath(self.path)}"))


_LOG: TestLogger | None = None


# ─────────────────────────────────────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_session_store():
    _header(1, "Session Store — DB-backed")
    from db import init_db
    from utils.session_store import (
        append_message, get_history, get_display_history,
        clear_session, add_file, get_files,
    )

    # Use a numeric string to match the real session_id format (str(user.id))
    sid = "99999"

    # DB-backed clear_session never raises — no try/except needed
    clear_session(sid)

    # ── 1. append_message with display_content (mirrors the /chat enrichment flow) ──
    _section("append_message · user + assistant + system")
    enriched_msg = (
        "Analyse HDFC Bank for me.\n\n"
        "[System note: session_id='99999'. No files uploaded in this session yet.]"
    )
    append_message(
        sid, "user",
        content=enriched_msg,
        display_content="Analyse HDFC Bank for me.",   # clean version for UI
    )
    append_message(sid, "assistant", "HDFC Bank (HDFCBANK.NS) is a leading private sector bank…")
    append_message(sid, "system",    "[User-provided context]: Focus on dividend history.")

    # ── 2. get_history — full history including system messages (used by agent) ──
    _section("get_history · agent view (all roles, enriched content)")
    hist = get_history(sid)
    _table(
        [(f"[{i+1}] {m['role']}", m["content"][:70]) for i, m in enumerate(hist)],
        title="session · get_history"
    )
    assert len(hist) == 3, f"Expected 3 messages, got {len(hist)}"
    assert hist[0]["role"] == "user"
    assert hist[1]["role"] == "assistant"
    assert hist[2]["role"] == "system"
    # Agent must receive the enriched content, not the clean display version
    assert "[System note:" in hist[0]["content"], \
        "get_history must return enriched content for agent memory"
    _pass("get_history returns all 3 messages with enriched content")
    _LOG.log_result("session_store_get_history", True)

    # ── 3. get_display_history — UI view (user + assistant only, clean text) ──
    _section("get_display_history · UI view (user + assistant, display_content)")
    display = get_display_history(sid)
    _table(
        [(f"[{i+1}] {m['role']}", m["content"][:70]) for i, m in enumerate(display)],
        title="session · get_display_history"
    )
    assert len(display) == 2, \
        f"Expected 2 display messages (system excluded), got {len(display)}"
    assert display[0]["role"] == "user"
    assert display[1]["role"] == "assistant"
    # Must expose display_content (clean text), not the enriched version with [System note:]
    assert "[System note:" not in display[0]["content"], \
        "get_display_history must return display_content, not enriched content"
    assert display[0]["content"] == "Analyse HDFC Bank for me.", \
        f"Expected clean display text, got: {display[0]['content']}"
    # Each record must carry a timestamp for the history UI
    assert "created_at" in display[0], "get_display_history entries must include created_at"
    _pass("get_display_history: 2 messages, system excluded, clean display_content returned")
    _LOG.log_result("session_store_display_history", True)

    # ── 4. File registration ──
    _section("add_file · get_files")
    add_file(sid, "uuid-test-001", "/tmp/annual_report.pdf", "annual_report.pdf")
    files = get_files(sid)
    _table([(f["file_id"][:12], f["filename"]) for f in files], title="registered files")
    assert len(files) == 1, f"Expected 1 file, got {len(files)}"
    assert files[0]["file_id"] == "uuid-test-001"
    assert files[0]["filename"] == "annual_report.pdf"
    assert "filepath" in files[0], "get_files must include 'filepath' for document tools"
    _pass("File registration and retrieval work correctly")
    _LOG.log_result("session_store_files", True)

    # ── 5. clear_session — wipes messages AND files ──
    _section("clear_session · idempotent cleanup")
    clear_session(sid)
    assert get_history(sid) == [], "get_history must be empty after clear_session"
    assert get_files(sid)   == [], "get_files must be empty after clear_session"
    # Second clear on an empty session must not raise
    clear_session(sid)
    _pass("clear_session wipes messages and files; safe to call on non-existent session")
    _LOG.log_result("session_store_clear", True)

    _LOG.log_result("session_store", True)


def test_formatters():
    _header(2, "Formatters — Real yfinance Data (HDFCBANK.NS)")
    import yfinance as yf
    from utils.formatters import sanitize_dataframe, sanitize_info_dict

    ticker = yf.Ticker("HDFCBANK.NS")

    # 2a. sanitize_dataframe
    _section("sanitize_dataframe · OHLCV 5d")
    raw_hist = ticker.history(period="5d", interval="1d")
    if raw_hist.empty:
        _fail("yfinance history", "No data — check network")
        _LOG.log_result("formatters_dataframe", False, "no data"); return

    result_df = sanitize_dataframe(raw_hist)
    rows = [(col, f"{vals[0]}  (+{len(vals)-1} more)" if isinstance(vals, list) and vals else repr(vals))
            for col, vals in result_df.items()]
    _table(rows, title="HDFCBANK · 5d OHLCV")
    ok = _json_check(result_df, "sanitize_dataframe")
    _LOG.log_result("formatters_dataframe", ok)
    _LOG.log_json("sanitize_dataframe", result_df)

    # 2b. sanitize_info_dict
    _section("sanitize_info_dict · HDFCBANK")
    raw_info = ticker.info
    if not raw_info:
        _fail("yfinance .info", "empty"); return

    result_info = sanitize_info_dict(raw_info)
    showcase = ["longName","currentPrice","marketCap","trailingPE",
                "priceToBook","debtToEquity","returnOnEquity","dividendYield",
                "fiftyTwoWeekHigh","fiftyTwoWeekLow","recommendationKey"]
    _table([(k, result_info.get(k, "—")) for k in showcase if k in result_info],
           title="sanitize_info_dict · HDFCBANK")
    none_count = sum(1 for v in result_info.values() if v is None)
    _kv("Total keys", len(result_info))
    _kv("None values", f"{none_count} / {len(result_info)}")
    ok = _json_check(result_info, "sanitize_info_dict")
    _LOG.log_result("formatters_info", ok)
    _LOG.log_json("sanitize_info_dict", result_info)


def test_stock_info():
    _header(3, "Stock Info — TCS · RELIANCE · INFY")
    from tools.stock_data import get_stock_info

    keys = ["longName","currentPrice","previousClose","trailingPE",
            "marketCap","fiftyTwoWeekHigh","fiftyTwoWeekLow",
            "debtToEquity","returnOnEquity","recommendationKey"]

    for sym in ["TCS", "RELIANCE", "INFY"]:
        _section(f"get_stock_info · {sym}")
        result = get_stock_info(sym, "NSE")
        if "error" in result:
            _fail(sym, result["error"])
            _LOG.log_result(f"stock_info_{sym}", False, result["error"]); continue
        _table([(k, result.get(k, "—")) for k in keys if k in result], title=f"{sym} · NSE")
        ok = _json_check(result, f"get_stock_info · {sym}")
        _LOG.log_result(f"stock_info_{sym}", ok)
        _LOG.log_json(f"stock_info_{sym}", result)


def test_stock_history():
    _header(4, "Stock History — WIPRO 3mo · SBIN 1y weekly")
    from tools.stock_data import get_stock_history

    cases = [
        ("WIPRO",  "NSE", "3mo", "1d"),
        ("SBIN",   "NSE", "1y",  "1wk"),
    ]
    for sym, ex, period, interval in cases:
        _section(f"{sym} · {period} · {interval}")
        r = get_stock_history(sym, ex, period, interval)
        if "error" in r:
            _fail(sym, r["error"])
            _LOG.log_result(f"stock_history_{sym}", False, r["error"]); continue
        dates  = r.get("dates", [])
        closes = r.get("close", [])
        highs  = r.get("high",  [])
        lows   = r.get("low",   [])
        rows = [("Candles", len(dates))]
        if dates:
            rows += [
                ("Range",       f"{dates[0]}  →  {dates[-1]}"),
                ("First Close", f"₹ {closes[0]}"),
                ("Last Close",  f"₹ {closes[-1]}"),
                ("Period High", f"₹ {max(highs)}" if highs else "—"),
                ("Period Low",  f"₹ {min(lows)}"  if lows  else "—"),
            ]
        _table(rows, title=f"{sym} · {period} · {interval}")
        ok = _json_check(r, f"get_stock_history · {sym}")
        _LOG.log_result(f"stock_history_{sym}", ok)
        _LOG.log_json(f"stock_history_{sym}", r)


def test_financials():
    _header(5, "Financials — RELIANCE Income · TATAMOTORS Balance Sheet")
    from tools.stock_data import get_financials

    cases = [
        ("RELIANCE",   "NSE", "income",        False),
        ("TATAMOTORS", "NSE", "balance_sheet",  False),
        ("INFY",       "NSE", "cashflow",       True),   # quarterly
    ]
    for sym, ex, stmt, qtr in cases:
        label = f"{sym} · {stmt} · {'quarterly' if qtr else 'annual'}"
        _section(label)
        r = get_financials(sym, ex, stmt, qtr)
        if "error" in r:
            _fail(sym, r["error"])
            _LOG.log_result(f"financials_{sym}_{stmt}", False, r["error"]); continue
        data = r.get("data", {})
        # Show first 5 metric keys and their first value
        preview_rows = [(k, str(v[0]) if isinstance(v, list) and v else str(v))
                        for k, v in list(data.items())[:5]]
        _table(preview_rows, title=label)
        ok = _json_check(r, f"get_financials · {label}")
        _LOG.log_result(f"financials_{sym}_{stmt}", ok)
        _LOG.log_json(f"financials_{sym}", r)


def test_corporate_actions():
    _header(6, "Corporate Actions — ITC Dividends / INFY Splits")
    from tools.stock_data import get_corporate_actions

    for sym in ["ITC", "INFY"]:
        _section(f"get_corporate_actions · {sym}")
        r = get_corporate_actions(sym, "NSE")
        if "error" in r:
            _fail(sym, r["error"])
            _LOG.log_result(f"corporate_{sym}", False, r["error"]); continue
        divs   = r.get("last_5_dividends", [])
        splits = r.get("all_splits", [])
        rows   = [(f"Div [{i+1}]", f"₹ {d['amount']}  on  {d['date'][:10]}")
                  for i, d in enumerate(divs)]
        rows  += [(f"Split [{i+1}]", f"{s['ratio']}:1  on  {s['date'][:10]}")
                  for i, s in enumerate(splits)]
        if rows:
            _table(rows, title=f"{sym} Corporate Actions")
        else:
            _kv("note", "No dividends or splits on record")
        ok = _json_check(r, f"corporate_actions · {sym}")
        _LOG.log_result(f"corporate_{sym}", ok)


def test_analyst_data():
    _header(7, "Analyst Data — SBIN · HDFCBANK")
    from tools.stock_data import get_analyst_data

    for sym in ["SBIN", "HDFCBANK"]:
        _section(f"get_analyst_data · {sym}")
        r = get_analyst_data(sym, "NSE")
        if "error" in r:
            _fail(sym, r["error"])
            _LOG.log_result(f"analyst_{sym}", False, r["error"]); continue
        rows = [
            ("Current Price",    f"₹ {r.get('current_price', '—')}"),
            ("Mean Target",      f"₹ {r.get('mean_target',  '—')}"),
            ("High Target",      f"₹ {r.get('high_target',  '—')}"),
            ("Low Target",       f"₹ {r.get('low_target',   '—')}"),
            ("Recommendation",   r.get("recommendation_key", "—")),
        ]
        _table(rows, title=f"{sym} · Analyst Consensus")
        ok = _json_check(r, f"get_analyst_data · {sym}")
        _LOG.log_result(f"analyst_{sym}", ok)


def test_holders():
    _header(8, "Holders — TATASTEEL")
    from tools.stock_data import get_holders

    _section("get_holders · TATASTEEL")
    r = get_holders("TATASTEEL", "NSE")
    if "error" in r:
        _fail("TATASTEEL", r["error"])
        _LOG.log_result("holders_TATASTEEL", False, r["error"]); return

    inst = r.get("top_5_institutional", {})
    mf   = r.get("top_5_mutual_fund",   {})
    _kv("Institutional holders keys", list(inst.keys())[:4] if isinstance(inst, dict) else "list")
    _kv("Mutual fund holders keys",   list(mf.keys())[:4]   if isinstance(mf,   dict) else "list")
    ok = _json_check(r, "get_holders")
    _LOG.log_result("holders_TATASTEEL", ok)


def test_esg():
    _header(9, "ESG Data — INFY (large-cap, usually available)")
    from tools.stock_data import get_esg_data

    _section("get_esg_data · INFY")
    r = get_esg_data("INFY", "NSE")
    if "error" in r:
        _skip(f"ESG not available for INFY: {r['error']}")
        _LOG.log_result("esg_INFY", False, r["error"]); return
    _kv("Keys", list(r.get("data", {}).keys())[:6])
    ok = _json_check(r, "get_esg_data")
    _LOG.log_result("esg_INFY", ok)


def test_upcoming_events():
    _header(10, "Upcoming Events — TCS · WIPRO")
    from tools.stock_data import get_upcoming_events

    for sym in ["TCS", "WIPRO"]:
        _section(f"get_upcoming_events · {sym}")
        r = get_upcoming_events(sym, "NSE")
        if "error" in r:
            _fail(sym, r.get("error", ""))
            _LOG.log_result(f"events_{sym}", False, r.get("error", "")); continue
        display = {k: v for k, v in r.items() if k != "symbol"}
        _table(list(display.items())[:6], title=f"{sym} Calendar")
        ok = _json_check(r, f"get_upcoming_events · {sym}")
        _LOG.log_result(f"events_{sym}", ok)


def test_web_search():
    _header(11, "Web Search — Tavily")
    from tools.web_search import search_web

    cases = [
        ("RBI repo rate decision 2025", 3),
        ("Nifty 50 outlook Q2 2025",    2),
    ]
    for query, n in cases:
        _section(f"query · {query}")
        result = search_web(query, max_results=n)
        if not result or (len(result) == 1 and "error" in result[0]):
            _fail(query, result[0].get("error", "empty")); continue
        for i, r in enumerate(result, 1):
            _kv(f"[{i}] title",   r.get("title",   "N/A"))
            _preview(f"[{i}] snippet", r.get("content", ""), chars=100)
        ok = _json_check(result, f"search_web · {query[:30]}")
        _LOG.log_result(f"web_search_{n}", ok)


def test_news_search():
    _header(12, "News Search — NewsAPI")
    from tools.news_search import search_news

    cases = [
        ("HDFC Bank quarterly results", 7),
        ("Indian stock market rally",   5),
    ]
    for query, days in cases:
        _section(f"query · {query}  [{days}d]")
        result = search_news(query, days_back=days)
        if not result or (len(result) == 1 and "error" in result[0]):
            _fail(query, result[0].get("error", "empty")); continue
        rows = []
        for i, a in enumerate(result[:3], 1):
            src = a.get("source", {})
            src_name = src.get("name", src) if isinstance(src, dict) else str(src)
            rows.append((f"[{i}] title",  a.get("title", "N/A")[:60]))
            rows.append((f"[{i}] source", src_name))
            rows.append((f"[{i}] date",   a.get("publishedAt", "N/A")[:10]))
        _table(rows, title=f"News · {query[:30]}")
        ok = _json_check(result, f"search_news · {query[:30]}")
        _LOG.log_result(f"news_{query[:20]}", ok)


def test_ticker_lookup():
    _header(13, "Ticker Lookup — India Listings")
    from tools.ticker_lookup import search_ticker

    cases = [
        ("Tata Steel",       "TATASTEEL"),
        ("Hindustan Unilever","HINDUNILVR"),
        ("hdfc bank",        "HDFCBANK"),
        ("500180",           None),           # BSE code lookup
        ("INFY",             "INFY"),         # exact ticker
        ("FAKECOMPANY999",   None),           # expect no results
    ]
    for query, expected_nse in cases:
        _section(f"query · {query}")
        results = search_ticker(query)
        if not results:
            if expected_nse is None and query == "FAKECOMPANY999":
                _pass(f"Correctly returned empty for '{query}'")
                _LOG.log_result(f"ticker_{query}", True)
            else:
                _fail(query, "no results")
                _LOG.log_result(f"ticker_{query}", False, "no results")
            continue
        rows = [(r.get("company_name","—")[:40], r.get("nse_symbol","—"))
                for r in results]
        _table(rows, title=f"Matches · {query}")
        if expected_nse:
            found = any(r.get("nse_symbol","").upper() == expected_nse.upper()
                        for r in results)
            if found:
                _pass(f"'{expected_nse}' found in results")
            else:
                _fail(query, f"expected '{expected_nse}' not in results")
            _LOG.log_result(f"ticker_{query}", found)
        else:
            _pass(f"{len(results)} result(s) returned")
            _LOG.log_result(f"ticker_{query}", True)


def test_document_parser():
    _header(14, "Document Parser — tests/files/")
    from utils.doc_parser import parse_uploaded_file

    test_dir = os.path.join(_TESTS_DIR, "files")
    if not os.path.exists(test_dir):
        _skip(f"'{test_dir}' not found — add sample files.")
        _LOG.log_result("doc_parser", False, "no test dir"); return

    files = [f for f in os.listdir(test_dir) if os.path.isfile(os.path.join(test_dir, f))]
    if not files:
        _skip("tests/files/ is empty."); return

    for filename in files:
        path = os.path.join(test_dir, filename)
        _section(f"Parsing · {filename}")
        r = parse_uploaded_file(path)
        if r["type"] == "error":
            _fail(filename, r["content"])
            _LOG.log_result(f"doc_parse_{filename}", False, r["content"]); continue
        _kv("type",       r["type"])
        _kv("char_count", r["char_count"])
        content = r["content"]
        if isinstance(content, str):
            _preview("text", content, chars=180)
        elif isinstance(content, dict):
            sheets = list(content.keys())
            _kv("sheets", sheets)
            if sheets and content[sheets[0]]:
                _kv("row[0]", content[sheets[0]][0])
        ok = _json_check(r, f"parse:{filename}")
        _LOG.log_result(f"doc_parse_{filename}", ok)


def test_rag_engine():
    _header(15, "RAG Engine — Index + Semantic Search")
    from utils.doc_parser import parse_uploaded_file
    from utils.rag_engine  import index_document, query_documents

    test_dir = os.path.join(_TESTS_DIR, "files")
    if not os.path.exists(test_dir) or not os.listdir(test_dir):
        _skip("No files in tests/files/ — skipping RAG.")
        _LOG.log_result("rag_engine", False, "no files"); return

    _section("Indexing documents")
    indexed = 0
    for filename in os.listdir(test_dir):
        path = os.path.join(test_dir, filename)
        if not os.path.isfile(path):
            continue
        parsed = parse_uploaded_file(path)
        if parsed["type"] != "error":
            index_document(filename, parsed)
            print(f"  {_c(BG_IDX, ' indexed ')}  {_c(WHITE, filename)}")
            indexed += 1

    if indexed == 0:
        _skip("No parseable files."); return

    queries = [
        "What are the key financial highlights?",
        "What risks are mentioned?",
        "revenue profit growth",
    ]
    for q in queries:
        _section(f"Query · {q}")
        chunks = query_documents(q, n_results=2)
        if chunks:
            for i, chunk in enumerate(chunks, 1):
                _preview(f"match[{i}]", chunk, chars=160)
            _pass(f"{len(chunks)} chunk(s) returned")
            ok = True
        else:
            _fail(q, "no results returned")
            ok = False
        _LOG.log_result(f"rag_{q[:20]}", ok)


def test_forecasting():
    _header(16, "Chronos T5 Forecasting — WIPRO · TCS")
    from tools.ts_model import predict_stock_prices

    cases = [("WIPRO", 10), ("TCS", 5)]
    for sym, horizon in cases:
        _section(f"{sym} · {horizon} days ahead")
        r = predict_stock_prices(sym, "NSE", horizon_days=horizon)
        if "error" in r:
            _fail(sym, r["error"])
            _LOG.log_result(f"forecast_{sym}", False, r["error"]); continue
        hist   = r.get("historical_closes", [])
        med    = r.get("forecast_median",   [])
        lo     = r.get("forecast_low",      [])
        hi     = r.get("forecast_high",     [])
        rows = []
        if hist:
            rows.append(("Last historical",       f"₹ {hist[-1]}"))
        if med:
            rows.append(("Forecast day 1 (med)",  f"₹ {med[0]}"))
            rows.append((f"Forecast day {horizon} (med)", f"₹ {med[-1]}"))
        if lo and hi:
            rows.append(("Day 1 range",            f"₹ {lo[0]}  —  ₹ {hi[0]}"))
            rows.append((f"Day {horizon} range",   f"₹ {lo[-1]}  —  ₹ {hi[-1]}"))
        _table(rows, title=f"Chronos · {sym} · {horizon}d")
        ok = _json_check(r, f"predict_stock_prices · {sym}")
        _LOG.log_result(f"forecast_{sym}", ok)
        _LOG.log_json(f"forecast_{sym}", {k: v for k, v in r.items() if k != "note"})


# ─────────────────────────────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _LOG = TestLogger()

    _blank()
    _thick()
    print(f"  {_c(BG_HEADER, '  ARTHA  ')}  {_c(WHITE, 'Tool Test Suite')}  "
          f"{_c(MUTED, datetime.now().strftime('%Y-%m-%d  %H:%M:%S'))}")
    _thick()

    # Initialise DB tables before any test that touches session_store.
    # Safe to call multiple times — SQLAlchemy only creates tables that don't exist.
    from db import init_db
    init_db()

    tests = [
        test_session_store,
        test_formatters,
        test_stock_info,
        test_stock_history,
        test_financials,
        test_corporate_actions,
        test_analyst_data,
        test_holders,
        test_esg,
        test_upcoming_events,
        test_web_search,
        test_news_search,
        test_ticker_lookup,
        test_document_parser,
        test_rag_engine,
        test_forecasting,
    ]

    passed, failed = 0, 0
    for fn in tests:
        try:
            fn()
            _pass(fn.__name__)
            _LOG.log_result(fn.__name__, True)
            passed += 1
        except AssertionError as e:
            _fail(fn.__name__, str(e))
            _LOG.log_result(fn.__name__, False, f"AssertionError: {e}")
            failed += 1
        except Exception as e:
            _fail(fn.__name__, f"{type(e).__name__}: {e}")
            _LOG.log_result(fn.__name__, False, f"{type(e).__name__}: {e}")
            failed += 1

    _blank()
    _thick()
    p = _c(BG_PASS, f"  {passed} passed  ")
    f = _c(BG_FAIL, f"  {failed} failed  ") if failed else _c(BG_JSON, f"  0 failed  ")
    print(f"  {p}   {f}")
    _thick()

    _LOG.close(passed, failed)
    _blank()
