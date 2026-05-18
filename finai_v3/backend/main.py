"""
main.py — FastAPI application entry point for FinAI v3
"""
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.auth.router import router as auth_router
from app.routers.api import router as api_router
from app.models.database import init_db

# ── Load environment ──────────────────────────────────────────────────────────
load_dotenv()

APP_ENV = os.getenv("APP_ENV", "development")
ALLOWED_ORIGINS_RAW = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000",
)
allowed_origins = [o.strip() for o in ALLOWED_ORIGINS_RAW.split(",") if o.strip()]

# ── App factory ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="FinAI v3",
    description="Bilingual AI financial assistant — multi-tenant, CSV import, PDF/Excel export.",
    version="3.0.0",
    docs_url="/docs" if APP_ENV != "production" else None,
    redoc_url="/redoc" if APP_ENV != "production" else None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(api_router, prefix="/api", tags=["Financial API"])

# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup() -> None:
    init_db()


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health() -> dict:
    return {"status": "ok", "env": APP_ENV}