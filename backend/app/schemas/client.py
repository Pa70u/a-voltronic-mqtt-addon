"""Schémas Pydantic clients."""
from __future__ import annotations

from pydantic import EmailStr, Field

from .common import APIModel


class ClientIn(APIModel):
    nom: str = Field(min_length=1, max_length=100)
    prenom: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    telephone: str | None = Field(default=None, max_length=30)
    adresse: str | None = Field(default=None, max_length=300)


class ClientUpdate(APIModel):
    nom: str | None = Field(default=None, max_length=100)
    prenom: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    telephone: str | None = Field(default=None, max_length=30)
    adresse: str | None = Field(default=None, max_length=300)
    pref_relance_email: int | None = Field(default=None, ge=0, le=1)
    pref_relance_sms: int | None = Field(default=None, ge=0, le=1)


class ClientOut(APIModel):
    id: int
    nom: str | None = None
    prenom: str | None = None
    email: str | None = None
    telephone: str | None = None
    adresse: str | None = None
    code_client: str | None = None
    role: str = "client"
    created_at: str | None = None
    pref_relance_email: int = 1
    pref_relance_sms: int = 1


class ClientCreated(APIModel):
    ok: bool = True
    id: int
    code: str
