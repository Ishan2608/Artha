# Artha Backend — Project Roadmap

## 1. Build Plan

**Day 1 — Skeleton**
Set up folder structure, `__init__.py` files, `config.py`, `requirements.txt`, `.env`, `.env.example`. Write `models/schemas.py`, `utils/session_store.py`, `utils/formatters.py`, and `tools/ticker_lookup.py`. Verify `python -c "from config import settings"` runs clean.

**Day 2 — Stock Data**
Write all functions in `tools/stock_data.py`. Verify no NaN, no Timestamp, no numpy types in any return value. Test edge cases: ticker not found, empty DataFrames — all must return `{"error": "..."}`, never raise.

**Day 3 — Search, News, Documents**
Write `tools/web_search.py`, `tools/news_search.py`, `utils/doc_parser.py`, `utils/rag_engine.py`. Test each against real data in `test_files/`.

**Day 4 — FastAPI**
Write `main.py` with all routes. Test every route in Swagger UI at `http://localhost:8000/docs`. Verify the full session lifecycle: create → upload → query → delete.

**Day 5 — Agent + MCP Server**
Write `mcp_server.py` (tool definitions, single source of truth) and `agent.py` (LangChain + Groq, fetches tools from MCP server via `MultiServerMCPClient`). Test with `python test_run.py`.

**Day 6 — End-to-end Demo**
Test: stock analysis with multi-tool reasoning, document upload and query, forecast. Fix rough edges. Write `README.md`.

**Day 7 — Chronos Forecasting**
Write `tools/ts_model.py`. Test: "Predict TCS price for 10 days." Verify `forecast_median`, `forecast_low`, `forecast_high` in response.


## 2. Folder Structure

```
artha_backend/
│
├── main.py                  # FastAPI app. All HTTP routes. Entry point for uvicorn.
├── agent.py                 # LangChain agent. Connects to mcp_server.py via MultiServerMCPClient.
├── mcp_server.py            # FastMCP server. Single source of truth for all tool definitions.
├── config.py                # Loads all env vars via pydantic-settings.
├── test_tools.py            # Tool-level test suite. Run: python test_tools.py
├── test_run.py              # Terminal chat UI with rich + per-session logging. Run: python test_run.py
├── requirements.txt
├── .env                     # API keys. Never commit.
├── .env.example             # Template. Safe to commit.
├── .gitignore
├── README.md
│
├── data/
│   ├── engg/
│   │   └── Listings.ipynb   # Notebook for engineering INDIA_LIST.csv from BSE + NSE lists.
│   └── listings/
│       ├── INDIA_LIST.csv   # Merged NSE + BSE listings. Used by ticker_lookup.py.
│       ├── BSE_LIST.csv
│       └── NSE_LIST.csv
│
├── docs/
│   ├── BACKEND_ROADMAP.md
│   ├── FRONTEND_ROADMAP.md
│   └── JOURNAL.md
│
├── learn/
│   ├── sqlite3.py           # SQLite3 experiments for local DB testing.
│   └── yfinance.py          # yfinance tutorial: data fetching, TA, FA.
│
│
├── models/
│   ├── __init__.py
│   └── schemas.py           # Pydantic request/response models for FastAPI.
│
├── tools/                   # Plain Python functions. No framework dependency.
│   ├── logs
│   ├── files
│   └── scripts.py
│       ├── test_run.py      # Runs the Agent UI in Termnial Mode.
│       └── test_tools.py    # Tests the working of tools.
│
├── tools/                   # Plain Python functions. No framework dependency.
│   ├── __init__.py
│   ├── stock_data.py        # yfinance: info, history, financials, actions, holders, ESG.
│   ├── web_search.py        # Tavily web search wrapper.
│   ├── news_search.py       # NewsAPI wrapper.
│   ├── ticker_lookup.py     # INDIA_LIST lookup: company name → NSE/BSE ticker.
│   └── ts_model.py          # Amazon Chronos zero-shot price forecasting.
│
├── utils/
│   ├── __init__.py
│   ├── formatters.py        # Sanitize DataFrames and info dicts for JSON serialization.
│   ├── doc_parser.py        # Parse PDF, DOCX, Excel, CSV, TXT, PPT into plain dicts.
│   ├── rag_engine.py        # Chunk, embed, and query uploaded documents via ChromaDB.
│   └── session_store.py     # In-memory session store: history + uploaded files.
│
├── test_files/              # Sample files for testing RAG and document parsing.
│
├── uploads/                 # Temp storage for user-uploaded files. Gitignored.
│
└── ml/                      # Phase 2 only.
    ├── __init__.py
    ├── data_pipeline.py
    ├── train.py
    ├── evaluate.py
    ├── models/
    │   ├── __init__.py
    │   ├── lstm_model.py
    │   └── transformer_model.py
    ├── saved_models/        # .pth checkpoints. Gitignored.
    └── notebooks/
        └── exploration.ipynb
```

## 3. Setup

### `requirements.txt`

```
# Web framework
fastapi==0.115.0
uvicorn[standard]==0.30.6
python-multipart==0.0.9

# LangChain + Groq
langchain==0.3.25
langchain-core==0.3.59
langchain-groq==0.3.2
langgraph==0.4.3
langchain-mcp-adapters==0.2.2

# MCP server
mcp==1.9.0

# Config
pydantic-settings==2.3.0
python-dotenv==1.0.1

# Financial data
yfinance==0.2.51
pandas==2.2.2
numpy==1.26.4

# Search
tavily-python==0.3.3
newsapi-python==0.2.7

# Document parsing
PyPDF2==3.0.1
openpyxl==3.1.5
python-docx==1.1.2
python-pptx==1.0.2

# RAG
chromadb==0.5.3
sentence-transformers==3.0.1

# Forecasting
torch==2.3.1
transformers==4.43.3
accelerate==0.33.0
# pip install git+https://github.com/amazon-science/chronos-forecasting.git

# Terminal UI
rich==13.7.1
colorama==0.4.6

# Phase 2 (uncomment when starting ml/)
# matplotlib==3.9.1
# scikit-learn==1.5.1
# tqdm==4.66.4
```

### API Keys

| Key | Where to get |
|---|---|
| `GEMINI_API_KEY` | https://aistudio.google.com/app/apikey — create a fresh key if quota runs out |
| `GROQ_API_KEY` | https://console.groq.com — 14,400 req/day free. Use `llama-3.3-70b-versatile` |
| `TAVILY_API_KEY` | https://app.tavily.com — 1,000 searches/month free |
| `NEWS_API_KEY` | https://newsapi.org/register — 100 req/day free |

`yfinance` requires no key.

**`.env`**
```
GEMINI_API_KEY=
GROQ_API_KEY=
TAVILY_API_KEY=
NEWS_API_KEY=
UPLOAD_DIR=uploads
SESSION_TTL_SECONDS=3600
```

### Installing Chronos

```bash
pip install torch==2.3.1
pip install git+https://github.com/amazon-science/chronos-forecasting.git
python -c "from chronos import ChronosPipeline; print('OK')"
```

Weights (~300 MB) download on first prediction call, then cached at `~/.cache/huggingface/hub/`.


## 4. Architecture Notes

### Tool Isolation

```
tools/          plain Python functions     ← testable directly, no framework
    ↓
mcp_server.py   FastMCP wrappers           ← single source of truth for all tool definitions
    ↓
agent.py        MultiServerMCPClient       ← fetches tools at runtime, defines none itself
```

Any tool change (docstring, logic, new tool) happens in `mcp_server.py` only. `agent.py` picks it up automatically on next startup.

### Running the App

| Goal | Command | MCP server |
|---|---|---|
| Terminal chat | `python test_run.py` | auto-started |
| Backend API | `uvicorn main:app --reload` | auto-started |
| Test tools | `python test_tools.py` | not needed |
| Debug MCP alone | `python mcp_server.py` | manual |

Never run `python mcp_server.py` manually during normal operation — `MultiServerMCPClient` spawns and manages it automatically.

### Session Note Injection

Every user message with uploaded files gets this appended before reaching the agent:

```
[System note: session_id='cli_20260319_125559'. Files: report.pdf.
Use parse_document_tool(session_id) or search_documents_tool(session_id, query).]
```

`MultiServerMCPClient` runs `mcp_server.py` in-process (shared memory), so `get_files(session_id)` in the document tools can read the session store populated by `test_run.py` or `main.py`.

### Data Block Protocol

The agent appends chart data at the very end of its response:

~~~
```data
{"chart_type": "candlestick", "ticker": "TCS.NS", "dates": [...], ...}
```
~~~

`_extract_data_block()` parses the JSON. `_strip_data_block()` removes it from the text shown to the user. `chart_type` options: `candlestick`, `line`, `bar`, `forecast`, `table`.

### stdout vs stderr in MCP Subprocess

Any `print()` in a file imported by `mcp_server.py` at module level will corrupt the MCP stdio protocol. Use `print(..., file=sys.stderr)` for startup messages. The only known case is in `ticker_lookup.py`:

```python
print(f"Loaded {len(_lookup_table)} lookup keys.", file=sys.stderr)
```

## 5. File Contents

### `config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Loads all config from .env via pydantic-settings.
    Import as: from config import settings
    Never re-instantiate — use the module-level singleton.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    GEMINI_API_KEY: str
    GROQ_API_KEY: str
    TAVILY_API_KEY: str
    NEWS_API_KEY: str
    UPLOAD_DIR: str = "uploads"
    SESSION_TTL_SECONDS: int = 3600

settings = Settings()
```

### `models/schemas.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, Any

class ChatRequest(BaseModel):
    """POST /chat. session_id groups messages. message is raw user input."""
    session_id: str = Field(..., description="Unique session identifier.")
    message: str = Field(..., description="User message text.")

class ChatResponse(BaseModel):
    """POST /chat response. text is the agent reply. data carries chart JSON or None."""
    session_id: str
    text: str
    data: Optional[dict[str, Any]] = None

class UploadResponse(BaseModel):
    """POST /upload response. file_id is the UUID used to reference this file later."""
    file_id: str
    filename: str
    message: str

class ContextRequest(BaseModel):
    """POST /context. Injects raw text as a system message into session history."""
    session_id: str
    context: str

class ClearSessionResponse(BaseModel):
    """DELETE /session/{id} response."""
    message: str
```

### `utils/formatters.py`

```python
import pandas as pd
import numpy as np

def sanitize_dataframe(df: pd.DataFrame) -> dict[str, list]:
    """
    Convert a yfinance DataFrame to a JSON-safe dict of lists.
    Calls reset_index() to turn the Date index into a regular column.
    Converts: NaN → None, numpy int64 → int, numpy float64 → float, Timestamp → ISO string.
    Returns: {"Date": [...], "Open": [...], "Close": [...], ...}
    """

def sanitize_info_dict(info: dict) -> dict:
    """
    Filter raw yfinance ticker.info through a whitelist of ~35 useful keys.
    Converts all numpy types to plain Python. NaN → None.
    Call ONCE per request — every access to ticker.info triggers a network call.
    Returns: flat dict, all values are str, int, float, or None.
    """

def series_to_chart_arrays(dates: list, values: list) -> dict[str, list]:
    """
    Package parallel lists into {"dates": [...], "values": [...]}.
    Raises ValueError if lengths differ.
    """
```

### `utils/session_store.py`

```python
from collections import defaultdict
from typing import Any

# Structure: { session_id: { "history": [{"role", "content"}, ...], "files": [{"file_id", "filepath", "filename"}, ...] } }
# Swap defaultdict for Redis in production — function signatures stay identical.

def default_session() -> dict[str, Any]:
    return {"history": [], "files": []}

_store: dict[str, dict[str, Any]] = defaultdict(default_session)

def get_session(session_id: str) -> dict[str, Any]:
    """Return full session dict, creating an empty one if it doesn't exist."""

def get_history(session_id: str) -> list[dict]:
    """Return the message history list in chronological order."""

def append_message(session_id: str, role: str, content: str) -> None:
    """Append {"role": role, "content": content} to session history."""

def add_file(session_id: str, file_id: str, filepath: str, filename: str) -> None:
    """Register an uploaded file in the session store."""

def get_files(session_id: str) -> list[dict]:
    """Return the list of file metadata dicts for a session."""

def clear_session(session_id: str) -> None:
    """Delete session from store. Does NOT delete files from disk."""
```

### `tools/ticker_lookup.py`

```python
import os, sys
import pandas as pd

_lookup_table: dict[str, dict] = {}
_listings_path = os.path.join("data", "listings", "INDIA_LIST.csv")

def _load_listings() -> None:
    """
    Load INDIA_LIST.csv into _lookup_table at import time. No disk access after this.
    Keys: lowercase company name + uppercase NSE symbol → entry dict.
    Prints to stderr to avoid corrupting MCP stdio protocol.
    """

def search_ticker(query: str) -> list[dict]:
    """
    Search by company name or ticker. Case-insensitive.
    Three-pass: exact → starts-with → contains. Returns up to 5 results.
    Each result: {company_name, nse_symbol, bse_code, isin}.
    """

_load_listings()
```

### `tools/stock_data.py`

```python
import yfinance as yf
from utils.formatters import sanitize_dataframe, sanitize_info_dict

def _build_ticker(symbol: str, exchange: str = "NSE") -> yf.Ticker:
    """Append .NS (NSE) or .BO (BSE) and return a yf.Ticker object."""

def get_stock_info(symbol: str, exchange: str = "NSE") -> dict:
    """
    Fetch and sanitize ticker.info through the whitelist.
    Store info in a local variable — direct access to ticker.info triggers a network call.
    Returns ~35 fields. On error: {"error": str, "symbol": symbol}.
    """

def get_stock_history(symbol: str, exchange: str = "NSE", period: str = "1mo", interval: str = "1d") -> dict:
    """
    Fetch OHLCV history in chart-ready format.
    Returns: {ticker, period, interval, dates, open, high, low, close, volume}
    OHLC rounded to 2dp, volume as int. On empty: {"error": "No data found"}.
    """

def get_financials(symbol: str, exchange: str = "NSE", statement: str = "income", quarterly: bool = False) -> dict:
    """
    Fetch income, balance_sheet, or cashflow statement. Transposes so dates become rows.
    Returns: {symbol, statement, frequency, data: sanitized dict of lists}.
    """

def get_corporate_actions(symbol: str, exchange: str = "NSE") -> dict:
    """
    Returns last 5 dividends and full split history.
    Each entry: {"date": ISO, "amount": float} or {"date": ISO, "ratio": float}.
    """

def get_analyst_data(symbol: str, exchange: str = "NSE") -> dict:
    """Returns mean/high/low price targets, recommendation key, and recommendations summary."""

def get_holders(symbol: str, exchange: str = "NSE") -> dict:
    """Returns major_holders, top_5_institutional, top_5_mutual_fund as lists."""

def get_esg_data(symbol: str, exchange: str = "NSE") -> dict:
    """
    Returns Sustainalytics ESG scores. Large-cap only.
    Returns {"error": "ESG data not available"} for uncovered stocks.
    """

def get_upcoming_events(symbol: str, exchange: str = "NSE") -> dict:
    """
    Returns ticker.calendar with all date values converted to ISO strings.
    Common keys: Earnings Date, Ex-Dividend Date.
    """
```

### `tools/web_search.py`

```python
from tavily import TavilyClient
from config import settings

_client = TavilyClient(api_key=settings.TAVILY_API_KEY)

def search_web(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the internet via Tavily. Use for macro events, regulatory changes, live data.
    Do NOT use for stock prices — use get_stock_info for that.
    Returns: list of {title, url, content, score}. On error: [{"error": str}].
    """
```

### `tools/news_search.py`

```python
from newsapi import NewsApiClient
from datetime import datetime, timedelta
from config import settings

_client = NewsApiClient(api_key=settings.NEWS_API_KEY)

def search_news(query: str, days_back: int = 7, page_size: int = 10) -> list[dict]:
    """
    Search recent news via NewsAPI. Prefer over search_web for structured news metadata.
    Filters out "[Removed]" placeholder articles.
    Returns: list of {title, source, published_at, description, url}. On error: [{"error": str}].
    """
```

### `utils/doc_parser.py`

```python
import os

def parse_uploaded_file(filepath: str) -> dict:
    """
    Dispatch to the correct parser by file extension.
    Supported: .pdf, .docx, .xlsx/.xls, .csv, .txt, .ppt/.pptx
    Returns: {"type": str, "filename": str, "content": str|dict, "char_count": int}
    On error: {"type": "error", "filename": str, "content": str}
    """

def _extract_pdf_text(filepath: str) -> str:
    """Extract all pages as a newline-joined string. Empty string for image-only PDFs."""

def _extract_xlsx_tables(filepath: str) -> dict[str, list[list]]:
    """
    Extract all sheets as {"SheetName": [[row], ...], ...}.
    Skips fully empty rows. Cell values are plain Python types only.
    """
```

### `utils/rag_engine.py`

```python
def index_document(doc_id: str, parsed_doc: dict) -> None:
    """
    Chunk parsed document content and upsert into ChromaDB.
    Text: split by paragraph. Excel: serialized row-by-row.
    Uses sentence-transformers for embeddings.
    """

def query_documents(filepaths: list[str], query: str, top_k: int = 5) -> dict:
    """
    Semantic search across documents at the given filepaths.
    Returns: {"status": "success", "results": [chunk_text, ...]}
          or {"status": "error", "message": str}
    """
```

### `tools/ts_model.py`

```python
import torch, numpy as np
from tools.stock_data import get_stock_history

_pipeline = None

def _get_pipeline():
    """
    Lazy-load amazon/chronos-t5-tiny on CPU.
    Chronos is a zero-shot T5-based time series model pre-trained on thousands of diverse
    time series. It generalizes without fine-tuning ("zero-shot").
    Tiny variant (21M params) runs in ~2-5s on CPU.
    Weights (~300MB) auto-download on first call to ~/.cache/huggingface/hub/.
    """

def predict_stock_prices(symbol: str, exchange: str = "NSE", horizon_days: int = 10) -> dict:
    """
    Forecast next N closing prices via Chronos. Short-term only (5–20 days recommended).
    Works on price patterns alone — no awareness of news or macro events.
    Returns:
        {symbol, chart_type: "forecast", historical_dates, historical_closes,
         forecast_median, forecast_low (p10), forecast_high (p90), horizon_days, note}
    On error: {"error": str, "symbol": symbol}
    """
```

### `mcp_server.py`

```python
from mcp.server.fastmcp import FastMCP
from tools.stock_data import (get_stock_info, get_stock_history, get_financials,
    get_corporate_actions, get_analyst_data, get_holders, get_esg_data, get_upcoming_events)
from tools.web_search import search_web
from tools.news_search import search_news
from tools.ticker_lookup import search_ticker
from tools.ts_model import predict_stock_prices
from utils.doc_parser import parse_uploaded_file
from utils.rag_engine import query_documents
from utils.session_store import get_files

mcp = FastMCP("artha-tools")

@mcp.tool()
def get_stock_info_tool(symbol: str, exchange: str = "NSE") -> dict:
    """Get real-time price, 52-week range, PE ratio, margins, debt ratios, analyst targets.
    Call when the user asks about a stock's current state or basic fundamentals.
    symbol: ticker WITHOUT suffix (TCS, WIPRO, INFY). exchange: NSE (default) or BSE."""
    return get_stock_info(symbol, exchange)

@mcp.tool()
def get_stock_history_tool(symbol: str, exchange: str = "NSE", period: str = "1mo", interval: str = "1d") -> dict:
    """Get OHLCV history for charts. period: 1d/5d/1mo/3mo/6mo/1y/2y/5y. interval: 1m/1h/1d/1wk."""
    return get_stock_history(symbol, exchange, period, interval)

@mcp.tool()
def get_financials_tool(symbol: str, exchange: str = "NSE", statement: str = "income", quarterly: bool = False) -> dict:
    """Get income statement, balance sheet, or cashflow. quarterly: True for last 4 quarters."""
    return get_financials(symbol, exchange, statement, quarterly)

@mcp.tool()
def get_corporate_actions_tool(symbol: str, exchange: str = "NSE") -> dict:
    """Get last 5 dividends and full split history."""
    return get_corporate_actions(symbol, exchange)

@mcp.tool()
def get_analyst_data_tool(symbol: str, exchange: str = "NSE") -> dict:
    """Get analyst price targets (mean/high/low) and buy/hold/sell recommendation counts."""
    return get_analyst_data(symbol, exchange)

@mcp.tool()
def get_holders_tool(symbol: str, exchange: str = "NSE") -> dict:
    """Get top institutional and mutual fund shareholders."""
    return get_holders(symbol, exchange)

@mcp.tool()
def get_esg_data_tool(symbol: str, exchange: str = "NSE") -> dict:
    """Get ESG risk scores from Sustainalytics. Large-cap stocks only."""
    return get_esg_data(symbol, exchange)

@mcp.tool()
def get_upcoming_events_tool(symbol: str, exchange: str = "NSE") -> dict:
    """Get upcoming earnings dates and ex-dividend dates."""
    return get_upcoming_events(symbol, exchange)

@mcp.tool()
def search_web_tool(query: str, max_results: int = 5) -> dict:
    """Search the internet via Tavily for macro events or live data. NOT for stock prices."""
    return {"results": search_web(query, max_results)}

@mcp.tool()
def search_news_tool(query: str, days_back: int = 7) -> dict:
    """Search recent news with source/date metadata. Prefer over search_web for news queries."""
    return {"results": search_news(query, days_back)}

@mcp.tool()
def search_ticker_tool(query: str) -> dict:
    """Find NSE/BSE ticker for an Indian company by name. Call FIRST when user gives a name not a ticker."""
    return {"results": search_ticker(query)}

@mcp.tool()
def parse_document_tool(session_id: str) -> dict:
    """Parse all uploaded documents in the session. Use for broad questions like 'summarise this file'.
    session_id: from the system note appended to the user message."""
    files = get_files(session_id)
    if not files:
        return {"error": "No documents uploaded in this session."}
    return {"documents": [
        {**parse_uploaded_file(f["filepath"]), "filename": f["filename"]} for f in files
    ]}

@mcp.tool()
def search_documents_tool(session_id: str, query: str, top_k: int = 5) -> dict:
    """Semantic search across uploaded documents. Prefer for specific questions like 'what was revenue in FY24?'.
    session_id: from the system note. query: natural-language question."""
    files = get_files(session_id)
    if not files:
        return {"error": "No documents uploaded in this session."}
    return query_documents([f["filepath"] for f in files], query, top_k)

@mcp.tool()
def predict_stock_tool(symbol: str, exchange: str = "NSE", horizon_days: int = 10) -> dict:
    """Forecast next N closing prices via Chronos. Call ONLY when user explicitly asks for a forecast.
    horizon_days: 5–20 trading days. Always pair with news and fundamental analysis."""
    return predict_stock_prices(symbol, exchange, horizon_days)

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### `agent.py`

```python
import json, os, re, sys
from dotenv import load_dotenv
load_dotenv()

from config import settings
os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY

from langgraph.prebuilt import create_react_agent
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from utils.session_store import get_history

SYSTEM_PROMPT = """You are Artha, an AI financial analyst for Indian retail investors.

TOOLS: stock info, history, financials, corporate actions, analyst data, holders, ESG,
upcoming events, web search, news search, ticker lookup, document parsing, document search,
price forecasting.

STOCK ANALYSIS: If given a company name call search_ticker_tool first. Then call
get_stock_info_tool, get_financials_tool, get_analyst_data_tool, search_news_tool.
Reply with: Summary, Fundamental Picture, Analyst View, Recent News, Key Risks, Disclaimer.
End with: "This is not financial advice."

DOCUMENTS: session_id is in the system note. For broad questions call parse_document_tool(session_id).
For specific questions call search_documents_tool(session_id, query).

CHARTS: Append chart data at the very end of your response:
  ```data
  {{"chart_type": "candlestick", "dates": [...], ...}}
  ```

RULES: Never fabricate data. Always use tools. Acknowledge errors gracefully."""

_agent = None

async def _get_agent():
    """
    Lazy-init on first run_agent() call. Connects to mcp_server.py via MultiServerMCPClient.
    All tool definitions come from mcp_server.py — this file defines none.
    """
    global _agent
    if _agent is not None:
        return _agent
    llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=settings.GROQ_API_KEY, temperature=0.1)
    mcp_client = MultiServerMCPClient({
        "artha": {
            "command": sys.executable,
            "args": [os.path.abspath("mcp_server.py")],
            "transport": "stdio",
            "env": dict(os.environ),
        }
    })
    tools = await mcp_client.get_tools()
    _agent = create_react_agent(model=llm, tools=tools, prompt=SYSTEM_PROMPT)
    return _agent

async def run_agent(session_id: str, message: str) -> dict:
    """
    Run one conversation turn. Builds message list from session history for multi-turn memory.
    Returns: {"text": str, "data": dict | None}
    """
    agent = await _get_agent()
    history = get_history(session_id)
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for msg in history:
        if msg["role"] == "user":        messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant": messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=message))
    result = await agent.ainvoke({"messages": messages})
    final_text = ""
    if result.get("messages"):
        last = result["messages"][-1]
        final_text = last.content if hasattr(last, "content") else str(last)
    return {"text": _strip_data_block(final_text), "data": _extract_data_block(final_text)}

def _extract_data_block(text: str) -> dict | None:
    """Parse the ```data ... ``` block from the agent's response. Returns None if absent or malformed."""
    match = re.search(r"```data\s*\n(.*?)```", text, re.DOTALL)
    if match:
        try: return json.loads(match.group(1).strip())
        except json.JSONDecodeError: return None
    return None

def _strip_data_block(text: str) -> str:
    """Remove the ```data ... ``` block, leaving only human-readable text."""
    return re.sub(r"```data\s*\n.*?```", "", text, flags=re.DOTALL).strip()
```

### `main.py`

```python
import os, uuid, shutil
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from models.schemas import ChatRequest, ChatResponse, UploadResponse, ContextRequest, ClearSessionResponse
from utils.session_store import append_message, add_file, get_files, clear_session
from agent import run_agent

app = FastAPI(title="Artha Backend", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".txt", ".ppt", ".pptx"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Append user message, inject session_id system note if files are uploaded, run agent, return reply."""

@app.post("/upload", response_model=UploadResponse)
async def upload_file(session_id: str = Query(...), file: UploadFile = File(...)):
    """Save file to uploads/ with UUID prefix, register in session store, return file_id."""

@app.post("/context")
async def add_text_context(request: ContextRequest):
    """Store raw text as a system message in session history."""

@app.delete("/session/{session_id}", response_model=ClearSessionResponse)
async def delete_session(session_id: str):
    """Delete uploaded files from disk first, then clear session from store."""

@app.get("/session/{session_id}/files")
async def list_session_files(session_id: str):
    """Return file_id and filename for each file in the session. Does not expose filepaths."""

@app.get("/health")
async def health_check():
    """Returns {"status": "ok", "version": "1.0.0"}"""
```
