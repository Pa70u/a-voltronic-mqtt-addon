"""Gestion des interventions."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from ..deps import current_admin, current_user_id, get_db
from ..schemas.common import OK
from ..schemas.intervention import (
    InterventionIn,
    InterventionOut,
    InterventionStatutUpdate,
)

router = APIRouter(prefix="/api/interventions", tags=["interventions"])

_SELECT = (
    "SELECT i.id, i.vehicule_id, i.client_id, i.date_entree, i.description, "
    "i.statut, i.montant_ht, i.montant_ttc, i.technicien, i.created_at, "
    "u.nom, u.prenom, v.immatriculation, v.marque, v.modele "
    "FROM interventions i "
    "JOIN users u ON i.client_id=u.id "
    "LEFT JOIN vehicules v ON i.vehicule_id=v.id "
)


@router.get("", response_model=list[InterventionOut])
def list_interventions(
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    rows = db.execute(_SELECT + "ORDER BY i.created_at DESC").fetchall()
    return [InterventionOut(**dict(r)) for r in rows]


@router.get("/miennes", response_model=list[InterventionOut])
def my_interventions(
    user_id: int = Depends(current_user_id),
    db: sqlite3.Connection = Depends(get_db),
):
    rows = db.execute(
        _SELECT + "WHERE i.client_id=? ORDER BY i.created_at DESC",
        (user_id,),
    ).fetchall()
    return [InterventionOut(**dict(r)) for r in rows]


@router.post("/nouveau", response_model=OK)
def create_intervention(
    payload: InterventionIn,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    db.execute(
        "INSERT INTO interventions(vehicule_id, client_id, date_entree, "
        "description, statut, montant_ht, montant_ttc, technicien) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (
            payload.vehicule_id,
            payload.client_id,
            payload.date_entree,
            payload.description,
            payload.statut,
            payload.montant_ht,
            payload.montant_ttc,
            payload.technicien,
        ),
    )
    db.commit()
    return OK()


@router.patch("/{iid}/statut", response_model=OK)
def update_statut(
    iid: int,
    payload: InterventionStatutUpdate,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    db.execute("UPDATE interventions SET statut=? WHERE id=?", (payload.statut, iid))
    db.commit()
    return OK()
