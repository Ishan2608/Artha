# Artha — AI Financial Analyst

Artha is an AI-powered financial analyst assistant for Indian retail investors.
Ask about stock prices, run full analyses, upload documents, and get price forecasts — all from a terminal or a REST API.

> **"Artha"** means wealth and purpose in Sanskrit.


## Stack

- **LLM:** Groq (`llama-3.3-70b-versatile`) via LangChain — generous free tier, fast inference
- **Agent framework:** LangChain + LangGraph
- **Tools:** yfinance, Tavily, NewsAPI, Amazon Chronos, ChromaDB
- **Backend API:** FastAPI
- **MCP Server:** FastMCP — single source of truth for all tool definitions


## Quickstart

### 1. Clone and create virtual environment

```bash
git clone <your-repo-url>
cd artha_backend

python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Install Chronos separately (not on PyPI):

```bash
pip install git+https://github.com/amazon-science/chronos-forecasting.git
```

Verify:

```bash
python -c "from chronos import ChronosPipeline; print('Chronos OK')"
```

The first forecast call will download model weights (~300 MB) and cache them at `~/.cache/huggingface/hub/`.

### 3. Set up API keys

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here
NEWS_API_KEY=your_key_here
UPLOAD_DIR=uploads
SESSION_TTL_SECONDS=3600
```

| Key | Get it from | Free tier |
|-----|-------------|-----------|
| `GROQ_API_KEY` | https://console.groq.com | 14,400 req/day |
| `GEMINI_API_KEY` | https://aistudio.google.com/app/apikey | ~1,500 req/day |
| `TAVILY_API_KEY` | https://app.tavily.com | 1,000 searches/month |
| `NEWS_API_KEY` | https://newsapi.org/register | 100 req/day |

`yfinance` requires no API key.


## Running the App

### Terminal chat (no frontend needed)

```bash
python tests/scripts/test_run.py
```

### Test Only Tools

```bash
python tests/scripts/test_tools.py
```

Starts an interactive terminal session. Supports file uploads, context injection, and full multi-turn conversation. Session transcripts are saved to `logs/`.

### Backend API (for a frontend)

```bash
uvicorn main:app --reload
```

Swagger UI: `http://localhost:8000/docs`

### Tool tests

```bash
python test_tools.py
```

Runs all tool functions independently and prints verbose output. No agent involved — good for verifying API keys and data quality.

## API Routes

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/chat` | Send a message to the agent |
| `POST` | `/upload?session_id=...` | Upload a file (PDF, DOCX, Excel, CSV, TXT, PPT) |
| `POST` | `/context` | Inject raw text context into a session |
| `DELETE` | `/session/{id}` | Clear a session and delete its uploaded files |
| `GET` | `/session/{id}/files` | List files uploaded in a session |
| `GET` | `/health` | Health check |


## Project Structure

```
artha_backend/
├── main.py            # FastAPI routes
├── agent.py           # LangChain agent + run_agent()
├── mcp_server.py      # FastMCP tool server
├── config.py          # Settings loaded from .env
├── test_run.py        # Terminal chat UI
├── test_tools.py      # Tool test suite
├── requirements.txt
├── .env               # Your API keys — never commit
├── .env.example
│
├── tests/             # Testing scripts, files and logs.
├── tools/             # Plain Python functions (no framework)
├── utils/             # Formatters, session store, doc parser, RAG engine
├── models/            # Pydantic schemas
├── data/              # Indian stock listings CSV
├── logs/              # Per-session chat transcripts
├── uploads/           # Uploaded files (auto-created, gitignored)
└── ml/                # Phase 2 — custom forecasting model
```

## Notes

- `mcp_server.py` is **never run manually**. It is launched automatically as a subprocess when the agent receives its first message.
- Any `print()` statement in files imported by `mcp_server.py` must use `file=sys.stderr` — stdout is reserved for MCP protocol messages.
- Session state is **in-memory only**. Restarting the server clears all sessions. For production, replace `utils/session_store.py` with a Redis backend.
