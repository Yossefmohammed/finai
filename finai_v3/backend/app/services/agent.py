"""
FinAI Agent — Powered by LangChain + LangGraph
================================================
Providers:
  1. Claude  (Anthropic)    — claude-sonnet-4-20250514
  2. GPT-4o  (OpenAI)       — gpt-4o-mini
  3. LLaMA   (Groq FREE)    — llama-3.3-70b-versatile
  4. Gemini  (Google FREE)  — gemini-1.5-flash
  5. Ollama  (Local FREE)   — llama3.2 / qwen2.5 / phi3 etc.
"""

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional
import json, re

from app.tools.financial_tools import call_tool

# ── System prompts ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are FinAI, a professional Arabic/English bilingual financial assistant \
powered by LangChain + LangGraph.

You have access to tools that query the user's real transaction data from their ERP system.

Rules:
- For financial questions: always call a tool to get real data before answering.
- For greetings or casual messages: reply directly in plain text — do NOT call any tool.
- Always reply in the same language the user used.
- Format all currency values with 2 decimal places.
- Be concise, professional, and insightful."""

# Special stricter prompt for local Ollama models
OLLAMA_SYSTEM_PROMPT = """You are FinAI, a financial assistant. You help users analyze their financial data.

You have these tools:
- get_expenses: fetch transactions filtered by period/category/type
- get_dashboard_summary: get income, expenses, profit overview
- compare_periods: compare two months
- detect_anomalies: find unusual transactions
- forecast_trend: predict future expenses or income

CRITICAL RULES:
1. For greetings like "hi", "hello", "how are you", "thanks" — reply in plain conversational text. Do NOT call any tool.
2. For financial questions — use a tool to get real data, then answer in plain language.
3. NEVER output raw JSON or tool call syntax in your final answer.
4. Always use period="all" when no specific period is mentioned.
5. Reply in the same language the user used (Arabic or English)."""


# ── Pydantic input schemas ─────────────────────────────────────────────────────
class GetExpensesInput(BaseModel):
    period: str = Field(default="all", description="'last_30_days', 'this_month', '2024-01', or 'all'")
    category: Optional[str] = Field(default="all", description="Category filter or 'all'")
    type: Optional[str] = Field(default="all", description="'income', 'expense', or 'all'")

class ComparePeriodsInput(BaseModel):
    period1: str = Field(description="First period e.g. '2024-01'")
    period2: str = Field(description="Second period e.g. '2024-02'")
    type: Optional[str] = Field(default="all")

class DetectAnomaliesInput(BaseModel):
    threshold: Optional[float] = Field(default=2.0)
    category: Optional[str] = Field(default="all")

class DashboardSummaryInput(BaseModel):
    period: Optional[str] = Field(default="all")

class ForecastTrendInput(BaseModel):
    months_ahead: int = Field(description="How many months ahead to forecast")
    type: str = Field(default="expense")


# ── LangChain StructuredTools ──────────────────────────────────────────────────
def build_tools(db: Session, user_id: int = 0) -> list:
    def get_expenses(period="all", category="all", type="all"):
        return json.dumps(call_tool("get_expenses",
            {"period": period, "category": category, "type": type, "user_id": user_id}, db),
            ensure_ascii=False)

    def compare_periods(period1: str, period2: str, type="all"):
        return json.dumps(call_tool("compare_periods",
            {"period1": period1, "period2": period2, "type": type, "user_id": user_id}, db),
            ensure_ascii=False)

    def detect_anomalies(threshold=2.0, category="all"):
        return json.dumps(call_tool("detect_anomalies",
            {"threshold": threshold, "category": category, "user_id": user_id}, db),
            ensure_ascii=False)

    def get_dashboard_summary(period="all"):
        return json.dumps(call_tool("get_dashboard_summary",
            {"period": period, "user_id": user_id}, db),
            ensure_ascii=False)

    def forecast_trend(months_ahead: int, type="expense"):
        return json.dumps(call_tool("forecast_trend",
            {"months_ahead": months_ahead, "type": type, "user_id": user_id}, db),
            ensure_ascii=False)

    return [
        StructuredTool.from_function(func=get_expenses, name="get_expenses",
            description="Fetch and summarize transactions. Use period='all' for all data.",
            args_schema=GetExpensesInput),
        StructuredTool.from_function(func=compare_periods, name="compare_periods",
            description="Compare spending between two time periods.",
            args_schema=ComparePeriodsInput),
        StructuredTool.from_function(func=detect_anomalies, name="detect_anomalies",
            description="Detect unusual or suspicious transactions using statistics.",
            args_schema=DetectAnomaliesInput),
        StructuredTool.from_function(func=get_dashboard_summary, name="get_dashboard_summary",
            description="Get full financial overview: total income, expenses, net profit, top categories.",
            args_schema=DashboardSummaryInput),
        StructuredTool.from_function(func=forecast_trend, name="forecast_trend",
            description="Forecast future income or expenses using historical trend.",
            args_schema=ForecastTrendInput),
    ]


# ── LLM factory ────────────────────────────────────────────────────────────────
def _get_llm(provider: str, api_key: str, ollama_model: str = "llama3.2"):
    p = provider.lower()
    if p == "claude":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model="claude-sonnet-4-20250514", api_key=api_key, max_tokens=1024)
    if p == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o-mini", api_key=api_key, max_tokens=1024)
    if p == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(model="llama-3.3-70b-versatile", api_key=api_key, max_tokens=1024)
    if p == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model="gemini-1.5-flash",
            google_api_key=api_key, max_output_tokens=1024, temperature=0.1)
    if p == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=ollama_model, base_url="http://localhost:11434",
            num_predict=1024, temperature=0.1)
    raise ValueError(f"Unknown provider: {provider}")


# ── Conversational detection — expanded ───────────────────────────────────────
_CONV_WORDS = [
    "hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "bye", "good",
    "how are you", "what are you", "who are you", "what can you do",
    "english", "arabic", "language", "speak", "talk", "help me",
    "مرحبا", "شكرا", "اهلا", "كيف حالك", "كيف", "صباح", "مساء", "من انت"
]

def _is_conversational(q: str) -> bool:
    q_lower = q.lower().strip()
    # Direct match on full phrase
    for phrase in _CONV_WORDS:
        if phrase in q_lower:
            # Only treat as conversational if no financial keywords
            financial = ["expense","income","profit","transaction","spend","cost",
                         "budget","forecast","data","report","category","amount",
                         "مصروف","دخل","ربح","بيانات","تقرير","ميزانية"]
            if not any(f in q_lower for f in financial):
                return True
    return False


# ── Clean up Ollama output that leaks raw JSON ─────────────────────────────────
def _clean_ollama_output(text: str) -> str:
    """Remove any leaked tool-call JSON from Ollama responses."""
    if not text:
        return text
    # Remove lines that look like raw tool JSON
    lines = text.split('\n')
    clean = []
    for line in lines:
        stripped = line.strip()
        # Skip lines that are raw tool call JSON
        if stripped.startswith('{"name"') or stripped.startswith('{"tool"'):
            continue
        if re.match(r'^\{"name":\s*"[a-z_]+"', stripped):
            continue
        clean.append(line)
    result = '\n'.join(clean).strip()
    return result if result else text


# ── Ollama-specific agent using direct tool execution ──────────────────────────
async def _run_ollama(question: str, db: Session, user_id: int,
                      ollama_model: str) -> str:
    """
    Custom Ollama handler — fetches data first, then asks LLM to explain it.
    More reliable than ReAct loop for local models.
    """
    from langchain_ollama import ChatOllama

    llm = ChatOllama(model=ollama_model, base_url="http://localhost:11434",
                     num_predict=1024, temperature=0.1)

    # Step 1: Use LLM to decide which tool to call
    tool_decision_prompt = f"""You are a financial data analyst. The user asks: "{question}"

Which ONE tool should you call to answer this question? Reply with ONLY the tool name and parameters in this exact JSON format (nothing else):

{{"tool": "tool_name", "params": {{...}}}}

Available tools:
- get_dashboard_summary: {{"period": "all"}} — for general overview, profit, income, expenses
- get_expenses: {{"period": "all", "category": "all", "type": "all"}} — for transaction details
- detect_anomalies: {{"threshold": 2.0}} — for unusual transactions
- compare_periods: {{"period1": "2024-01", "period2": "2024-02"}} — for comparing months
- forecast_trend: {{"months_ahead": 3, "type": "expense"}} — for future predictions

If this is a greeting or casual message (hi, how are you, thanks, etc.), reply with:
{{"tool": "none", "params": {{}}}}"""

    decision_response = await llm.ainvoke([HumanMessage(content=tool_decision_prompt)])
    decision_text = decision_response.content.strip()

    # Step 2: Parse and execute the tool
    tool_data = None
    tool_name = None
    try:
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', decision_text, re.DOTALL)
        if json_match:
            decision = json.loads(json_match.group())
            tool_name = decision.get("tool", "none")
            params    = decision.get("params", {})

            if tool_name != "none" and tool_name in [
                "get_dashboard_summary", "get_expenses",
                "detect_anomalies", "compare_periods", "forecast_trend"
            ]:
                params["user_id"] = user_id
                tool_data = call_tool(tool_name, params, db)
    except Exception:
        pass

    # Step 3: Ask LLM to answer using the real data
    if tool_data:
        answer_prompt = f"""You are FinAI, a financial assistant. The user asked: "{question}"

Here is the real financial data from their database:
{json.dumps(tool_data, ensure_ascii=False, indent=2)}

Answer the user's question clearly and concisely using this data.
- Use the same language the user used (Arabic or English)
- Format currency with 2 decimal places
- Be helpful and specific
- Do NOT output JSON or technical terms — just plain readable answer"""
    else:
        # Conversational or tool decision failed — just answer directly
        answer_prompt = f"""{OLLAMA_SYSTEM_PROMPT}

User: {question}
Assistant:"""

    final_response = await llm.ainvoke([HumanMessage(content=answer_prompt)])
    result = _clean_ollama_output(final_response.content)
    return result or "I could not process your request. Please try rephrasing."


# ── Main entry point ───────────────────────────────────────────────────────────
async def run_agent(
    question: str,
    provider: str,
    api_key: str,
    db: Session,
    user_id: int = 0,
    ollama_model: str = "llama3.2"
) -> str:
    """Route to correct provider. Ollama uses custom handler for reliability."""
    p = provider.lower()

    # Ollama gets its own reliable handler
    if p == "ollama":
        try:
            return await _run_ollama(question, db, user_id, ollama_model)
        except Exception as e:
            err = str(e)
            if "connection" in err.lower() or "refused" in err.lower():
                return ("❌ Cannot connect to Ollama.\n"
                        "Run this in a terminal: ollama serve\n"
                        f"Then try again. (Model: {ollama_model})")
            return f"❌ Ollama error: {err[:150]}"

    # Cloud providers use LangGraph ReAct
    try:
        llm   = _get_llm(provider, api_key, ollama_model)
        tools = build_tools(db, user_id=user_id)

        if _is_conversational(question):
            response = await llm.ainvoke([
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=question)
            ])
            return response.content

        agent  = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)
        result = await agent.ainvoke({"messages": [HumanMessage(content=question)]})

        for msg in reversed(result.get("messages", [])):
            if (hasattr(msg, "content") and msg.content
                    and msg.__class__.__name__ == "AIMessage"
                    and not getattr(msg, "tool_calls", None)):
                return msg.content

        return "I could not complete the analysis. Please try again."

    except Exception as e:
        err = str(e)
        if "401" in err or "authentication" in err.lower():
            return "❌ Invalid API key. Please check your key in the sidebar."
        if "429" in err or "rate_limit" in err.lower():
            return "⏳ Rate limit reached. Please wait a moment and try again."
        if "quota" in err.lower() and p == "gemini":
            return "⏳ Gemini free quota reached. Switch to Groq (also free)."
        try:
            llm = _get_llm(provider, api_key, ollama_model)
            r   = await llm.ainvoke([
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=f"{question}\n\n(Answer generally, data unavailable.)")
            ])
            return r.content
        except Exception:
            return f"Sorry, I encountered an error: {err[:120]}"