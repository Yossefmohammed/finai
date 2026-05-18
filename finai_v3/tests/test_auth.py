"""
tests/test_auth.py — Auth endpoint tests
"""


def test_register_success(client):
    resp = client.post(
        "/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "Password123!",
            "business_name": "My Biz",
        },
    )
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert "email" in data or "id" in data


def test_register_duplicate_email(client, registered_user):
    resp = client.post("/auth/register", json=registered_user)
    assert resp.status_code == 400


def test_login_success(client, registered_user):
    resp = client.post(
        "/auth/login",
        data={
            "username": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, registered_user):
    resp = client.post(
        "/auth/login",
        data={
            "username": registered_user["email"],
            "password": "wrongpassword",
        },
    )
    assert resp.status_code == 401


def test_get_profile(client, auth_headers):
    resp = client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "email" in data


def test_get_profile_unauthenticated(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401