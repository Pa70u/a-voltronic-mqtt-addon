"""Vérifie le bypass d'auth via DISABLE_AUTH (mode dev/beta)."""
import importlib

from fastapi.testclient import TestClient

from app.security import hash_password


def test_disable_auth_bypasses_token(db, monkeypatch):
    # Crée un admin "alice" qui sera celui retourné par le bypass
    db.execute(
        "INSERT OR IGNORE INTO users(id, nom, email, password_hash, role) "
        "VALUES (40001, 'Alice', 'alice@dev.fr', ?, 'admin')",
        (hash_password("pw"),),
    )
    db.commit()

    # Active le bypass et purge le cache des settings
    monkeypatch.setenv("DISABLE_AUTH", "true")
    from app import config
    config.get_settings.cache_clear()

    # Rejoue les routes avec un import frais de main pour avoir l'app à jour
    import main as main_module
    importlib.reload(main_module)

    try:
        client = TestClient(main_module.app)

        # /api/dashboard/stats sans token → doit passer
        r = client.get("/api/dashboard/stats")
        assert r.status_code == 200, r.text

        # /api/health expose bien le flag
        r = client.get("/api/health")
        assert r.json()["auth_disabled"] is True
    finally:
        monkeypatch.delenv("DISABLE_AUTH", raising=False)
        config.get_settings.cache_clear()
        importlib.reload(main_module)
