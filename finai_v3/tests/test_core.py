"""
tests/test_core.py — Unit tests for JWT & password utilities
"""
import os
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest-only")

from app.auth.core import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)


def test_password_hash_and_verify():
    plain = "MyStr0ngPass!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)


def test_wrong_password_fails():
    hashed = hash_password("correct-password")
    assert not verify_password("wrong-password", hashed)


def test_create_and_decode_token():
    data = {"sub": "user@example.com", "user_id": 42}
    token = create_access_token(data)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user@example.com"
    assert decoded["user_id"] == 42


def test_invalid_token_returns_none():
    result = decode_access_token("this.is.not.a.valid.token")
    assert result is None