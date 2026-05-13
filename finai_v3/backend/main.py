from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models.database import init_db
from app.routers.api import router
from app.auth.router import router as auth_router

app = FastAPI(
    title="FinAI — AI Financial Assistant",
    description="Multi-tenant AI financial assistant with LangChain + LangGraph",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()

app.include_router(auth_router)   # /auth/register, /auth/login, /auth/me
app.include_router(router)        # /api/chat, /api/upload, etc.

@app.get("/")
def root():
    return {"status": "ok", "version": "2.0.0", "message": "FinAI API running"}