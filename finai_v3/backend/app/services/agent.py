"""
FinAI Agent — Powered by LangChain + LangGraph
================================================
Providers supported:
  1. Claude        (Anthropic)       — claude-sonnet-4-20250514
  2. GPT-4o        (OpenAI)          — gpt-4o-mini
  3. LLaMA 3.3     (Groq — FREE)     — llama-3.3-70b-versatile
  4. Gemini        (Google — FREE)   — gemini-1.5-flash
  5. Ollama        (Local — FREE)    — any model on your machine
"""

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional
import json

from app.tools.financial_tools import call_tool

# ── System prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are FinAI, a professional Arabic/English bilingual financial assistant \
powered by LangChain + LangGraph.

You have access to tools that query the user's real transaction data from their ERP system.

Rules:
- For financial questions: always call a tool to get real data before answering.
- For greetings or casual messages: reply directly, no tool needed.
- Always reply in the same language the user used.
- Format all currency values with 2 decimal places.
- Be concise, professional, and insightful."""


# ── Pydantic input schemas ─────────────────────────────────────────────────────
class GetExpensesInput(BaseModel):
    period: str = Field(default="all", description="e.g. 'last_30_days', 'this_month', '2024-01', 'all'")
    category: Optional[str] = Field(default="all", description="Category filter or 'all'")
    type: Optional[str] = Field(default="all", description="'income', 'expense', or 'all'")

class ComparePeriodsInput(BaseModel):
    period1: str = Field(description="First period e.g. '2024-01'")
    period2: str = Field(description="Second period e.g. '2024-02'")
    type: Optional[str] = Field(default="all", description="'income', 'expense', or 'all'")

class DetectAnomaliesInput(BaseModel):
    threshold: Optional[float] = Field(default=2.0, description="Z-score threshold")
    category: Optional[str] = Field(default="all", description="Category to analyze or 'all'")

class DashboardSummaryInput(BaseModel):
    period: Optional[str] = Field(default="last_30_days", description="Period to summarize")

class ForecastTrendInput(BaseModel):
    months_ahead: int = Field(description="How many months to forecast")
    type: str = Field(default="expense", description="'income' or 'expense'")


# ── LangChain StructuredTools ─────────────────────────────────────────────────
def build_tools(db: Session, user_id: int = 0) -> list:
    def get_expenses(period="all", category="all", type="all"):
        return json.dumps(call_tool("get_expenses",
            {"period": period, "category": category, "type": type, "user_id": user_id}, db), ensure_ascii=False)

    def compare_periods(period1: str, period2: str, type="all"):
        return json.dumps(call_tool("compare_periods",
            {"period1": period1, "period2": period2, "type": type, "user_id": user_id}, db), ensure_ascii=False)

    def detect_anomalies(threshold=2.0, category="all"):
        return json.dumps(call_tool("detect_anomalies",
            {"threshold": threshold, "category": category, "user_id": user_id}, db), ensure_ascii=False)

    def get_dashboard_summary(period="last_30_days"):
        return json.dumps(call_tool("get_dashboard_summary",
            {"period": period, "user_id": user_id}, db), ensure_ascii=False)

    def forecast_trend(months_ahead: int, type="expense"):
        return json.dumps(call_tool("forecast_trend",
            {"months_ahead": months_ahead, "type": type, "user_id": user_id}, db), ensure_ascii=False)

    return [
        StructuredTool.from_function(func=get_expenses, name="get_expenses",
            description="Fetch and summarize transactions by period, category, and type.",
            args_schema=GetExpensesInput),
        StructuredTool.from_function(func=compare_periods, name="compare_periods",
            description="Compare spending or income between two time periods.",
            args_schema=ComparePeriodsInput),
        StructuredTool.from_function(func=detect_anomalies, name="detect_anomalies",
            description="Detect unusual transactions using Z-score statistical analysis.",
            args_schema=DetectAnomaliesInput),
        StructuredTool.from_function(func=get_dashboard_summary, name="get_dashboard_summary",
            description="Get full financial overview: income, expenses, profit, top categories.",
            args_schema=DashboardSummaryInput),
        StructuredTool.from_function(func=forecast_trend, name="forecast_trend",
            description="Forecast future income or expense trend using moving average.",
            args_schema=ForecastTrendInput),
    ]


# ── LLM factory — all 5 providers ─────────────────────────────────────────────
def _get_llm(provider: str, api_key: str, ollama_model: str = "llama3.2"):
    p = provider.lower()

    if p == "claude":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=api_key,
            max_tokens=1024,
        )

    if p == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o-mini",
            api_key=api_key,
            max_tokens=1024,
        )

    if p == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=api_key,
            max_tokens=1024,
        )

    if p == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",       # free tier — 15 RPM
            google_api_key=api_key,
            max_output_tokens=1024,
            temperature=0.1,
        )

    if p == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=ollama_model,             # e.g. llama3.2, phi3, gemma2
            base_url="http://localhost:11434",
            num_predict=1024,
        )

    raise ValueError(f"Unknown provider: {provider}. Choose: claude, openai, groq, gemini, ollama")


# ── Conversational detection ───────────────────────────────────────────────────
_CONV = [
    "hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "bye",
    "english", "arabic", "language", "speak", "talk",
    "مرحبا", "شكرا", "اهلا", "كيف", "صباح", "مساء"
]

def _is_conversational(q: str) -> bool:
    q_lower = q.lower().strip()
    return len(q_lower.split()) <= 5 and any(kw in q_lower for kw in _CONV)


# ── Main entry point ───────────────────────────────────────────────────────────
async def run_agent(
    question: str,
    provider: str,
    api_key: str,
    db: Session,
    user_id: int = 0,
    ollama_model: str = "llama3.2"
) -> str:
    """
    LangGraph ReAct agent — routes to the correct provider and returns answer.
    Supports: claude | openai | groq | gemini | ollama
    """
    try:
        llm = _get_llm(provider, api_key, ollama_model)

        # Conversational shortcut — no tools needed
        if _is_conversational(question):
            response = await llm.ainvoke([
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=question)
            ])
            return response.content

        tools = build_tools(db, user_id=user_id)

        # LangGraph ReAct agent
        agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)
        result = await agent.ainvoke({
            "messages": [HumanMessage(content=question)]
        })

        # Extract final AI answer (skip intermediate tool-call messages)
        for msg in reversed(result.get("messages", [])):
            if (hasattr(msg, "content") and msg.content
                    and msg.__class__.__name__ == "AIMessage"
                    and not getattr(msg, "tool_calls", None)):
                return msg.content

        return "I could not complete the analysis. Please try again."

    except Exception as e:
        err = str(e)

        # Friendly error messages per provider
        if "401" in err or "authentication" in err.lower() or "api_key" in err.lower():
            return "❌ Invalid API key. Please check your key in the sidebar."
        if "429" in err or "rate_limit" in err.lower():
            return "⏳ Rate limit reached. Please wait a moment and try again."
        if "connection" in err.lower() and provider.lower() == "ollama":
            return ("❌ Cannot connect to Ollama. Make sure it is running:\n"
                    "1. Install from https://ollama.com\n"
                    "2. Run: ollama pull llama3.2\n"
                    "3. Run: ollama serve")
        if "quota" in err.lower() and provider.lower() == "gemini":
            return "⏳ Gemini free quota reached. Wait a minute or switch to Groq (also free)."

        # Fallback — answer without tools
        try:
            llm = _get_llm(provider, api_key, ollama_model)
            r = await llm.ainvoke([
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=f"{question}\n\n(Data tools unavailable. Answer generally.)")
            ])
            return r.content
        except Exception:
            return f"Sorry, I encountered an error: {err[:120]}"