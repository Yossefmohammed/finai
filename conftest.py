"""
tests/conftest.py — Shared fixtures for FinAI v3 tests
"""
import os
import pytest

# Use an in-memory SQLite DB and a test JWT secret during tests
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_finai.db")

from fastapi.testclient import TestClient

# Import after env vars are set
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "finai_v3", "backend"))

from main import app
from app.models.database import init_db, Base, engine


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Create all tables once per test session, then drop them."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Return a TestClient for the FastAPI app."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def registered_user(client):
    """Register a fresh test user and return credentials."""
    payload = {
        "email": "testuser@example.com",
        "password": "SecurePass123!",
        "business_name": "Test Business",
    }
    client.post("/auth/register", json=payload)
    return payload


@pytest.fixture
def auth_headers(client, registered_user):
    """Log in and return Authorization headers."""
    resp = client.post(
        "/auth/login",
        data={
            "username": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}