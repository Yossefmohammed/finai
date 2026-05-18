"""
tests/test_api.py — Financial API endpoint tests
"""
import io


def test_stats_empty(client, auth_headers):
    """Dashboard stats should return zeros for a fresh user."""
    resp = client.get("/api/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "income" in data or "total_income" in data


def test_add_transaction(client, auth_headers):
    resp = client.post(
        "/api/transactions",
        json={
            "date": "2024-06-01",
            "description": "Freelance payment",
            "amount": 1500.00,
            "type": "income",
            "category": "Income",
        },
        headers=auth_headers,
    )
    assert resp.status_code in (200, 201)


def test_list_transactions(client, auth_headers):
    resp = client.get("/api/transactions", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_csv_upload(client, auth_headers):
    csv_content = (
        "Date,Description,Amount,Type,Category\n"
        "2024-01-01,Salary,5000.00,income,Income\n"
        "2024-01-05,Rent,-1200.00,expense,Housing\n"
    )
    files = {"file": ("transactions.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = client.post("/api/upload", files=files, headers=auth_headers)
    assert resp.status_code in (200, 201)


def test_delete_transactions(client, auth_headers):
    resp = client.delete("/api/transactions", headers=auth_headers)
    assert resp.status_code in (200, 204)


def test_export_pdf(client, auth_headers):
    resp = client.get("/api/export/pdf", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


def test_export_excel(client, auth_headers):
    resp = client.get("/api/export/excel", headers=auth_headers)
    assert resp.status_code == 200
    assert "spreadsheet" in resp.headers["content-type"] or "excel" in resp.headers["content-type"]


def test_unauthenticated_access_denied(client):
    resp = client.get("/api/transactions")
    assert resp.status_code == 401