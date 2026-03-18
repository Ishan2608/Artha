# Shree_v2 Backend — Complete Project 
## 1. Roadmap

**Day 1: Skeleton, config, schemas, session store, formatters, ticker lookup, and test scaffold. Everything that requires zero API keys.**

- Create full folder structure with all `__init__.py` files. Write `config.py` using pydantic-settings, `.env.example`, and a `requirements.txt`. Verify `python -c "from config import settings"` runs clean.
- Write `models/schemas.py` with all Pydantic models. Write `utils/session_store.py` and `utils/formatters.py` in full. Write `tools/ticker_lookup.py` that loads `data/indian_listings.xlsx` into a dict at startup.
- Write the full `test_tools.py` scaffold with all test function stubs. Write a `utils/test_session.py` quick script that calls every session store function and prints pass/fail. Commit the skeleton to GitHub.

**Day 2: yfinance tool — all stock data functions written, tested, and returning clean JSON.**

- Write every function in `tools/stock_data.py`: info, history, financials, corporate actions, analyst data, holders, ESG, and upcoming events. Each function calls `sanitize_info_dict` or `sanitize_dataframe` before returning.
- Register all stock tools in `mcp_server.py` with their `@server.tool()` wrappers. Run `test_tools.py` stock tests and verify no NaN, no Timestamp, no numpy types in any return value.
- Test edge cases: ticker not found, exchange BSE vs NSE, empty DataFrames. All must return `{"error": "..."}` dicts, never raise unhandled exceptions.

**Day 3: Web search, news search, and document parser tools complete and registered.**

- Write `tools/web_search.py` wrapping Tavily and `tools/news_search.py` wrapping NewsAPI. Both wrapped in try/except returning error dicts on failure.
- Write `tools/doc_parser.py` for PDF and XLSX extraction. Test against a real PDF and a real Excel file and verify the output is a plain dict the agent can read.
- Register all three tools in `mcp_server.py`. Add `tool_search_ticker` for the Indian listings Excel lookup. Run all test functions in `test_tools.py` and confirm every tool passes.

**Day 4: FastAPI routes complete, Swagger UI works, file upload and session management verified.**

- Write `main.py` with all five routes: `/chat`, `/upload`, `/context`, `/session/{id}` DELETE, `/session/{id}/files` GET, and `/health`.
- Run the server with `uvicorn main:app --reload` and manually test every route in Swagger UI at `http://localhost:8000/docs`. Verify request and response shapes match schemas.
- Test the session lifecycle end to end: create session, add context, upload a file, list files, delete session, verify file is deleted from disk.

**Day 5: Google ADK agent wiring — agent calls tools and full chat turn works end to end.**

- Write `agent.py` with ADK `Agent`, `MCPToolset` pointed at `mcp_server.py`, `Runner`, system prompt, and both `_extract_data_block` and `_strip_data_block` helpers.
- Test the first real agent call: POST to `/chat` with `{"session_id": "test1", "message": "What is the current price of TCS on NSE?"}`. Confirm the agent calls `tool_get_stock_info` and returns a price.
- Test multi-tool call: ask "Give me a brief analysis of TCS including recent news." Confirm the agent calls both stock info and news tools and synthesizes a coherent reply.

**Day 6: Contextual analysis — system prompt tuned, data block output verified, report format confirmed.**

- Refine the system prompt in `agent.py` to instruct the agent to always consider FA, TA indicators, news, and analyst consensus together when asked about a stock. Add explicit instructions for when to embed a `data` block.
- Test a full analysis request: "Analyze WIPRO for me." Verify the response includes a structured text report with sections and a `data` block with chart arrays. Verify `_extract_data_block` parses it correctly.
- Test document context: upload a PDF annual report, then ask "Summarize the key financial highlights from my uploaded document." Verify the agent calls `tool_parse_document` and references the content.

**Day 7: HuggingFace Chronos forecast tool integrated, full end-to-end demo polished, README written.**

- Write `tools/ts_model.py` with lazy-loaded Chronos pipeline. Register `tool_predict_stock` in `mcp_server.py`. Test a forecast call: "Predict TCS price for the next 10 days." Verify the data block contains `forecast_median`, `forecast_low`, `forecast_high` arrays.
- Run a complete demo script covering: basic chat, stock analysis with multi-tool reasoning, document upload and query, forecast request, session clear. Fix any rough edges.
- Write `README.md` with setup instructions, env var descriptions, how to run the server, and a sample request for each endpoint.

---

## 2. Folder Structure

```
shree_v2_backend/
│
├── main.py                      # FastAPI app. All HTTP routes. Entry point for uvicorn.
├── agent.py                     # Google ADK agent: wiring, MCPToolset, Runner, data-block parsing.
├── mcp_server.py                # MCP tool server. Every tool the agent can call is registered here.
├── config.py                    # Loads all env vars via pydantic-settings. Single source of truth.
├── test_tools.py                # Manual test script. Run with: python test_tools.py
├── requirements.txt             # All pip dependencies with pinned versions.
├── .env                         # Your actual API keys. Never commit. In .gitignore.
├── .env.example                 # Template showing required keys. Safe to commit.
├── .gitignore                   # Ignores .env, uploads/, __pycache__, .venv, saved_models/.
├── README.md                    # Setup instructions, env vars, how to run, sample requests.
│
├── data/
│   └── indian_listings.xlsx     # Your Indian stock market listings file. Used by ticker_lookup.py.
│
├── docs/
│   └── BACKEND ROADMAP.md
│   └── FRONTEND ROADMAP.md
│   └── JOUNRAL.md
│
├── models/
│   ├── __init__.py              # Empty. Makes models/ a Python package.
│   └── schemas.py               # All Pydantic request/response models used by FastAPI routes.
│
├── tools/
│   ├── __init__.py              # Empty. Makes tools/ a Python package.
│   ├── document_search.py       # Query user uploaded documents.
│   ├── stock_data.py            # All yfinance logic: info, history, financials, actions, holders, ESG.
│   ├── web_search.py            # Tavily web search wrapper. Returns clean list of result dicts.
│   ├── news_search.py           # NewsAPI wrapper. Returns clean list of article dicts.
│   ├── ticker_lookup.py         # Loads indian_listings.xlsx. Provides company-name to ticker search.
│   └── ts_model.py              # Amazon Chronos HuggingFace wrapper. Zero-shot price forecasting.
│
├── utils/
│   ├── __init__.py              # Empty. Makes utils/ a Python package.
│   ├── formatters.py            # Sanitize DataFrames: strip NaN, convert Timestamps, round floats.
│   ├── doc_parser.py            # PDF (PyPDF2) and XLSX (openpyxl) extraction into JSON-safe dicts.
│   ├── session_store.py         # In-memory session store keyed by session_id. History + files.
│   └── rag_engine.py            # Chunk and index parsed documents.
│
├── test_files/                  # Sample files to check RAG capabilities.
│   
├── ml/                          # Phase 2 only. All custom model code lives here.
│   ├── __init__.py
│   ├── data_pipeline.py         # Fetch, normalize, sliding window, chronological split.
│   ├── train.py                 # Generic training loop with MSELoss, Adam, checkpoint saving.
│   ├── evaluate.py              # MAE, RMSE computation, prediction vs actual plotting.
│   ├── models/
│   │   ├── __init__.py
│   │   ├── lstm_model.py        # LSTMForecaster: 2-layer LSTM with linear output head.
│   │   └── transformer_model.py # TransformerForecaster: positional encoding + attention.
│   ├── saved_models/            # .pth checkpoint files. Gitignored.
│   └── notebooks/
│       └── exploration.ipynb    # Free experimentation. Does not affect production code.
│
└── uploads/                     # Temp storage for user-uploaded files. Auto-created. Gitignored.
```

---

## 3. Project Setup

### requirements.txt

```
# Web framework
fastapi==0.115.0
uvicorn[standard]==0.30.6

# Google ADK — PIN THIS EXACT VERSION AFTER YOU INSTALL IT
# Run: pip install google-adk, then check: pip show google-adk, then pin it here.
google-adk==0.4.0

# MCP protocol library
mcp==1.3.0

# Pydantic settings for config.py
pydantic-settings==2.3.0

# Google Generative AI (pulled in by ADK, but explicit pin prevents surprises)
google-generativeai==0.8.3

# Financial data
yfinance==0.2.51

# Data handling
pandas==2.2.2
numpy==1.26.4

# Web search
tavily-python==0.3.3

# News search
newsapi-python==0.2.7

# Document parsing
PyPDF2==3.0.1
openpyxl==3.1.5

# File upload handling in FastAPI
python-multipart==0.0.9

# HuggingFace + Chronos time series (Phase 1)
torch==2.3.1
transformers==4.43.3
accelerate==0.33.0
# Install Chronos separately after the above:
# pip install git+https://github.com/amazon-science/chronos-forecasting.git

# Phase 2 additions (add when you start ml/)
matplotlib==3.9.1
scikit-learn==1.5.1
tqdm==4.66.4
```

### API Keys — What You Need and Where to Get Them

**GEMINI_API_KEY**
Go to `https://aistudio.google.com/app/apikey`. Click "Create API Key". This is what the ADK uses to call Gemini 2.0 Flash as the agent's LLM brain. Free tier is sufficient for development.

**TAVILY_API_KEY**
Go to `https://app.tavily.com`. Sign up, open the Dashboard, go to API Keys. The free Developer plan gives 1000 searches per month, which is more than enough during development.

**NEWS_API_KEY**
Go to `https://newsapi.org/register`. Sign up for the free Developer plan. Gives 100 requests per day. More than enough for testing.

yfinance requires no API key. It scrapes Yahoo Finance directly.

Your `.env` file:

```
GEMINI_API_KEY=your_gemini_key_here
TAVILY_API_KEY=your_tavily_key_here
NEWS_API_KEY=your_newsapi_key_here
UPLOAD_DIR=uploads
SESSION_TTL_SECONDS=3600
```

Your `.env.example` file (safe to commit to GitHub):

```
GEMINI_API_KEY=
TAVILY_API_KEY=
NEWS_API_KEY=
UPLOAD_DIR=uploads
SESSION_TTL_SECONDS=3600
```

### Base Schema Setup

`models/schemas.py` — copy this exactly on Day 1:

```python
from pydantic import BaseModel, Field
from typing import Optional, Any


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique ID for this conversation session.")
    message: str = Field(..., description="The user's message to the agent.")


class ChatResponse(BaseModel):
    session_id: str
    text: str
    data: Optional[dict[str, Any]] = None
    # data carries chart-ready JSON: {"chart_type": "candlestick", "dates": [...], ...}
    # If None, the frontend only renders the text field.


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    message: str


class ContextRequest(BaseModel):
    session_id: str
    context: str


class ClearSessionResponse(BaseModel):
    message: str
```

### Installing and Verifying Chronos

```bash
# Step 1: Install PyTorch CPU version first
pip install torch==2.3.1

# Step 2: Install Chronos from source
pip install git+https://github.com/amazon-science/chronos-forecasting.git

# Step 3: Verify the import
python -c "from chronos import ChronosPipeline; print('Chronos OK')"

# Step 4: First prediction call will auto-download weights (~300MB for tiny).
# This happens inside ts_model.py when _get_pipeline() runs the first time.
# You need internet access on that first run. After that, weights are cached locally
# at ~/.cache/huggingface/hub/
```

---

## 4. File Contents (TODO Format)

### `config.py`

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Loads all configuration from environment variables or the .env file.

    Pydantic-settings automatically reads the .env file at startup.
    You never need to call dotenv.load() anywhere else in the project.

    Usage in any file:
        from config import settings
        print(settings.GEMINI_API_KEY)
    """

    GEMINI_API_KEY: str
    TAVILY_API_KEY: str
    NEWS_API_KEY: str
    UPLOAD_DIR: str = "uploads"
    SESSION_TTL_SECONDS: int = 3600

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# TODO: Instantiate settings as a module-level singleton.
#       Every other file imports this 'settings' object — never re-instantiate it.
settings = Settings()
```

### `models/schemas.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, Any


class ChatRequest(BaseModel):
    """
    Request body for POST /chat.
    session_id groups all messages belonging to one conversation.
    message is the user's raw text input sent to the agent.
    """
    session_id: str = Field(..., description="Unique session identifier.")
    message: str = Field(..., description="User message text.")


class ChatResponse(BaseModel):
    """
    Response for POST /chat.
    text is the agent's plain-language reply shown in the chat bubble.
    data carries structured chart/table output for frontend rendering.
    The frontend checks data for a 'chart_type' key to decide which
    visualization component to render. If data is None, render text only.
    """
    session_id: str
    text: str
    data: Optional[dict[str, Any]] = None


class UploadResponse(BaseModel):
    """
    Response for POST /upload.
    file_id is the UUID the agent uses to locate the file later via tool_parse_document.
    """
    file_id: str
    filename: str
    message: str


class ContextRequest(BaseModel):
    """
    Request body for POST /context.
    Lets the user paste raw text (a news excerpt, a company description,
    personal notes) that the agent should consider in its replies.
    """
    session_id: str
    context: str


class ClearSessionResponse(BaseModel):
    """Response for DELETE /session/{session_id}."""
    message: str


# TODO: In future phases, add:
#       ForecastRequest(ticker, horizon_days) for a dedicated /forecast endpoint.
#       AnalysisReport with typed sections if you add a structured /report endpoint.
```

### `utils/formatters.py`

```python
import pandas as pd
import numpy as np
from typing import Any


def sanitize_dataframe(df: pd.DataFrame) -> dict[str, list]:
    """
    Convert a pandas DataFrame into a JSON-safe dict of lists.

    The problem: yfinance DataFrames contain NaN (not a valid JSON value),
    numpy float64 and int64 (not JSON serializable), and pandas Timestamps
    (also not JSON serializable). FastAPI's json encoder will crash on all of these.

    The solution: iterate every cell, detect the type, convert to plain Python.

    Args:
        df: Any pandas DataFrame from yfinance — history, financials, balance sheet, etc.

    Returns:
        Dict where keys are column name strings and values are plain Python lists.
        Timestamps become ISO strings. NaN becomes None. numpy types become int/float.
        Example: {"Date": ["2024-01-01", ...], "Close": [1234.5, None, 1238.0, ...]}
    """
    # TODO: Call df.reset_index() to turn the index (usually Date) into a regular column.
    # TODO: Convert all column names to strings:
    #       df.columns = [str(c) for c in df.columns]
    #       Some yfinance financials have Timestamp column names.
    # TODO: Initialize result = {}.
    # TODO: For each column name col in df.columns:
    #         Initialize clean_col = [].
    #         For each value in df[col]:
    #           If isinstance(value, (pd.Timestamp, np.datetime64)):
    #             Append value.isoformat() if it has isoformat, else str(value).
    #           Elif isinstance(value, float) and np.isnan(value):
    #             Append None.
    #           Elif isinstance(value, np.integer):
    #             Append int(value).
    #           Elif isinstance(value, np.floating):
    #             Append round(float(value), 4).
    #           Else:
    #             Append value.
    #         result[col] = clean_col.
    # TODO: Return result.
    pass


def sanitize_info_dict(info: dict) -> dict:
    """
    Clean a raw yfinance .info dictionary for JSON serialization.

    The .info dict from yfinance has ~150 keys, many of them None or irrelevant.
    This function uses a whitelist to return only the fields that matter,
    with all values converted to plain Python types.

    Args:
        info: The raw dict from ticker.info. Call this ONCE per request —
              every access to ticker.info triggers a network call.

    Returns:
        A clean flat dict. All values are str, int, float, or None.
    """
    # TODO: Define WHITELIST as a list of key strings:
    #       ["longName", "shortName", "currentPrice", "previousClose", "open",
    #        "dayHigh", "dayLow", "volume", "marketCap", "financialCurrency",
    #        "typeDisp", "exchange", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
    #        "fiftyTwoWeekChangePercent", "fiftyDayAverage", "twoHundredDayAverage",
    #        "trailingPE", "forwardPE", "priceToBook", "dividendYield",
    #        "targetMeanPrice", "targetHighPrice", "targetLowPrice",
    #        "recommendationKey", "currentRatio", "debtToEquity",
    #        "returnOnEquity", "returnOnAssets", "grossMargins", "operatingMargins",
    #        "profitMargins", "revenueGrowth", "earningsGrowth",
    #        "totalRevenue", "totalDebt", "freeCashflow"]
    # TODO: Initialize result = {}.
    # TODO: For each key in WHITELIST:
    #         val = info.get(key)
    #         If val is None, result[key] = None. Continue.
    #         If isinstance(val, float) and np.isnan(val), result[key] = None. Continue.
    #         If isinstance(val, np.integer), result[key] = int(val). Continue.
    #         If isinstance(val, np.floating), result[key] = round(float(val), 4). Continue.
    #         Else: result[key] = val.
    # TODO: Return result.
    pass


def series_to_chart_arrays(dates: list, values: list) -> dict[str, list]:
    """
    Package a date list and value list into the frontend's standard chart-data shape.

    This is used when you have a pre-built date and value pair (e.g. from a
    dividends Series or a simple metric over time) and want to format it
    consistently with how history data is returned.

    Args:
        dates: List of date strings already formatted as ISO strings.
        values: List of float values already sanitized.

    Returns:
        {"dates": [...], "values": [...]}

    Raises:
        ValueError if len(dates) != len(values).
    """
    # TODO: Assert len(dates) == len(values), raise ValueError with a clear message if not.
    # TODO: Return {"dates": dates, "values": values}.
    pass
```

### `utils/session_store.py`

```python
from collections import defaultdict
from typing import Any


# Module-level in-memory store.
# Structure: { session_id: { "history": [...], "files": [...] } }
# Each history entry: {"role": "user"|"assistant"|"system", "content": str}
# Each file entry: {"file_id": str, "filepath": str, "filename": str}
#
# For production, swap this defaultdict for a Redis client.
# The function interfaces defined below stay identical — only the implementation changes.

def default_session() -> dict[str, Any]:
    return {"history": [], "files": []}

_store: dict[str, dict[str, Any]] = defaultdict(default_session)


def get_session(session_id: str) -> dict[str, Any]:
    """
    Retrieve the full session dict for a given session_id.
    If the session does not exist, the defaultdict creates an empty one automatically.

    Args:
        session_id: The unique identifier from the frontend request.

    Returns:
        Dict with keys "history" and "files".
    """
    # TODO: Return _store[session_id].
    pass


def get_history(session_id: str) -> list[dict]:
    """
    Return the message history list for a session.

    Args:
        session_id: Target session.

    Returns:
        List of message dicts in chronological order.
    """
    # TODO: Return _store[session_id]["history"].
    pass


def append_message(session_id: str, role: str, content: str) -> None:
    """
    Append a single message to a session's history.

    Args:
        session_id: Target session.
        role: One of "user", "assistant", or "system".
        content: The text content of the message.
    """
    # TODO: Append {"role": role, "content": content} to _store[session_id]["history"].
    pass


def add_file(session_id: str, file_id: str, filepath: str, filename: str) -> None:
    """
    Register an uploaded file in the session so the agent can reference it later.

    Args:
        session_id: Target session.
        file_id: UUID string assigned at upload time.
        filepath: Absolute path to the saved file on disk.
        filename: Original filename as provided by the user.
    """
    # TODO: Append {"file_id": file_id, "filepath": filepath, "filename": filename}
    #       to _store[session_id]["files"].
    pass


def get_files(session_id: str) -> list[dict]:
    """
    Return the list of files registered for a session.

    Args:
        session_id: Target session.

    Returns:
        List of file metadata dicts. Each dict has file_id, filepath, filename.
    """
    # TODO: Return _store[session_id]["files"].
    pass


def clear_session(session_id: str) -> None:
    """
    Delete a session and all its data from the in-memory store.
    Does NOT delete uploaded files from disk — the caller (main.py route) handles that.

    Args:
        session_id: The session to destroy.
    """
    # TODO: If session_id in _store: del _store[session_id].
    pass
```

### `tools/ticker_lookup.py`

```python
import os
import pandas as pd
from config import settings

# Module-level lookup table loaded once at startup.
# Structure: {"company name lowercase": {"symbol": "TCS", "exchange": "NSE", "isin": "..."}, ...}
# Also supports direct symbol lookup.
_lookup_table: dict[str, dict] = {}
_listings_path = os.path.join("data", "indian_listings.xlsx")


def _load_listings() -> None:
    """
    Load the Indian stock market listings Excel file into the in-memory lookup table.

    This runs once when the module is first imported. After that, all lookups
    are dictionary lookups — no disk access.

    Your Excel file likely has columns like: Company Name, NSE Symbol, BSE Code, ISIN.
    Adjust the column name constants below to match your actual column headers.
    """
    # TODO: Define column name constants that match your Excel file. Example:
    #       COL_NAME = "Company Name"
    #       COL_NSE  = "NSE Symbol"
    #       COL_BSE  = "BSE Code"
    #       COL_ISIN = "ISIN"
    #       Adjust these to match your actual column headers exactly.
    # TODO: If _listings_path does not exist, print a warning and return.
    #       The tool will still be registered but will return "not found" for all queries.
    # TODO: Load: df = pd.read_excel(_listings_path, dtype=str).fillna("")
    # TODO: For each row in df.itertuples():
    #         company_name = getattr(row, COL_NAME, "").strip().lower()
    #         nse_symbol   = getattr(row, COL_NSE, "").strip().upper()
    #         bse_code     = getattr(row, COL_BSE, "").strip()
    #         isin         = getattr(row, COL_ISIN, "").strip()
    #         entry = {"nse_symbol": nse_symbol, "bse_code": bse_code, "isin": isin,
    #                  "company_name": getattr(row, COL_NAME, "").strip()}
    #         If company_name: _lookup_table[company_name] = entry
    #         If nse_symbol: _lookup_table[nse_symbol.lower()] = entry
    # TODO: Print how many entries were loaded.


def search_ticker(query: str) -> list[dict]:
    """
    Search for a stock by company name or ticker symbol.

    The agent calls this when the user says something like "analyze HDFC Bank"
    instead of "analyze HDFCBANK.NS" — the agent needs to resolve the name
    to a yfinance-compatible ticker first.

    Args:
        query: A company name fragment or a ticker symbol. Case-insensitive.
               Examples: "tata steel", "TCS", "hdfc bank", "wipro"

    Returns:
        List of matching dicts. Each dict has: company_name, nse_symbol, bse_code, isin.
        Returns up to 5 best matches, ranked by relevance.
        Returns empty list if no match found.
    """
    # TODO: If _lookup_table is empty, call _load_listings() first.
    # TODO: query_lower = query.strip().lower().
    # TODO: Initialize matches = [].
    # TODO: Search strategy — three passes in priority order:
    #       Pass 1 (exact): if query_lower in _lookup_table, append the entry and return [entry].
    #       Pass 2 (starts with): find all keys that start with query_lower, append their entries.
    #       Pass 3 (contains): find all keys that contain query_lower but do not start with it.
    # TODO: Combine pass 2 and pass 3 results, deduplicate by nse_symbol.
    # TODO: Return the first 5 results.
    pass


# Load listings at import time.
_load_listings()
```

### `tools/stock_data.py`

```python
import yfinance as yf
import pandas as pd
from utils.formatters import sanitize_dataframe, sanitize_info_dict


def _build_ticker(symbol: str, exchange: str = "NSE") -> yf.Ticker:
    """
    Build a yfinance Ticker with the correct exchange suffix.

    NSE tickers get .NS appended, BSE tickers get .BO appended.
    Example: "TCS" + "NSE" -> yf.Ticker("TCS.NS")

    Args:
        symbol: Ticker without suffix. Must be uppercase.
        exchange: "NSE" or "BSE". Default NSE.

    Returns:
        A yfinance Ticker object ready to query.
    """
    # TODO: suffix = ".NS" if exchange.upper() == "NSE" else ".BO"
    # TODO: Return yf.Ticker(symbol.upper() + suffix).
    pass


def get_stock_info(symbol: str, exchange: str = "NSE") -> dict:
    """
    Fetch key fundamental and real-time pricing info for a stock.

    IMPORTANT: Store ticker.info in a local variable before accessing any keys.
    Every direct access to ticker.info triggers a fresh HTTP request to Yahoo Finance.
    Calling it twice in the same function doubles your network time.

    Args:
        symbol: Ticker symbol without suffix. Example: "TCS", "INFY", "HDFCBANK".
        exchange: "NSE" or "BSE".

    Returns:
        Clean dict with ~35 fields including current_price, 52w range, PE ratios,
        margins, debt-to-equity, analyst targets, and recommendation key.
        All values are plain Python types safe for JSON serialization.
    """
    # TODO: ticker = _build_ticker(symbol, exchange)
    # TODO: info = ticker.info   ← store it once here, access only this variable below
    # TODO: Pass info to sanitize_info_dict(info) and return the result.
    # TODO: Wrap in try/except. On exception, return {"error": str(e), "symbol": symbol}.
    pass


def get_stock_history(symbol: str, exchange: str = "NSE", period: str = "1mo", interval: str = "1d") -> dict:
    """
    Fetch OHLCV historical price data in chart-ready format.

    The returned dict is structured so the frontend can directly feed it
    to a candlestick chart with zero transformation:
      dates -> x-axis labels
      open, high, low, close -> candlestick OHLC values
      volume -> volume bar chart below the candlestick

    Args:
        symbol: Ticker symbol. Example: "WIPRO"
        exchange: "NSE" or "BSE"
        period: yfinance period string.
                Valid values: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"
        interval: Candle size. Valid: "1m"(last 7d only), "5m", "15m", "1h", "1d", "1wk", "1mo"

    Returns:
        Dict with keys: ticker, period, interval, dates, open, high, low, close, volume.
        All numeric lists are rounded to 2 decimal places.
        If no data is found, returns {"error": "No data found", "ticker": symbol}.
    """
    # TODO: ticker = _build_ticker(symbol, exchange)
    # TODO: df = ticker.history(period=period, interval=interval)
    # TODO: If df.empty: return {"error": "No data found", "ticker": symbol, "period": period}
    # TODO: Format index as ISO strings: df.index.strftime("%Y-%m-%d %H:%M").tolist()
    # TODO: Build and return dict. Use .round(2).tolist() for OHLC, .astype(int).tolist() for volume.
    # TODO: Wrap in try/except. On exception return {"error": str(e), "ticker": symbol}.
    pass


def get_financials(symbol: str, exchange: str = "NSE", statement: str = "income", quarterly: bool = False) -> dict:
    """
    Fetch one of the three core financial statements.

    The three statements are:
      income       -> Revenue, Gross Profit, EBITDA, Net Income (P&L statement)
      balance_sheet -> Total Assets, Total Debt, Stockholders Equity
      cashflow     -> Operating, Investing, Financing cash flows

    Rows represent financial metrics. Columns represent reporting dates (4 periods max).
    We transpose before returning so rows become dates and columns become metrics —
    this makes it easier for the frontend to render as a time-series table or bar chart.

    Args:
        symbol: Ticker symbol.
        exchange: "NSE" or "BSE"
        statement: One of "income", "balance_sheet", or "cashflow".
        quarterly: True for quarterly data (last 4 quarters), False for annual (last 4 years).

    Returns:
        Dict with keys: symbol, statement, frequency ("annual"/"quarterly"), data (sanitized).
        data is a dict of lists, one key per financial metric.
    """
    # TODO: ticker = _build_ticker(symbol, exchange)
    # TODO: Build a dispatch map:
    #       attr_map = {
    #           "income":       {True: ticker.quarterly_financials,  False: ticker.financials},
    #           "balance_sheet":{True: ticker.quarterly_balance_sheet, False: ticker.balance_sheet},
    #           "cashflow":     {True: ticker.quarterly_cashflow,    False: ticker.cashflow},
    #       }
    # TODO: df = attr_map.get(statement, {}).get(quarterly)
    # TODO: If df is None or df.empty: return {"error": "Data not available", "symbol": symbol}
    # TODO: df = df.T  (transpose: dates become rows, metrics become columns)
    # TODO: data = sanitize_dataframe(df)
    # TODO: Return {"symbol": symbol, "statement": statement,
    #               "frequency": "quarterly" if quarterly else "annual", "data": data}
    pass


def get_corporate_actions(symbol: str, exchange: str = "NSE") -> dict:
    """
    Fetch dividends and stock split history for a company.

    Dividends tell you about shareholder returns policy.
    Splits tell you about historical price adjustments.
    Together they give context to long-term price history charts.

    Args:
        symbol: Ticker symbol. Example: "ITC"
        exchange: "NSE" or "BSE"

    Returns:
        Dict with keys: symbol, last_5_dividends, all_splits.
        last_5_dividends: list of {date: str, amount: float} dicts.
        all_splits: list of {date: str, ratio: float} dicts.
        Either list may be empty if the company has no history.
    """
    # TODO: ticker = _build_ticker(symbol, exchange)
    # TODO: divs = ticker.dividends (a pandas Series indexed by Timestamp)
    # TODO: splits = ticker.splits (a pandas Series indexed by Timestamp)
    # TODO: For divs: take .tail(5), convert to list of dicts:
    #         [{"date": ts.isoformat(), "amount": round(float(val), 4)} for ts, val in divs.items()]
    # TODO: For splits: convert full series to list of dicts similarly.
    # TODO: Handle empty Series gracefully by returning [].
    # TODO: Return {"symbol": symbol, "last_5_dividends": div_list, "all_splits": split_list}
    pass


def get_analyst_data(symbol: str, exchange: str = "NSE") -> dict:
    """
    Fetch analyst price targets and recommendation summary counts.

    This is one of the most useful signals for decision-making context because
    it tells you what professional analysts think the stock is worth and
    whether more analysts are bullish or bearish.

    Args:
        symbol: Ticker symbol. Example: "SBIN"
        exchange: "NSE" or "BSE"

    Returns:
        Dict with: symbol, current_price, mean_target, high_target, low_target,
        recommendation_key (string like "buy", "hold", "sell"),
        recommendations_summary (list of dicts with period and count columns).
    """
    # TODO: ticker = _build_ticker(symbol, exchange)
    # TODO: info = ticker.info  ← store once
    # TODO: rec_summary = ticker.recommendations_summary
    # TODO: Convert rec_summary to list of dicts if not None:
    #         rec_list = rec_summary.to_dict("records") or []
    #         Sanitize each dict value (numpy types to Python types).
    # TODO: Return assembled dict. Use .get() with None defaults for all info fields.
    pass


def get_holders(symbol: str, exchange: str = "NSE") -> dict:
    """
    Fetch institutional and mutual fund holders for a stock.

    Institutional ownership is a useful signal — high institutional ownership
    often indicates analyst coverage and liquidity. Changes in institutional
    holdings can precede price moves.

    Args:
        symbol: Ticker symbol. Example: "HDFCBANK"
        exchange: "NSE" or "BSE"

    Returns:
        Dict with: symbol, major_holders (list), top_5_institutional (list),
        top_5_mutual_fund (list). Any list may be empty if data is unavailable.
    """
    # TODO: ticker = _build_ticker(symbol, exchange)
    # TODO: For each of major_holders, institutional_holders, mutualfund_holders:
    #         Get the DataFrame from ticker.
    #         If None or empty, use [].
    #         Else convert .head(5) using sanitize_dataframe().
    # TODO: Return dict with symbol and all three lists.
    pass


def get_esg_data(symbol: str, exchange: str = "NSE") -> dict:
    """
    Fetch ESG (Environmental, Social, Governance) risk scores from Sustainalytics.

    ESG data is only available for large-cap stocks that Sustainalytics covers.
    Most mid-cap and small-cap Indian stocks will return the error dict.
    A lower total ESG score means lower risk.

    Args:
        symbol: Ticker symbol. Example: "INFY"
        exchange: "NSE" or "BSE"

    Returns:
        Dict with ESG scores and ratings, or {"error": "ESG data not available"}.
    """
    # TODO: ticker = _build_ticker(symbol, exchange)
    # TODO: esg = ticker.sustainability
    # TODO: If esg is None: return {"error": "ESG data not available for this ticker.", "symbol": symbol}
    # TODO: data = sanitize_dataframe(esg)
    # TODO: Return {"symbol": symbol, "data": data}
    pass


def get_upcoming_events(symbol: str, exchange: str = "NSE") -> dict:
    """
    Fetch upcoming earnings announcement dates and ex-dividend dates.

    The calendar dict from yfinance contains datetime.date objects which
    are not JSON serializable. We convert every value that is a date or
    datetime to an ISO string.

    Args:
        symbol: Ticker symbol. Example: "TCS"
        exchange: "NSE" or "BSE"

    Returns:
        Dict of calendar events with ISO-formatted dates.
        Keys vary by ticker but commonly include: Earnings Date, Ex-Dividend Date.
    """
    # TODO: ticker = _build_ticker(symbol, exchange)
    # TODO: cal = ticker.calendar  (a plain dict, not a DataFrame)
    # TODO: If cal is None or not isinstance(cal, dict): return {"error": "No calendar data", "symbol": symbol}
    # TODO: Iterate over cal.items(). For each value:
    #         If isinstance(value, (pd.Timestamp, datetime.date, datetime.datetime)):
    #           Convert to .isoformat()
    #         If isinstance(value, list): convert each element similarly.
    #         Else keep as is.
    # TODO: Return the cleaned dict with "symbol" key added.
    pass
```

### `tools/web_search.py`

```python
from tavily import TavilyClient
from config import settings


_client = TavilyClient(api_key=settings.TAVILY_API_KEY)


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the internet using Tavily and return clean result dicts.

    Use this for questions requiring live internet data: macro events,
    regulatory changes, company announcements, general financial concepts.
    Do NOT use this for real-time stock prices — use get_stock_info for that.

    Args:
        query: Focused search query. More specific = better results.
               Example: "RBI repo rate decision June 2025"
               Bad example: "stocks" (too broad)
        max_results: Number of results to return. 5 is the right default.
                     Go up to 10 only if the user explicitly needs comprehensive coverage.

    Returns:
        List of dicts. Each dict has: title, url, content (snippet), score (0.0 to 1.0).
        On API error, returns [{"error": str}] — never raises.
    """
    # TODO: Wrap everything in try/except. On any exception, return [{"error": str(e)}].
    # TODO: response = _client.search(query=query, max_results=max_results)
    # TODO: results = response.get("results", [])
    # TODO: For each r in results, build:
    #         {"title": r.get("title"), "url": r.get("url"),
    #          "content": r.get("content"), "score": r.get("score")}
    # TODO: Return the list of clean dicts.
    pass
```

### `tools/news_search.py`

```python
from newsapi import NewsApiClient
from datetime import datetime, timedelta
from config import settings


_client = NewsApiClient(api_key=settings.NEWS_API_KEY)


def search_news(query: str, days_back: int = 7, page_size: int = 10) -> list[dict]:
    """
    Search recent financial news using NewsAPI.

    Prefer this over search_web when the user asks specifically about news,
    press releases, or recent events related to a company or market sector.
    NewsAPI returns structured metadata (source, date, description) that is
    more useful for presenting a news digest than raw web search snippets.

    Args:
        query: Search string. Examples: "Tata Motors EV sales", "Nifty 50 correction"
        days_back: How many days back to search. Default 7. Max 30 on free plan.
        page_size: Articles to return. Default 10. Max 100 on free plan.

    Returns:
        List of dicts. Each dict has: title, source, published_at (ISO string),
        description (snippet), url.
        Articles where title is "[Removed]" (NewsAPI placeholder) are filtered out.
        On API error, returns [{"error": str}] — never raises.
    """
    # TODO: Wrap everything in try/except. On any exception, return [{"error": str(e)}].
    # TODO: from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    # TODO: response = _client.get_everything(
    #           q=query, from_param=from_date, sort_by="relevancy",
    #           language="en", page_size=page_size)
    # TODO: articles = response.get("articles", [])
    # TODO: Build clean dicts. Filter out any where a.get("title") == "[Removed]".
    # TODO: Return filtered list.
    pass
```

### `tools/doc_parser.py`

```python
import os
import PyPDF2
import openpyxl


def parse_uploaded_file(filepath: str) -> dict:
    """
    Parse a user-uploaded file and return its content in a structure the agent can reason over.

    Dispatches to the appropriate parser based on file extension.
    Supports: .pdf (text extraction), .xlsx/.xls (table extraction), .txt/.csv (raw read).

    The agent receives this dict and reasons over its 'content' field.
    For PDFs, it reasons over the extracted text directly.
    For Excel files, it reasons over the 2D table structure.
    The 'char_count' field helps the agent decide if the content is too long to include
    in full and whether to summarize or chunk.

    Args:
        filepath: Absolute path to the file in the uploads/ directory.

    Returns:
        Dict with keys: type, filename, content, char_count.
        On any parsing error, returns {"type": "error", "filename": ..., "content": str(error)}.
    """
    # TODO: ext = os.path.splitext(filepath)[1].lower()
    # TODO: filename = os.path.basename(filepath)
    # TODO: Wrap in try/except. On exception: return {"type": "error", "filename": filename, "content": str(e)}
    # TODO: Dispatch:
    #         if ext == ".pdf":        content = _extract_pdf_text(filepath),   type_ = "pdf"
    #         elif ext in (".xlsx", ".xls"): content = _extract_xlsx_tables(filepath), type_ = "xlsx"
    #         else:                    content = open(filepath, "r", errors="ignore").read(), type_ = "text"
    # TODO: Compute char_count:
    #         If content is a string: char_count = len(content)
    #         If content is a dict (xlsx): char_count = sum of lengths of all string cell values.
    # TODO: Return {"type": type_, "filename": filename, "content": content, "char_count": char_count}
    pass


def _extract_pdf_text(filepath: str) -> str:
    """
    Extract all text from a PDF file as a single concatenated string.

    Pages are joined with newlines. Pages with no extractable text (scanned images
    without OCR) contribute an empty string — no error is raised.
    For scanned PDFs, consider adding pytesseract OCR support in Phase 3.

    Args:
        filepath: Path to the PDF file.

    Returns:
        Full extracted text. May be empty for image-only PDFs.
    """
    # TODO: Open filepath in "rb" mode.
    # TODO: reader = PyPDF2.PdfReader(file_handle)
    # TODO: pages = [page.extract_text() or "" for page in reader.pages]
    # TODO: Return "\n".join(pages)
    pass


def _extract_xlsx_tables(filepath: str) -> dict[str, list[list]]:
    """
    Extract all sheets from an Excel file as a dict of 2D lists.

    Each sheet becomes a key. The value is a list of rows where each row
    is a list of cell values as plain Python types.
    Empty rows (all None values) are skipped to reduce noise.

    This structure lets the agent reason over financial tables the user has prepared —
    for example, a personal portfolio tracker or a custom financial model.

    Args:
        filepath: Path to the .xlsx file.

    Returns:
        {"Sheet1": [[val, val, ...], [val, val, ...]], "Sheet2": [...]}
        Cell values are str, int, float, or None. No pandas or numpy types.
    """
    # TODO: wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    # TODO: result = {}
    # TODO: For each sheet_name in wb.sheetnames:
    #         ws = wb[sheet_name]
    #         rows = []
    #         For each row in ws.iter_rows():
    #           row_values = [cell.value for cell in row]
    #           If any(v is not None for v in row_values):  ← skip fully empty rows
    #             rows.append(row_values)
    #         result[sheet_name] = rows
    # TODO: Return result
    pass
```

### `tools/ts_model.py`

```python
import torch
import numpy as np
from tools.stock_data import get_stock_history

_pipeline = None

def _get_pipeline():
    """
    Lazy-load the Amazon Chronos T5 Tiny forecasting pipeline.

    Simple explanation:
    Chronos is like a pre-trained analyst who has studied thousands of different
    time series (sales data, weather data, energy prices, financial data). You show
    it your stock's price history, and it draws on everything it learned to suggest
    where prices might go. No training needed on your end — it already knows patterns.

    Technical explanation:
    Chronos is a zero-shot time series foundation model based on the T5 transformer
    architecture. It was pre-trained on a large corpus of diverse real and synthetic
    time series. It tokenizes continuous values into a discrete vocabulary, then uses
    the T5 encoder-decoder to autoregressively sample from the predictive distribution.
    "Zero-shot" means it generalizes to new series without fine-tuning.

    The "tiny" variant (21M parameters) is CPU-feasible in ~2-5 seconds per prediction.

    Returns:
        A loaded ChronosPipeline ready for .predict() calls.
    """
    # TODO: global _pipeline
    # TODO: If _pipeline is None:
    #         from chronos import ChronosPipeline
    #         _pipeline = ChronosPipeline.from_pretrained(
    #             "amazon/chronos-t5-tiny",
    #             device_map="cpu",
    #             torch_dtype=torch.float32,
    #         )
    # TODO: Return _pipeline
    pass


def predict_stock_prices(symbol: str, exchange: str = "NSE", horizon_days: int = 10) -> dict:
    """
    Forecast the next N closing prices for a stock using Amazon Chronos.

    This tool is for short-term probabilistic forecasting only. It works on
    price patterns alone — it has no knowledge of news events, earnings releases,
    or macro changes. The agent should always pair a forecast with context from
    the news and analysis tools to give the user a complete picture.

    How the output is structured for the frontend:
    The returned dict is designed to plot a continuation chart:
      - Historical dates + closes draw the historical line up to today.
      - Forecast dates are projected forward from today.
      - forecast_median is the center line of the forecast band.
      - forecast_low / forecast_high form a shaded confidence band.

    Args:
        symbol: Ticker symbol. Example: "TCS"
        exchange: "NSE" or "BSE"
        horizon_days: Future trading days to forecast. Keep between 5 and 20.
                      Beyond 20 days, Chronos tiny degrades significantly.

    Returns:
        {
            "symbol": str,
            "chart_type": "forecast",              <- frontend uses this to pick the right chart
            "historical_dates": [str, ...],
            "historical_closes": [float, ...],
            "forecast_median": [float, ...],
            "forecast_low": [float, ...],
            "forecast_high": [float, ...],
            "horizon_days": int,
            "note": str                            <- always include disclaimer
        }
        On error, returns {"error": str, "symbol": symbol}.
    """
    # TODO: Wrap everything in try/except. On exception return {"error": str(e), "symbol": symbol}.
    # TODO: history = get_stock_history(symbol, exchange, period="3mo", interval="1d")
    # TODO: If "error" in history: return history (propagate the error)
    # TODO: closes = history["close"]
    # TODO: historical_dates = history["dates"]
    # TODO: context = torch.tensor(closes, dtype=torch.float32).unsqueeze(0)
    #       Shape after unsqueeze: [1, T] — batch dimension required by Chronos
    # TODO: pipeline = _get_pipeline()
    # TODO: forecast = pipeline.predict(context=context, prediction_length=horizon_days, num_samples=20)
    #       forecast shape: [1, num_samples, horizon_days]
    # TODO: samples = forecast[0].numpy()  ← shape: [num_samples, horizon_days]
    # TODO: Compute:
    #         forecast_median = np.median(samples, axis=0).round(2).tolist()
    #         forecast_low    = np.percentile(samples, 10, axis=0).round(2).tolist()
    #         forecast_high   = np.percentile(samples, 90, axis=0).round(2).tolist()
    # TODO: Return the assembled dict. Set chart_type = "forecast".
    #       note = "This forecast is generated by a statistical model using price patterns only.
    #               It does not account for news, earnings, or macro events.
    #               This is for educational purposes and not financial advice."
    pass
```

### `mcp_server.py`

```python
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server

from tools.stock_data import (
    get_stock_info, get_stock_history, get_financials,
    get_corporate_actions, get_analyst_data, get_holders,
    get_esg_data, get_upcoming_events,
)
from tools.web_search import search_web
from tools.news_search import search_news
from tools.doc_parser import parse_uploaded_file
from tools.ticker_lookup import search_ticker
from tools.ts_model import predict_stock_prices
from utils.session_store import get_files

server = Server("shree-tools")

# STOCK DATA TOOLS
# Each function's docstring is the instruction the agent reads when deciding whether to call it.
# Write docstrings precisely — they are the agent's tool-selection guide.

@server.tool()
async def tool_get_stock_info(symbol: str, exchange: str = "NSE") -> dict:
    """
    # Docstring.
    """
    Get real-time price, 52-week range, PE ratio, margins, debt ratios, and analyst targets.
    Call this when the user asks about a stock's current state, price, or basic fundamentals.
    symbol: NSE/BSE ticker WITHOUT suffix. Examples: TCS, WIPRO, INFY, HDFCBANK, SBIN.
    exchange: NSE (default) or BSE.
    """
    # TODO: return get_stock_info(symbol, exchange)
    pass


@server.tool()
async def tool_get_stock_history(symbol: str, exchange: str = "NSE", period: str = "1mo", interval: str = "1d") -> dict:
    """
    Get OHLCV historical price data formatted for candlestick or line charts.
    Call this when the user asks for a price chart, trend analysis, or historical performance.
    period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y. interval: 1m (last 7d only), 1h, 1d, 1wk.
    """
    # TODO: return get_stock_history(symbol, exchange, period, interval)
    pass


@server.tool()
async def tool_get_financials(symbol: str, exchange: str = "NSE", statement: str = "income", quarterly: bool = False) -> dict:
    """
    Get financial statements: income statement, balance sheet, or cash flow statement.
    Call this when analyzing revenue, profit, debt levels, or cash generation.
    statement: "income" (P&L), "balance_sheet" (assets/liabilities), or "cashflow".
    quarterly: True for last 4 quarters, False for last 4 annual periods.
    """
    # TODO: return get_financials(symbol, exchange, statement, quarterly)
    pass


@server.tool()
async def tool_get_corporate_actions(symbol: str, exchange: str = "NSE") -> dict:
    """
    Get dividend history and stock split history.
    Call this when the user asks about dividends, shareholder returns, or historical splits.
    """
    # TODO: return get_corporate_actions(symbol, exchange)
    pass


@server.tool()
async def tool_get_analyst_data(symbol: str, exchange: str = "NSE") -> dict:
    """
    Get analyst consensus: price targets (mean/high/low) and buy/hold/sell recommendation counts.
    Call this when the user asks what analysts think, or to add analyst consensus to an analysis.
    """
    # TODO: return get_analyst_data(symbol, exchange)
    pass


@server.tool()
async def tool_get_holders(symbol: str, exchange: str = "NSE") -> dict:
    """
    Get top institutional and mutual fund shareholders.
    Call this when the user asks about ownership structure or institutional interest.
    """
    # TODO: return get_holders(symbol, exchange)
    pass


@server.tool()
async def tool_get_esg_data(symbol: str, exchange: str = "NSE") -> dict:
    """
    Get ESG (Environmental, Social, Governance) risk scores from Sustainalytics.
    Call this when the user asks about sustainability, ESG rating, or ethical investing.
    Note: only available for large-cap stocks. Returns error dict for uncovered stocks.
    """
    # TODO: return get_esg_data(symbol, exchange)
    pass


@server.tool()
async def tool_get_upcoming_events(symbol: str, exchange: str = "NSE") -> dict:
    """
    Get upcoming earnings dates and ex-dividend dates from the stock calendar.
    Call this when the user asks when the next earnings report or dividend is.
    """
    # TODO: return get_upcoming_events(symbol, exchange)
    pass


# WEB AND NEWS TOOLS

@server.tool()
async def tool_search_web(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the internet for current information using Tavily.
    Call this for macro events, regulatory changes, sector news, or anything needing live data.
    Do NOT call this for stock prices or financial statements — use the stock tools above instead.
    Keep queries specific: "RBI rate decision impact on bank stocks" not just "banks".
    """
    # TODO: return search_web(query, max_results)
    pass


@server.tool()
async def tool_search_news(query: str, days_back: int = 7) -> list[dict]:
    """
    Search recent news articles with source, date, and description metadata.
    Prefer this over tool_search_web when the user explicitly asks about news,
    press releases, or recent company/sector events with structured metadata.
    days_back: How many days of history to search. Default 7.
    """
    # TODO: return search_news(query, days_back)
    pass


# TICKER LOOKUP TOOL

@server.tool()
async def tool_search_ticker(query: str) -> list[dict]:
    """
    Find the NSE/BSE ticker symbol for an Indian company by name or partial name.
    Call this FIRST when the user mentions a company by name instead of ticker symbol.
    Example: user says "analyze HDFC Bank" -> call this with "hdfc bank" -> get "HDFCBANK".
    Returns up to 5 matches with company_name, nse_symbol, bse_code, and ISIN.
    """
    # TODO: return search_ticker(query)
    pass


# DOCUMENT TOOL

@server.tool()
async def tool_parse_document(session_id: str, file_id: str) -> dict:
    """
    Parse a user-uploaded document (PDF or Excel) and return its extractable content.
    Call this when the user asks questions about a file they have uploaded in the current session.
    session_id: The current conversation session ID.
    file_id: The UUID returned to the user at upload time.
    """
    # TODO: files = get_files(session_id)
    # TODO: Find entry where entry["file_id"] == file_id.
    # TODO: If not found: return {"error": f"File {file_id} not found in session.", "session_id": session_id}
    # TODO: return parse_uploaded_file(entry["filepath"])
    pass


# TIME SERIES FORECAST TOOL

@server.tool()
async def tool_predict_stock(symbol: str, exchange: str = "NSE", horizon_days: int = 10) -> dict:
    """
    Forecast the next N closing prices for a stock using Amazon Chronos (zero-shot model).
    Call this ONLY when the user explicitly asks for a price prediction or forecast.
    Do NOT call this for current prices — use tool_get_stock_info for that.
    Always pair this forecast with news context and fundamental analysis in your response.
    The model uses price patterns only and cannot account for news or macro events.
    horizon_days: Future trading days to forecast. Recommended range: 5 to 20.
    """
    # TODO: return predict_stock_prices(symbol, exchange, horizon_days)
    pass


# SERVER ENTRY POINT

if __name__ == "__main__":
    # Run the MCP server in stdio mode.
    # The ADK agent in agent.py will launch this as a subprocess and communicate with it
    # over stdin/stdout using the MCP protocol. You do not run this manually.
    # TODO: asyncio.run(stdio_server(server))
    pass
```

### `agent.py`

```python
import json
import re
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


SYSTEM_PROMPT = """
You are Shree, an AI financial analyst assistant designed for Indian retail investors.
Your job is to translate complex financial data into clear, plain-language insights.

Your tools give you access to:
  - Real-time stock prices and fundamentals (PE, margins, debt ratios, 52-week range)
  - Historical OHLCV price data (for charts)
  - Financial statements (income, balance sheet, cash flow — annual and quarterly)
  - Corporate actions (dividends, splits)
  - Analyst consensus (price targets, buy/hold/sell counts)
  - Institutional and mutual fund holders
  - ESG risk scores
  - Upcoming earnings and dividend dates
  - Live web search and recent news search
  - User-uploaded documents (PDF, Excel)
  - Price forecasts using a time series model
  - Indian stock ticker lookup by company name

HOW TO RESPOND TO STOCK ANALYSIS REQUESTS:
When a user asks you to analyze a stock or asks "should I invest in X?", do the following:
1. If the user gave a company name, not a ticker, call tool_search_ticker first.
2. Call tool_get_stock_info to understand current price and valuation.
3. Call tool_get_financials for the income statement (annual) to assess revenue and profit trends.
4. Call tool_get_analyst_data to get analyst consensus.
5. Call tool_search_news to check for recent significant news.
6. Synthesize all of this into a structured response with clear sections.
7. Include a data block with chart-ready price history from tool_get_stock_history.

RESPONSE FORMAT FOR STOCK ANALYSIS:
Use markdown headers for sections. Example structure:
## Summary
One paragraph plain-language overview.
## Fundamental Picture
Revenue growth, profit margins, debt levels, PE vs sector.
## Analyst View
Price targets and recommendation consensus.
## Recent News
2-3 key recent headlines and their significance.
## Technical Snapshot
52-week position, trend direction from price history.
## Key Risks
What could go wrong.
## Disclaimer
Always end with a disclaimer that this is not financial advice.

DATA BLOCK RULES:
When your response includes data for visualization, embed it at the very end using this exact format:
```data
{"chart_type": "candlestick", "ticker": "TCS.NS", "dates": [...], "open": [...], ...}
```
The chart_type field tells the frontend which component to render. Options:
  candlestick   -> OHLCV price history (dates, open, high, low, close, volume)
  line          -> Simple price or metric over time (dates, values, label)
  bar           -> Financial metric comparison (labels, values, label)
  forecast      -> Price forecast band (historical_dates, historical_closes,
                   forecast_median, forecast_low, forecast_high)
  table         -> Financial statements or holders data (rows, columns)

TOOL CALLING RULES:
- Only call a tool when it is genuinely needed. Do not call tools speculatively.
- Never fabricate stock prices. If you do not have the data, call the tool.
- If a tool returns an error dict, acknowledge it gracefully in your response.
- For forecasts, always accompany the data with the tool's disclaimer text.
"""


_toolset = MCPToolset(
    connection_params=StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
    )
)

_agent = Agent(
    model="gemini-2.0-flash",
    name="shree_agent",
    instruction=SYSTEM_PROMPT,
    tools=[_toolset],
)

_session_service = InMemorySessionService()

_runner = Runner(
    agent=_agent,
    app_name="shree_v2",
    session_service=_session_service,
)


async def run_agent(session_id: str, message: str) -> dict:
    """
    Run the ADK agent for one conversation turn and return the structured result.

    Manages ADK session creation on first message (the ADK's InMemorySessionService
    is separate from our own session_store — both must be maintained).
    Streams agent events and collects the final response text.
    Extracts and strips the embedded data block before returning.

    Args:
        session_id: The session identifier from the HTTP request.
        message: The user's message text for this turn.

    Returns:
        {"text": str, "data": dict | None}
        text: Agent's plain-language reply with the data block stripped out.
        data: Parsed dict from the embedded data block, or None if absent.
    """
    # TODO: Check if ADK session exists:
    #         session = await _session_service.get_session(
    #             app_name="shree_v2", user_id=session_id, session_id=session_id)
    # TODO: If session is None, create it:
    #         await _session_service.create_session(
    #             app_name="shree_v2", user_id=session_id, session_id=session_id)
    # TODO: Build content object:
    #         content = types.Content(role="user", parts=[types.Part(text=message)])
    # TODO: Initialize final_text = ""
    # TODO: Async iterate over _runner.run_async(
    #           user_id=session_id, session_id=session_id, new_message=content):
    #         If event.is_final_response() and event.content and event.content.parts:
    #           For each part in event.content.parts:
    #             If part.text: final_text += part.text
    # TODO: data = _extract_data_block(final_text)
    # TODO: clean_text = _strip_data_block(final_text)
    # TODO: Return {"text": clean_text, "data": data}
    pass


def _extract_data_block(text: str) -> dict | None:
    """
    Find and parse the embedded JSON data block in the agent's response.

    The agent is instructed to embed chart and table data inside a fenced block:
        ```data
        {"chart_type": "candlestick", ...}
        ```
    This function finds that block using a regex and parses the JSON inside it.
    If the block is absent or malformed, returns None — the frontend falls back
    to text-only rendering.

    Args:
        text: The full raw response text from the agent, including the data block.

    Returns:
        Parsed dict if a valid data block is present, None otherwise.
    """
    # TODO: match = re.search(r"```data\n(.*?)```", text, re.DOTALL)
    # TODO: If match:
    #         Try: return json.loads(match.group(1).strip())
    #         Except JSONDecodeError: return None
    # TODO: Return None
    pass


def _strip_data_block(text: str) -> str:
    """
    Remove the embedded data block from the agent's response text.

    After extracting the data block, we strip it so the chat bubble only
    shows the human-readable explanation without the raw JSON.

    Args:
        text: Full raw response including the data block.

    Returns:
        Clean text with the ```data ... ``` block removed and whitespace stripped.
    """
    # TODO: return re.sub(r"```data\n.*?```", "", text, flags=re.DOTALL).strip()
    pass
```

### `main.py`

```python
import os
import uuid
import shutil

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from models.schemas import ChatRequest, ChatResponse, UploadResponse, ContextRequest, ClearSessionResponse
from utils.session_store import append_message, add_file, get_files, clear_session
from agent import run_agent


app = FastAPI(
    title="Shree_v2 Backend",
    description="AI Financial Analyst Agent API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Tighten to specific origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main conversational endpoint.

    Receives a user message, appends it to session history, runs the ADK agent,
    appends the agent reply to history, and returns the structured response.
    The 'data' field in the response carries chart-ready JSON when present.
    The 'text' field carries the plain-language reply for the chat bubble.
    Raises HTTP 500 if the agent raises an unhandled exception.
    """
    # TODO: append_message(request.session_id, "user", request.message)
    # TODO: Wrap the agent call in try/except HTTPException:
    #         try:
    #           result = await run_agent(request.session_id, request.message)
    #         except Exception as e:
    #           raise HTTPException(status_code=500, detail=str(e))
    # TODO: append_message(request.session_id, "assistant", result["text"])
    # TODO: Return ChatResponse(session_id=request.session_id,
    #             text=result["text"], data=result.get("data"))
    pass


@app.post("/upload", response_model=UploadResponse)
async def upload_file(session_id: str, file: UploadFile = File(...)):
    """
    File upload endpoint.

    Saves the uploaded file to uploads/ with a UUID prefix to avoid collisions.
    Registers the file in the session store so the agent can access it later
    via tool_parse_document.
    Supported file types: .pdf, .xlsx, .xls, .txt, .csv.
    Returns the file_id the user (and agent) reference to access this file.
    """
    # TODO: file_id = str(uuid.uuid4())
    # TODO: dest = os.path.join(settings.UPLOAD_DIR, file_id + "_" + file.filename)
    # TODO: os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    # TODO: Open dest in "wb" mode and shutil.copyfileobj(file.file, dest_handle)
    # TODO: add_file(session_id, file_id, dest, file.filename)
    # TODO: Return UploadResponse(file_id=file_id, filename=file.filename,
    #             message=f"'{file.filename}' uploaded. You can now ask questions about it.")
    pass


@app.post("/context")
async def add_text_context(request: ContextRequest):
    """
    Text context injection endpoint.

    Lets the user paste raw text into the session: a company description, a news
    excerpt, personal notes, or any other context they want the agent to consider.
    The context is stored as a system message in the session history.
    Returns the character count so the frontend can warn if the context is very large.
    """
    # TODO: content = f"[User-provided context]:\n{request.context}"
    # TODO: append_message(request.session_id, "system", content)
    # TODO: Return {"message": "Context added to your session.", "char_count": len(request.context)}
    pass


@app.delete("/session/{session_id}", response_model=ClearSessionResponse)
async def delete_session(session_id: str):
    """
    Session cleanup endpoint.

    Deletes all uploaded files for this session from disk, then clears the
    session from the in-memory store. Call this when the user starts a new
    conversation or explicitly requests to reset.
    File deletion must happen BEFORE clearing the session — we need the file
    list from the session to know what to delete.
    """
    # TODO: files = get_files(session_id)
    # TODO: For each file in files:
    #         If os.path.exists(file["filepath"]):
    #           os.remove(file["filepath"])
    # TODO: clear_session(session_id)
    # TODO: Return ClearSessionResponse(message=f"Session {session_id} cleared.")
    pass


@app.get("/session/{session_id}/files")
async def list_session_files(session_id: str):
    """
    List uploaded files in a session.

    Returns file_id and filename for each uploaded file in the session.
    Used by the frontend to show the user which files are available.
    Does NOT return filepaths — those are internal server details.
    """
    # TODO: files = get_files(session_id)
    # TODO: Return {"session_id": session_id,
    #               "files": [{"file_id": f["file_id"], "filename": f["filename"]} for f in files]}
    pass


@app.get("/health")
async def health_check():
    """Health check endpoint. Returns 200 OK with version. Used to verify the server is running."""
    # TODO: Return {"status": "ok", "version": "1.0.0"}
    pass
```

### `test_tools.py`

```python
"""
Manual test script. Run with: python test_tools.py
Not a pytest suite. A quick sanity check to confirm each tool function
returns clean, JSON-serializable output before wiring into the agent.
Each test is wrapped independently so one failure does not block others.
"""

import json


def assert_json_safe(obj, label: str) -> bool:
    """
    Verify that obj can be serialized to JSON without errors.
    Prints PASS or FAIL with the label.
    Returns True if safe, False if not.
    """
    # TODO: try json.dumps(obj). On success, print f"  JSON-safe: PASS ({label})". Return True.
    # TODO: On TypeError or ValueError as e: print f"  JSON-safe: FAIL ({label}) — {e}". Return False.
    pass


def test_session_store():
    """Test all session store functions using no external dependencies."""
    print("\nSession Store Tests")
    # TODO: from utils.session_store import (append_message, get_history, add_file, get_files, clear_session)
    # TODO: sid = "test_session_001"
    # TODO: append_message(sid, "user", "Hello")
    # TODO: append_message(sid, "assistant", "Hi there")
    # TODO: hist = get_history(sid)
    # TODO: assert len(hist) == 2, "Expected 2 messages"
    # TODO: assert hist[0]["role"] == "user"
    # TODO: add_file(sid, "file001", "/tmp/test.pdf", "test.pdf")
    # TODO: files = get_files(sid)
    # TODO: assert len(files) == 1
    # TODO: assert files[0]["file_id"] == "file001"
    # TODO: clear_session(sid)
    # TODO: assert get_history(sid) == []
    # TODO: print("  All session store tests: PASS")
    pass


def test_formatters():
    """Test sanitize_dataframe and sanitize_info_dict with synthetic data."""
    print("\nFormatter Tests")
    # TODO: import pandas as pd, numpy as np
    # TODO: from utils.formatters import sanitize_dataframe, sanitize_info_dict
    # TODO: Build a test DataFrame with NaN, numpy float64, and Timestamp values:
    #         df = pd.DataFrame({
    #             "Date": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")],
    #             "Close": [np.float64(1234.5), np.float64(float("nan"))],
    #             "Volume": [np.int64(1000000), np.int64(2000000)],
    #         })
    # TODO: result = sanitize_dataframe(df)
    # TODO: assert_json_safe(result, "sanitize_dataframe")
    # TODO: assert result["Close"][1] is None, "NaN should become None"
    # TODO: Build a test info dict with numpy types and NaN:
    #         info = {"longName": "Test Corp", "currentPrice": np.float64(500.0),
    #                 "trailingPE": np.float64(float("nan")), "marketCap": np.int64(1000000000)}
    # TODO: result2 = sanitize_info_dict(info)
    # TODO: assert_json_safe(result2, "sanitize_info_dict")
    # TODO: assert result2.get("trailingPE") is None, "NaN PE should become None"
    # TODO: print("  All formatter tests: PASS")
    pass


def test_stock_info():
    """Test get_stock_info returns clean dict for TCS.NS."""
    print("\nStock Info Test (TCS.NS)")
    # TODO: from tools.stock_data import get_stock_info
    # TODO: result = get_stock_info("TCS", "NSE")
    # TODO: print(json.dumps(result, indent=2))
    # TODO: assert "error" not in result, f"Unexpected error: {result}"
    # TODO: assert result.get("currentPrice") is not None, "currentPrice missing"
    # TODO: assert_json_safe(result, "get_stock_info TCS")
    # TODO: print("  PASS")
    pass


def test_stock_history():
    """Test get_stock_history returns chart-ready arrays for WIPRO."""
    print("\nStock History Test (WIPRO.NS, 1mo)")
    # TODO: from tools.stock_data import get_stock_history
    # TODO: result = get_stock_history("WIPRO", "NSE", "1mo", "1d")
    # TODO: assert "error" not in result
    # TODO: assert "dates" in result and "close" in result
    # TODO: assert len(result["dates"]) == len(result["close"]), "dates and close length mismatch"
    # TODO: assert_json_safe(result, "get_stock_history WIPRO")
    # TODO: print(f"  {len(result['dates'])} candles returned.")
    # TODO: print(f"  First date: {result['dates'][0]}, Last close: {result['close'][-1]}")
    # TODO: print("  PASS")
    pass


def test_web_search():
    """Test Tavily returns results for a finance query."""
    print("\nWeb Search Test")
    # TODO: from tools.web_search import search_web
    # TODO: result = search_web("TCS Tata Consultancy Services Q4 results 2025")
    # TODO: assert isinstance(result, list)
    # TODO: assert len(result) > 0
    # TODO: assert "error" not in result[0]
    # TODO: assert_json_safe(result, "search_web")
    # TODO: print(f"  First result: {result[0].get('title')}")
    # TODO: print("  PASS")
    pass


def test_news_search():
    """Test NewsAPI returns articles."""
    print("\nNews Search Test")
    # TODO: from tools.news_search import search_news
    # TODO: result = search_news("Infosys", days_back=7)
    # TODO: assert isinstance(result, list)
    # TODO: assert_json_safe(result, "search_news")
    # TODO: if len(result) > 0 and "error" not in result[0]:
    #         print(f"  First article: {result[0].get('title')}")
    # TODO: print("  PASS")
    pass


def test_ticker_lookup():
    """Test ticker lookup by company name using the Indian listings file."""
    print("\nTicker Lookup Test")
    # TODO: from tools.ticker_lookup import search_ticker
    # TODO: results = search_ticker("tata steel")
    # TODO: assert isinstance(results, list)
    # TODO: print(f"  Results for 'tata steel': {results}")
    # TODO: results2 = search_ticker("TCS")
    # TODO: print(f"  Results for 'TCS': {results2}")
    # TODO: print("  PASS (verify results manually)")
    pass


if __name__ == "__main__":
    print("=" * 55)
    print("Shree_v2 Tool Tests")
    print("=" * 55)

    # TODO: Run each test in a try/except block so one failure does not stop others.
    # TODO: for test_fn in [test_session_store, test_formatters, test_stock_info,
    #                        test_stock_history, test_web_search, test_news_search,
    #                        test_ticker_lookup]:
    #         try:
    #           test_fn()
    #         except Exception as e:
    #           print(f"  EXCEPTION in {test_fn.__name__}: {e}")
    # TODO: Print final summary.
    pass
```

---

## Bonus Section — Basic Time Series Model Pipeline (If Days Remain)

If you finish Phase 1 with a day or two left, build a basic training pipeline. The goal is not a production model. The goal is to practice the full data engineering loop: raw data in, clean tensors out, model trains, loss curves print. Whether the predictions are good or not does not matter at this stage — understanding the pipeline does.

### What to Build in the Remaining Days

**If 1 day remains:** Build `DataPipeline` only. Fetch 5 years of TCS data. Run normalization and sliding window creation. Print the shape of X_train, y_train, X_val, y_val, X_test, y_test. That is the milestone. You will have confirmed the data engineering works.

**If 2 days remain:** Build `DataPipeline` on day one, `LSTMForecaster` and a basic training loop on day two. Train for 10 epochs and print the loss. Do not worry about good results yet.

---

## Phase 2 Roadmap

### Milestones

1. Study LSTM theory. Build a toy LSTM in pure PyTorch that learns to predict a sine wave. No finance data yet. Understand every line.
2. Build `DataPipeline` class. Fetch 5-year TCS data, normalize with MinMaxScaler, create 60-day input windows with 10-day targets. Print split shapes to verify no data leakage.
3. Build `LSTMForecaster` class. Train on TCS 2-year daily OHLCV data for 50 epochs. Plot training and validation loss curves using matplotlib.
4. Evaluate LSTM: plot predictions vs actuals on the test set. Compute MAE and RMSE. Understand why the model fails on sudden news-driven price spikes.
5. Build `TransformerForecaster` class with positional encoding, multi-head attention, and linear output head. Train on the same dataset.
6. Compare LSTM vs Transformer on the same test set. Document findings in `notebooks/exploration.ipynb`.
7. Replace `chronos-t5-tiny` in `tools/ts_model.py` with your trained model. Test the full integration end to end through `/chat`.
8. Extend to multi-stock training: train one model on NIFTY 50 constituents and evaluate generalization on a held-out stock.

Realistic time estimate for you: 6 to 8 weeks. Week 1 is theory and toy data. Weeks 2 through 4 are the LSTM pipeline. Weeks 5 and 6 are the Transformer. Weeks 7 and 8 are integration and multi-stock evaluation.

### Project Structure and Setup

Add the `ml/` folder inside `shree_v2_backend/`. No new API keys needed. Additional pip dependencies to add to `requirements.txt`:

```
matplotlib==3.9.1
scikit-learn==1.5.1
tqdm==4.66.4
```

```
ml/
├── __init__.py
├── data_pipeline.py             # Fetch, normalize, sliding windows, chronological split.
├── train.py                     # Generic training loop: MSELoss, Adam, checkpoint saving.
├── evaluate.py                  # MAE, RMSE, prediction vs actual plot.
├── models/
│   ├── __init__.py
│   ├── lstm_model.py            # LSTMForecaster: 2-layer LSTM with linear output head.
│   └── transformer_model.py     # TransformerForecaster: positional encoding + attention.
├── saved_models/                # .pth checkpoint files. In .gitignore.
└── notebooks/
    └── exploration.ipynb        # Free experimentation. Does not affect production code.
```

### Data Engineering Pipeline (`ml/data_pipeline.py`)

```python
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tools.stock_data import get_stock_history


class DataPipeline:
    """
    Fetches stock OHLCV data from yfinance and transforms it into PyTorch-ready sequences.

    Simple explanation:
    Imagine teaching someone to predict tomorrow's stock price by showing them 60 days of
    history. You create training examples by sliding a 60-day window across the full history,
    labeling each window with the 10 days that follow it. This class automates that process
    and handles the normalization so all features are on the same scale.

    Technical explanation:
    Implements standard supervised time series preparation:
    1. MinMaxScaler normalization fitted ONLY on training data to prevent data leakage.
    2. Sliding window creation: input_len timesteps predict output_len future closes.
    3. Chronological train/val/test split — never shuffle (future cannot inform the past).
    The scaler is fitted on the training slice, then used to transform val and test.

    Args:
        symbol: Stock symbol without suffix. Example: "TCS"
        exchange: "NSE" or "BSE"
        input_len: Look-back window size in trading days. Default 60.
        output_len: Forecast horizon in trading days. Default 10.
        features: Input feature columns. Default: all 5 OHLCV columns.
        target_col: Column to predict. Default "close".
        train_ratio: Fraction of data for training. Default 0.70.
        val_ratio: Fraction for validation. Default 0.15. Test gets the remainder.
    """

    def __init__(
        self,
        symbol: str,
        exchange: str = "NSE",
        input_len: int = 60,
        output_len: int = 10,
        features: list[str] = None,
        target_col: str = "close",
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
    ):
        # TODO: Store all constructor args as instance attributes.
        # TODO: self.features = features or ["open", "high", "low", "close", "volume"]
        # TODO: self.scaler = MinMaxScaler(feature_range=(0, 1))
        # TODO: self.raw_df = None
        # TODO: self.scaled_data = None
        pass

    def fetch_and_prepare(self, period: str = "5y") -> None:
        """
        Fetch raw data from yfinance and run the full normalization pipeline.

        Must be called before get_splits(). Populates self.raw_df and self.scaled_data.
        5 years of daily data gives roughly 1250 rows — a reasonable dataset for initial training.

        Args:
            period: yfinance period string. "5y" recommended for training. "3mo" for fast tests.
        """
        # TODO: Call get_stock_history(self.symbol, self.exchange, period, "1d").
        # TODO: Build a DataFrame from the returned dict. Set dates as the index.
        # TODO: self.raw_df = df (store for reference)
        # TODO: Extract feature columns in self.features order as a numpy array.
        # TODO: Compute train_end = int(len(feature_array) * self.train_ratio).
        # TODO: Fit scaler ONLY on feature_array[:train_end] (training data only).
        #       This prevents data leakage — test distribution cannot influence normalization.
        # TODO: self.scaled_data = self.scaler.transform(feature_array)
        #       Transform the FULL array using the training-fitted scaler.
        pass

    def _create_sequences(self, data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Convert a 2D array into supervised learning sequences via sliding window.

        X shape: [num_samples, input_len, num_features]
        y shape: [num_samples, output_len]

        X[i] is the input_len-day window starting at index i.
        y[i] is the output_len-day sequence of close prices following that window.

        Args:
            data: Scaled numpy array of shape [T, num_features].

        Returns:
            Tuple (X, y) of numpy arrays with shapes documented above.
        """
        # TODO: close_idx = self.features.index(self.target_col)
        # TODO: X, y = [], []
        # TODO: For i in range(len(data) - self.input_len - self.output_len):
        #         X.append(data[i : i + self.input_len])
        #         y.append(data[i + self.input_len : i + self.input_len + self.output_len, close_idx])
        # TODO: Return np.array(X), np.array(y)
        pass

    def get_splits(self) -> dict[str, tuple[np.ndarray, np.ndarray]]:
        """
        Return chronologically ordered train, validation, and test splits.

        The split is performed on the raw time axis BEFORE creating sequences,
        so training windows never overlap with validation or test windows.

        Returns:
            {"train": (X_train, y_train), "val": (X_val, y_val), "test": (X_test, y_test)}
        """
        # TODO: n = len(self.scaled_data)
        # TODO: train_end = int(n * self.train_ratio)
        # TODO: val_end = int(n * (self.train_ratio + self.val_ratio))
        # TODO: Slice: train_data = self.scaled_data[:train_end]
        #              val_data   = self.scaled_data[train_end:val_end]
        #              test_data  = self.scaled_data[val_end:]
        # TODO: Call _create_sequences on each slice.
        # TODO: Return the dict.
        pass

    def inverse_transform_predictions(self, scaled_predictions: np.ndarray) -> np.ndarray:
        """
        Convert scaled model output back to real rupee prices.

        The scaler was fitted on all features together. To inverse-transform only
        the close column, we place predictions into a dummy array of the full
        feature shape, inverse-transform the whole array, then extract close.

        Args:
            scaled_predictions: Shape [N, output_len] — N predictions, each of length output_len.

        Returns:
            Shape [N, output_len] with real prices in original rupee scale.
        """
        # TODO: num_features = len(self.features)
        # TODO: close_idx = self.features.index(self.target_col)
        # TODO: real_preds = []
        # TODO: For each row in scaled_predictions:
        #         dummy = np.zeros((self.output_len, num_features))
        #         dummy[:, close_idx] = row
        #         real_row = self.scaler.inverse_transform(dummy)[:, close_idx]
        #         real_preds.append(real_row)
        # TODO: Return np.array(real_preds)
        pass
```

### Training the Time Series Model (`ml/train.py`)

```python
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from tqdm import tqdm
import os


def train_model(
    model: nn.Module,
    splits: dict,
    epochs: int = 50,
    batch_size: int = 32,
    lr: float = 1e-3,
    save_path: str = "ml/saved_models/model.pth",
) -> dict:
    """
    Generic training loop usable for both LSTMForecaster and TransformerForecaster.

    Simple explanation:
    The model makes a prediction, we measure how wrong it was (the loss), and we
    nudge the model's weights slightly in the direction that would have made that
    prediction more accurate. We repeat this thousands of times until the model
    stops improving. This is what "training" means.

    Technical explanation:
    Standard PyTorch training loop using MSELoss and Adam optimizer.
    MSELoss (mean squared error) penalizes large errors more than small ones,
    which is appropriate for price prediction where big misses matter more.
    Adam adapts the learning rate per parameter, which converges faster than SGD.
    After each epoch, validates on the val set. Saves the checkpoint whenever
    val loss improves (early stopping by best-model tracking, not hard stopping).

    Args:
        model: An nn.Module (LSTMForecaster or TransformerForecaster).
        splits: Output of DataPipeline.get_splits().
        epochs: Full passes through training data.
        batch_size: Samples per gradient update. 32 is a safe default.
        lr: Adam learning rate. 1e-3 is the standard starting point.
        save_path: File path for the best model checkpoint.

    Returns:
        {"train_losses": [float per epoch], "val_losses": [float per epoch]}
        Use these lists to plot the learning curve in evaluate.py.
    """
    # TODO: X_train, y_train = splits["train"]
    # TODO: X_val, y_val = splits["val"]
    # TODO: Convert numpy arrays to float32 tensors:
    #         X_train_t = torch.tensor(X_train, dtype=torch.float32)
    #         y_train_t = torch.tensor(y_train, dtype=torch.float32)
    # TODO: Wrap in TensorDataset and DataLoader (shuffle=True for train, False for val).
    # TODO: criterion = nn.MSELoss()
    # TODO: optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    # TODO: best_val_loss = float("inf")
    # TODO: train_losses, val_losses = [], []
    # TODO: for epoch in tqdm(range(epochs), desc="Training"):
    #         TRAIN:
    #           model.train()
    #           running_loss = 0.0
    #           for X_batch, y_batch in train_loader:
    #             optimizer.zero_grad()
    #             output = model(X_batch)       <- shape [batch, output_len]
    #             loss = criterion(output, y_batch)
    #             loss.backward()
    #             optimizer.step()
    #             running_loss += loss.item()
    #           train_losses.append(running_loss / len(train_loader))
    #
    #         VALIDATE:
    #           model.eval()
    #           with torch.no_grad():
    #             compute val loss the same way
    #           val_losses.append(avg_val_loss)
    #
    #         CHECKPOINT:
    #           if val_loss < best_val_loss:
    #             best_val_loss = val_loss
    #             os.makedirs(os.path.dirname(save_path), exist_ok=True)
    #             torch.save(model.state_dict(), save_path)
    # TODO: Return {"train_losses": train_losses, "val_losses": val_losses}
    pass
```

### LSTM Model (`ml/models/lstm_model.py`)

```python
import torch
import torch.nn as nn


class LSTMForecaster(nn.Module):
    """
    Two-layer LSTM with dropout and a linear projection head for multi-step forecasting.

    Simple explanation:
    An LSTM reads through a sequence one step at a time, like a person reading through
    60 days of price data one day at a time. It has a "memory cell" that lets it remember
    things from early in the sequence when making its final prediction. After reading all
    60 days, the final hidden state is passed to a linear layer that outputs 10 predictions.

    Technical explanation:
    Input shape:  [batch_size, input_len, num_features]
    LSTM output:  [batch_size, input_len, hidden_size] (we discard all but the last step)
    Final hidden: h_n[-1] shape [batch_size, hidden_size]  (last layer, last timestep)
    Output shape: [batch_size, output_len]  (via linear projection)

    Dropout is applied between stacked LSTM layers (not after the final layer) to
    regularize the model and prevent memorizing the training data.

    Args:
        input_size: Number of input features per timestep. Example: 5 for OHLCV.
        hidden_size: LSTM hidden units. Default 128. Try 64 or 256 if underfitting/overfitting.
        num_layers: Stacked LSTM layers. Default 2. More layers = more capacity, slower training.
        output_len: Number of future steps to predict. Must match DataPipeline.output_len.
        dropout: Dropout probability between layers. Default 0.2. Range: 0.1 to 0.5.
    """

    def __init__(
        self,
        input_size: int,
        hidden_size: int = 128,
        num_layers: int = 2,
        output_len: int = 10,
        dropout: float = 0.2,
    ):
        # TODO: super().__init__()
        # TODO: Store all args as instance attributes.
        # TODO: self.lstm = nn.LSTM(
        #           input_size=input_size, hidden_size=hidden_size,
        #           num_layers=num_layers, batch_first=True, dropout=dropout)
        #       batch_first=True means input shape is [batch, seq, features] not [seq, batch, features].
        # TODO: self.fc = nn.Linear(hidden_size, output_len)
        pass

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through LSTM and linear head.

        Args:
            x: Input tensor. Shape: [batch_size, input_len, input_size].

        Returns:
            Predictions tensor. Shape: [batch_size, output_len].
        """
        # TODO: out, (h_n, c_n) = self.lstm(x)
        #       h_n shape: [num_layers, batch_size, hidden_size]
        #       out shape: [batch_size, input_len, hidden_size] — we do not use this
        # TODO: last_hidden = h_n[-1]
        #       Shape: [batch_size, hidden_size] — final layer's hidden state at last timestep
        # TODO: return self.fc(last_hidden)
        #       Shape: [batch_size, output_len]
        pass
```

### Adding the Custom Model as a Tool

When Phase 2 is complete, update `tools/ts_model.py` to load your trained LSTM instead of Chronos. The key design principle is that `predict_stock_prices` keeps the exact same function signature and return dict shape. That means `mcp_server.py`, `agent.py`, and `main.py` require zero changes. Only `ts_model.py` changes internally.

```python
# Updated tools/ts_model.py — replace Chronos with custom model

import torch
import numpy as np
import os
from ml.data_pipeline import DataPipeline
from ml.models.lstm_model import LSTMForecaster

_model = None
MODEL_PATH = "ml/saved_models/model.pth"

# Hyperparameters must match what was used during training.
# Store these in config.py eventually so they are not hardcoded here.
MODEL_INPUT_SIZE = 5    # OHLCV = 5 features
MODEL_HIDDEN_SIZE = 128
MODEL_OUTPUT_LEN = 10


def _load_model() -> LSTMForecaster | None:
    """
    Lazy-load the trained LSTM model from checkpoint.
    Returns None if the checkpoint does not exist yet (falls back to Chronos).
    """
    # TODO: global _model
    # TODO: If _model is None and os.path.exists(MODEL_PATH):
    #         model = LSTMForecaster(
    #             input_size=MODEL_INPUT_SIZE,
    #             hidden_size=MODEL_HIDDEN_SIZE,
    #             output_len=MODEL_OUTPUT_LEN,
    #         )
    #         model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
    #         model.eval()
    #         _model = model
    # TODO: Return _model (None if no checkpoint exists)
    pass


def predict_stock_prices(symbol: str, exchange: str = "NSE", horizon_days: int = 10) -> dict:
    """
    Same interface as the Chronos version.
    Tries the custom LSTM first. Falls back to Chronos if no checkpoint exists.
    Return dict shape is identical — frontend code requires no changes.
    """
    # TODO: model = _load_model()
    # TODO: If model is None: fall back to the Chronos implementation.
    #         from chronos import ChronosPipeline
    #         (use the original Chronos code path)
    # TODO: Build DataPipeline(symbol, exchange, output_len=horizon_days).
    # TODO: Call pipeline.fetch_and_prepare("3mo").
    # TODO: Use the last input_len rows of pipeline.scaled_data as the input sequence.
    # TODO: Convert to tensor: x = torch.tensor(...).unsqueeze(0)  <- add batch dim
    # TODO: With torch.no_grad(): output = model(x)  <- shape [1, output_len]
    # TODO: scaled_preds = output[0].numpy().reshape(1, -1)  <- shape [1, output_len]
    # TODO: real_preds = pipeline.inverse_transform_predictions(scaled_preds)[0]
    # TODO: Return dict with same structure as Chronos version.
    #       historical_dates, historical_closes from pipeline.raw_df.
    #       forecast_median = real_preds.tolist()
    #       forecast_low and forecast_high: for the basic LSTM, set these equal to median
    #       (the LSTM gives a point estimate, not a distribution — unlike Chronos).
    #       Add a note explaining this is a point forecast without confidence bands.
    pass
```
