# ⬡ Artha Backend

REST API for the Artha AI financial analyst. Built with FastAPI + LangGraph + Groq.

Artha is an AI Agent built for Financial Assitance with various capabilities
- Data Fetching
- Data Analyses
  - Technical Analyses
  - Fundamental Analyses
- Visualization
- Predictions, 
- Education,
- Summarization

Two Approaches:
- Single Agent
- Multi-Agent
  - A guide/router that decides which sub agent to use. 
  - An analyst tool to perform stock data related tasks.
  - Aggregator tool to fetch and summarize data from internet, news, and files.
---

## Sample Output

![Test Run - Query](./docs/outputs/1.PNG)
![Test Run - Result](./docs/outputs/2.PNG)
![UI - Auth Page](./docs/outputs/3.PNG)

## Stack

| Aspect | Tool/Source |
|--------|-------------|
| API | FastAPI + Uvicorn |
| Agent | LangGraph ReAct + LangChain |
| LLM | Groq — Llama 3.3 70B |
| Stock Data | yfinance (NSE + BSE) |
| Web Search | Tavily |
| News | NewsAPI |
| Forecasting | Amazon Chronos T5 Tiny |
| Document RAG | ChromaDB + SentenceTransformers |

---

## Setup

```bash
git clone https://github.com/Ishan2608/Artha.git
cd artha-backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # fill in your API keys
uvicorn main:app --reload
```

API runs at `http://localhost:8000` · Swagger at `http://localhost:8000/docs`

## Environment Variables

```
GROQ_API_KEY=
GEMINI_API_KEY=
TAVILY_API_KEY=
NEWS_API_KEY=
UPLOAD_DIR=uploads
```

## API

| Method | Route | Description |
|---|---|---|
| `POST` | `/chat` | Send a message, get agent reply + optional chart data |
| `POST` | `/upload?session_id=` | Upload a file (PDF, DOCX, XLSX, CSV, TXT, PPT) |
| `POST` | `/context` | Inject raw text context into a session |
| `DELETE` | `/session/{id}` | Clear session and delete uploaded files |
| `GET` | `/session/{id}/files` | List files in a session |
| `GET` | `/health` | Health check |

---

## Testing

```bash
python tests/scripts/test_tools.py   # tool-level tests, no agent
python tests/scripts/test_agent.py   # automated end-to-end, 8 prompts
python tests/scripts/test_run.py     # interactive terminal chat
```

Logs saved to `tests/logs/`.

---

## Structure

```
├── main.py              # FastAPI routes
├── agent.py             # LangGraph agent + all tool definitions
├── config.py            # Env config via pydantic-settings
├── auth.py              # Authentication utilities -> hash_password(plain), verify_password(plain, hashed), create_access_token(user_id), get_current_user(token, db)
├── db.py                # SQLite is used out-of-the-box so no infrastructure is needed.
├── tools/               # Stock data, web/news search, ticker lookup, forecasting
├── utils/               # Doc parser, RAG engine, session store, formatters
├── ml/                  # DL training. Contains IPYNB and model.
├── models/schemas.py    # Pydantic request/response models
├── data/                # Contains list of companies listed on Indian Stock Market, and the code to extract that data.
└── tests/               # Tool tests, agent tests, terminal chat client
```

## Disclaimer

For educational purposes only. Nothing produced by this API constitutes financial advice.
