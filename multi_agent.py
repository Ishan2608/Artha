"""
multi_agent.py — Artha Multi-Agent System (Production Grade)

Architecture:
  guide_agent (Groq / llama-3.3-70b-versatile)
      ├── call_stock_analysis_agent (Gemini 2.5 Flash Lite) -> Fundamental/Market Data Specialist
      └── call_stock_aggregator_agent (Gemini 2.5 Flash Lite) -> Research/RAG/Forecasting Specialist

Key Features:
  1. Multi-Agent Orchestration: Guide agent routes complex queries to domain specialists.
  2. Context Propagation: Guide provides resolved entities, session_id, and chat state to
     stateless specialists — enabling document tools to work across all sub-agents.
  3. Session / History Integration: Mirrors agent.py's run_agent() contract exactly.
     - Reads conversation history (user, assistant, system) from session_store before each turn.
     - System-role context injections are folded into labelled HumanMessages so Groq/Llama
       does not choke on multiple SystemMessage objects.
     - Both user and assistant messages are appended by main.py AFTER this returns — never here.
  4. Resilience: Sub-agent failures are caught and reported gracefully to the orchestrator.
  5. Data Integrity: Strict instructions for preserving markdown-wrapped JSON data blocks.
  6. Singleton Pattern: LLMs and agent executors are initialized once and reused.

Public entry point (drop-in replacement for agent.py):
  run_agent(session_id, message) -> {"text": str, "data": dict | None}

Caller contract (main.py):
  Do NOT append the current user message to session_store before calling run_agent().
  Append both user message AND assistant reply AFTER it returns — exactly as with agent.py.
"""

import json
import re
import asyncio
import concurrent.futures
from typing import Dict, Any, Optional

from config import settings

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool

from utils.session_store import get_history


# ─────────────────────────────────────────────────────────────────────────────
# SPECIALIST SYSTEM PROMPTS
# ─────────────────────────────────────────────────────────────────────────────

STOCK_ANALYSIS_SYSTEM_PROMPT = """You are Artha's Stock Analysis specialist for Indian retail investors.
Task: Retrieve and analyze structured financial data.

# YOUR TOOLS
- get_stock_info_tool: Price, valuation, fundamental margins.
- get_stock_history_tool: OHLCV data for charts.
- get_financials_tool: P&L, Balance Sheet, Cash Flow.
- get_corporate_actions_tool: Dividends, bonuses, splits.
- get_analyst_data_tool: Price targets, ratings.
- get_holders_tool: FII/DII/Promoter ownership.
- get_esg_data_tool: Sustainability scores.
- get_upcoming_events_tool: Earnings dates.
- search_ticker_tool: Resolve company name to ticker.

# RULES
1. Use the provided Context to identify the company if the Task refers to "it" or "the company".
2. Always resolve company names to NSE/BSE tickers using search_ticker_tool first.
3. For charts, output exactly one candlestick data block in the specified format.
4. End every response with: "This is not financial advice."

# CHART FORMAT
After any historical data response, append exactly one block:
```data
{"chart_type":"candlestick","symbol":"SYMBOL","dates":[...],"open":[...],"high":[...],"low":[...],"close":[...]}
```
"""

STOCK_AGGREGATOR_SYSTEM_PROMPT = """You are Artha's Research & Forecasting specialist for Indian retail investors.
Task: Search unstructured data (web/news/docs) and perform time-series forecasting.

# YOUR TOOLS
- search_web_tool: General internet research.
- search_news_tool: Latest news sentiment.
- parse_document_tool: Full text extraction from uploaded session files.
- search_documents_tool: RAG-based search across uploaded session files.
- predict_stock_tool: Transformer-based forecasting (trained on NIFTY 50 stocks + more).

# RULES
1. Pass the session_id EXACTLY as given in the task prompt to all document tools.
2. For forecasting, provide the forecast data block exactly as specified below.
3. Clearly explain that forecasts are based on learned price patterns and technical indicators.
4. Note: Forecasting works for NIFTY 50 and other major Indian stocks.
5. End every response with: "This is not financial advice."

# FORECAST FORMAT
After any forecast response, append exactly one block:
```data
{"chart_type":"forecast","symbol":"SYMBOL","horizon_days":N,"historical_dates":[...],"historical_closes":[...],"forecast_median":[...],"forecast_low":[...],"forecast_high":[...]}
```
"""

GUIDE_SYSTEM_PROMPT = """You are Artha's Guide Agent, the central orchestrator for an Indian financial AI system.

# SPECIALISTS
1. call_stock_analysis_agent: For hard data — prices, fundamentals, financials, corporate actions, shareholding.
2. call_stock_aggregator_agent: For research, news, uploaded documents, and price forecasts.

# CRITICAL: SESSION ID
Every user message contains a system note with session_id in the format: [System note: session_id='<id>'. ...]
You MUST extract this session_id and pass it unchanged to EVERY specialist call.
Without the correct session_id, document tools will fail to locate uploaded files.

# WORKFLOW
1. RESOLVE: Identify entities and resolve pronouns using conversation history.
2. STATE: Summarize relevant background for the specialist (e.g., "Analyzing TCS (TCS.NS)").
3. DELEGATE: Call specialists. For complex tasks (e.g., "analyze and forecast"), call both.
4. PRESERVE: Copy any ```data``` blocks from specialist responses into your final reply verbatim.
   Never paraphrase, reformat, or truncate a ```data``` block. It must appear exactly as received.
5. INTEGRATE: Synthesize all specialist findings into a single, cohesive professional response.
6. DISCLAIM: End every response with: "This is not financial advice."

# DELEGATION EXAMPLES
- "What is the PE of TCS?" → call_stock_analysis_agent(task="Get PE ratio for TCS", context="User asking about TCS", session_id=<extracted>)
- "Forecast Reliance for 10 days" → call_stock_aggregator_agent(task="Forecast Reliance Industries for 10 trading days", context="User asking about Reliance Industries", session_id=<extracted>)
- "Full analysis of INFY with forecast" → call BOTH specialists
- "What does the uploaded report say about risks?" → call_stock_aggregator_agent with the document query
"""


# ─────────────────────────────────────────────────────────────────────────────
# STOCK ANALYSIS TOOLS  (bound to the Analysis specialist)
# ─────────────────────────────────────────────────────────────────────────────

@tool
def get_stock_info_tool(symbol: str, exchange: str = "NSE") -> dict:
    """
    Get current snapshot for a listed Indian stock: price, PE, PB, margins,
    market cap, and analyst consensus targets.

    symbol   : NSE/BSE ticker without exchange suffix (e.g. TCS, WIPRO, HDFCBANK).
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
    Get OHLCV historical price data. Use when the user asks for charts or trend analysis.

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
    Get financial statements: 'income' (P&L), 'balance_sheet', or 'cashflow'.

    quarterly : True = last 4 quarters | False = last 4 annual periods (default).
    """
    from tools.stock_data import get_financials
    return get_financials(symbol, exchange, statement, quarterly)


@tool
def get_corporate_actions_tool(symbol: str, exchange: str = "NSE") -> dict:
    """
    Get dividend payment history and stock split history for a company.
    """
    from tools.stock_data import get_corporate_actions
    return get_corporate_actions(symbol, exchange)


@tool
def get_analyst_data_tool(symbol: str, exchange: str = "NSE") -> dict:
    """
    Get analyst consensus: mean, high, and low 12-month price targets plus
    buy/hold/sell vote counts.
    """
    from tools.stock_data import get_analyst_data
    return get_analyst_data(symbol, exchange)


@tool
def get_holders_tool(symbol: str, exchange: str = "NSE") -> dict:
    """
    Get institutional and mutual fund shareholding patterns.
    """
    from tools.stock_data import get_holders
    return get_holders(symbol, exchange)


@tool
def get_esg_data_tool(symbol: str, exchange: str = "NSE") -> dict:
    """
    Get ESG risk scores from Sustainalytics for large-cap and mid-cap stocks.
    """
    from tools.stock_data import get_esg_data
    return get_esg_data(symbol, exchange)


@tool
def get_upcoming_events_tool(symbol: str, exchange: str = "NSE") -> dict:
    """
    Get upcoming earnings announcement dates and ex-dividend dates.
    """
    from tools.stock_data import get_upcoming_events
    return get_upcoming_events(symbol, exchange)


@tool
def search_ticker_tool(query: str) -> dict:
    """
    Resolve a company name to its NSE/BSE ticker.
    Call this FIRST whenever the user provides a company name instead of a symbol.
    """
    from tools.ticker_lookup import search_ticker
    return {"results": search_ticker(query)}


STOCK_ANALYSIS_TOOLS = [
    get_stock_info_tool,
    get_stock_history_tool,
    get_financials_tool,
    get_corporate_actions_tool,
    get_analyst_data_tool,
    get_holders_tool,
    get_esg_data_tool,
    get_upcoming_events_tool,
    search_ticker_tool,
]


# ─────────────────────────────────────────────────────────────────────────────
# RESEARCH & AGGREGATOR TOOLS  (bound to the Aggregator specialist)
# ─────────────────────────────────────────────────────────────────────────────

@tool
def search_web_tool(query: str, max_results: int = 5) -> dict:
    """
    Search live internet for macro-data, industry trends, or company announcements.
    """
    from tools.web_search import search_web
    return {"results": search_web(query, max_results)}


@tool
def search_news_tool(query: str, days_back: int = 2) -> dict:
    """
    Search recent news articles for market sentiment or breaking developments.
    """
    from tools.news_search import search_news
    return {"results": search_news(query, days_back)}


@tool
def parse_document_tool(session_id: str) -> dict:
    """
    Parse all uploaded documents for the given session and return full raw content.
    Use for broad overview questions about uploaded files.

    session_id : Must match the session_id from the system note in the user's message.
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
    Semantically search inside uploaded session documents for a specific answer.
    Use for targeted questions — returns only the most relevant passages.

    session_id : Must match the session_id from the system note in the user's message.
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
        return {"status": "no_results", "results": []}
    return {"status": "success", "results": chunks}


@tool
def predict_stock_tool(
    symbol: str,
    exchange: str = "NSE",
    horizon_days: int = 5,
) -> dict:
    """
    Forecast the next N closing prices using the Transformer model trained on NIFTY 50 stocks.
    Call ONLY when the user explicitly asks for a price forecast or prediction.

    symbol       : Stock ticker without suffix (e.g., RELIANCE, TCS, INFY).
    exchange     : 'NSE' (default) or 'BSE'.
    horizon_days : Number of trading days to forecast (default: 5).
    """
    from tools.ts_model import predict_stock_prices
    return predict_stock_prices(symbol, exchange, horizon_days)


STOCK_AGGREGATOR_TOOLS = [
    search_web_tool,
    search_news_tool,
    parse_document_tool,
    search_documents_tool,
    predict_stock_tool,
]


# ─────────────────────────────────────────────────────────────────────────────
# AGENT SINGLETONS
# Built once on the first run_agent() call and reused forever.
# Heavy tool dependencies (yfinance, torch, chromadb, etc.) load lazily inside
# each tool's inline import — NOT at agent startup.
# ─────────────────────────────────────────────────────────────────────────────

_analysis_agent = None
_aggregator_agent = None
_guide_agent = None


def _build_agents() -> None:
    """
    Initialize all three agents if they have not been built yet.

    The two Gemini specialists are created first as plain LangGraph ReAct agents.
    The delegation wrapper tools (call_stock_analysis_agent,
    call_stock_aggregator_agent) close over those agents and are then bound
    to the Groq Guide Agent.

    This function is idempotent — safe to call on every request.
    """
    global _analysis_agent, _aggregator_agent, _guide_agent
    if _guide_agent is not None:
        return

    # ── Specialist LLMs ──────────────────────────────────────────────────────
    gemini_analysis_llm = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite-preview",
        google_api_key=settings.GEMINI_API_KEY_ANALYSIS,
        temperature=0.1,
    )
    gemini_aggregator_llm = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite-preview",
        google_api_key=settings.GEMINI_API_KEY_AGGREGATOR,
        temperature=0.1,
    )

    # ── Orchestrator LLM ─────────────────────────────────────────────────────
    # qroq_llm = ChatGoogleGenerativeAI(
    #     model="gemini-3.1-flash-lite-preview",
    #     google_api_key=settings.GEMINI_API_KEY,
    #     temperature=0.1,
    # )
    orchestrator = ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite-preview",
        api_key=settings.GEMINI_API_KEY,
        temperature=0.1,
    )

    # ── Specialist Agent Executors ────────────────────────────────────────────
    _analysis_agent   = create_react_agent(model=gemini_analysis_llm,   tools=STOCK_ANALYSIS_TOOLS)
    _aggregator_agent = create_react_agent(model=gemini_aggregator_llm, tools=STOCK_AGGREGATOR_TOOLS)

    # ── Delegation helper ─────────────────────────────────────────────────────
    def _run_specialist(agent, system_prompt: str, task: str, context: str, session_id: str) -> str:
        """
        Run a specialist agent synchronously from within a LangGraph tool call.

        LangGraph tool functions are synchronous, but the specialist agents are
        async. The two branches below handle both cases:

          - If a running event loop exists (i.e., we are inside FastAPI's async
            context), we cannot call loop.run_until_complete() — that would
            deadlock. Instead we dispatch to a fresh thread that owns its own
            event loop.
          - If no loop is running yet (rare: testing, CLI), we create one in the
            current thread.
        """
        async def _invoke():
            prompt = (
                f"Context: {context}\n"
                f"Task: {task}\n"
                f"[session_id: {session_id}]"
            )
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt),
            ]
            result = await agent.ainvoke({"messages": messages})
            last = result["messages"][-1]
            content = getattr(last, "content", "")
            if isinstance(content, list):
                return "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            return str(content)

        try:
            asyncio.get_running_loop()
            # We ARE inside an async context. Run the coroutine in a dedicated
            # thread to avoid blocking / deadlocking the main event loop.
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, _invoke())
                return future.result(timeout=120)
        except RuntimeError:
            # No running loop — safe to create one here.
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_invoke())
            finally:
                loop.close()

    # ── Guide-facing tool wrappers ────────────────────────────────────────────

    @tool
    def call_stock_analysis_agent(task: str, context: str, session_id: str) -> str:
        """
        Delegate to the Stock Analysis specialist for prices, fundamentals, financials,
        corporate actions, shareholding data, or analyst targets.

        task       : Clear instruction (e.g., 'Get the P&L statement for TCS for the last 4 years').
        context    : Background to resolve pronouns (e.g., 'User is analyzing TCS. Ticker is TCS.').
        session_id : Extracted from the [System note: session_id='...'] in the user's message.
        """
        try:
            return _run_specialist(
                _analysis_agent,
                STOCK_ANALYSIS_SYSTEM_PROMPT,
                task,
                context,
                session_id,
            )
        except Exception as e:
            return f"[Analysis Agent Error]: {str(e)}"

    @tool
    def call_stock_aggregator_agent(task: str, context: str, session_id: str) -> str:
        """
        Delegate to the Research & Forecasting specialist for news, web research,
        uploaded document queries, or price forecasts.

        task       : Clear instruction (e.g., 'Forecast TCS price for the next 10 trading days').
        context    : Background to resolve pronouns (e.g., 'User is analyzing TCS. Ticker is TCS.').
        session_id : Extracted from the [System note: session_id='...'] in the user's message.
                     This is CRITICAL for document tools to locate the user's uploaded files.
        """
        try:
            return _run_specialist(
                _aggregator_agent,
                STOCK_AGGREGATOR_SYSTEM_PROMPT,
                task,
                context,
                session_id,
            )
        except Exception as e:
            return f"[Aggregator Agent Error]: {str(e)}"

    # ── Guide Agent ───────────────────────────────────────────────────────────
    _guide_agent = create_react_agent(
        model=orchestrator,
        tools=[call_stock_analysis_agent, call_stock_aggregator_agent],
    )


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# Drop-in replacement for agent.py's run_agent().
# ─────────────────────────────────────────────────────────────────────────────

async def run_agent(session_id: str, message: str) -> dict:
    """
    Execute one conversational turn through the Guide Agent.

    This function is the sole public interface of this module and is designed to
    be a transparent drop-in replacement for agent.py's run_agent().

    Message list construction (identical contract to agent.py):
      [0]   SystemMessage  — GUIDE_SYSTEM_PROMPT (exactly once)
      [1..] Previous turns reconstructed from session_store:
            - 'user'      -> HumanMessage   (includes enriched session_id note)
            - 'assistant' -> AIMessage
            - 'system'    -> HumanMessage labelled [Context]
               (Groq/Llama does not support multiple SystemMessages — context
                injections added via POST /context are folded into HumanMessages.)
      [-1]  HumanMessage  — current enriched message from main.py

    Session write-back:
      This function does NOT write to session_store. main.py appends both the
      enriched user message and the assistant reply AFTER this returns. This
      matches the exact contract of agent.py.

    Response extraction:
      The Guide agent may produce multiple AIMessage chunks. We collect all
      meaningful text parts in order. If the total is suspiciously short
      (< 50 chars) we fall back to the last substantive AIMessage, which
      handles the edge case where tool calls absorb most of the output budget.

    Returns:
        {
            "text": str           — assistant reply with the ```data``` block stripped,
            "data": dict | None   — parsed JSON from the ```data``` block, or None
        }
    """
    _build_agents()

    # ── Reconstruct full message history ──────────────────────────────────────
    messages: list = [SystemMessage(content=GUIDE_SYSTEM_PROMPT)]

    for msg in get_history(session_id):
        role, content = msg["role"], msg["content"]
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
        elif role == "system":
            # Groq/Llama does not support multiple SystemMessages.
            # Fold injected context into a labelled HumanMessage so the model
            # still receives it without breaking the API constraint.
            messages.append(HumanMessage(content=f"[Context]\n{content}"))

    # Current turn (enriched by main.py with session_id note + file hints).
    messages.append(HumanMessage(content=message))

    # ── Invoke Guide Agent ────────────────────────────────────────────────────
    result = await _guide_agent.ainvoke({"messages": messages})

    # ── Extract final text from the agent's message sequence ─────────────────
    # The Guide produces a mix of AIMessages (reasoning + final reply) and
    # ToolMessages (specialist responses). We collect all text content from
    # AIMessages and ToolMessages in order, then join them.
    final_text = ""
    if result.get("messages"):
        text_parts = []
        for msg in result["messages"]:
            msg_class = msg.__class__.__name__
            if msg_class in ("HumanMessage", "SystemMessage"):
                continue
            content = getattr(msg, "content", "")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                    else:
                        text_parts.append(str(part))
            elif content:
                text_parts.append(str(content))
        final_text = "".join(text_parts)

    # Fallback: if we collected very little (tool call dominated the turn),
    # pull just the last substantive AIMessage.
    if len(final_text) < 50:
        for msg in reversed(result.get("messages", [])):
            if msg.__class__.__name__ == "AIMessage":
                content = getattr(msg, "content", "")
                if isinstance(content, list):
                    parts = []
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            parts.append(part.get("text", ""))
                        elif not isinstance(part, dict):
                            parts.append(str(part))
                    candidate = "".join(parts)
                else:
                    candidate = str(content)
                if candidate:
                    final_text = candidate
                    break

    data       = _extract_data_block(final_text)
    clean_text = _strip_data_block(final_text)

    return {"text": clean_text, "data": data}


# ─────────────────────────────────────────────────────────────────────────────
# DATA BLOCK HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _extract_data_block(text: str) -> Optional[Dict[str, Any]]:
    """Parse the first ```data ... ``` block in *text* and return it as a dict."""
    match = re.search(r"```data\s*\n(.*?)```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            return None
    return None


def _strip_data_block(text: str) -> str:
    """Remove all ```data ... ``` blocks from *text* and return the cleaned string."""
    return re.sub(r"```data\s*\n.*?```", "", text, flags=re.DOTALL).strip()
