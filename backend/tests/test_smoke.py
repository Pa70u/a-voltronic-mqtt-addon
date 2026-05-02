"""Tests fumée du backend GarageOS — vérifient juste que l'app démarre."""
from fastapi.testclient import TestClient

import main


def test_app_imports():
    assert main.app is not None
    assert main.app.title == "GarageOS API v4"


def test_health_endpoint():
    client = TestClient(main.app)
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "app": "GarageOS v4"}


def test_login_requires_credentials():
    client = TestClient(main.app)
    # DB vide → 401 attendu (et pas un crash)
    r = client.post("/api/auth/login", json={"email": "x@y.z", "password": "wrong"})
    assert r.status_code == 401
