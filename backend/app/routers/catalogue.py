"""Gestion du catalogue (familles + prestations)."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import current_admin, current_user_id, get_db
from ..schemas.catalogue import (
    CatalogueResponse,
    FamilleIn,
    FamilleOut,
    FamilleUpdate,
    PrestationIn,
    PrestationOut,
    PrestationUpdate,
)
from ..schemas.common import OK

router = APIRouter(prefix="/api/catalogue", tags=["catalogue"])


# ── Vue combinée pour la popup 2 colonnes ──────────────────────────────────
@router.get("", response_model=CatalogueResponse)
def get_catalogue(
    actif_only: bool = True,
    _: int = Depends(current_user_id),  # accessible aux clients aussi
    db: sqlite3.Connection = Depends(get_db),
):
    where_f = "WHERE actif=1" if actif_only else ""
    where_p = "WHERE p.actif=1" if actif_only else ""
    familles = [
        FamilleOut(**dict(r))
        for r in db.execute(
            f"SELECT id, nom, icone, ordre, actif FROM prestations_familles "
            f"{where_f} ORDER BY ordre, nom"
        ).fetchall()
    ]
    prestations = [
        PrestationOut(**dict(r))
        for r in db.execute(
            "SELECT p.id, p.famille_id, p.libelle, p.pu_ht, p.duree_min, p.actif, "
            "p.ordre, f.nom AS famille_nom "
            "FROM prestations p JOIN prestations_familles f ON p.famille_id=f.id "
            f"{where_p} ORDER BY f.ordre, p.ordre, p.libelle"
        ).fetchall()
    ]
    return CatalogueResponse(familles=familles, prestations=prestations)


# ── Familles ───────────────────────────────────────────────────────────────
@router.get("/familles", response_model=list[FamilleOut])
def list_familles(
    _: int = Depends(current_user_id),
    db: sqlite3.Connection = Depends(get_db),
):
    rows = db.execute(
        "SELECT id, nom, icone, ordre, actif FROM prestations_familles "
        "ORDER BY ordre, nom"
    ).fetchall()
    return [FamilleOut(**dict(r)) for r in rows]


@router.post("/familles", response_model=FamilleOut)
def create_famille(
    payload: FamilleIn,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    try:
        cur = db.execute(
            "INSERT INTO prestations_familles(nom, icone, ordre, actif) VALUES (?,?,?,?)",
            (payload.nom, payload.icone, payload.ordre, payload.actif),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Famille existe déjà : {e}")
    return FamilleOut(id=cur.lastrowid, **payload.model_dump())


@router.patch("/familles/{fid}", response_model=OK)
def update_famille(
    fid: int,
    payload: FamilleUpdate,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        return OK()
    sets = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [fid]
    db.execute(f"UPDATE prestations_familles SET {sets} WHERE id=?", values)
    db.commit()
    return OK()


@router.delete("/familles/{fid}", response_model=OK)
def delete_famille(
    fid: int,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    db.execute("DELETE FROM prestations_familles WHERE id=?", (fid,))
    db.commit()
    return OK()


# ── Prestations ────────────────────────────────────────────────────────────
@router.get("/prestations", response_model=list[PrestationOut])
def list_prestations(
    famille_id: int | None = None,
    actif_only: bool = True,
    _: int = Depends(current_user_id),
    db: sqlite3.Connection = Depends(get_db),
):
    sql = (
        "SELECT p.id, p.famille_id, p.libelle, p.pu_ht, p.duree_min, p.actif, "
        "p.ordre, f.nom AS famille_nom "
        "FROM prestations p JOIN prestations_familles f ON p.famille_id=f.id "
    )
    where = []
    params: list = []
    if famille_id is not None:
        where.append("p.famille_id=?")
        params.append(famille_id)
    if actif_only:
        where.append("p.actif=1")
    if where:
        sql += "WHERE " + " AND ".join(where) + " "
    sql += "ORDER BY f.ordre, p.ordre, p.libelle"
    rows = db.execute(sql, params).fetchall()
    return [PrestationOut(**dict(r)) for r in rows]


@router.post("/prestations", response_model=PrestationOut)
def create_prestation(
    payload: PrestationIn,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    cur = db.execute(
        "INSERT INTO prestations(famille_id, libelle, pu_ht, duree_min, actif, ordre) "
        "VALUES (?,?,?,?,?,?)",
        (payload.famille_id, payload.libelle, payload.pu_ht,
         payload.duree_min, payload.actif, payload.ordre),
    )
    db.commit()
    return PrestationOut(id=cur.lastrowid, **payload.model_dump())


@router.patch("/prestations/{pid}", response_model=OK)
def update_prestation(
    pid: int,
    payload: PrestationUpdate,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        return OK()
    sets = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [pid]
    db.execute(f"UPDATE prestations SET {sets} WHERE id=?", values)
    db.commit()
    return OK()


@router.delete("/prestations/{pid}", response_model=OK)
def delete_prestation(
    pid: int,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    db.execute("DELETE FROM prestations WHERE id=?", (pid,))
    db.commit()
    return OK()
