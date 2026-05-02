"""Dépendances FastAPI partagées (auth, accès BDD)."""
from __future__ import annotations

import sqlite3
from typing import Generator

from fastapi import Depends, HTTPException, Request, status

from .database import connect


def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def _extract_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token manquant")
    return auth[len("Bearer "):].strip()


def current_user_id(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
) -> int:
    token = _extract_token(request)
    row = db.execute(
        "SELECT user_id FROM tokens WHERE token=? AND expires_at > datetime('now')",
        (token,),
    ).fetchone()
    if not row:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalide ou expiré")
    return row["user_id"]


def current_admin(
    user_id: int = Depends(current_user_id),
    db: sqlite3.Connection = Depends(get_db),
) -> int:
    row = db.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
    if not row or row["role"] != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès admin requis")
    return user_id
