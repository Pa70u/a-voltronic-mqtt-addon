"""Endpoints d'authentification."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import current_user_id, get_db
from ..schemas.auth import LoginIn, LoginOut, UserOut
from ..security import (
    create_token,
    hash_password,
    needs_rehash,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginOut)
def login(payload: LoginIn, db: sqlite3.Connection = Depends(get_db)):
    user = db.execute(
        "SELECT id, nom, prenom, email, password_hash, role FROM users WHERE email=?",
        (payload.email,),
    ).fetchone()
    if not user or not verify_password(payload.password, user["password_hash"] or ""):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants incorrects")

    # Migration transparente SHA-256 → bcrypt
    if needs_rehash(user["password_hash"] or ""):
        new_hash = hash_password(payload.password)
        db.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, user["id"]))
        db.commit()

    token = create_token(db, user["id"])
    return LoginOut(
        token=token,
        id=user["id"],
        nom=user["nom"],
        prenom=user["prenom"],
        email=user["email"],
        role=user["role"] or "client",
    )


@router.get("/me", response_model=UserOut)
def me(user_id: int = Depends(current_user_id), db: sqlite3.Connection = Depends(get_db)):
    row = db.execute(
        "SELECT id, nom, prenom, email, role, telephone, adresse, code_client, "
        "pref_relance_email, pref_relance_sms FROM users WHERE id=?",
        (user_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Utilisateur introuvable")
    return UserOut(**dict(row))
