"""Gestion des emplacements parking."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import current_admin, get_db
from ..schemas.common import OK
from ..schemas.parking import (
    EmplacementIn,
    EmplacementOut,
    EmplacementRenameIn,
    EmplacementStatutUpdate,
)

router = APIRouter(prefix="/api/emplacements", tags=["emplacements"])


@router.get("", response_model=list[EmplacementOut])
def list_emplacements(
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    rows = db.execute("SELECT * FROM emplacements ORDER BY etage, numero").fetchall()
    return [EmplacementOut(**dict(r)) for r in rows]


@router.post("/nouveau")
def create_emplacement(
    payload: EmplacementIn,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    try:
        cur = db.execute(
            "INSERT INTO emplacements(numero, statut, etage, prix_mensuel, prix_journalier) "
            "VALUES (?,?,?,?,?)",
            (payload.numero, payload.statut, payload.etage,
             payload.prix_mensuel, payload.prix_journalier),
        )
        db.commit()
        return {"ok": True, "id": cur.lastrowid}
    except sqlite3.IntegrityError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Numéro déjà existant : {e}")


@router.patch("/{eid}/statut", response_model=OK)
def update_statut(
    eid: int,
    payload: EmplacementStatutUpdate,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    db.execute("UPDATE emplacements SET statut=? WHERE id=?", (payload.statut, eid))
    db.commit()
    return OK()


@router.patch("/{eid}/renommer", response_model=OK)
def rename_emplacement(
    eid: int,
    payload: EmplacementRenameIn,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    try:
        db.execute("UPDATE emplacements SET numero=? WHERE id=?", (payload.numero, eid))
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Numéro déjà utilisé : {e}")
    return OK()


@router.delete("/{eid}/supprimer", response_model=OK)
def delete_emplacement(
    eid: int,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    db.execute("DELETE FROM abonnements WHERE emplacement_id=?", (eid,))
    db.execute("DELETE FROM emplacements WHERE id=?", (eid,))
    db.commit()
    return OK()
