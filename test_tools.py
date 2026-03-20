"""
test_tools.py
Run with: python test_tools.py

Verbose manual sanity-check suite.
Prints inputs, outputs, and JSON-safety checks with coloured output.
"""

import json
import os
import textwrap
import time
import traceback

# ── Colour support ────────────────────────────────────────────────────────────
try:
    from colorama import init as colorama_init, Fore, Back, Style
    colorama_init(autoreset=True)
except ImportError:
    class Fore:
        RED = GREEN = YELLOW = CYAN = MAGENTA = BLUE = WHITE = ""
    class Back:
        RED = GREEN = YELLOW = ""
    class Style:
        BRIGHT = DIM = RESET_ALL = ""

# ── Constants ─────────────────────────────────────────────────────────────────
W = 80
_results: list[dict] = []   # Accumulates {name, status, duration, reason}


# ─────────────────────────────────────────────────────────────────────────────
# FORMATTING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _line(char="─"):
    print(f"{Style.DIM}{char * W}{Style.RESET_ALL}")

def _header(title: str, number: int | None = None):
    print()
    print(f"{Fore.CYAN}{Style.BRIGHT}{'═' * W}{Style.RESET_ALL}")
    label = f"  TEST {number}: {title}  " if number else f"  {title}  "
    print(f"{Fore.CYAN}{Style.BRIGHT}{label.center(W)}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'═' * W}{Style.RESET_ALL}")

def _section(title: str):
    print(f"\n{Fore.YELLOW}{Style.BRIGHT}  ▸ {title}{Style.RESET_ALL}")

def _kv(key: str, value, indent: int = 4, value_color: str = Fore.WHITE):
    prefix = " " * indent
    val_str = str(value)
    if len(val_str) > W - indent - len(key) - 4:
        wrapped = textwrap.fill(
            val_str,
            width=W - indent - 2,
            initial_indent=prefix + f"{key}: ",
            subsequent_indent=prefix + " " * (len(key) + 2),
        )
        print(f"{prefix}{Fore.CYAN}{key}{Style.RESET_ALL}:\n{value_color}{wrapped}{Style.RESET_ALL}")
    else:
        print(f"{prefix}{Fore.CYAN}{key}{Style.RESET_ALL}: {value_color}{val_str}{Style.RESET_ALL}")

def _preview(label: str, text: str, chars: int = 220, indent: int = 4):
    prefix = " " * indent
    clean = str(text).replace("\n", " ").strip()
    wrapped = textwrap.fill(
        clean[:chars],
        width=W - indent,
        initial_indent=prefix + f"{Fore.CYAN}{label}{Style.RESET_ALL}: {Fore.WHITE}",
        subsequent_indent=prefix + " " * (len(label) + 2),
    )
    print(wrapped + (f"{Style.DIM}…{Style.RESET_ALL}" if len(clean) > chars else "") + Style.RESET_ALL)

def _pass(label: str = ""):
    print(f"    {Back.GREEN}{Fore.WHITE}{Style.BRIGHT} PASS {Style.RESET_ALL} {Fore.GREEN}{label}{Style.RESET_ALL}")

def _fail(label: str, reason: str):
    print(f"    {Back.RED}{Fore.WHITE}{Style.BRIGHT} FAIL {Style.RESET_ALL} {Fore.RED}{label}{Style.RESET_ALL}: {Style.DIM}{reason}{Style.RESET_ALL}")

def _skip(reason: str):
    print(f"    {Back.YELLOW}{Fore.WHITE}{Style.BRIGHT} SKIP {Style.RESET_ALL} {Fore.YELLOW}{reason}{Style.RESET_ALL}")

def _info(msg: str, indent: int = 4):
    print(f"{' ' * indent}{Style.DIM}{msg}{Style.RESET_ALL}")

def assert_json_safe(obj, label: str) -> bool:
    try:
        json.dumps(obj)
        _pass(f"JSON-serializable: {label}")
        return True
    except (TypeError, ValueError) as e:
        _fail(f"JSON-serializable: {label}", str(e))
        return False


# ─────────────────────────────────────────────────────────────────────────────
# TEST RUNNER
# Wraps each test, catches exceptions, records result for the summary table.
# ─────────────────────────────────────────────────────────────────────────────

def _run(name: str, fn):
    t0 = time.perf_counter()
    status, reason = "PASS", ""
    try:
        fn()
    except AssertionError as e:
        status, reason = "FAIL", str(e)
        print(f"\n    {Back.RED}{Fore.WHITE}{Style.BRIGHT} ASSERTION FAILED {Style.RESET_ALL} {Fore.RED}{e}{Style.RESET_ALL}")
    except Exception as e:
        status, reason = "ERROR", f"{type(e).__name__}: {e}"
        print(f"\n    {Back.RED}{Fore.WHITE}{Style.BRIGHT} EXCEPTION {Style.RESET_ALL} {Fore.RED}{reason}{Style.RESET_ALL}")
        _info(traceback.format_exc())
    duration = time.perf_counter() - t0
    _results.append({"name": name, "status": status, "duration": duration, "reason": reason})


# ─────────────────────────────────────────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_session_store():
    _header("Session Store", 1)
    from utils.session_store import append_message, get_history, add_file, get_files, clear_session

    sid = "test_session_001"

    _section("Appending messages")
    append_message(sid, "user", "What is the stock price?")
    append_message(sid, "assistant", "Let me check that for you.")
    _info("Appended 2 messages (user + assistant)")

    _section("Retrieving history")
    hist = get_history(sid)
    for m in hist:
        role_color = Fore.BLUE if m["role"] == "user" else Fore.GREEN
        _kv(m["role"].capitalize(), m["content"], value_color=role_color)

    assert len(hist) == 2, f"Expected 2 messages, got {len(hist)}"
    _pass("History length correct (2 messages)")

    _section("Adding a dummy file entry")
    add_file(sid, "file_001", "/tmp/test.pdf", "test.pdf")
    files = get_files(sid)
    assert len(files) == 1
    _kv("Registered file", files[0]["filename"])
    _kv("File ID", files[0]["file_id"])
    _pass("File registered in session")

    _section("Clearing session")
    clear_session(sid)
    assert get_history(sid) == []
    assert get_files(sid) == []
    _pass("Session cleared successfully")


def test_formatters():
    _header("Formatters — Data Sanitization", 2)
    import pandas as pd
    import numpy as np
    from utils.formatters import sanitize_dataframe, sanitize_info_dict

    # ── sanitize_dataframe ────────────────────────────────────────────────────
    _section("sanitize_dataframe: simulated yfinance OHLCV for TCS.NS")
    df = pd.DataFrame({
        "Date": [
            pd.Timestamp("2025-03-10 00:00:00+0530"),
            pd.Timestamp("2025-03-11 00:00:00+0530"),
            pd.Timestamp("2025-03-12 00:00:00+0530"),
            pd.Timestamp("2025-03-13 00:00:00+0530"),
            pd.Timestamp("2025-03-14 00:00:00+0530"),
        ],
        "Open": [np.float64(3812.5), np.float64(3798.0), np.float64(3820.0), np.float64(3756.0), np.float64(3780.0)],
        "High": [np.float64(3845.0), np.float64(3831.5), np.float64(3835.0), np.float64(3795.0), np.float64(3810.0)],
        "Low": [np.float64(3790.0), np.float64(3780.0), np.float64(3798.0), np.float64(3740.0), np.float64(3762.0)],
        "Close": [np.float64(3801.25), np.float64(float("nan")), np.float64(3822.75), np.float64(3758.50), np.float64(3795.00)],
        "Volume": [np.int64(2_341_200), np.int64(1_987_500), np.int64(2_104_800), np.int64(3_215_600), np.int64(1_876_300)],
    })
    df = df.set_index("Date")
    _info("Input dtypes: " + ", ".join(f"{c}={df[c].dtype}" for c in df.columns))
    _info(f"Intentional NaN: Close[1] = {df['Close'].iloc[1]}")

    result = sanitize_dataframe(df)

    _section("Output (JSON-safe, ready for frontend chart)")
    for col, vals in result.items():
        _kv(col, vals)

    assert result["Close"][1] is None,              "NaN close should become None"
    assert isinstance(result["Volume"][0], int),    "numpy int64 should become plain int"
    assert isinstance(result["Close"][0], float),   "numpy float64 should become plain float"
    _pass("NaN → None, int64 → int, float64 → float")
    assert_json_safe(result, "sanitize_dataframe")

    # ── sanitize_info_dict ────────────────────────────────────────────────────
    _section("sanitize_info_dict: simulated TCS.NS ticker.info")
    info = {
        "longName": "Tata Consultancy Services Limited",
        "shortName": "TCS.NS",
        "currentPrice": np.float64(3795.00),
        "previousClose": np.float64(3758.50),
        "open": np.float64(3780.00),
        "dayHigh": np.float64(3812.40),
        "dayLow": np.float64(3762.10),
        "volume": np.int64(1_876_300),
        "marketCap": np.int64(1_378_542_329_856),
        "financialCurrency": "INR",
        "exchange": "NSE",
        "fiftyTwoWeekHigh": np.float64(4592.25),
        "fiftyTwoWeekLow": np.float64(3056.05),
        "trailingPE": np.float64(28.43),
        "forwardPE": np.float64(float("nan")),     # yfinance frequently returns NaN
        "priceToBook": np.float64(13.21),
        "dividendYield": np.float64(0.0172),
        "targetMeanPrice": np.float64(4280.0),
        "recommendationKey": "buy",
        "profitMargins": np.float64(0.1872),
        "totalRevenue": np.int64(2_408_270_004_224),
        "debtToEquity": np.float64(float("nan")),     # TCS near-zero debt, often NaN
        "returnOnEquity": np.float64(0.5231),
        "irrelevantKey": "should be filtered out by whitelist",
    }
    _info(f"Input: {len(info)} keys, 2 intentional NaNs (forwardPE, debtToEquity), 1 non-whitelisted key")

    result2 = sanitize_info_dict(info)

    _section("Output (whitelist-filtered, all numpy types converted)")
    for k, v in result2.items():
        color = Fore.YELLOW if v is None else Fore.WHITE
        _kv(k, v, value_color=color)
    none_keys = [k for k, v in result2.items() if v is None]
    _kv("None keys (were NaN or absent)", none_keys, value_color=Fore.YELLOW)

    assert "irrelevantKey" not in result2, "non-whitelisted key must be excluded"
    assert result2["forwardPE"] is None, "NaN forwardPE should become None"
    assert result2["debtToEquity"] is None, "NaN debtToEquity should become None"
    assert result2["currentPrice"] == 3795.0, "float64 should become plain float"
    assert result2["marketCap"] == 1_378_542_329_856, "int64 should become plain int"
    assert result2["recommendationKey"] == "buy", "string should pass through unchanged"
    _pass("All 6 type/filter assertions passed")
    assert_json_safe(result2, "sanitize_info_dict")


def test_stock_info():
    _header("Stock Info — TCS (NSE)", 3)
    from tools.stock_data import get_stock_info

    _section("Fetching from Yahoo Finance…")
    result = get_stock_info("TCS", "NSE")

    if "error" in result:
        _fail("get_stock_info", result["error"])
        return

    showcase = [
        ("longName", "Company Name"),
        ("currentPrice", "Current Price (₹)"),
        ("trailingPE", "Trailing P/E"),
        ("forwardPE", "Forward P/E"),
        ("marketCap", "Market Cap"),
        ("fiftyTwoWeekHigh", "52W High (₹)"),
        ("fiftyTwoWeekLow", "52W Low (₹)"),
        ("recommendationKey", "Analyst Consensus"),
        ("targetMeanPrice", "Analyst Mean Target (₹)"),
        ("profitMargins", "Profit Margin"),
        ("debtToEquity", "Debt / Equity"),
    ]
    for field, label in showcase:
        if field in result:
            val = result[field]
            color = Fore.GREEN if isinstance(val, (int, float)) and val else Fore.WHITE
            _kv(label, val, value_color=color)

    _info(f"Total fields returned: {len(result)}")
    assert_json_safe(result, "get_stock_info")


def test_stock_history():
    _header("Stock History — WIPRO 1mo (daily candles)", 4)
    from tools.stock_data import get_stock_history

    _section("Fetching OHLCV data…")
    result = get_stock_history("WIPRO", "NSE", "1mo", "1d")

    if "error" in result:
        _fail("get_stock_history", result["error"])
        return

    dates  = result.get("dates", [])
    opens  = result.get("open", [])
    highs  = result.get("high", [])
    lows   = result.get("low", [])
    closes = result.get("close", [])
    vols   = result.get("volume", [])

    _kv("Candles returned", len(dates))
    if dates:
        _kv("Date range", f"{dates[0]}  →  {dates[-1]}")

    # Mini ASCII sparkline of closing prices
    if closes:
        lo, hi = min(closes), max(closes)
        span = hi - lo or 1
        bars = "▁▂▃▄▅▆▇█"
        spark = "".join(bars[int((c - lo) / span * 7)] for c in closes)
        print(f"    {Fore.MAGENTA}Close sparkline: {spark}{Style.RESET_ALL}")
        _kv("Close range", f"₹{lo}  –  ₹{hi}", value_color=Fore.GREEN)

    if dates:
        print(f"\n   {Style.BRIGHT}{'Date':<14}{'Open':>10}{'High':>10}{'Low':>10}{'Close':>10}{'Volume':>14}{Style.RESET_ALL}")
        _line()
        for row in zip(dates[-5:], opens[-5:], highs[-5:], lows[-5:], closes[-5:], vols[-5:]):
            d, o, h, l, c, v = row
            print(
                f"{Fore.WHITE}{d:<14}{o:>10.2f}{h:>10.2f}{l:>10.2f}"
                f"{Fore.GREEN}{c:>10.2f}{Style.RESET_ALL}{Fore.CYAN}{v:>14,}{Style.RESET_ALL}"
            )

    assert_json_safe(result, "get_stock_history")


def test_web_search():
    _header("Web Search — Tavily", 5)
    from tools.web_search import search_web

    query = "TCS results 2025"
    _section(f"Query: '{query}'")

    result = search_web(query, max_results=3)

    if not result or (len(result) == 1 and "error" in result[0]):
        _fail("search_web", result[0].get("error", "empty response"))
        return

    _kv("Results returned", len(result))
    for i, r in enumerate(result, 1):
        print(f"\n    {Fore.YELLOW}{Style.BRIGHT}Result {i}{Style.RESET_ALL}")
        _kv("Title", r.get("title", "N/A"), value_color=Fore.WHITE)
        _kv("URL", r.get("url", "N/A"), value_color=Fore.BLUE)
        _kv("Score", r.get("score", "N/A"), value_color=Fore.MAGENTA)
        _preview("Snippet", r.get("content", ""), chars=150)

    assert_json_safe(result, "search_web")


def test_news_search():
    _header("News Search — NewsAPI", 6)
    from tools.news_search import search_news

    query = "Infosys quarterly results"
    _section(f"Query: '{query}'  (last 7 days)")

    result = search_news(query, days_back=7)

    if not result or (len(result) == 1 and "error" in result[0]):
        _fail("search_news", result[0].get("error", "empty response"))
        return

    _kv("Articles returned", len(result))
    for i, a in enumerate(result[:3], 1):
        print(f"\n    {Fore.YELLOW}{Style.BRIGHT}Article {i}{Style.RESET_ALL}")
        _kv("Title", a.get("title", "N/A"))
        _kv("Source", a.get("source", {}).get("name", "N/A") if isinstance(a.get("source"), dict) else a.get("source", "N/A"), value_color=Fore.CYAN)
        _kv("Published At", a.get("publishedAt", "N/A"), value_color=Fore.MAGENTA)
        _preview("Description", a.get("description", ""), chars=120)

    assert_json_safe(result, "search_news")


def test_ticker_lookup():
    _header("Ticker Lookup — INDIA_LIST.csv", 7)
    from tools.ticker_lookup import search_ticker

    cases = [
        ("Exact NSE symbol", "TCS"),
        ("Partial name", "hdfc"),
        ("Full company name", "tata steel"),
        ("BSE code", "500180"),
        ("Invalid query", "FAKECOMPANYXYZ999"),
    ]

    for label, query in cases:
        _section(f"{label}: '{query}'")
        results = search_ticker(query)
        if not results:
            _info("No matches found.", indent=6)
        else:
            for r in results:
                print(
                    f"{Fore.GREEN}{r.get('company_name', 'N/A'):<40}{Style.RESET_ALL}"
                    f"NSE: {Fore.CYAN}{r.get('nse_symbol', '-'):<12}{Style.RESET_ALL}"
                    f"BSE: {Fore.YELLOW}{r.get('bse_code', '-')}{Style.RESET_ALL}"
                )


def test_document_parser():
    _header("Document Parser", 8)
    from utils.doc_parser import parse_uploaded_file

    test_dir = "test_files"
    if not os.path.exists(test_dir):
        _skip(f"Directory '{test_dir}' not found. Create it and drop test files in to run this test.")
        return

    files = [f for f in os.listdir(test_dir) if os.path.isfile(os.path.join(test_dir, f))]
    if not files:
        _skip(f"No files found in '{test_dir}/'.")
        return

    _kv("Files found", len(files))
    for filename in files:
        filepath = os.path.join(test_dir, filename)
        _section(f"Parsing: {filename}")

        result = parse_uploaded_file(filepath)
        if result.get("type") == "error":
            _fail(filename, result.get("content", "unknown error"))
            continue

        doc_type = result.get("type", "unknown")
        _kv("Detected type", doc_type, value_color=Fore.MAGENTA)

        content = result.get("content")
        if isinstance(content, str):
            _kv("Characters extracted", f"{len(content):,}")
            _preview("Text preview", content, chars=200)
        elif isinstance(content, dict):
            sheets = list(content.keys())
            _kv("Sheets / tables", sheets)
            for sheet in sheets[:2]:
                rows = content[sheet]
                _kv(f"  '{sheet}' rows", len(rows))
                if rows:
                    _kv("  Row 1 sample", str(rows[0])[:120])

        assert_json_safe(result, f"parse: {filename}")


def test_rag_search():
    _header("RAG Engine — Index + Semantic Search", 9)
    from utils.doc_parser import parse_uploaded_file
    from utils.rag_engine import index_document
    from tools.document_search import search_uploaded_documents

    test_dir = "test_files"
    if not os.path.exists(test_dir) or not any(
        os.path.isfile(os.path.join(test_dir, f)) for f in os.listdir(test_dir)
    ):
        _skip("No test files found. Add files to 'test_files/' to run this test.")
        return

    _section("Indexing documents")
    indexed = 0
    for filename in os.listdir(test_dir):
        filepath = os.path.join(test_dir, filename)
        if not os.path.isfile(filepath):
            continue
        parsed = parse_uploaded_file(filepath)
        if parsed.get("type") != "error":
            index_document(filename, parsed)
            _info(f"Indexed: {filename}")
            indexed += 1
    _kv("Total indexed", indexed)

    queries = [
        "What is the revenue for this year?",
        "Summarise the key risks mentioned.",
        "What are the main findings?",
    ]
    for query in queries:
        _section(f"Query: '{query}'")
        res = search_uploaded_documents(query)
        status = res.get("status", "unknown")
        if status == "success":
            results = res.get("results", [])
            _kv("Chunks returned", len(results))
            for i, chunk in enumerate(results[:2], 1):
                _preview(f"Match {i}", str(chunk), chars=180)
            _pass(f"Query returned {len(results)} result(s)")
        elif status == "no_results":
            _info("No matches found for this query.")
        else:
            _fail("Query", res.get("message", "unknown error"))
        assert_json_safe(res, f"search_uploaded_documents: {query[:40]}")


def test_forecasting():
    _header("Chronos T5 — Price Forecasting", 10)
    from tools.ts_model import predict_stock_prices

    symbol = "WIPRO"
    horizon = 10
    _section(f"Forecasting {symbol} for next {horizon} trading days…")
    _info("Loading Amazon Chronos T5 Tiny model (first run may take ~30s)…")

    result = predict_stock_prices(symbol, "NSE", horizon_days=horizon)

    if "error" in result:
        _fail("predict_stock_prices", result["error"])
        return

    hist   = result.get("historical_closes",[])
    dates  = result.get("historical_dates",[])
    median = result.get("forecast_median",[])
    low    = result.get("forecast_low",[])
    high   = result.get("forecast_high",[])

    _kv("Historical data points", len(hist))
    if hist and dates:
        _kv("Historical range", f"{dates[0]}  →  {dates[-1]}")
        _kv("Last close", f"₹{hist[-1]}", value_color=Fore.GREEN)

    if median:
        _kv("Forecast horizon", f"{horizon} trading days")
        _kv("Median range", f"₹{min(median):.2f}  –  ₹{max(median):.2f}", value_color=Fore.MAGENTA)

        print(f"\n{Style.BRIGHT}{'Day':>5}  {'Low (₹)':>10}  {'Median (₹)':>12}  {'High (₹)':>10}{Style.RESET_ALL}")
        _line()
        for i, (l, m, h) in enumerate(zip(low, median, high), 1):
            trend = "▲" if i == 1 or m >= median[i - 2] else "▼"
            t_color = Fore.GREEN if trend == "▲" else Fore.RED
            print(
                f"{Fore.WHITE}{i:>5}{Style.RESET_ALL}"
                f"{Fore.YELLOW}{l:>10.2f}{Style.RESET_ALL}"
                f"{t_color}{m:>12.2f} {trend}{Style.RESET_ALL}"
                f"{Fore.CYAN}{h:>10.2f}{Style.RESET_ALL}"
            )

    note = result.get("note", "")
    if note:
        print(f"\n{Fore.YELLOW}⚠  {Style.DIM}{note[:120]}{'…' if len(note) > 120 else ''}{Style.RESET_ALL}")

    assert_json_safe(result, "predict_stock_prices")


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY TABLE
# ─────────────────────────────────────────────────────────────────────────────

def _print_summary():
    print(f"\n\n{Fore.CYAN}{Style.BRIGHT}{'═' * W}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'  RESULTS SUMMARY  '.center(W)}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'═' * W}{Style.RESET_ALL}")

    print(f"  {Style.BRIGHT}{'Test':<40}{'Status':^10}{'Duration':>10}{Style.RESET_ALL}")
    _line()

    passed = failed = errors = 0
    for r in _results:
        status = r["status"]
        dur = f"{r['duration']:.2f}s"
        if status == "PASS":
            status_str = f"{Fore.GREEN}{Style.BRIGHT} PASS {Style.RESET_ALL}"
            passed += 1
        elif status == "FAIL":
            status_str = f"{Fore.RED}{Style.BRIGHT} FAIL {Style.RESET_ALL}"
            failed += 1
        else:
            status_str = f"{Fore.RED}{Style.BRIGHT} ERR  {Style.RESET_ALL}"
            errors += 1

        print(f"  {Fore.WHITE}{r['name'][:38]:<40}{Style.RESET_ALL}{status_str:^10}{Fore.CYAN}{dur:>10}{Style.RESET_ALL}")
        if r["reason"]:
            _info(f"↳ {r['reason'][:76]}", indent=4)

    _line()
    summary_color = Fore.GREEN if (failed + errors) == 0 else Fore.RED
    print(
        f"\n  {summary_color}{Style.BRIGHT}{passed} passed{Style.RESET_ALL}  "
        f"{Fore.RED}{failed + errors} failed{Style.RESET_ALL}  "
        f"{Style.DIM}({len(_results)} total)  "
        f"total time: {sum(r['duration'] for r in _results):.2f}s{Style.RESET_ALL}\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'═' * W}")
    print("  ARTHA — Tool Test Suite".center(W))
    print(f"{'═' * W}{Style.RESET_ALL}")

    suite = [
        ("Session Store",       test_session_store),
        ("Formatters",          test_formatters),
        ("Stock Info",          test_stock_info),
        ("Stock History",       test_stock_history),
        ("Web Search",          test_web_search),
        ("News Search",         test_news_search),
        ("Ticker Lookup",       test_ticker_lookup),
        ("Document Parser",     test_document_parser),
        ("RAG Engine",          test_rag_search),
        ("Chronos Forecasting", test_forecasting),
    ]

    for name, fn in suite:
        _run(name, fn)

    _print_summary()
