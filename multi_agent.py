"""
multi_agent.py — Artha Multi-Agent System

Architecture:
  guide_agent  (Groq / llama-3.3-70b-versatile)
      ├── call_stock_analysis_agent  (Gemini 3.1 Flash Lite) — price, fundamentals, financials
      └── call_stock_aggregator_agent (Gemini 3.1 Flash Lite) — news, web, docs, forecasting

Design:
  - Guide agent orchestrates. Specialists do the actual tool calls.
  - Delegation tools (call_*) are defined INSIDE _build_agents() so they close
    over the already-constructed specialist agents — the only correct approach
    since they reference _analysis_agent and _aggregator_agent by name.
  - All three agents are singletons: built once, reused forever.
  - Public surface is identical to agent.py: run_agent(session_id, message) -> dict
    so main.py, test_run.py, and test_agent.py need zero changes.

Config required in .env:
  GEMINI_API_KEY_ANALYSIS   — key for the stock analysis specialist
  GEMINI_API_KEY_AGGREGATOR — key for the research/forecast specialist
  GROQ_API_KEY              — key for the guide orchestrator

  Using separate API keys for each Gemini specialist spreads the per-key
  rate-limit load, which is the primary reason for this multi-agent design.
"""

import json
import re
import os
from typing import Optional, Dict, Any

from config import settings
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from utils.session_store import get_history


# ─────────────────────────────────────────────────────────────────────────────
# MODEL STRINGS
# ─────────────────────────────────────────────────────────────────────────────

GEMINI_MODEL = "gemini-3.1-flash-lite-preview-06-17"  # both specialists
GROQ_MODEL = "llama-3.3-70b-versatile"              # orchestrator

# ─────────────────────────────────────────────────────────────────────────────
# SPECIALIST SYSTEM PROMPTS
# ─────────────────────────────────────────────────────────────────────────────

STOCK_ANALYSIS_SYSTEM_PROMPT = """You are Artha's Stock Analysis specialist for Indian retail investors.
Retrieve and analyse structured financial data using your tools.

## YOUR TOOLS
- search_ticker_tool       : Resolve company name → NSE/BSE ticker. ALWAYS call first for names.
- get_stock_info_tool      : Price, valuation, PE, margins, market cap.
- get_stock_history_tool   : OHLCV historical data for charts.
- get_financials_tool      : P&L, Balance Sheet, Cash Flow.
- get_corporate_actions_tool : Dividends and stock splits.
- get_analyst_data_tool    : Price targets and buy/hold/sell ratings.
- get_holders_tool         : FII/DII/Promoter ownership.
- get_esg_data_tool        : ESG sustainability scores.
- get_upcoming_events_tool : Earnings dates and ex-dividend dates.

## RULES
1. Use Context to resolve pronouns like "it" or "the company".
2. Always resolve company names to tickers via search_ticker_tool first.
3. For chart data, emit exactly one candlestick data block at the end:
```data
{"chart_type":"candlestick","symbol":"SYMBOL","dates":[...],"open":[...],"high":[...],"low":[...],"close":[...]}
```
4. End every response with: "This is not financial advice."
"""

STOCK_AGGREGATOR_SYSTEM_PROMPT = """You are Artha's Research & Forecasting specialist for Indian retail investors.
Search unstructured data and perform time-series forecasting.

## YOUR TOOLS
- search_web_tool       : General internet research — macro, policy, sector trends.
- search_news_tool      : Latest news and sentiment for a company or sector.
- parse_document_tool   : Full text extraction from uploaded session files.
- search_documents_tool : RAG-based semantic search across uploaded session files.
- predict_stock_tool    : Amazon Chronos zero-shot price forecasting.

## RULES
1. Pass session_id exactly as given in the Context to all document tools.
2. For forecasts, emit exactly one forecast data block at the end:
```data
{"chart_type":"forecast","symbol":"SYMBOL","horizon_days":N,"historical_dates":[...],"historical_closes":[...],"forecast_median":[...],"forecast_low":[...],"forecast_high":[...]}
```
3. Always clarify that forecasts are probabilistic and based on price patterns only.
4. End every response with: "This is not financial advice."
"""

GUIDE_SYSTEM_PROMPT = """You are Artha, an AI financial analyst for Indian retail investors.
You orchestrate two specialist agents to answer user queries.

## YOUR TOOLS (delegation only — you have no direct data tools)
- call_stock_analysis_agent  : For stock prices, fundamentals, financials, charts.
- call_stock_aggregator_agent: For news, web research, uploaded documents, forecasts.

## WORKFLOW
1. RESOLVE  : Identify company names and resolve pronouns using conversation history.
2. DELEGATE : Call the right specialist(s). For complex tasks, call both sequentially.
3. PRESERVE : Copy any ```data``` blocks from specialists into your final reply verbatim.
4. SYNTHESISE: Combine specialist outputs into one cohesive professional response.
5. DISCLAIM : End every financial response with: "This is not financial advice."

## DELEGATION RULES
- Always pass context summarising who/what the user is asking about.
- Always pass the session_id from the user message note to aggregator calls.
- For "analyse and forecast" tasks: call analysis agent first, then aggregator.
- Do NOT fabricate data. If a specialist returns an error, report it honestly.
"""


# ─────────────────────────────────────────────────────────────────────────────
# STOCK ANALYSIS TOOLS  (bound to the analysis specialist)
# ─────────────────────────────────────────────────────────────────────────────

@tool
def get_stock_info_tool(symbol: str, exchange: str = "NSE") -> dict:
    """Get current snapshot: price, PE, PB, margins, market cap, analyst consensus."""
    from tools.stock_data import get_stock_info
    return get_stock_info(symbol, exchange)

@tool
def get_stock_history_tool(
    symbol: str, exchange: str = "NSE", period: str = "1mo", interval: str = "1d"
) -> dict:
    """Get OHLCV historical price data. Use for chart or trend analysis requests."""
    from tools.stock_data import get_stock_history
    return get_stock_history(symbol, exchange, period, interval)

@tool
def get_financials_tool(
    symbol: str, exchange: str = "NSE", statement: str = "income", quarterly: bool = False
) -> dict:
    """Get financial statements: 'income', 'balance_sheet', or 'cashflow'."""
    from tools.stock_data import get_financials
    return get_financials(symbol, exchange, statement, quarterly)

@tool
def get_corporate_actions_tool(symbol: str, exchange: str = "NSE") -> dict:
    """Get dividend history and stock split history."""
    from tools.stock_data import get_corporate_actions
    return get_corporate_actions(symbol, exchange)

@tool
def get_analyst_data_tool(symbol: str, exchange: str = "NSE") -> dict:
    """Get analyst price targets and buy/hold/sell vote counts."""
    from tools.stock_data import get_analyst_data
    return get_analyst_data(symbol, exchange)

@tool
def get_holders_tool(symbol: str, exchange: str = "NSE") -> dict:
    """Get institutional and mutual fund shareholding patterns."""
    from tools.stock_data import get_holders
    return get_holders(symbol, exchange)

@tool
def get_esg_data_tool(symbol: str, exchange: str = "NSE") -> dict:
    """Get ESG risk scores from Sustainalytics (large/mid-cap only)."""
    from tools.stock_data import get_esg_data
    return get_esg_data(symbol, exchange)

@tool
def get_upcoming_events_tool(symbol: str, exchange: str = "NSE") -> dict:
    """Get upcoming earnings dates and ex-dividend dates."""
    from tools.stock_data import get_upcoming_events
    return get_upcoming_events(symbol, exchange)

@tool
def search_ticker_tool(query: str) -> dict:
    """Resolve a company name to NSE/BSE ticker. Call FIRST for any company name."""
    from tools.ticker_lookup import search_ticker
    return {"results": search_ticker(query)}

STOCK_ANALYSIS_TOOLS = [
    search_ticker_tool, get_stock_info_tool, get_stock_history_tool,
    get_financials_tool, get_corporate_actions_tool, get_analyst_data_tool,
    get_holders_tool, get_esg_data_tool, get_upcoming_events_tool,
]

# ─────────────────────────────────────────────────────────────────────────────
# RESEARCH & AGGREGATOR TOOLS  (bound to the aggregator specialist)
# ─────────────────────────────────────────────────────────────────────────────

@tool
def search_web_tool(query: str, max_results: int = 5) -> dict:
    """Search live internet for macro data, industry trends, or announcements."""
    from tools.web_search import search_web
    return {"results": search_web(query, max_results)}

@tool
def search_news_tool(query: str, days_back: int = 7) -> dict:
    """Search recent news articles for market sentiment or breaking developments."""
    from tools.news_search import search_news
    return {"results": search_news(query, days_back)}

@tool
def parse_document_tool(session_id: str) -> dict:
    """Parse all uploaded documents in the session. Use for broad document questions."""
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
    """Semantically search uploaded session documents for a specific answer."""
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
        return {"status": "no_results", "results": []}
    return {"status": "success", "results": chunks}

@tool
def predict_stock_tool(symbol: str, exchange: str = "NSE", horizon_days: int = 10) -> dict:
    """Forecast next N closing prices using Amazon Chronos. Only call when forecasting is requested."""
    from tools.ts_model import predict_stock_prices
    return predict_stock_prices(symbol, exchange, horizon_days)

STOCK_AGGREGATOR_TOOLS = [
    search_web_tool, search_news_tool,
    parse_document_tool, search_documents_tool, predict_stock_tool,
]


# ─────────────────────────────────────────────────────────────────────────────
# AGENT SINGLETONS
# ─────────────────────────────────────────────────────────────────────────────

_analysis_agent   = None
_aggregator_agent = None
_guide_agent      = None


def _extract_content(result: dict) -> str:
    """Pull the final text out of a LangGraph agent result, handling list content."""
    if not result.get("messages"):
        return ""
    last    = result["messages"][-1]
    content = getattr(last, "content", "")
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content)


def _build_agents() -> None:
    """
    Build all three agents once. Safe to call multiple times — no-op if already built.

    The delegation tools (call_stock_analysis_agent, call_stock_aggregator_agent)
    MUST be defined inside this function so they close over _analysis_agent and
    _aggregator_agent after those objects exist. Defining them at module level
    would capture None and break at call time.
    """
    global _analysis_agent, _aggregator_agent, _guide_agent
    if _guide_agent is not None:
        return

    # ── Specialist LLMs (separate API keys = separate rate-limit pools) ────────
    gemini_analysis_llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=settings.GEMINI_API_KEY_ANALYSIS,
        temperature=0.1,
    )
    gemini_aggregator_llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=settings.GEMINI_API_KEY_AGGREGATOR,
        temperature=0.1,
    )

    # ── Guide LLM ─────────────────────────────────────────────────────────────
    groq_llm = ChatGroq(
        model=GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.1,
    )

    # ── Build specialist agents ────────────────────────────────────────────────
    _analysis_agent   = create_react_agent(model=gemini_analysis_llm,   tools=STOCK_ANALYSIS_TOOLS)
    _aggregator_agent = create_react_agent(model=gemini_aggregator_llm, tools=STOCK_AGGREGATOR_TOOLS)

    # ── Delegation tools — defined here to close over the agents above ─────────

    @tool
    async def call_stock_analysis_agent(task: str, context: str, session_id: str) -> str:
        """
        Delegate to the Stock Analysis specialist.
        Use for: stock prices, fundamentals, financials, OHLCV charts, corporate actions,
        analyst targets, holders, ESG, upcoming events.
        task      : Specific instruction (e.g. 'Get income statement for TCS for last 4 years').
        context   : Background to resolve pronouns (e.g. 'User has been asking about TCS').
        session_id: Pass through exactly from the user message system note.
        """
        try:
            prompt   = f"Context: {context}\nTask: {task}\n[session_id: {session_id}]"
            messages = [
                SystemMessage(content=STOCK_ANALYSIS_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
            result = await _analysis_agent.ainvoke({"messages": messages})
            return _extract_content(result)
        except Exception as e:
            return f"[Analysis Agent Error: {type(e).__name__}: {e}]"

    @tool
    async def call_stock_aggregator_agent(task: str, context: str, session_id: str) -> str:
        """
        Delegate to the Research & Forecasting specialist.
        Use for: latest news, web research, uploaded document Q&A, price forecasting.
        task      : Specific instruction (e.g. 'Forecast PETRONET for next 10 days').
        context   : Background to resolve pronouns (e.g. 'User is asking about Petronet LNG').
        session_id: Pass through exactly from the user message system note.
        """
        try:
            prompt   = f"Context: {context}\nTask: {task}\n[session_id: {session_id}]"
            messages = [
                SystemMessage(content=STOCK_AGGREGATOR_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
            result = await _aggregator_agent.ainvoke({"messages": messages})
            return _extract_content(result)
        except Exception as e:
            return f"[Aggregator Agent Error: {type(e).__name__}: {e}]"

    # ── Build guide agent with delegation tools ────────────────────────────────
    _guide_agent = create_react_agent(
        model=groq_llm,
        tools=[call_stock_analysis_agent, call_stock_aggregator_agent],
    )


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# Identical signature to agent.py — drop-in replacement, no changes needed
# in main.py, test_run.py, or test_agent.py.
# ─────────────────────────────────────────────────────────────────────────────

async def run_agent(session_id: str, message: str) -> dict:
    """
    Run one conversational turn through the guide agent.

    Message list construction:
      [0]   SystemMessage — GUIDE_SYSTEM_PROMPT
      [1..] Previous turns from session_store (user/assistant/system)
      [-1]  HumanMessage — current enriched message

    Returns: {"text": str, "data": dict | None}
    """
    _build_agents()

    messages: list = [SystemMessage(content=GUIDE_SYSTEM_PROMPT)]

    for msg in get_history(session_id):
        role, content = msg["role"], msg["content"]
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
        elif role == "system":
            # Groq does not support multiple SystemMessages — fold into HumanMessage
            messages.append(HumanMessage(content=f"[Context]\n{content}"))

    messages.append(HumanMessage(content=message))

    result     = await _guide_agent.ainvoke({"messages": messages})
    final_text = _extract_content(result)

    data       = _extract_data_block(final_text)
    clean_text = _strip_data_block(final_text)
    return {"text": clean_text, "data": data}


# ─────────────────────────────────────────────────────────────────────────────
# DATA BLOCK HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _extract_data_block(text: str) -> Optional[Dict[str, Any]]:
    match = re.search(r"```data\s*\n(.*?)```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            return None
    return None

def _strip_data_block(text: str) -> str:
    return re.sub(r"```data\s*\n.*?```", "", text, flags=re.DOTALL).strip()

