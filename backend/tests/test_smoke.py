"""Tests fumée du backend."""
from fastapi.testclient import TestClient

import main


def test_app_imports():
    assert main.app is not None
    assert "GarageOS" in main.app.title


def test_health_endpoint():
    client = TestClient(main.app)
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["app"] == "GarageOS"
    assert "auth_disabled" in body


def test_login_requires_credentials():
    client = TestClient(main.app)
    r = client.post("/api/auth/login", json={"email": "x@y.z", "password": "wrong"})
    assert r.status_code == 401
