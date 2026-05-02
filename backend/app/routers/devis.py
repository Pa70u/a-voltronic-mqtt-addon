"""Gestion des devis."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import current_admin, get_db
from ..schemas.common import OK
from ..schemas.devis import (
    DevisCreated,
    DevisIn,
    DevisOut,
    DevisStatutUpdate,
    DevisUpdate,
    EnvoyerDevis,
)

router = APIRouter(prefix="/api/devis", tags=["devis"])

_SELECT = (
    "SELECT d.id, d.numero, d.client_id, d.vehicule_id, d.lignes, "
    "d.total_ht, d.tva, d.total_ttc, d.statut, d.notes, d.validite, "
    "d.date_echeance, d.created_at, "
    "u.nom, u.prenom, u.email, u.telephone, "
    "v.immatriculation, v.marque, v.modele "
    "FROM devis d "
    "JOIN users u ON d.client_id=u.id "
    "LEFT JOIN vehicules v ON d.vehicule_id=v.id "
)


def _next_numero(db: sqlite3.Connection) -> str:
    now = datetime.now()
    count = db.execute("SELECT COUNT(*) AS c FROM devis").fetchone()["c"]
    return f"DEV_{now.strftime('%Y_%m')}_{count + 1:03d}"


@router.get("", response_model=list[DevisOut])
def list_devis(
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    rows = db.execute(_SELECT + "ORDER BY d.created_at DESC").fetchall()
    return [DevisOut(**dict(r)) for r in rows]


@router.post("", response_model=DevisCreated)
def create_devis(
    payload: DevisIn,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    total_ht = round(sum(l.total() for l in payload.lignes), 2)
    total_ttc = round(total_ht * (1 + payload.tva / 100), 2)
    numero = _next_numero(db)
    lignes_json = json.dumps([l.model_dump() for l in payload.lignes], ensure_ascii=False)

    cur = db.execute(
        "INSERT INTO devis(numero, client_id, vehicule_id, lignes, total_ht, "
        "tva, total_ttc, statut, notes, validite) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            numero, payload.client_id, payload.vehicule_id, lignes_json,
            total_ht, payload.tva, total_ttc, "brouillon",
            payload.notes, payload.validite,
        ),
    )
    db.commit()
    return DevisCreated(numero=numero, id=cur.lastrowid)


@router.patch("/{did}/statut", response_model=OK)
def update_statut(
    did: int,
    payload: DevisStatutUpdate,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    db.execute("UPDATE devis SET statut=? WHERE id=?", (payload.statut, did))
    db.commit()
    return OK()


@router.patch("/{did}/modifier", response_model=OK)
def update_devis(
    did: int,
    payload: DevisUpdate,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    fields = payload.model_dump(exclude_unset=True)
    if "lignes" in fields and fields["lignes"] is not None:
        lignes = payload.lignes or []
        total_ht = round(sum(l.total() for l in lignes), 2)
        tva = fields.get("tva")
        if tva is None:
            existing = db.execute("SELECT tva FROM devis WHERE id=?", (did,)).fetchone()
            tva = existing["tva"] if existing else 20.0
        total_ttc = round(total_ht * (1 + tva / 100), 2)
        fields["lignes"] = json.dumps([l.model_dump() for l in lignes], ensure_ascii=False)
        fields["total_ht"] = total_ht
        fields["total_ttc"] = total_ttc

    if not fields:
        return OK()

    sets = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [did]
    db.execute(f"UPDATE devis SET {sets} WHERE id=?", values)
    db.commit()
    return OK()


@router.post("/{did}/convertir")
def convertir_devis(
    did: int,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    dev = db.execute("SELECT * FROM devis WHERE id=?", (did,)).fetchone()
    if not dev:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Devis introuvable")

    now = datetime.now()
    count = db.execute("SELECT COUNT(*) AS c FROM factures").fetchone()["c"]
    numero = f"FAC_{now.strftime('%Y_%m')}_{count + 1:03d}"
    exp = (now + timedelta(days=30)).strftime("%Y-%m-%d")

    db.execute(
        "INSERT INTO factures(numero, devis_id, client_id, vehicule_id, lignes, "
        "total_ht, tva, total_ttc, statut, notes, date_echeance, date_facture) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            numero, dev["id"], dev["client_id"], dev["vehicule_id"], dev["lignes"],
            dev["total_ht"], dev["tva"], dev["total_ttc"],
            "impayee", dev["notes"], exp, now.strftime("%Y-%m-%d"),
        ),
    )
    db.execute("UPDATE devis SET statut='facture' WHERE id=?", (did,))
    db.commit()
    return {"ok": True, "numero": numero}


@router.post("/{did}/envoyer")
def envoyer_devis(
    did: int,
    payload: EnvoyerDevis,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    """Stub — l'envoi réel arrive au jalon 4 (service notifications + PDF)."""
    return {
        "ok": True,
        "results": {"info": "Envoi en cours d'implémentation (jalon 4)"},
        "payment_url": "",
    }
