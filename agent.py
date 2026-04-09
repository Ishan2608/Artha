"""
agent.py — Artha Agent (LangChain + Groq, no MCP)

Tools are bound directly as LangChain @tool functions defined in this file.
Each tool wraps the plain functions in tools/ and utils/ — zero MCP overhead,
no subprocess, no IPC, no session-store isolation bug.

Singleton design:
  _agent is built once on the first run_agent() call and reused forever.
  Heavy imports (chromadb, sentence-transformers, chronos, torch) are kept
  inside their respective modules and loaded lazily — only when a tool is
  actually called, not at agent startup.

Public entry point:
  run_agent(session_id, message) -> {"text": str, "data": dict | None}

Caller contract (main.py):
  Do NOT append the current user message to session_store before calling
  run_agent(). Append both user message AND assistant reply AFTER it returns.
"""

import json
import re
import os

from config import settings

os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool

from utils.session_store import get_history


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Artha, an AI financial analyst for Indian retail investors.
# TOOLS
- Stock: get_stock_info_tool, get_stock_history_tool, get_financials_tool,
get_corporate_actions_tool, get_analyst_data_tool, get_holders_tool,
get_esg_data_tool, get_upcoming_events_tool
- Search: search_web_tool, search_news_tool
- Ticker: search_ticker_tool
- Documents: parse_document_tool, search_documents_tool
- Forecast: predict_stock_tool

# RULES
1. Never fabricate data. Always use tools.
2. Company name given → call search_ticker_tool FIRST. Never guess tickers.
3. Chain tools as needed in one turn. Don't stop early.
4. Handle tool errors gracefully.
5. End every financial analysis with: "This is not financial advice."

# TOOL SELECTION
- Company name (not ticker)  → search_ticker_tool → then data tools
- Price / fundamentals       → get_stock_info_tool
- Historical prices / chart  → get_stock_history_tool
- Financials (P&L/BS/CF)     → get_financials_tool
- Analyst targets            → get_analyst_data_tool
- Forecast / prediction      → predict_stock_tool
- News                       → search_news_tool
- General research           → search_web_tool
- Uploaded file (broad)      → parse_document_tool(session_id)
- Uploaded file (specific)   → search_documents_tool(session_id, query)

# MULTI-STEP WORKFLOW
For complex tasks (e.g. "find top impacted sectors, analyse companies, forecast"):
1. RESEARCH → search_news_tool / search_web_tool
2. IDENTIFY → extract company names from results
3. RESOLVE  → search_ticker_tool per company
4. FETCH    → get_stock_info_tool (+ others) per ticker
5. ANALYSE  → synthesise into structured report
6. FORECAST → predict_stock_tool per ticker if requested
7. REPORT   → write final response

# STOCK REPORT FORMAT
1. Summary | 2. Current Price (52w range, vs target) | 3. Fundamentals (PE, P/B, margins, D/E, ROE)
4. Financials (trend) | 5. Analyst View | 6. Recent News (2–3 items) | 7. Key Risks (3–5) | 8. Disclaimer

# CHARTS
After any historical or forecast response, append exactly one data block at the end:

Candlestick:
```data
{"chart_type":"candlestick","symbol":"SYMBOL","dates":[...],"open":[...],"high":[...],"low":[...],"close":[...]}
```
Forecast:
```data
{"chart_type":"forecast","symbol":"SYMBOL","horizon_days":N,"historical_dates":[...],"historical_closes":[...],"forecast_median":[...],"forecast_low":[...],"forecast_high":[...]}
```

# DOCUMENTS
session_id is in the system note appended to every user message. Pass it exactly to document tools.
"""


# ─────────────────────────────────────────────────────────────────────────────
# TOOL DEFINITIONS
# Each tool imports its dependency inline so the heavy library is loaded only
# on first call, not at agent startup.
# ─────────────────────────────────────────────────────────────────────────────

@tool
def get_stock_info_tool(symbol: str, exchange: str = "NSE") -> dict:
    """
    Get current snapshot for a listed Indian stock: real-time price, previous close,
    day high/low, 52-week range, PE ratio, forward PE, P/B ratio, dividend yield,
    market cap, debt-to-equity, ROE, gross/operating/profit margins, analyst price
    targets (mean, high, low) and consensus recommendation.

    Use this as the FIRST data call whenever the user asks about a stock's current
    state, valuation, or fundamentals. Call it for EACH company in multi-company analysis.

    symbol   : NSE/BSE ticker WITHOUT exchange suffix. E.g. TCS, WIPRO, HDFCBANK.
    exchange : 'NSE' (default) or 'BSE'.
    """
    from tools.stock_data import get_stock_info
    return get_stock_info(symbol, exchange)


@tool
def get_stock_history_tool(
    symbol: str,
    exchange: str = "NSE",
    period: str = "1mo",
    interval: str = "1d",
) -> dict:
    """
    Get OHLCV (Open, High, Low, Close, Volume) historical price data.

    Use when the user asks for a price chart, trend analysis, historical performance,
    or any question needing past price data. Also call before running a forecast.

    period   : How far back to fetch. Options: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y.
    interval : Candle size. Options: 1m (last 7d only), 1h, 1d, 1wk.
    """
    from tools.stock_data import get_stock_history
    return get_stock_history(symbol, exchange, period, interval)


@tool
def get_financials_tool(
    symbol: str,
    exchange: str = "NSE",
    statement: str = "income",
    quarterly: bool = False,
) -> dict:
    """
    Get a company's financial statements.

    statement : 'income' (P&L), 'balance_sheet', or 'cashflow'.
    quarterly : True = last 4 quarters | False = last 4 annual periods (default).

    Call for deep fundamental analysis, margin trends, debt levels, or when the
    user asks about revenue, profit, earnings, or balance sheet metrics.
    """
    from tools.stock_data import get_financials
    return get_financials(symbol, exchange, statement, quarterly)


@tool
def get_corporate_actions_tool(symbol: str, exchange: str = "NSE") -> dict:
    """
    Get dividend payment history and stock split history for a company.

    Call when the user asks about dividends, dividend yield track record,
    shareholder returns, or whether the company has done splits/bonuses.
    """
    from tools.stock_data import get_corporate_actions
    return get_corporate_actions(symbol, exchange)


@tool
def get_analyst_data_tool(symbol: str, exchange: str = "NSE") -> dict:
    """
    Get analyst consensus: mean, high, and low 12-month price targets plus
    buy/hold/sell vote counts.

    Call when the user asks what analysts think, for upside potential calculations,
    or as part of a full stock analysis report.
    """
    from tools.stock_data import get_analyst_data
    return get_analyst_data(symbol, exchange)


@tool
def get_holders_tool(symbol: str, exchange: str = "NSE") -> dict:
    """
    Get the top institutional shareholders and top mutual fund holders.

    Call when the user asks about ownership structure, FII/DII activity,
    promoter holding, or institutional interest in a stock.
    """
    from tools.stock_data import get_holders
    return get_holders(symbol, exchange)


@tool
def get_esg_data_tool(symbol: str, exchange: str = "NSE") -> dict:
    """
    Get ESG (Environmental, Social, Governance) risk scores from Sustainalytics.

    Call when the user asks about sustainability, ESG ratings, or ethical investing.
    Note: only available for large-cap and mid-cap stocks.
    """
    from tools.stock_data import get_esg_data
    return get_esg_data(symbol, exchange)


@tool
def get_upcoming_events_tool(symbol: str, exchange: str = "NSE") -> dict:
    """
    Get upcoming earnings announcement dates and ex-dividend dates.

    Call when the user asks when the next earnings report is, upcoming dividends,
    or wants to know about near-term catalysts for a stock.
    """
    from tools.stock_data import get_upcoming_events
    return get_upcoming_events(symbol, exchange)


@tool
def search_web_tool(query: str, max_results: int = 5) -> dict:
    """
    Search the live internet using Tavily for any general information.

    Use for: macro-economic data, regulatory changes, government policy, industry
    trends, company announcements, or any factual question needing current data.
    Do NOT use for stock prices — use get_stock_info_tool for that.
    Prefer search_news_tool when the user explicitly asks about news articles.
    """
    from tools.web_search import search_web
    return {"results": search_web(query, max_results)}


@tool
def search_news_tool(query: str, days_back: int = 7) -> dict:
    """
    Search recent news articles. Returns title, source, date, and description.

    Use when the user asks about latest news about a company or sector, recent
    market events, sentiment around a stock, or breaking developments.

    days_back : How many days back to search (default 7, max ~30).
    """
    from tools.news_search import search_news
    return {"results": search_news(query, days_back)}


@tool
def search_ticker_tool(query: str) -> dict:
    """
    Resolve a company name to its NSE/BSE ticker symbol using the India listings database.

    ALWAYS call this FIRST when the user gives a company name instead of a ticker.
    Do not guess tickers — always look them up.

    Examples: 'HDFC Bank' -> HDFCBANK | 'Tata Motors' -> TATAMOTORS | 'Infosys' -> INFY
    For multi-company workflows, call once per company name before fetching data.
    """
    from tools.ticker_lookup import search_ticker
    return {"results": search_ticker(query)}


@tool
def parse_document_tool(session_id: str) -> dict:
    """
    Parse all uploaded documents in this session and return their FULL raw content.

    Use for BROAD questions about an uploaded file:
      - 'Summarise this document'
      - 'What is this file about?'
      - 'Give me an overview of the uploaded report'

    This tool also indexes the documents into the vector store so that
    search_documents_tool can be called afterwards for specific questions.

    session_id : Provided in the system note appended to the user's message.
    """
    from utils.session_store import get_files
    from utils.doc_parser import parse_uploaded_file
    from utils.rag_engine import index_document

    files = get_files(session_id)
    if not files:
        return {"error": "No documents uploaded in this session."}

    results = []
    for f in files:
        parsed = parse_uploaded_file(f["filepath"])
        parsed["filename"] = f["filename"]
        results.append(parsed)
        if parsed.get("type") != "error":
            index_document(f["file_id"], parsed)

    return {"documents": results}


@tool
def search_documents_tool(session_id: str, query: str, top_k: int = 5) -> dict:
    """
    Semantically search across uploaded documents for a specific answer.

    Use for SPECIFIC questions about an uploaded file:
      - 'What was the revenue in FY24?'
      - 'What does the document say about risk factors?'
      - 'Find the section about capital allocation'

    Prefer this over parse_document_tool for targeted questions — it returns
    only the most relevant passages rather than the entire document.
    Safe to call even if parse_document_tool was not called first.

    session_id : Provided in the system note appended to the user's message.
    query      : Natural-language question to search for.
    top_k      : Number of most relevant passages to return (default 5).
    """
    from utils.session_store import get_files
    from utils.doc_parser import parse_uploaded_file
    from utils.rag_engine import index_document, query_documents

    files = get_files(session_id)
    if not files:
        return {"error": "No documents uploaded in this session."}

    for f in files:
        parsed = parse_uploaded_file(f["filepath"])
        if parsed.get("type") != "error":
            index_document(f["file_id"], parsed)

    chunks = query_documents(query=query, n_results=top_k)
    if not chunks:
        return {
            "status": "no_results",
            "message": "No relevant passages found. Try rephrasing the query.",
            "results": [],
        }
    return {"status": "success", "query": query, "results": chunks}


@tool
def predict_stock_tool(
    symbol: str,
    exchange: str = "NSE",
    horizon_days: int = 10,
) -> dict:
    """
    Forecast the next N daily closing prices using Amazon Chronos (zero-shot time-series model).

    Call ONLY when the user explicitly asks for a price forecast, prediction, or outlook.
    Do NOT call for current prices — use get_stock_info_tool for that.

    Recommended call sequence:
      1. search_ticker_tool  (if company name given)
      2. get_stock_history_tool (period='3mo') for recent trend context
      3. predict_stock_tool  (this tool) for the forward projection
      4. get_analyst_data_tool for comparison with analyst targets

    horizon_days : Number of trading days to forecast. Recommended: 5 to 20. Default: 10.
    """
    from tools.ts_model import predict_stock_prices
    return predict_stock_prices(symbol, exchange, horizon_days)


# ─────────────────────────────────────────────────────────────────────────────
# ALL TOOLS LIST
# ─────────────────────────────────────────────────────────────────────────────

ALL_TOOLS = [
    get_stock_info_tool,
    get_stock_history_tool,
    get_financials_tool,
    get_corporate_actions_tool,
    get_analyst_data_tool,
    get_holders_tool,
    get_esg_data_tool,
    get_upcoming_events_tool,
    search_web_tool,
    search_news_tool,
    search_ticker_tool,
    parse_document_tool,
    search_documents_tool,
    predict_stock_tool,
]


# ─────────────────────────────────────────────────────────────────────────────
# AGENT SINGLETON
# Built once on first run_agent() call. Reused for every subsequent call.
# Heavy tool dependencies (yfinance, torch, chromadb, etc.) are NOT loaded here
# — they load lazily inside each tool's inline import on first invocation.
# ─────────────────────────────────────────────────────────────────────────────

_agent = None
GEMINI_3 = "gemini-3.1-flash-lite-preview"

def _build_agent():
    global _agent
    if _agent is not None:
        return

    # llm = ChatGroq(
    #     model="llama-3.3-70b-versatile",
    #     api_key=settings.GROQ_API_KEY,
    #     temperature=0.1,
    # )
    llm = ChatGoogleGenerativeAI(
        model=GEMINI_3,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0.1,
    )
    _agent = create_react_agent(model=llm, tools=ALL_TOOLS)


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

async def run_agent(session_id: str, message: str) -> dict:
    """
    Run one conversational turn of the agent.

    Builds the agent on the first call (LLM + tool binding only — no heavy
    libraries loaded). Subsequent calls reuse the compiled agent; only the
    Groq API call and any tool network/compute requests happen per turn.

    Message list construction:
      [0]   SystemMessage  — SYSTEM_PROMPT (exactly once)
      [1..] Previous turns from session_store
            - 'user'      -> HumanMessage
            - 'assistant' -> AIMessage
            - 'system'    -> HumanMessage tagged [Context]
      [-1]  HumanMessage  — current user message (includes session_id note)

    The caller appends user + assistant to session_store AFTER this returns.

    Returns:
        {"text": str, "data": dict | None}
    """
    _build_agent()

    messages: list = [SystemMessage(content=SYSTEM_PROMPT)]

    for msg in get_history(session_id):
        role, content = msg["role"], msg["content"]
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
        elif role == "system":
            # Groq/Llama does not support multiple SystemMessages.
            # Fold injected context into a labelled HumanMessage.
            messages.append(HumanMessage(content=f"[Context]\n{content}"))

    messages.append(HumanMessage(content=message))

    # result = await _agent.ainvoke({"messages": messages})
    result = await _agent.ainvoke({"messages": messages})
    final_text = ""
    if result.get("messages"):
        last = result["messages"][-1]
        content = getattr(last, "content", "")
        if isinstance(content, list):
            final_text = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
        else:
            final_text = str(content)

    data = _extract_data_block(final_text)
    clean_text = _strip_data_block(final_text)
    return {"text": clean_text, "data": data}


# ─────────────────────────────────────────────────────────────────────────────
# DATA BLOCK HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _extract_data_block(text: str) -> dict | None:
    match = re.search(r"```data\s*\n(.*?)```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            return None
    return None


def _strip_data_block(text: str) -> str:
    return re.sub(r"```data\s*\n.*?```", "", text, flags=re.DOTALL).strip()
