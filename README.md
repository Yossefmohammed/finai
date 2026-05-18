# FinAI v3

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi)
![LangChain](https://img.shields.io/badge/LangChain-LangGraph-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)

**FinAI v3** is a bilingual AI-powered financial assistant. It supports multi-tenant transaction tracking, CSV upload, JWT authentication, financial summaries, AI chat, and PDF/Excel report export.

---

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Quick Start (Docker)](#quick-start-docker)
- [Manual Setup](#manual-setup)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [CSV Format](#csv-format)
- [Running Tests](#running-tests)
- [Deployment](#deployment)
- [License](#license)

---

## Features

- User registration and JWT authentication
- CSV upload for bulk transaction import
- AI chat interface (Anthropic, OpenAI, Groq, Gemini, Ollama)
- Transaction CRUD with per-user data isolation
- Dashboard summary — income, expenses, profit, top categories
- Export reports as PDF or Excel
- Bilingual support (Arabic & English)

---

## Project Structure

```
finai/
├── finai_v3/
│   ├── backend/
│   │   ├── main.py                  # FastAPI entry point
│   │   ├── requirements.txt
│   │   └── app/
│   │       ├── auth/
│   │       │   ├── core.py          # JWT & password utilities
│   │       │   └── router.py        # Auth endpoints
│   │       ├── models/
│   │       │   └── database.py      # SQLAlchemy models & DB setup
│   │       ├── routers/
│   │       │   └── api.py           # Protected financial API routes
│   │       ├── services/
│   │       │   ├── csv_service.py   # CSV parsing & import
│   │       │   └── agent.py         # AI agent integration
│   │       └── tools/
│   │           └── financial_tools.py
│   └── frontend/
│       ├── index.html               # Main UI
│       └── auth.html                # Login / register page
├── tests/                           # pytest test suite
├── sample_transactions.csv
├── customers-100.csv
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
└── LICENSE
```

---

## Quick Start (Docker)

**Requirements:** [Docker](https://docs.docker.com/get-docker/) and Docker Compose

```bash
# 1. Clone the repo
git clone https://github.com/Yossefmohammed/finai.git
cd finai

# 2. Create your .env file
cp .env.example .env
# Open .env and fill in JWT_SECRET_KEY and your AI provider keys

# 3. Start everything
docker compose up --build

# Backend → http://localhost:8000
# Frontend → http://localhost:3000
# API docs → http://localhost:8000/docs
```

---

## Manual Setup

### Backend

```bash
# Navigate to backend
cd finai_v3/backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp ../../.env.example ../../.env
# Edit .env and set JWT_SECRET_KEY and AI provider keys

# Start the API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

Open `finai_v3/frontend/index.html` directly in your browser, or serve it:

```bash
cd finai_v3/frontend
python -m http.server 3000
```

---

## Environment Variables

Copy `.env.example` to `.env` and set the following:

| Variable | Required | Description |
|---|---|---|
| `JWT_SECRET_KEY` | ✅ Yes | Strong random secret for signing JWTs |
| `JWT_ALGORITHM` | No | Default: `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Default: `60` |
| `DATABASE_URL` | No | Default: `sqlite:///./finai.db` |
| `ANTHROPIC_API_KEY` | If using Claude | Your Anthropic API key |
| `OPENAI_API_KEY` | If using GPT | Your OpenAI API key |
| `GROQ_API_KEY` | If using Groq | Your Groq API key |
| `GEMINI_API_KEY` | If using Gemini | Your Google Gemini API key |
| `ALLOWED_ORIGINS` | No | Comma-separated CORS origins |
| `APP_ENV` | No | `development` or `production` |

> Generate a secure JWT secret with:
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

---

## API Reference

### Auth Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Create a new user account |
| `POST` | `/auth/login` | Obtain a JWT access token |
| `GET` | `/auth/me` | Get current user profile |
| `PUT` | `/auth/update` | Update business name or password |
| `DELETE` | `/auth/account` | Delete account and all data |

### Financial Endpoints (require `Authorization: Bearer <token>`)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/upload` | Upload a transaction CSV file |
| `POST` | `/api/chat` | Ask AI questions about your finances |
| `GET` | `/api/transactions` | List all transactions |
| `POST` | `/api/transactions` | Add a transaction manually |
| `DELETE` | `/api/transactions` | Delete all transactions |
| `GET` | `/api/stats` | Dashboard summary |
| `GET` | `/api/providers` | List supported AI providers |
| `GET` | `/api/export/pdf` | Download PDF report |
| `GET` | `/api/export/excel` | Download Excel report |

Interactive API docs are available at `http://localhost:8000/docs` in development mode.

---

## CSV Format

Upload transactions using a CSV with these columns:

```csv
Date,Description,Amount,Type,Category
2024-01-01,Salary Deposit,5000.00,income,Income
2024-01-05,Office Rent,1200.00,expense,Housing
```

> **Note:** `customers-100.csv` is example contact data — it cannot be used as a transaction file.

A ready-to-use sample is included at `sample_transactions.csv`.

---

## Running Tests

```bash
# From the project root
pip install pytest httpx

pytest
```

Tests use an in-memory SQLite database and a throwaway JWT secret — no `.env` required.

---

## Deployment

### Render (free tier)

1. Push your repo to GitHub.
2. Go to [render.com](https://render.com) → New Web Service.
3. Set **Build Command:** `pip install -r finai_v3/backend/requirements.txt`
4. Set **Start Command:** `cd finai_v3/backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add all environment variables from `.env.example` in the Render dashboard.

### Railway

```bash
npm install -g @railway/cli
railway login
railway up
```
Set env vars via `railway variables set JWT_SECRET_KEY=...`

### Production Database

For production, switch from SQLite to PostgreSQL by setting:
```
DATABASE_URL=postgresql://user:password@host:5432/finai_db
```

---

## License

This project is licensed under the [MIT License](LICENSE).