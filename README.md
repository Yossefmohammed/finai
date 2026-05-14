# FinAI v3

FinAI v3 is a bilingual AI financial assistant built with FastAPI, SQLAlchemy, and LangChain/LangGraph. It supports multi-tenant transaction tracking, CSV upload, authenticated user access, financial summaries, and PDF/Excel export.

## Project Structure

- `finai_v3/`
  - `backend/` - FastAPI backend API, authentication, database models, AI agent, CSV import, and report generation.
  - `frontend/` - Static HTML UI for the financial assistant and authentication.
- `customers-100.csv` - Example customer list data (not a transaction CSV).
- `sample_transactions.csv` - A sample transaction CSV file that matches the expected import format.

## Key Features

- User registration and JWT authentication
- CSV upload for transaction import
- AI chat interface powered by LangChain/LangGraph and multiple providers
- Transaction listing, adding, and clearing for the authenticated user
- Dashboard summary with income, expenses, profit, and top categories
- Export reports to PDF or Excel

## Backend Overview

The backend is located in `finai_v3_auth/finai_v3/backend`.

- `main.py` - FastAPI application entrypoint
- `app/models/database.py` - SQLAlchemy models and DB setup
- `app/auth/core.py` - JWT and password handling
- `app/auth/router.py` - registration, login, profile, and account routes
- `app/routers/api.py` - protected financial API routes
- `app/services/csv_service.py` - CSV parsing and transaction import
- `app/services/agent.py` - AI agent integration
- `app/tools/financial_tools.py` - analytics and tool implementations

## Installation

1. Navigate to the backend folder:

```bash
cd /home/user2/Desktop/my-work/finai_v3_auth/finai_v3/backend
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Initialize the database:

```bash
python -c "from app.models.database import init_db; init_db()"
```

## Running the API

Start the FastAPI server from the backend folder:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

## Authentication

The backend uses JWT authentication.

### Endpoints

- `POST /auth/register` - Create a new user account
- `POST /auth/login` - Obtain JWT token
- `GET /auth/me` - Get current user profile
- `PUT /auth/update` - Update business name or password
- `DELETE /auth/account` - Delete user account and all data

## Financial API

These routes require an authenticated user and the access token in the `Authorization: Bearer <token>` header.

- `POST /api/upload` - Upload a transaction CSV file
- `POST /api/chat` - Ask AI questions about your financial data
- `GET /api/transactions` - List transactions for the logged-in user
- `POST /api/transactions` - Add a new transaction manually
- `DELETE /api/transactions` - Delete all transactions for the user
- `GET /api/stats` - Get dashboard summary
- `GET /api/providers` - List supported AI providers
- `GET /api/export/pdf` - Download a PDF financial report
- `GET /api/export/excel` - Download an Excel financial report

## CSV Format

The expected transaction CSV should include columns similar to:

- `Date`
- `Description`
- `Amount`
- `Type`
- `Category`

Example row:

```csv
Date,Description,Amount,Type,Category
2024-01-01,Salary Deposit,5000.00,income,Income
```

> Note: `customers-100.csv` is customer contact data, not financial transactions. It cannot be imported as transaction data.

## Frontend

The frontend static files are in `finai_v3_auth/finai_v3/frontend`.

- `index.html` - Main UI
- `auth.html` - Authentication page

You can open these files directly in the browser or serve them from a simple static server.

## Notes

- The SQLite database file is `finai.db` in the backend folder.
- The default JWT secret is hardcoded in `app/auth/core.py`. For production, replace it with a secure environment variable.
- The project is configured to work with several AI providers, including Anthropic, OpenAI, Groq, Gemini, and Ollama.

## License

This repository does not include a license file. Add one as needed for your project.
