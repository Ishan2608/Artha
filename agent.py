"""
agent.py — Artha Agent (LangChain + Groq + MCP)

Tool definitions live exclusively in mcp_server.py.
This file connects to mcp_server.py via MultiServerMCPClient,
fetches all tools from it, and wires them into the LangGraph agent.

Separation of concerns:
  tools/          -> plain Python functions, no framework, testable directly
  mcp_server.py   -> FastMCP wrappers, single source of truth for all tool definitions
  agent.py        -> LLM + agent logic only, zero tool definitions

Public entry point: run_agent(session_id, message) -> {"text": str, "data": dict | None}
"""

import json
import os
import re
import sys

from dotenv import load_dotenv
load_dotenv()

from config import settings
os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY

from langgraph.prebuilt import create_react_agent
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

from utils.session_store import get_history


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Shree, an AI financial analyst for Indian retail investors.

TOOLS: stock info, history, financials, corporate actions, analyst data, holders, ESG, upcoming events, web search, news search, ticker lookup, document parsing, document search, price forecasting.

STOCK ANALYSIS: If given a company name call search_ticker_tool first. Then call get_stock_info_tool, get_financials_tool, get_analyst_data_tool, search_news_tool. Reply with sections: Summary, Fundamental Picture, Analyst View, Recent News, Key Risks, Disclaimer. End with: "This is not financial advice."

DOCUMENTS: session_id is in the system note. For broad questions call parse_document_tool(session_id). For specific questions call search_documents_tool(session_id, query).

CHARTS: If response includes chart data, append at the very end:
```data
{{"chart_type": "candlestick", "dates": [...], ...}}
```

RULES: Never fabricate data. Always use tools. Acknowledge errors gracefully."""


# ─────────────────────────────────────────────────────────────────────────────
# LAZY AGENT — built on first run_agent() call
# Uses MultiServerMCPClient to fetch all tools from mcp_server.py.
# ─────────────────────────────────────────────────────────────────────────────

_agent = None


async def _get_agent():
    global _agent
    if _agent is not None:
        return _agent

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=settings.GROQ_API_KEY,
        temperature=0.1,
    )

    # Connect to mcp_server.py as a subprocess.
    # All tool definitions come from there — agent.py defines none itself.
    mcp_client = MultiServerMCPClient({
        "artha": {
            "command": sys.executable,
            "args": [os.path.abspath("mcp_server.py")],
            "transport": "stdio",
            "env": dict(os.environ),
        }
    })
    tools = await mcp_client.get_tools()

    _agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )
    return _agent


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

async def run_agent(session_id: str, message: str) -> dict:
    """
    Run the agent for one conversation turn.
    Fetches tools from mcp_server.py on first call.
    Pulls chat history from session_store for multi-turn memory.
    Returns: {"text": str, "data": dict | None}
    """
    agent = await _get_agent()

    history = get_history(session_id)
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=message))

    result = await agent.ainvoke({"messages": messages})

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
