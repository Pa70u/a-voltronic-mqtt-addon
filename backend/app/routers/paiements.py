"""Gestion des paiements (mock + listing client)."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from ..deps import current_user_id, get_db
from ..schemas.common import OK
from ..schemas.parking import PaiementSimuler

router = APIRouter(prefix="/api/paiements", tags=["paiements"])


@router.post("/simuler", response_model=OK)
def simuler_paiement(
    payload: PaiementSimuler,
    user_id: int = Depends(current_user_id),
    db: sqlite3.Connection = Depends(get_db),
):
    db.execute(
        "INSERT INTO paiements(client_id, type, montant, methode, statut) "
        "VALUES (?,?,?,?,?)",
        (user_id, payload.type, payload.montant, payload.methode, "paye"),
    )
    db.commit()
    return OK()


@router.get("/miens")
def my_paiements(
    user_id: int = Depends(current_user_id),
    db: sqlite3.Connection = Depends(get_db),
):
    rows = db.execute(
        "SELECT * FROM paiements WHERE client_id=? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]
