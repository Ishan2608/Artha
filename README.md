# ⬡ Artha — AI Financial Analyst for Indian Markets

Artha is a conversational AI agent designed to assist Indian retail investors. You talk to it like a chat interface — ask it to analyse a stock, fetch the latest news, predict prices, or explain a concept — and it figures out what tools to use, runs them, and gives you a structured answer, often with a chart.

It is not a simple chatbot that looks things up. It is a tool-calling agent that can reason across multiple steps: fetch historical price data, compute technical indicators, search the web for news, read a document you uploaded, and synthesise all of that into a single coherent response.

---

## What it can do

**Market data and analysis**
- Fetch historical OHLCV price data for any NSE or BSE listed stock
- Compute technical indicators (RSI, MACD, Bollinger Bands, moving averages)
- Run fundamental analysis (P/E ratio, EPS, revenue, balance sheet metrics)
- Plot candlestick charts with volume

**Forecasting**
- Generate multi-day price forecasts using Amazon Chronos T5 Tiny, a time-series foundation model
- Returns forecast with confidence intervals (10th–90th percentile ribbon)

**Web and news search**
- Live web search via Tavily for any financial or general query
- Dedicated news fetch via NewsAPI filtered to Indian markets and specific companies

**Document analysis**
- Upload PDFs, Word documents, Excel sheets, CSVs, PowerPoint files
- Ask questions about the uploaded document — Artha reads and answers using RAG (ChromaDB + SentenceTransformers)
- Multiple documents can coexist in a session

**Conversation memory**
- Every message is saved to a database, linked to your account
- History is restored on every login — you pick up exactly where you left off
- The agent always has the full conversation in context, so follow-up questions work naturally

---

## How it works

Artha exposes a FastAPI backend. A Streamlit frontend talks to it over HTTP. The core of the system is a LangGraph ReAct agent.

```
User (browser)
     │
     ▼
Streamlit Frontend  ──HTTP──►  FastAPI Backend
                                     │
                              JWT Auth check
                                     │
                              Load chat history
                              from SQLite DB
                                     │
                                     ▼
                            LangGraph ReAct Agent
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                 ▼
              Stock Tools      Search Tools     Document Tools
              (yfinance)    (Tavily, NewsAPI)  (ChromaDB RAG)
                    │                                  │
                    └──────────────┬───────────────────┘
                                   ▼
                          Forecasting Tool
                          (Chronos T5 Tiny)
                                   │
                                   ▼
                        Agent assembles response
                        (text + optional chart data)
                                   │
                                   ▼
                        Saved to DB, returned to frontend
```

**ReAct loop**: The agent receives your message plus the full conversation history. It decides which tools to call (if any), calls them, observes the results, and may call more tools before writing its final answer. This means a single question like *"Compare TCS and Infosys technically over the last month"* will trigger multiple sequential tool calls automatically.

**Two agent modes**: A single-agent setup where one LangGraph agent handles everything, and a multi-agent setup with a router that delegates to a specialist analyst agent (stock data) or an aggregator agent (web, news, documents) depending on the query.

**Session = User**: Each registered user has exactly one persistent chat session. The session ID is derived from the user's database ID. This keeps the architecture simple while ensuring the agent always has the right history and files in context.

---

## Sample Output

![Test Run - Query](./docs/outputs/1.PNG)
![Test Run - Result](./docs/outputs/2.PNG)

---

## Stack

| Aspect | Technology |
|---|---|
| Frontend | Streamlit + Plotly |
| Backend API | FastAPI + Uvicorn |
| Agent framework | LangGraph ReAct + LangChain |
| LLMs | Groq — Llama 3.3 70B · Google Gemini |
| Stock data | yfinance (NSE + BSE) |
| Web search | Tavily |
| News | NewsAPI |
| Forecasting | Amazon Chronos T5 Tiny |
| Document RAG | ChromaDB + SentenceTransformers |
| Database | SQLite (default) |
| Auth | JWT (python-jose) + bcrypt (passlib) |

---

## Project Structure

```
artha/
│
├── main.py              # FastAPI app — all HTTP routes and middleware
├── agent.py             # Single-agent: LangGraph ReAct + tool definitions
├── multi_agent.py       # Multi-agent: router, analyst agent, aggregator agent
├── config.py            # All env config loaded via pydantic-settings
├── db.py                # SQLAlchemy engine, session factory, table init
├── auth.py              # Password hashing, JWT sign/verify, FastAPI dependency
│
├── models/
│   ├── db_models.py     # ORM models: User, Message, UploadedFile
│   └── schemas.py       # Pydantic request/response schemas for all routes
│
├── tools/               # Individual tool modules
│   │                    # (stock data, web search, news, ticker lookup, forecasting)
│
├── utils/
│   ├── session_store.py # DB-backed memory: get_history, append_message, etc.
│   ├── doc_parser.py    # Extracts text from PDF, DOCX, XLSX, CSV, PPT
│   ├── rag_engine.py    # ChromaDB vector store for document Q&A
│   └── formatters.py    # Response post-processing helpers
│
├── data/
│   └── listings/
│       └── INDIA_LIST.csv  # Merged NSE + BSE ticker listings for symbol lookup
│
├── tests/
│   └── scripts/
│       ├── test_tools.py   # Unit tests for individual tools, no agent involved
│       ├── test_agent.py   # End-to-end tests, 8 automated prompts
│       └── test_run.py     # Interactive terminal chat client (login → chat)
│
└── frontend/            # Streamlit frontend
    ├── app.py           # Entry point — routing between auth and chat screens
    ├── config.py        # Backend URL and all endpoint paths, theme tokens
    ├── utils/
    │   ├── api_client.py   # Every HTTP call to the backend, centralised
    │   └── formatters.py   # Plotly chart builder for all chart types
    ├── components/
    │   ├── auth_page.py    # Login / register screen with tabbed form
    │   ├── chat_page.py    # Conversation interface, message bubbles, suggestions
    │   ├── sidebar.py      # File upload, context injection, session controls
    │   └── chart_card.py   # Renders Plotly charts from agent data blocks
    └── styles/
        └── main.css        # Dark financial theme injected into Streamlit
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/Ishan2608/Artha.git
cd Artha
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
pip install streamlit plotly    # frontend
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Fill in `.env`:

```
# Auth — generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=

# LLMs
GROQ_API_KEY=
GEMINI_API_KEY=
GEMINI_API_KEY_ANALYSIS=
GEMINI_API_KEY_AGGREGATOR=

# Tools
TAVILY_API_KEY=
NEWS_API_KEY=

# Storage
UPLOAD_DIR=uploads
```

The SQLite database (`artha.db`) and uploads folder are created automatically on first run.

---

## Running the Program

### Backend

```bash
uvicorn main:app --reload
```

Runs at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

### Frontend

Open a second terminal in the same virtual environment:

```bash
cd frontend
streamlit run app.py
```

Opens at `http://localhost:8501`. Register an account on first visit, then start chatting.

### Terminal client (optional)

If you prefer testing without a browser:

```bash
python tests/scripts/test_run.py
```

This presents a login/register prompt in the terminal, then drops into a full conversation loop with file upload and colour-coded output.

---

## API Reference

All routes except auth and health require `Authorization: Bearer <token>` in the request header. The token is returned by `/auth/register` and `/auth/login`.

| Method | Route | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | ❌ | Create account, returns JWT |
| `POST` | `/auth/login` | ❌ | Verify credentials, returns JWT |
| `GET` | `/auth/me` | ✅ | Current user profile |
| `POST` | `/chat` | ✅ | Send a message, get agent reply + optional chart data |
| `GET` | `/chat/history` | ✅ | Full conversation history for this user |
| `DELETE` | `/chat/history` | ✅ | Wipe conversation and delete all uploaded files |
| `POST` | `/upload` | ✅ | Upload a document (PDF, DOCX, XLSX, CSV, TXT, PPT) |
| `GET` | `/files` | ✅ | List files uploaded in this session |
| `POST` | `/context` | ✅ | Inject raw text context into the session |
| `GET` | `/health` | ❌ | Health check |

---

## Testing

```bash
python tests/scripts/test_tools.py   # tool-level, no agent
python tests/scripts/test_agent.py   # automated end-to-end, 8 prompts
python tests/scripts/test_run.py     # interactive terminal chat with login
```

Logs are saved to `tests/logs/` as Markdown files.

---

## Disclaimer

For educational purposes only. Nothing produced by this application constitutes financial advice.
