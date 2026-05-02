"""Gestion des clients (admins uniquement)."""
from __future__ import annotations

import secrets
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import current_admin, get_db
from ..schemas.client import ClientCreated, ClientIn, ClientOut, ClientUpdate
from ..schemas.common import OK
from ..security import hash_password

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("", response_model=list[ClientOut])
def list_clients(_: int = Depends(current_admin), db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute(
        "SELECT id, nom, prenom, email, telephone, adresse, code_client, role, "
        "created_at, pref_relance_email, pref_relance_sms "
        "FROM users WHERE role='client' ORDER BY nom, prenom"
    ).fetchall()
    return [ClientOut(**dict(r)) for r in rows]


def _next_client_code(db: sqlite3.Connection) -> str:
    last = db.execute(
        "SELECT code_client FROM users WHERE code_client IS NOT NULL "
        "ORDER BY code_client DESC LIMIT 1"
    ).fetchone()
    try:
        n = int((last["code_client"] or "CL0000").replace("CL", "")) + 1
    except (TypeError, ValueError):
        n = 1000
    return f"CL{n:04d}"


@router.post("/nouveau", response_model=ClientCreated)
def create_client(
    payload: ClientIn,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    code = _next_client_code(db)
    email = str(payload.email) if payload.email else f"{code}@garage.fr"
    # Mot de passe aléatoire haché en bcrypt — l'utilisateur fera un reset au 1er login
    pw = hash_password(secrets.token_hex(16))

    try:
        cur = db.execute(
            "INSERT INTO users(nom, prenom, email, password_hash, role, telephone, "
            "adresse, code_client, pref_relance_email, pref_relance_sms) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                payload.nom,
                payload.prenom or "",
                email,
                pw,
                "client",
                payload.telephone or "",
                payload.adresse or "",
                code,
                1, 1,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Email déjà utilisé : {e}")

    return ClientCreated(id=cur.lastrowid, code=code)


@router.patch("/{cid}", response_model=OK)
def update_client(
    cid: int,
    payload: ClientUpdate,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        return OK()
    sets = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [cid]
    db.execute(f"UPDATE users SET {sets} WHERE id=?", values)
    db.commit()
    return OK()
