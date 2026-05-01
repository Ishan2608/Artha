# ⬡ Artha — AI Financial Analyst

> A production-ready REST API for conversational financial intelligence. Artha combines a ReAct agent, real-time market data, document RAG, and a custom-trained Transformer forecasting model into a single, authenticated backend.

---

## Table of Contents

- [Overview](#overview)
- [Capabilities](#capabilities)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Machine Learning](#machine-learning)
- [Sample Output](#sample-output)
- [Disclaimer](#disclaimer)

---

## Overview

Artha is a backend service that lets users have natural-language conversations about Indian stock markets. A user sends a message; the agent decides which tools to invoke — fetching live prices, running technical or fundamental analysis, searching the news, parsing uploaded documents, or generating a price forecast — and returns a structured response with optional chart data.

Authentication is handled via JWT. Each user's conversation history, uploaded files, and session context are persisted in SQLite, scoped to their user ID.

---

## Capabilities

| Capability | What Artha can do |
|---|---|
| **Data Fetching** | Live and historical OHLCV prices for any NSE / BSE ticker via yfinance |
| **Technical Analysis** | Moving averages, RSI, MACD, Bollinger Bands, volume profiles |
| **Fundamental Analysis** | P/E, EPS, revenue, debt ratios, dividend history, balance sheet |
| **Forecasting** | 5-day price prediction using a custom Transformer trained on Nifty-50 |
| **Web Search** | Real-time query answering via Tavily |
| **News Aggregation** | Latest market news filtered by ticker or topic via NewsAPI |
| **Document RAG** | Upload PDFs, DOCX, XLSX, CSV, TXT, PPT — ask questions about them |
| **Visualization** | Returns structured chart data (candlestick, forecast, indicators) |
| **Education** | Explains financial concepts in plain language |
| **Summarization** | Condenses long reports, filings, and news into key takeaways |

---

## Architecture

Artha supports two agent configurations:

### Single Agent
One ReAct agent with access to the full tool suite. Best for straightforward queries.

### Multi-Agent *(in branch - multi-agent)*
A three-tier system with specialised roles:

```
User Message
     │
     ▼
 ┌─────────────────────────┐
 │   Router / Orchestrator │  — decides which sub-agent handles the request
 └────────────┬────────────┘
              │
     ┌────────┴──────────┐
     ▼                   ▼
┌──────────┐      ┌──────────────┐
│ Analyst  │      │  Aggregator  │
│  Agent   │      │    Agent     │
│          │      │              │
│ Live data│      │ Web search   │
│ TA / FA  │      │ News fetch   │
│ Charts   │      │ Doc RAG      │
│ Forecast │      │ Summarise    │
└──────────┘      └──────────────┘
```

---

## Tech Stack

| Layer | Tool |
|---|---|
| **API framework** | FastAPI + Uvicorn |
| **Agent** | LangGraph ReAct + LangChain |
| **LLM** | Google Gemini (via `GEMINI_API_KEY`) |
| **Authentication** | JWT (python-jose) + bcrypt |
| **Database** | SQLite via SQLAlchemy ORM |
| **Stock Data** | yfinance (NSE + BSE) |
| **Web Search** | Tavily |
| **News** | NewsAPI |
| **Forecasting** | Custom Transformer (Nifty-50, PyTorch) |
| **Document RAG** | ChromaDB + SentenceTransformers |
| **Config** | pydantic-settings + `.env` |

---

## Project Structure

```
artha-backend/
│
├── main.py                  # FastAPI app, route definitions, lifespan
├── agent.py                 # LangGraph ReAct agent + tool registrations
├── auth.py                  # JWT creation, password hashing, Depends guard
├── config.py                # Centralised settings via pydantic-settings
├── db.py                    # SQLAlchemy engine, SessionLocal, Base, init_db()
│
├── models/
│   ├── db_models.py         # ORM: User, Message, UploadedFile
│   └── schemas.py           # Pydantic request / response models
│
├── tools/
│   ├── stock_data.py        # OHLCV fetch, historical data helpers
│   ├── technical.py         # TA indicators (RSI, MACD, BB, SMA …)
│   ├── fundamental.py       # Fundamentals, ratios, balance sheet
│   ├── ticker_lookup.py     # Fuzzy company → NSE/BSE ticker resolution
│   ├── news.py              # NewsAPI integration
│   ├── search.py            # Tavily web search
│   └── ts_model.py          # Price forecasting (custom Transformer / Chronos)
│
├── utils/
│   ├── session_store.py     # DB-backed per-user message + file registry
│   ├── doc_parser.py        # Multi-format file text extraction
│   ├── rag_engine.py        # ChromaDB ingestion + semantic search
│   └── formatters.py        # Agent output → JSON-serialisable response
│
├── ml/
│   ├── custom/
│   │   └── nifty50_model/   # Trained Transformer checkpoint (PyTorch zip)
│   └── training_akshat.ipynb  # Full training notebook (data → model → eval)
│
├── data/
│   ├── companies.json       # All NSE / BSE listed companies + metadata
│   └── fetch_listings.py    # Script used to build companies.json
│
├── tests/
│   ├── scripts/
│   │   ├── test_tools.py    # 16 isolated tool tests, no agent involved
│   │   ├── test_run.py      # Interactive terminal chat client
│   │   └── test_agent.py    # Automated end-to-end, 8 canned prompts
│   └── logs/                # Session logs (auto-generated)
│
├── uploads/                 # User-uploaded files (runtime, gitignored)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup

### Prerequisites

- Python 3.10+
- A `.env` file with the keys listed below

### Install

```bash
git clone https://github.com/Ishan2608/Artha.git
cd artha-backend

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env            # then fill in your API keys
```

### Run

```bash
uvicorn main:app --reload
```

| Endpoint | URL |
|---|---|
| API base | `http://localhost:8000` |
| Interactive docs | `http://localhost:8000/docs` |
| Redoc | `http://localhost:8000/redoc` |

The SQLite database (`artha.db`) and the `uploads/` directory are created automatically on first startup via the FastAPI lifespan handler — no migrations needed.

---

## Environment Variables

Copy `.env.example` to `.env` and populate every key before running.

```env
# LLM
GEMINI_API_KEY=your_gemini_key

# Tool API keys
TAVILY_API_KEY=your_tavily_key
NEWS_API_KEY=your_newsapi_key

# Auth
SECRET_KEY=a_long_random_secret_string
ACCESS_TOKEN_EXPIRE_HOURS=24

# File storage
UPLOAD_DIR=uploads

# Database (SQLite default; swap for Postgres URL when scaling)
DATABASE_URL=sqlite:///./artha.db

# Session
SESSION_TTL_SECONDS=3600
```

> **Note** — `DATABASE_URL` can be swapped to a PostgreSQL connection string (`postgresql+psycopg2://user:pass@host/db`) with no code changes. SQLite is the default for zero-infrastructure local development.

---

## API Reference

All routes except `/auth/*` and `/health` require a `Bearer` token in the `Authorization` header.

### Authentication

| Method | Route | Description |
|---|---|---|
| `POST` | `/auth/register` | Create a new user account |
| `POST` | `/auth/login` | Exchange credentials for a JWT access token |

### Chat

| Method | Route | Description |
|---|---|---|
| `POST` | `/chat` | Send a message; receive agent reply + optional chart data |
| `GET` | `/chat/history` | Retrieve conversation history for the current user |

### Files & Context

| Method | Route | Description |
|---|---|---|
| `POST` | `/upload` | Upload a file into the user's session (PDF, DOCX, XLSX, CSV, TXT, PPT) |
| `POST` | `/context` | Inject raw text context or instructions into the session |
| `GET` | `/session/{id}/files` | List all files registered for a session |
| `DELETE` | `/session/{id}` | Clear session history and delete uploaded files |

### Utility

| Method | Route | Description |
|---|---|---|
| `GET` | `/health` | Liveness check — returns `{"status": "ok"}` |

### Request / Response shapes

**`POST /chat`**
```json
// Request
{ "message": "Analyse HDFC Bank for me" }

// Response
{
  "text": "HDFC Bank (HDFCBANK.NS) is a leading private-sector bank…",
  "data": {
    "chart_type": "candlestick",
    "symbol": "HDFCBANK",
    "dates": ["2025-01-02", "…"],
    "open":  [1640.0, "…"],
    "high":  [1658.5, "…"],
    "low":   [1635.2, "…"],
    "close": [1651.0, "…"]
  }
}
```

**`POST /upload`**
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "Authorization: Bearer <token>" \
  -F "file=@annual_report.pdf"
```

---

## Testing

Three test scripts are provided, each with a different scope.

```bash
# 1. Tool-level tests (no agent, no LLM calls)
#    Runs 16 isolated tests covering every tool and the DB-backed session store.
python tests/scripts/test_tools.py

# 2. Interactive terminal chat
#    Full agent loop in your terminal. Supports /upload, /history, /clear, etc.
python tests/scripts/test_run.py

# 3. Automated end-to-end
#    Fires 8 canned financial prompts through the full agent stack and logs results.
python tests/scripts/test_agent.py
```

Logs from all three scripts are written to `tests/logs/` with timestamped filenames.

### Terminal client commands

| Command | Action |
|---|---|
| `/upload` | Upload a file into the active session |
| `/context` | Inject plain-text context or instructions |
| `/files` | List files uploaded in this session |
| `/history` | Print clean conversation history |
| `/clear` | Wipe session history and files |
| `/new` | Start a fresh session |
| `/session` | Show current session ID and log path |
| `/help` | Show all commands |
| `/quit` | Exit |

---

## Machine Learning

### Custom Nifty-50 Transformer

Artha ships with a custom-trained time-series Transformer for 5-day price forecasting, replacing the original Amazon Chronos dependency.

| Property | Value |
|---|---|
| **Architecture** | Transformer Encoder (2 layers, 4 heads, d_model=64) |
| **Input** | 120-day look-back window, 15 features per timestep |
| **Output** | 5 trading-day point forecast |
| **Training data** | 5 years of OHLCV for all 48 Nifty-50 constituents |
| **Features** | Open, High, Low, Close, Volume + return_1d, return_5d, SMA-20, EMA-12, EMA-26, MACD, RSI-14, BB width, volatility, volume ratio |
| **Stock coverage** | Known stocks use a dedicated learned embedding; unseen stocks use zero-shot mean embedding transfer |
| **Checkpoint** | `ml/custom/nifty50_model/` (PyTorch zip format) |

The full training pipeline — data fetching, feature engineering, training loop, few-shot adaptation, and evaluation — is documented in `ml/training_akshat.ipynb`.

### Reverting to Chronos

The original Chronos T5 Tiny backend is preserved as commented-out code in `tools/ts_model.py`. To switch back:

1. Comment out the **CUSTOM MODEL** section in `ts_model.py`.
2. Uncomment the **CHRONOS BACKEND** section below it.

No other files need to change.

---

## Sample Output

**Terminal chat — query and response**

![Test Run - Query](./docs/outputs/1.PNG)
![Test Run - Result](./docs/outputs/2.PNG)

**Web UI **

![UI - Auth Page](./docs/outputs/3.PNG)
![Sample Chatting](./docs/outputs/chat_ans1.PNG)
![Sample Chatting](./docs/outputs/chat_ans2.PNG)
![Sample Chatting](./docs/outputs/chat_ans3.PNG)
![Sample Chatting](./docs/outputs/chat_ans4.PNG)

---

## Disclaimer

Artha is built for educational and research purposes only. Nothing produced by this API — including price forecasts, technical signals, or fundamental summaries — constitutes financial advice. Always consult a qualified financial professional before making investment decisions.
