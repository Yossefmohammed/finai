import pandas as pd
import io
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.database import Transaction

# ── Keyword → category map (Arabic + English) ────────────────────────────────
CATEGORY_MAP = {
    "Food & Dining": [
        "restaurant", "cafe", "coffee", "food", "pizza", "burger", "kfc", "mcdonalds",
        "subway", "sushi", "bakery", "grocery", "supermarket", "carrefour", "spinneys",
        "مطعم", "كافيه", "قهوة", "طعام", "بيتزا", "برجر", "مخبز", "سوبرماركت", "كارفور"
    ],
    "Transport": [
        "uber", "careem", "taxi", "metro", "bus", "petrol", "gas", "fuel", "parking",
        "أوبر", "كريم", "تاكسي", "مترو", "أتوبيس", "بنزين", "وقود", "موقف"
    ],
    "Shopping": [
        "amazon", "noon", "jumia", "mall", "shop", "store", "market", "clothes", "fashion",
        "أمازون", "نون", "جوميا", "مول", "متجر", "ملابس", "موضة"
    ],
    "Bills & Utilities": [
        "electricity", "water", "gas", "internet", "phone", "mobile", "vodafone", "etisalat",
        "orange", "we ", "bill", "كهرباء", "مياه", "غاز", "انترنت", "موبايل", "فاتورة"
    ],
    "Health": [
        "pharmacy", "doctor", "hospital", "clinic", "medical", "drug", "medicine",
        "صيدلية", "دكتور", "مستشفى", "عيادة", "دواء"
    ],
    "Entertainment": [
        "netflix", "spotify", "cinema", "movie", "game", "sport", "gym", "club",
        "نيتفليكس", "سبوتيفاي", "سينما", "فيلم", "لعبة", "رياضة", "جيم"
    ],
    "Education": [
        "school", "university", "course", "book", "tuition", "education",
        "مدرسة", "جامعة", "كورس", "كتاب", "تعليم"
    ],
    "Income": [
        "salary", "freelance", "payment", "transfer", "deposit", "revenue",
        "راتب", "فريلانس", "دفع", "تحويل", "إيداع", "إيراد"
    ],
    "Rent & Housing": [
        "rent", "lease", "mortgage", "property",
        "إيجار", "أيجار", "رهن", "عقار"
    ],
}

INCOME_KEYWORDS = ["salary", "freelance", "revenue", "deposit", "income",
                   "راتب", "إيداع", "إيراد", "دخل"]

def _categorize(desc: str) -> tuple[str, str]:
    """Return (category, type) for a transaction description."""
    d = str(desc).lower()
    for cat, keywords in CATEGORY_MAP.items():
        for kw in keywords:
            if kw in d:
                txtype = "income" if cat == "Income" or any(k in d for k in INCOME_KEYWORDS) else "expense"
                return cat, txtype
    return "Other", "expense"

def _detect_columns(df: pd.DataFrame) -> dict:
    """Heuristically detect which column is date / description / amount."""
    mapping = {}
    cols_lower = {c.lower(): c for c in df.columns}

    for key, candidates in {
        "date":   ["date", "تاريخ", "datum", "fecha", "data"],
        "desc":   ["description", "details", "narration", "وصف", "البيان", "particulars", "memo"],
        "amount": ["amount", "مبلغ", "debit", "credit", "value", "القيمة"],
        "type":   ["type", "نوع", "transaction type"],
        "category": ["category", "فئة", "الفئة"],
    }.items():
        for c in candidates:
            if c in cols_lower:
                mapping[key] = cols_lower[c]
                break

    # Fallback: guess by dtype
    if "date" not in mapping:
        for col in df.columns:
            try:
                pd.to_datetime(df[col].dropna().iloc[0])
                mapping["date"] = col
                break
            except Exception:
                pass

    if "amount" not in mapping:
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                mapping["amount"] = col
                break

    if "desc" not in mapping:
        str_cols = [c for c in df.columns if df[c].dtype == object and c != mapping.get("date")]
        if str_cols:
            mapping["desc"] = str_cols[0]

    return mapping


def parse_csv(contents: bytes, db: Session, user_id: int = 0) -> dict:
    """Parse CSV bytes, auto-detect columns, insert transactions, return summary."""
    df = pd.read_csv(io.BytesIO(contents), encoding="utf-8-sig")
    df.columns = df.columns.str.strip()

    cols = _detect_columns(df)
    if "amount" not in cols:
        raise ValueError("Could not find an amount column in CSV")

    inserted = 0
    skipped = 0
    categories_seen = set()

    for _, row in df.iterrows():
        try:
            amount_raw = str(row[cols["amount"]]).replace(",", "").replace("(", "-").replace(")", "")
            amount = float(amount_raw)
            if amount == 0:
                continue

            desc = str(row.get(cols.get("desc", ""), "No description")).strip()
            cat_col = cols.get("category")
            type_col = cols.get("type")

            if cat_col and pd.notna(row.get(cat_col)):
                category = str(row[cat_col]).strip()
                txtype = "income" if amount > 0 else "expense"
            else:
                category, txtype = _categorize(desc)

            if type_col and pd.notna(row.get(type_col)):
                txtype = "income" if "in" in str(row[type_col]).lower() or "credit" in str(row[type_col]).lower() else "expense"

            date_raw = row.get(cols.get("date", ""), datetime.utcnow())
            try:
                date = pd.to_datetime(date_raw)
            except Exception:
                date = datetime.utcnow()

            tx = Transaction(
                user_id=user_id,
                date=date,
                description=desc[:500],
                amount=abs(amount),
                type=txtype,
                category=category,
                merchant=desc[:200],
            )
            db.add(tx)
            categories_seen.add(category)
            inserted += 1
        except Exception:
            skipped += 1

    db.commit()
    return {"inserted": inserted, "skipped": skipped, "categories": list(categories_seen)}