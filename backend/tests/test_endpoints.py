"""Tests bout-en-bout des principaux endpoints (auth + catalogue)."""
from fastapi.testclient import TestClient

import main
from app.security import create_token, hash_password
from seeds.catalogue import seed as seed_catalogue


def _login_admin(db):
    db.execute(
        "INSERT OR IGNORE INTO users(id, nom, email, password_hash, role) "
        "VALUES (?, ?, ?, ?, ?)",
        (10001, "Tester", "tester@test.fr", hash_password("pw"), "admin"),
    )
    db.commit()
    token = create_token(db, 10001)
    return token


def _login_client(db):
    db.execute(
        "INSERT OR IGNORE INTO users(id, nom, email, password_hash, role) "
        "VALUES (?, ?, ?, ?, ?)",
        (10002, "Cli", "cli@test.fr", hash_password("pw"), "client"),
    )
    db.commit()
    token = create_token(db, 10002)
    return token


def test_dashboard_requires_admin(db):
    token_client = _login_client(db)
    client = TestClient(main.app)
    r = client.get("/api/dashboard/stats",
                   headers={"Authorization": f"Bearer {token_client}"})
    assert r.status_code == 403


def test_dashboard_admin_returns_stats(db):
    token = _login_admin(db)
    client = TestClient(main.app)
    r = client.get("/api/dashboard/stats",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert "clients" in data
    assert "ca_mois" in data


def test_catalogue_seed_and_endpoint(db):
    seed_catalogue(db)
    token = _login_admin(db)
    client = TestClient(main.app)

    r = client.get("/api/catalogue",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["familles"]) == 12
    assert len(data["prestations"]) == 135


def test_catalogue_filter_by_famille(db):
    seed_catalogue(db)
    token = _login_admin(db)
    client = TestClient(main.app)

    famille_id = db.execute(
        "SELECT id FROM prestations_familles WHERE nom='Freinage'"
    ).fetchone()["id"]

    r = client.get(f"/api/catalogue/prestations?famille_id={famille_id}",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 11  # nb prestations Freinage
    assert all(p["famille_id"] == famille_id for p in items)


def test_create_client_returns_code(db):
    token = _login_admin(db)
    client = TestClient(main.app)

    r = client.post(
        "/api/clients/nouveau",
        json={"nom": "Dupont", "prenom": "Jean", "email": "test_dupont@x.fr",
              "telephone": "0612345678"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["code"].startswith("CL")


def test_engagement_6mois_blocks_resiliation(db):
    token = _login_admin(db)
    cli = TestClient(main.app)

    # Crée un client + emplacement + abonnement actif (date_debut = aujourd'hui)
    db.execute(
        "INSERT INTO users(id, nom, email, password_hash, role) "
        "VALUES (20001, 'C', 'c@x.fr', '', 'client')"
    )
    db.execute(
        "INSERT INTO emplacements(id, numero, statut) VALUES (5001, 'TEST_P5001', 'libre')"
    )
    db.commit()

    r = cli.post(
        "/api/abonnements/nouveau",
        json={"client_id": 20001, "emplacement_id": 5001,
              "date_debut": "2026-05-01", "montant": 80, "statut": "actif"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text

    aid = db.execute(
        "SELECT id FROM abonnements WHERE client_id=20001"
    ).fetchone()["id"]

    # Tentative de résiliation avant 6 mois → 400
    r = cli.patch(
        f"/api/abonnements/{aid}/statut",
        json={"statut": "resilie"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
    assert "engagement" in r.text.lower()
