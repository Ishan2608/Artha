"""
agent.py — Artha Agent (LangChain)

Uses langchain.agents.create_react_agent — the correct stable import.
NOTE: create_react_agent was briefly moved to langgraph.prebuilt, then
      moved back to langchain.agents. langchain.agents.create_agent does
      NOT exist despite what some deprecation messages claim.

Invocation pattern:
    agent.invoke({"messages": [HumanMessage(...)]})
    -> {"messages": [...]}  (last message is the reply)

Public entry point: run_agent(session_id, message) -> {"text": str, "data": dict | None}
"""

import json
import os
import re

from dotenv import load_dotenv
load_dotenv()

from config import settings
os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY

from langgraph.prebuilt import create_react_agent
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tools.stock_data import (
    get_stock_info,
    get_stock_history,
    get_financials,
    get_corporate_actions,
    get_analyst_data,
    get_holders,
    get_esg_data,
    get_upcoming_events,
)
from tools.web_search import search_web
from tools.news_search import search_news
from tools.ticker_lookup import search_ticker
from tools.ts_model import predict_stock_prices
from utils.doc_parser import parse_uploaded_file
from utils.rag_engine import query_documents
from utils.session_store import get_files, get_history


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Artha, an AI financial analyst assistant for Indian retail investors.
"Artha" means wealth and purpose in Sanskrit — that is your domain.

Your tools give you access to:
  - Real-time stock prices and fundamentals (PE, margins, debt ratios, 52-week range)
  - Historical OHLCV price data (for charts)
  - Financial statements (income, balance sheet, cash flow — annual and quarterly)
  - Corporate actions (dividends, splits)
  - Analyst consensus (price targets, buy/hold/sell counts)
  - Institutional and mutual fund holders
  - ESG risk scores
  - Upcoming earnings and dividend dates
  - Live web search and recent news
  - User-uploaded documents (PDF, DOCX, Excel, CSV, TXT, PPT)
  - Semantic search across uploaded documents
  - Price forecasts using a time series model
  - Indian stock ticker lookup by company name

HOW TO RESPOND TO STOCK ANALYSIS REQUESTS:
1. If the user gave a company name not a ticker, call search_ticker_tool first.
2. Call get_stock_info_tool for current price and valuation.
3. Call get_financials_tool for the annual income statement.
4. Call get_analyst_data_tool for analyst consensus.
5. Call search_news_tool for recent news.
6. Synthesize into sections:
   ## Summary | ## Fundamental Picture | ## Analyst View | ## Recent News | ## Technical Snapshot | ## Key Risks | ## Disclaimer
   Always end Disclaimer with: "This analysis is for educational purposes only and is not financial advice."

HOW TO HANDLE DOCUMENT QUESTIONS:
- Broad questions ("summarise this file") -> call parse_document_tool(session_id)
- Specific questions ("what was revenue in FY24?") -> call search_documents_tool(session_id, query)
  The session_id is always in the system note appended to the user message.

DATA BLOCK RULES:
When your response includes chart data, embed it at the very end:
  ```data
  {{"chart_type": "candlestick", "ticker": "TCS.NS", "dates": [...], ...}}
  ```

TOOL CALLING RULES:
- Never fabricate stock prices or financial data. Always call the tool.
- If a tool returns an error key, acknowledge it gracefully.
- Call all needed tools before composing your reply."""


# ─────────────────────────────────────────────────────────────────────────────
# TOOLS
# @tool wraps a plain Python function into a LangChain tool object.
# The underlying functions (get_stock_info, search_web, etc.) remain
# plain callables — test_tools.py imports them directly without touching these.
# ─────────────────────────────────────────────────────────────────────────────

@tool
def get_stock_info_tool(symbol: str, exchange: str = "NSE") -> dict:
    """Get real-time price, 52-week range, PE ratio, margins, debt ratios, and analyst targets.
    Call this when the user asks about a stock's current state, price, or basic fundamentals.
    symbol: NSE/BSE ticker WITHOUT suffix. Examples: TCS, WIPRO, INFY, HDFCBANK, SBIN.
    exchange: NSE (default) or BSE."""
    return get_stock_info(symbol, exchange)


@tool
def get_stock_history_tool(symbol: str, exchange: str = "NSE", period: str = "1mo", interval: str = "1d") -> dict:
    """Get OHLCV historical price data for candlestick or line charts.
    Call when the user asks for price charts, trend analysis, or historical performance.
    period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y.
    interval: 1m (last 7d only), 1h, 1d, 1wk."""
    return get_stock_history(symbol, exchange, period, interval)


@tool
def get_financials_tool(symbol: str, exchange: str = "NSE", statement: str = "income", quarterly: bool = False) -> dict:
    """Get financial statements: income statement, balance sheet, or cash flow.
    statement: 'income' for P&L, 'balance_sheet' for assets/liabilities, 'cashflow' for cash flows.
    quarterly: True for last 4 quarters, False for last 4 annual periods."""
    return get_financials(symbol, exchange, statement, quarterly)


@tool
def get_corporate_actions_tool(symbol: str, exchange: str = "NSE") -> dict:
    """Get dividend history and stock split history.
    Call when the user asks about dividends, shareholder returns, or splits."""
    return get_corporate_actions(symbol, exchange)


@tool
def get_analyst_data_tool(symbol: str, exchange: str = "NSE") -> dict:
    """Get analyst consensus: price targets (mean/high/low) and buy/hold/sell counts.
    Call when the user asks what analysts think about a stock."""
    return get_analyst_data(symbol, exchange)


@tool
def get_holders_tool(symbol: str, exchange: str = "NSE") -> dict:
    """Get top institutional and mutual fund shareholders.
    Call when the user asks about ownership structure or institutional interest."""
    return get_holders(symbol, exchange)


@tool
def get_esg_data_tool(symbol: str, exchange: str = "NSE") -> dict:
    """Get ESG risk scores from Sustainalytics.
    Call when the user asks about sustainability or ethical investing.
    Only available for large-cap stocks."""
    return get_esg_data(symbol, exchange)


@tool
def get_upcoming_events_tool(symbol: str, exchange: str = "NSE") -> dict:
    """Get upcoming earnings dates and ex-dividend dates.
    Call when the user asks when the next earnings report or dividend is."""
    return get_upcoming_events(symbol, exchange)


@tool
def search_web_tool(query: str, max_results: int = 5) -> dict:
    """Search the internet for current information using Tavily.
    Use for macro events, regulatory changes, or anything needing live data.
    Do NOT use for stock prices — use get_stock_info_tool instead."""
    return {"results": search_web(query, max_results)}


@tool
def search_news_tool(query: str, days_back: int = 7) -> dict:
    """Search recent news articles with source, date, and description metadata.
    Prefer over search_web_tool when the user asks specifically about news."""
    return {"results": search_news(query, days_back)}


@tool
def search_ticker_tool(query: str) -> dict:
    """Find NSE/BSE ticker symbol for an Indian company by name or partial name.
    Call this FIRST when the user gives a company name instead of a ticker.
    Example: 'HDFC Bank' -> returns 'HDFCBANK'."""
    return {"results": search_ticker(query)}


@tool
def predict_stock_tool(symbol: str, exchange: str = "NSE", horizon_days: int = 10) -> dict:
    """Forecast next N closing prices using Amazon Chronos (zero-shot model).
    Call ONLY when the user explicitly asks for a forecast or prediction.
    horizon_days: Trading days to forecast. Recommended: 5 to 20."""
    return predict_stock_prices(symbol, exchange, horizon_days)


@tool
def parse_document_tool(session_id: str) -> dict:
    """Parse all uploaded documents in the session and return their full content.
    Call for broad questions like 'summarise this file' or 'what is this document about'.
    session_id: provided in the system note at the end of the user message."""
    files = get_files(session_id)
    if not files:
        return {"error": "No documents uploaded in this session."}
    results = []
    for f in files:
        parsed = parse_uploaded_file(f["filepath"])
        parsed["filename"] = f["filename"]
        results.append(parsed)
    return {"documents": results}


@tool
def search_documents_tool(session_id: str, query: str, top_k: int = 5) -> dict:
    """Semantically search across uploaded documents for a specific answer.
    Prefer over parse_document_tool for specific questions like 'what was revenue in FY24?'.
    session_id: provided in the system note at the end of the user message.
    query: natural-language question to search for."""
    files = get_files(session_id)
    if not files:
        return {"error": "No documents uploaded in this session."}
    filepaths = [f["filepath"] for f in files]
    return query_documents(filepaths, query, top_k)


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
    predict_stock_tool,
    parse_document_tool,
    search_documents_tool,
]


# ─────────────────────────────────────────────────────────────────────────────
# LAZY AGENT — built only on first run_agent() call
# ─────────────────────────────────────────────────────────────────────────────

_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        # llm = ChatGoogleGenerativeAI(
        #     model="gemini-2.0-flash",
        #     google_api_key=settings.GEMINI_API_KEY,
        #     temperature=0.1,
        # )
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=settings.GROQ_API_KEY,
            temperature=0.1,
        )
        _agent = create_react_agent(
            model=llm,
            tools=ALL_TOOLS,
            prompt=SYSTEM_PROMPT,
        )
    return _agent


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

async def run_agent(session_id: str, message: str) -> dict:
    """
    Run the agent for one conversation turn.
    Pulls chat history from session_store for multi-turn memory.
    Returns: {"text": str, "data": dict | None}
    """
    agent = _get_agent()

    # Build message list from stored history + current message
    history = get_history(session_id)
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=message))

    result = await agent.ainvoke({"messages": messages})

    # Result is {"messages": [...]} — last message is the agent's reply
    final_text = ""
    if result.get("messages"):
        last = result["messages"][-1]
        final_text = last.content if hasattr(last, "content") else str(last)

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
