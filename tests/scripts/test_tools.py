"""
test_tools.py — Artha Tool Test Suite
======================================
Run from the project root:
    python tests/scripts/test_tools.py

Verbose manual sanity-check suite.
Prints inputs, outputs, and JSON-safety checks for every tool.
"""

import sys
import os

# ── Path bootstrap ─────────────────────────────────────────────────────────────
_HERE         = os.path.dirname(os.path.abspath(__file__))  # .../tests/scripts
_TESTS_DIR    = os.path.dirname(_HERE)                      # .../tests
_PROJECT_ROOT = os.path.dirname(_TESTS_DIR)                 # .../artha_backend
sys.path.insert(0, _PROJECT_ROOT)
# ──────────────────────────────────────────────────────────────────────────────

import json
import textwrap

# ── Colorama ──────────────────────────────────────────────────────────────────
try:
    from colorama import init as _cinit, Fore, Style
    _cinit(autoreset=True)
except ImportError:
    class Fore:
        YELLOW = LIGHTYELLOW_EX = WHITE = LIGHTWHITE_EX = RED = CYAN = \
        GREEN  = LIGHTGREEN_EX  = RESET = MAGENTA = ""
    class Style:
        BRIGHT = DIM = RESET_ALL = NORMAL = ""

# ── Palette ───────────────────────────────────────────────────────────────────
GOLD   = Style.BRIGHT + Fore.YELLOW          # bright gold     — headers, titles
AMBER  = Fore.YELLOW                         # amber           — keys, labels
DIM    = Style.DIM    + Fore.YELLOW          # dim gold        — rules, chrome
WHITE  = Style.BRIGHT + Fore.WHITE           # bright white    — values, body
MUTED  = Style.DIM    + Fore.WHITE           # dim white       — hints, secondary
PASS_C = Style.BRIGHT + Fore.LIGHTGREEN_EX   # light mint      — PASS (not harsh)
SKIP_C = Style.BRIGHT + Fore.LIGHTYELLOW_EX  # bright lemon    — SKIP
FAIL_C = Style.BRIGHT + Fore.RED             # red             — FAIL / ERROR
RESET  = Style.RESET_ALL

W = 80

# ── Primitives ────────────────────────────────────────────────────────────────

def _c(color: str, text: str) -> str:
    return f"{color}{text}{RESET}"

def _blank():
    print()

def _rule(char: str = "─"):
    print(_c(DIM, char * W))

def _double_rule():
    print(_c(GOLD, "═" * W))


# ── Structural chrome ─────────────────────────────────────────────────────────

def _header(title: str):
    _blank()
    _double_rule()
    print(_c(GOLD, f"  {title}"))
    _rule()

def _section(title: str):
    _blank()
    print(_c(AMBER, f"  ┌ {title}"))

def _kv(key: str, value, indent: int = 4):
    val_str  = str(value)
    full_len = indent + len(key) + 2 + len(val_str)
    prefix   = " " * indent
    if full_len > W:
        wrapped = textwrap.fill(
            val_str,
            width=W - indent - 2,
            initial_indent=prefix + _c(AMBER, f"{key}: "),
            subsequent_indent=prefix + " " * (len(key) + 2),
        )
        print(wrapped)
    else:
        print(f"{prefix}{_c(AMBER, key + ':')} {_c(WHITE, val_str)}")

def _preview(label: str, text: str, chars: int = 220, indent: int = 4):
    prefix  = " " * indent
    clean   = text.replace("\n", " ").strip()
    snippet = clean[:chars] + (_c(MUTED, "…") if len(clean) > chars else "")
    wrapped = textwrap.fill(
        snippet,
        width=W - indent,
        initial_indent=prefix + _c(AMBER, f"{label}: "),
        subsequent_indent=prefix + " " * (len(label) + 2),
    )
    print(wrapped)


# ── Result indicators ─────────────────────────────────────────────────────────

def _pass(label: str = ""):
    print(_c(PASS_C, "  ✔  PASS") + (_c(MUTED, f"  {label}") if label else ""))

def _fail(label: str, reason: str):
    print(_c(FAIL_C, f"  ✖  FAIL  {label}") + _c(MUTED, f"  —  {reason}"))

def _skip(reason: str):
    print(_c(SKIP_C, "  ◌  SKIP") + _c(MUTED, f"  {reason}"))

def assert_json_safe(obj, label: str) -> bool:
    try:
        json.dumps(obj)
        print(_c(PASS_C, "  ✔  JSON-safe") + _c(MUTED, f"  {label}"))
        return True
    except (TypeError, ValueError) as e:
        print(_c(FAIL_C, f"  ✖  NOT JSON-safe  {label}") + _c(MUTED, f"  —  {e}"))
        return False


# ── 1. SESSION STORE ───────────────────────────────────────────────────────────

def test_session_store():
    _header("TEST 1 · Session Store")
    from utils.session_store import append_message, get_history, add_file, get_files, clear_session

    sid = "test_session_001"
    append_message(sid, "user",      "What is the stock price?")
    append_message(sid, "assistant", "Let me check that for you.")

    hist = get_history(sid)
    _section("History Output")
    for m in hist:
        _kv(f"role={m['role']}", m["content"])

    assert len(hist) == 2
    _pass("Session Store")


# ── 2. FORMATTERS ──────────────────────────────────────────────────────────────

def test_formatters():
    _header("TEST 2 · Formatters  (Data Sanitization)")
    import pandas as pd
    import numpy as np
    from utils.formatters import sanitize_dataframe, sanitize_info_dict

    _section("Input DataFrame  (Pandas Timestamps + Numpy NaNs)")
    df = pd.DataFrame({
        "Date":   [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")],
        "Close":  [np.float64(1234.5),         np.float64(float("nan"))],
        "Volume": [np.int64(1000),             np.int64(2000)],
    })
    for line in str(df).splitlines():
        print(_c(MUTED, "    " + line))

    _section("Sanitized DataFrame  →  JSON-ready dict")
    result = sanitize_dataframe(df)
    for col, vals in result.items():
        _kv(col, vals)
    assert_json_safe(result, "sanitize_dataframe")

    _section("Input Info Dict  (Numpy floats + NaN)")
    info = {"price": np.float64(500.0), "PE": np.float64(float("nan"))}
    _kv("raw", info)
    result2 = sanitize_info_dict(info)
    _kv("sanitized", result2)
    assert_json_safe(result2, "sanitize_info_dict")


# ── 3. STOCK INFO ──────────────────────────────────────────────────────────────

def test_stock_info():
    _header("TEST 3 · Stock Info  (TCS.NS)")
    from tools.stock_data import get_stock_info

    result = get_stock_info("TCS", "NSE")
    if "error" in result:
        _fail("get_stock_info", result["error"])
        return

    _section("Stock Output")
    for k in ["longName", "currentPrice", "trailingPE", "marketCap"]:
        if k in result:
            _kv(k, result[k])

    assert_json_safe(result, "get_stock_info")


# ── 4. STOCK HISTORY ───────────────────────────────────────────────────────────

def test_stock_history():
    _header("TEST 4 · Stock History  (WIPRO · 1mo)")
    from tools.stock_data import get_stock_history

    result = get_stock_history("WIPRO", "NSE", "1mo", "1d")
    if "error" in result:
        _fail("get_stock_history", result["error"])
        return

    dates  = result.get("dates",  [])
    closes = result.get("close",  [])

    _section("History Output")
    _kv("Total Days", len(dates))
    if dates:
        _kv("First Day", f"{dates[0]}  |  Close: {closes[0]}")
        _kv("Last Day",  f"{dates[-1]}  |  Close: {closes[-1]}")

    assert_json_safe(result, "get_stock_history")


# ── 5. WEB SEARCH ─────────────────────────────────────────────────────────────

def test_web_search():
    _header("TEST 5 · Web Search")
    from tools.web_search import search_web

    query = "TCS results 2025"
    _section(f"Query: '{query}'")

    result = search_web(query, max_results=2)
    if not result or (len(result) == 1 and "error" in result[0]):
        _fail("search_web", result[0].get("error", "empty response"))
        return

    _section("Results")
    for i, r in enumerate(result, 1):
        _kv(f"[{i}] title", r.get("title",   "N/A"))
        _preview("snippet", r.get("content", "N/A"), chars=100)

    assert_json_safe(result, "search_web")


# ── 6. NEWS SEARCH ────────────────────────────────────────────────────────────

def test_news_search():
    _header("TEST 6 · News Search")
    from tools.news_search import search_news

    query = "Infosys"
    _section(f"Query: '{query}'")

    result = search_news(query, days_back=7)
    if not result or (len(result) == 1 and "error" in result[0]):
        _fail("search_news", result[0].get("error", "empty response"))
        return

    _section("Articles")
    for i, a in enumerate(result[:2], 1):
        _kv(f"[{i}] title", a.get("title",  "N/A"))
        _kv("    source",   a.get("source", "N/A"))

    assert_json_safe(result, "search_news")


# ── 7. TICKER LOOKUP ──────────────────────────────────────────────────────────

def test_ticker_lookup():
    _header("TEST 7 · Ticker Lookup")
    from tools.ticker_lookup import search_ticker

    query = "tata steel"
    _section(f"Query: '{query}'")

    results = search_ticker(query)
    for r in results:
        _kv("match", f"{r.get('company_name')}  |  NSE: {r.get('nse_symbol')}")


# ── 8. DOCUMENT PARSER ────────────────────────────────────────────────────────

def test_document_parser():
    _header("TEST 8 · Document Parser")
    from utils.doc_parser import parse_uploaded_file

    test_dir = os.path.join(_TESTS_DIR, "files")
    if not os.path.exists(test_dir):
        _skip(f"'{test_dir}' not found — add sample files to tests/files/")
        return

    files = [f for f in os.listdir(test_dir) if os.path.isfile(os.path.join(test_dir, f))]
    if not files:
        _skip("tests/files/ is empty.")
        return

    for filename in files:
        filepath = os.path.join(test_dir, filename)
        _section(f"Parsing: {filename}")

        result = parse_uploaded_file(filepath)
        if result["type"] == "error":
            _fail(filename, result["content"])
            continue

        _kv("type", result["type"])
        content = result["content"]
        if isinstance(content, str):
            _preview("text", content, chars=150)
        elif isinstance(content, dict):
            sheets = list(content.keys())
            _kv("sheets", sheets)
            if sheets and content[sheets[0]]:
                _kv("row[0]", content[sheets[0]][0])

        assert_json_safe(result, f"parse:{filename}")


# ── 9. RAG ENGINE ─────────────────────────────────────────────────────────────

def test_rag_search():
    _header("TEST 9 · RAG Engine")
    from utils.doc_parser import parse_uploaded_file
    from utils.rag_engine import index_document
    from tools.document_search import search_uploaded_documents

    test_dir = os.path.join(_TESTS_DIR, "files")
    if not os.path.exists(test_dir) or not os.listdir(test_dir):
        _skip("No files in tests/files/ — skipping RAG.")
        return

    _section("Indexing")
    for filename in os.listdir(test_dir):
        filepath = os.path.join(test_dir, filename)
        if os.path.isfile(filepath):
            parsed = parse_uploaded_file(filepath)
            if parsed["type"] != "error":
                index_document(filename, parsed)
                print(_c(PASS_C, "    ✔ ") + _c(WHITE, filename))

    query = "What activation function is used in CNNs?"
    _section(f"Query: '{query}'")

    res = search_uploaded_documents(query)
    if res.get("status") == "success":
        for i, chunk in enumerate(res.get("results", [])[:2], 1):
            _preview(f"match[{i}]", chunk, chars=200)
    else:
        _fail("query", res.get("message", "unknown error"))

    assert_json_safe(res, "search_uploaded_documents")


# ── 10. FORECASTING ───────────────────────────────────────────────────────────

def test_forecasting():
    _header("TEST 10 · Chronos T5 Forecasting")
    from tools.ts_model import predict_stock_prices

    symbol  = "WIPRO"
    horizon = 10
    _section(f"Input: {symbol}  ·  {horizon} days")

    result = predict_stock_prices(symbol, "NSE", horizon_days=horizon)
    if "error" in result:
        _fail("predict_stock_prices", result["error"])
        return

    hist_closes = result.get("historical_closes", [])
    med         = result.get("forecast_median",   [])

    _section("Forecast Output")
    if hist_closes:
        _kv("last historical close", hist_closes[-1])
    _kv(f"median path ({horizon}d)", med)
    _kv("low path",                  result.get("forecast_low",  []))
    _kv("high path",                 result.get("forecast_high", []))

    assert_json_safe(result, "predict_stock_prices")


# ── RUNNER ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _double_rule()
    print(_c(GOLD, "  Artha — Tool Test Suite"))
    _double_rule()

    test_functions = [
        test_session_store,
        test_formatters,
        test_stock_info,
        test_stock_history,
        test_web_search,
        test_news_search,
        test_ticker_lookup,
        test_document_parser,
        test_rag_search,
        test_forecasting,
    ]

    passed, failed = 0, 0
    for test_fn in test_functions:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(_c(FAIL_C, f"\n  ✖  ASSERT  {test_fn.__name__}") + _c(MUTED, f"  —  {e}"))
            failed += 1
        except Exception as e:
            print(_c(FAIL_C, f"\n  ✖  ERROR   {test_fn.__name__}  {type(e).__name__}") + _c(MUTED, f"  —  {e}"))
            failed += 1

    _blank()
    _double_rule()
    p_str = _c(PASS_C, f"  {passed} passed") if passed else _c(MUTED, "  0 passed")
    f_str = _c(FAIL_C, f"  {failed} failed") if failed else _c(MUTED, "  0 failed")
    print(p_str + _c(DIM, "  ·") + f_str)
    _double_rule()
