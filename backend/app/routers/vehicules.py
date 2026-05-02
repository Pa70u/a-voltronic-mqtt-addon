"""Gestion des véhicules."""
from __future__ import annotations

import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import current_admin, current_user_id, get_db
from ..schemas.common import OK
from ..schemas.vehicule import (
    KilometrageUpdate,
    VehiculeIn,
    VehiculeOut,
    VehiculeUpdate,
)

router = APIRouter(prefix="/api/vehicules", tags=["vehicules"])

_SELECT_COLS = (
    "v.id, v.client_id, v.immatriculation, v.marque, v.modele, v.annee, "
    "v.kilometrage, v.kilometrage_date, v.vin, v.type_vehicule, "
    "v.date_dernier_ct, v.date_prochain_ct, v.created_at, "
    "u.nom, u.prenom, u.email, u.telephone"
)


@router.get("", response_model=list[VehiculeOut])
def list_vehicules(
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    rows = db.execute(
        f"SELECT {_SELECT_COLS} FROM vehicules v "
        "JOIN users u ON v.client_id=u.id "
        "ORDER BY v.created_at DESC"
    ).fetchall()
    return [VehiculeOut(**dict(r)) for r in rows]


@router.get("/miens", response_model=list[VehiculeOut])
def my_vehicules(
    user_id: int = Depends(current_user_id),
    db: sqlite3.Connection = Depends(get_db),
):
    rows = db.execute(
        f"SELECT {_SELECT_COLS} FROM vehicules v "
        "JOIN users u ON v.client_id=u.id WHERE v.client_id=? "
        "ORDER BY v.created_at DESC",
        (user_id,),
    ).fetchall()
    return [VehiculeOut(**dict(r)) for r in rows]


@router.post("/nouveau", response_model=OK)
def create_vehicule(
    payload: VehiculeIn,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    today = datetime.now().strftime("%Y-%m-%d")
    db.execute(
        "INSERT INTO vehicules(client_id, immatriculation, marque, modele, "
        "annee, kilometrage, kilometrage_date, vin, type_vehicule, "
        "date_dernier_ct, date_prochain_ct) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            payload.client_id,
            payload.immatriculation,
            payload.marque,
            payload.modele,
            payload.annee,
            payload.kilometrage,
            today if payload.kilometrage is not None else None,
            payload.vin,
            payload.type_vehicule,
            payload.date_dernier_ct,
            payload.date_prochain_ct,
        ),
    )
    db.commit()
    return OK()


@router.patch("/{vid}", response_model=OK)
def update_vehicule(
    vid: int,
    payload: VehiculeUpdate,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        return OK()
    # Si kilométrage modifié, on met à jour la date associée
    if "kilometrage" in fields:
        fields["kilometrage_date"] = datetime.now().strftime("%Y-%m-%d")
    sets = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [vid]
    db.execute(f"UPDATE vehicules SET {sets} WHERE id=?", values)
    db.commit()
    return OK()


@router.patch("/{vid}/kilometrage", response_model=OK)
def update_kilometrage(
    vid: int,
    payload: KilometrageUpdate,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    """Endpoint dédié à la popup de mise à jour kilométrage à l'ouverture devis/facture."""
    today = datetime.now().strftime("%Y-%m-%d")
    cur = db.execute(
        "UPDATE vehicules SET kilometrage=?, kilometrage_date=? WHERE id=?",
        (payload.kilometrage, today, vid),
    )
    db.commit()
    if cur.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Véhicule introuvable")
    return OK()
