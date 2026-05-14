from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.models.database import get_db, Transaction, User
from app.services.agent import run_agent
from app.services.csv_service import parse_csv
from app.auth.core import get_current_user

router = APIRouter(prefix="/api")

# ── Schemas ───────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str
    provider: str = "groq"
    api_key: str = ""
    ollama_model: Optional[str] = "llama3.2"

class TransactionIn(BaseModel):
    date: str
    description: str
    amount: float
    type: str
    category: str = "Other"
    currency: str = "EGP"

# ── Chat — tenant isolated ─────────────────────────────────────────────────────
@router.post("/chat")
async def chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        answer = await run_agent(
            req.question, req.provider, req.api_key, db,
            user_id=current_user.id,
            ollama_model=req.ollama_model or "llama3.2"
        )
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── CSV Upload — scoped to current user ───────────────────────────────────────
@router.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    contents = await file.read()
    try:
        summary = parse_csv(contents, db, user_id=current_user.id)
        return {"success": True, **summary}
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


# ── Transactions — only current user's data ───────────────────────────────────
@router.get("/transactions")
def list_transactions(
    skip: int = 0, limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (db.query(Transaction)
            .filter(Transaction.user_id == current_user.id)
            .order_by(Transaction.date.desc())
            .offset(skip).limit(limit).all())
    return [
        {"id": r.id, "date": r.date.strftime("%Y-%m-%d"),
         "description": r.description, "amount": r.amount,
         "type": r.type, "category": r.category, "currency": r.currency}
        for r in rows
    ]


@router.post("/transactions")
def add_transaction(
    tx: TransactionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import datetime
    row = Transaction(
        user_id=current_user.id,
        date=datetime.strptime(tx.date, "%Y-%m-%d"),
        description=tx.description,
        amount=tx.amount, type=tx.type,
        category=tx.category, currency=tx.currency,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "message": "Transaction added"}


@router.delete("/transactions")
def clear_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(Transaction).filter(Transaction.user_id == current_user.id).delete()
    db.commit()
    return {"message": "All your transactions deleted"}


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.tools.financial_tools import get_dashboard_summary
    return get_dashboard_summary(db, "all", user_id=current_user.id)


@router.get("/providers")
def list_providers():
    return {"providers": [
        {"id": "claude",  "name": "Claude (Anthropic)",    "free": False, "key_url": "https://console.anthropic.com"},
        {"id": "openai",  "name": "GPT-4o (OpenAI)",       "free": False, "key_url": "https://platform.openai.com"},
        {"id": "groq",    "name": "LLaMA 3.3 (Groq)",      "free": True,  "key_url": "https://console.groq.com"},
        {"id": "gemini",  "name": "Gemini 1.5 (Google)",   "free": True,  "key_url": "https://aistudio.google.com/apikey"},
        {"id": "ollama",  "name": "Ollama (Local)",         "free": True,  "key_url": "https://ollama.com"},
    ]}


# ── Export endpoints ──────────────────────────────────────────────────────────
from fastapi.responses import StreamingResponse
import io

@router.get("/export/pdf")
def export_pdf(
    period: str = "all",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download a professional PDF financial report."""
    from app.services.report_service import generate_pdf
    try:
        pdf_bytes = generate_pdf(db, current_user.id,
                                  current_user.business_name, period)
        filename = f"FinAI_Report_{current_user.business_name}_{period}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/excel")
def export_excel(
    period: str = "all",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download a professional Excel financial workbook."""
    from app.services.report_service import generate_excel
    try:
        excel_bytes = generate_excel(db, current_user.id,
                                      current_user.business_name, period)
        filename = f"FinAI_Report_{current_user.business_name}_{period}.xlsx"
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))