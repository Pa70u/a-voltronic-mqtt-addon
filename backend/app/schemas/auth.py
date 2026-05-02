"""Schémas Pydantic pour l'authentification."""
from __future__ import annotations

from pydantic import EmailStr, Field

from .common import APIModel


class LoginIn(APIModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class LoginOut(APIModel):
    token: str
    id: int
    nom: str | None = None
    prenom: str | None = None
    email: str
    role: str


class UserOut(APIModel):
    id: int
    nom: str | None = None
    prenom: str | None = None
    email: str | None = None
    role: str
    telephone: str | None = None
    adresse: str | None = None
    code_client: str | None = None
    pref_relance_email: int = 1
    pref_relance_sms: int = 1
