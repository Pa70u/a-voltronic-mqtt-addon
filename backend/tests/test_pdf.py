"""Tests de génération PDF + endpoints /pdf."""
import json
import secrets

from fastapi.testclient import TestClient

import main
from app.security import create_token, hash_password
from app.services.pdf import build_devis_pdf, build_facture_pdf


def _uniq(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(4)}"


def _setup_admin_and_data(db):
    db.execute(
        "INSERT OR IGNORE INTO users(id, nom, email, password_hash, role) "
        "VALUES (30001, 'Adm', 'pdf_admin@test.fr', ?, 'admin')",
        (hash_password("pw"),),
    )
    db.execute(
        "INSERT OR IGNORE INTO users(id, nom, prenom, email, telephone, adresse, "
        "password_hash, role) VALUES (30002, 'Dupont', 'Jean', 'jean@test.fr', "
        "'0612345678', '12 rue Test, 75001 Paris', '', 'client')"
    )
    db.execute(
        "INSERT OR IGNORE INTO vehicules(id, client_id, immatriculation, marque, "
        "modele, kilometrage) VALUES (30003, 30002, 'AA-123-BB', 'Renault', 'Clio', 80000)"
    )
    # Mentions légales si pas déjà seedées
    for cle, valeur in [
        ("nom", "Garage de la Montagne"),
        ("adresse", "Z.I. de la Montagne"),
        ("cp_ville", "94510 La Queue-en-Brie"),
        ("siret", "487 723 306 00014"),
        ("tva", "FR 08 487 723 306"),
        ("forme", "SARL"),
        ("capital", "8000"),
        ("rcs", "487 723 306 R.C.S. Créteil"),
        ("naf", "45.20A"),
    ]:
        db.execute("INSERT OR IGNORE INTO config_garage(cle, valeur) VALUES (?,?)",
                   (cle, valeur))
    db.commit()
    return create_token(db, 30001)


def _insert_facture(db) -> tuple[int, str]:
    numero = _uniq("FAC_TEST")
    lignes = json.dumps([
        {"desc": "Vidange + filtre huile", "qte": 1, "pu_ht": 65, "total_ht": 65},
        {"desc": "Plaquettes avant", "qte": 1, "pu_ht": 80, "total_ht": 80},
    ], ensure_ascii=False)
    cur = db.execute(
        "INSERT INTO factures(numero, client_id, vehicule_id, lignes, total_ht, "
        "tva, total_ttc, statut, date_facture, date_echeance) "
        "VALUES (?, 30002, 30003, ?, 145, 20, 174, 'impayee', "
        "'2026-05-02', '2026-06-01')",
        (numero, lignes),
    )
    db.commit()
    return cur.lastrowid, numero


def _insert_devis(db) -> tuple[int, str]:
    numero = _uniq("DEV_TEST")
    lignes = json.dumps([
        {"desc": "Diagnostic moteur", "qte": 1, "pu_ht": 55, "total_ht": 55},
    ], ensure_ascii=False)
    cur = db.execute(
        "INSERT INTO devis(numero, client_id, vehicule_id, lignes, total_ht, "
        "tva, total_ttc, statut, validite) "
        "VALUES (?, 30002, 30003, ?, 55, 20, 66, 'brouillon', 30)",
        (numero, lignes),
    )
    db.commit()
    return cur.lastrowid, numero


def test_build_facture_pdf_returns_valid_bytes(db):
    _setup_admin_and_data(db)
    fid, numero = _insert_facture(db)

    pdf, filename = build_facture_pdf(db, fid)
    assert filename == f"facture_{numero}.pdf"
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


def test_build_devis_pdf_returns_valid_bytes(db):
    _setup_admin_and_data(db)
    did, numero = _insert_devis(db)

    pdf, filename = build_devis_pdf(db, did)
    assert filename == f"devis_{numero}.pdf"
    assert pdf.startswith(b"%PDF-")


def test_build_facture_pdf_unknown_id_raises(db):
    _setup_admin_and_data(db)
    try:
        build_facture_pdf(db, 999999)
    except ValueError as e:
        assert "introuvable" in str(e)
    else:
        raise AssertionError("ValueError attendue")


def test_endpoint_facture_pdf(db):
    token = _setup_admin_and_data(db)
    fid, numero = _insert_facture(db)

    client = TestClient(main.app)
    r = client.get(f"/api/factures/{fid}/pdf",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert f"facture_{numero}.pdf" in r.headers["content-disposition"]
    assert r.content.startswith(b"%PDF-")


def test_endpoint_devis_pdf(db):
    token = _setup_admin_and_data(db)
    did, _ = _insert_devis(db)

    client = TestClient(main.app)
    r = client.get(f"/api/devis/{did}/pdf",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.content.startswith(b"%PDF-")


def test_endpoint_facture_pdf_unauthorized(db):
    _setup_admin_and_data(db)
    fid, _ = _insert_facture(db)

    client = TestClient(main.app)
    r = client.get(f"/api/factures/{fid}/pdf")
    assert r.status_code == 401


def test_endpoint_facture_pdf_404(db):
    token = _setup_admin_and_data(db)
    client = TestClient(main.app)
    r = client.get("/api/factures/999999/pdf",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404
