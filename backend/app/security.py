"""Hachage de mots de passe + tokens.

Stratégie de migration : on accepte SHA-256 (legacy) ET bcrypt (cible).
Quand un user se connecte avec un mot de passe encore haché en SHA-256,
on le re-hashe en bcrypt automatiquement → migration transparente.
"""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta

import bcrypt

from .config import get_settings


def _is_bcrypt(hashed: str) -> bool:
    return bool(hashed) and hashed.startswith(("$2a$", "$2b$", "$2y$"))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    if _is_bcrypt(hashed):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except ValueError:
            return False
    # Fallback SHA-256 legacy (sans sel) — accepté pendant la migration
    legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return secrets.compare_digest(legacy, hashed)


def needs_rehash(hashed: str) -> bool:
    """True si le hash est en SHA-256 (à upgrader)."""
    return bool(hashed) and not _is_bcrypt(hashed)


def create_token(conn: sqlite3.Connection, user_id: int) -> str:
    settings = get_settings()
    token = secrets.token_hex(32)
    exp = (datetime.now() + timedelta(days=settings.token_lifetime_days)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    conn.execute(
        "INSERT INTO tokens(token, user_id, expires_at) VALUES (?,?,?)",
        (token, user_id, exp),
    )
    conn.commit()
    return token


def revoke_token(conn: sqlite3.Connection, token: str) -> None:
    conn.execute("DELETE FROM tokens WHERE token=?", (token,))
    conn.commit()


def cleanup_expired_tokens(conn: sqlite3.Connection) -> int:
    cur = conn.execute("DELETE FROM tokens WHERE expires_at <= datetime('now')")
    conn.commit()
    return cur.rowcount
