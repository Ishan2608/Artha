# Shree — AI Financial Analyst

Shree is an AI financial analyst assistant tailored for Indian retail investors. It is powered by **Google ADK** and **Gemini 2.0 Flash**, and exposes a **FastAPI** backend that a frontend or CLI client can talk to.

---

## Architecture Overview

```
tools/                  Pure business logic (stock data, web search, news, etc.)
utils/                  Shared utilities (formatters, doc parser, RAG engine, session store)
agent.py                ADK wiring layer — registers tools, exposes run_agent()
main.py                 FastAPI server — /chat, /upload, /context, /session routes
mcp_server.py           Optional standalone MCP server for external MCP clients
test_run.py             Terminal chat client — full agent experience, no server needed
test_tools.py           Tool-level sanity check suite
data/listings/          INDIA_LIST.csv — NSE/BSE ticker lookup table
uploads/                Runtime file upload directory (created automatically)
```

---

## Setup

### 1. Virtual Environment

```bash
# Create
python -m venv venv

# Activate — Windows
venv\Scripts\activate

# Activate — macOS / Linux
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install --upgrade pip

pip install \
  fastapi uvicorn[standard] \
  google-adk google-generativeai \
  mcp \
  pydantic-settings \
  yfinance pandas numpy \
  tavily-python newsapi-python \
  PyPDF2 python-docx openpyxl python-pptx \
  python-multipart \
  torch transformers accelerate \
  chromadb sentence-transformers \
  colorama

# Chronos forecasting model (installs from GitHub)
pip install git+https://github.com/amazon-science/chronos-forecasting.git
```

> **Note for AMD GPU / CPU-only machines:** PyTorch CUDA is not required. The Chronos model runs on CPU by default.

### 3. Save Dependencies

```bash
# Freeze current environment to requirements.txt
pip freeze > requirements.txt

# Reinstall from requirements.txt on another machine
pip install -r requirements.txt
```

---

## Configuration

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
NEWS_API_KEY=your_newsapi_key_here
```

| Key | Where to get it |
|---|---|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `TAVILY_API_KEY` | [Tavily](https://app.tavily.com) |
| `NEWS_API_KEY` | [NewsAPI](https://newsapi.org) |

---

## Running the Project

### FastAPI Server
```bash
uvicorn main:app --reload
```
Swagger UI available at `http://localhost:8000/docs`.

### Terminal Chat Client (no server needed)
```bash
python test_run.py
```
Full agent experience — tool calls, file uploads, chart data — all from the command line.

### Tool Sanity Checks
```bash
python test_tools.py
```
Runs all 10 tools in isolation with coloured pass/fail output.

### MCP Server (optional — for external MCP clients only)
```bash
python mcp_server.py
```
Only needed if connecting an external MCP client (e.g. Claude Desktop). Not used by the FastAPI server or CLI.

---

## API Routes

| Method | Route | Description |
|---|---|---|
| `POST` | `/chat` | Send a message to the agent |
| `POST` | `/upload?session_id=...` | Upload a file (PDF, DOCX, Excel, CSV, TXT, PPT) |
| `POST` | `/context` | Inject raw text context into a session |
| `DELETE` | `/session/{session_id}` | Clear session and delete uploaded files |
| `GET` | `/session/{session_id}/files` | List files uploaded in a session |
| `GET` | `/health` | Health check |
