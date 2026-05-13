from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from app.models.database import Transaction
from datetime import datetime, timedelta
import statistics

# ── Tool definitions (passed to AI APIs) ──────────────────────────────────────
TOOL_DEFINITIONS = [
    {
        "name": "get_expenses",
        "description": "Fetch and summarize transactions filtered by period and/or category. Use for questions about spending, income, or transaction lists.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "e.g. '2024-01', 'last_month', 'last_30_days', 'all'"},
                "category": {"type": "string", "description": "Category filter or 'all'"},
                "type": {"type": "string", "enum": ["income", "expense", "all"], "description": "Transaction type"}
            },
            "required": ["period"]
        }
    },
    {
        "name": "compare_periods",
        "description": "Compare spending or income between two time periods (month-over-month).",
        "input_schema": {
            "type": "object",
            "properties": {
                "period1": {"type": "string", "description": "First period e.g. '2024-01'"},
                "period2": {"type": "string", "description": "Second period e.g. '2024-02'"},
                "type": {"type": "string", "enum": ["income", "expense", "all"]}
            },
            "required": ["period1", "period2"]
        }
    },
    {
        "name": "detect_anomalies",
        "description": "Detect unusual transactions or spending spikes using statistical analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "threshold": {"type": "number", "description": "Z-score threshold, default 2.0"},
                "category": {"type": "string", "description": "Category to analyze or 'all'"}
            },
            "required": []
        }
    },
    {
        "name": "get_dashboard_summary",
        "description": "Get a full financial overview: total income, expenses, profit, top categories.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "Period to summarize, default 'last_30_days'"}
            },
            "required": []
        }
    },
    {
        "name": "forecast_trend",
        "description": "Project future income or expense trend based on historical data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "months_ahead": {"type": "integer", "description": "How many months to forecast"},
                "type": {"type": "string", "enum": ["income", "expense"]}
            },
            "required": ["months_ahead", "type"]
        }
    }
]

# OpenAI format (function calling)
TOOLS_OPENAI = [
    {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"]
        }
    }
    for t in TOOL_DEFINITIONS
]

# ── Tool implementations ───────────────────────────────────────────────────────
def _parse_period(period: str):
    """Return (start, end) datetime for a period string."""
    now = datetime.utcnow()
    if period in ("all", None, ""):
        return None, None
    if period == "last_30_days":
        return now - timedelta(days=30), now
    if period == "last_month":
        first = now.replace(day=1) - timedelta(days=1)
        start = first.replace(day=1)
        return start, first
    if period == "this_month":
        return now.replace(day=1), now
    # YYYY-MM
    try:
        dt = datetime.strptime(period, "%Y-%m")
        if dt.month == 12:
            end = dt.replace(year=dt.year + 1, month=1, day=1) - timedelta(seconds=1)
        else:
            end = dt.replace(month=dt.month + 1, day=1) - timedelta(seconds=1)
        return dt, end
    except ValueError:
        return None, None


def get_expenses(db: Session, period="all", category="all", type="all", user_id: int = 0) -> dict:
    q = db.query(Transaction)
    if user_id: q = q.filter(Transaction.user_id == user_id)
    start, end = _parse_period(period)
    if start:
        q = q.filter(Transaction.date >= start, Transaction.date <= end)
    if category and category != "all":
        q = q.filter(Transaction.category.ilike(f"%{category}%"))
    if type and type != "all":
        q = q.filter(Transaction.type == type)
    rows = q.order_by(Transaction.date.desc()).all()
    if not rows:
        return {"count": 0, "total": 0, "records": []}
    total = sum(r.amount for r in rows)
    by_category = {}
    for r in rows:
        by_category[r.category] = by_category.get(r.category, 0) + r.amount
    top_cats = sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:5]
    return {
        "count": len(rows),
        "total": round(total, 2),
        "top_categories": [{"category": k, "amount": round(v, 2)} for k, v in top_cats],
        "records": [
            {"date": r.date.strftime("%Y-%m-%d"), "description": r.description,
             "amount": r.amount, "category": r.category, "type": r.type}
            for r in rows[:20]
        ]
    }


def compare_periods(db: Session, period1: str, period2: str, type="all", user_id: int = 0) -> dict:
    def _sum(period):
        q = db.query(func.sum(Transaction.amount)).filter(Transaction.amount > 0)
        start, end = _parse_period(period)
        if start:
            q = q.filter(Transaction.date >= start, Transaction.date <= end)
        if type != "all":
            q = q.filter(Transaction.type == type)
        result = q.scalar()
        return round(result or 0, 2)

    s1, s2 = _sum(period1), _sum(period2)
    diff = round(s2 - s1, 2)
    pct = round((diff / s1 * 100) if s1 else 0, 1)
    return {
        "period1": {"label": period1, "total": s1},
        "period2": {"label": period2, "total": s2},
        "difference": diff,
        "change_percent": pct,
        "trend": "up" if diff > 0 else "down"
    }


def detect_anomalies(db: Session, threshold=2.0, category="all", user_id: int = 0) -> dict:
    q = db.query(Transaction)
    if category and category != "all":
        q = q.filter(Transaction.category.ilike(f"%{category}%"))
    rows = q.all()
    if len(rows) < 3:
        return {"anomalies": [], "message": "Not enough data"}
    amounts = [r.amount for r in rows]
    mean = statistics.mean(amounts)
    std = statistics.stdev(amounts)
    if std == 0:
        return {"anomalies": [], "message": "All amounts identical"}
    flagged = [
        {"date": r.date.strftime("%Y-%m-%d"), "description": r.description,
         "amount": r.amount, "category": r.category,
         "z_score": round((r.amount - mean) / std, 2)}
        for r in rows if abs((r.amount - mean) / std) >= threshold
    ]
    flagged.sort(key=lambda x: abs(x["z_score"]), reverse=True)
    return {"anomalies": flagged[:10], "mean": round(mean, 2), "std": round(std, 2)}


def get_dashboard_summary(db: Session, period="last_30_days", user_id: int = 0) -> dict:
    start, end = _parse_period(period)
    q = db.query(Transaction)
    if start:
        q = q.filter(Transaction.date >= start, Transaction.date <= end)
    rows = q.all()
    income = sum(r.amount for r in rows if r.type == "income")
    expenses = sum(r.amount for r in rows if r.type == "expense")
    by_cat = {}
    for r in rows:
        by_cat[r.category] = by_cat.get(r.category, 0) + r.amount
    top_cats = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)[:5]
    return {
        "period": period,
        "income": round(income, 2),
        "expenses": round(expenses, 2),
        "profit": round(income - expenses, 2),
        "transaction_count": len(rows),
        "top_categories": [{"category": k, "amount": round(v, 2)} for k, v in top_cats]
    }


def forecast_trend(db: Session, months_ahead=3, type="expense", user_id: int = 0) -> dict:
    q = db.query(Transaction).filter(Transaction.type == type)
    if user_id: q = q.filter(Transaction.user_id == user_id)
    rows = q.all()
    if not rows:
        return {"forecast": [], "message": "No data available"}
    monthly = {}
    for r in rows:
        key = r.date.strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + r.amount
    if len(monthly) < 2:
        return {"forecast": [], "message": "Need at least 2 months of data"}
    sorted_months = sorted(monthly.keys())
    values = [monthly[m] for m in sorted_months]
    window = min(3, len(values))
    moving_avg = sum(values[-window:]) / window
    forecast = []
    last = datetime.strptime(sorted_months[-1], "%Y-%m")
    for i in range(1, months_ahead + 1):
        m = last.month + i
        y = last.year + (m - 1) // 12
        m = ((m - 1) % 12) + 1
        forecast.append({"month": f"{y}-{m:02d}", "projected": round(moving_avg, 2)})
    return {"historical": monthly, "forecast": forecast, "method": "moving_average"}


# Dispatcher
def call_tool(name: str, args: dict, db: Session) -> dict:
    if name == "get_expenses":
        return get_expenses(db, **args)
    if name == "compare_periods":
        return compare_periods(db, **args)
    if name == "detect_anomalies":
        return detect_anomalies(db, **args)
    if name == "get_dashboard_summary":
        return get_dashboard_summary(db, **args)
    if name == "forecast_trend":
        return forecast_trend(db, **args)
    return {"error": f"Unknown tool: {name}"}