"""Schémas devis & factures (lignes communes)."""
from __future__ import annotations

from pydantic import Field

from .common import APIModel


class LigneDevis(APIModel):
    desc: str
    qte: float = 1.0
    pu_ht: float = 0
    total_ht: float | None = None  # calculé si absent

    def total(self) -> float:
        if self.total_ht is not None:
            return self.total_ht
        return round(self.qte * self.pu_ht, 2)


class DevisIn(APIModel):
    client_id: int
    vehicule_id: int | None = None
    lignes: list[LigneDevis] = Field(default_factory=list)
    tva: float = Field(default=20.0, ge=0, le=100)
    notes: str | None = None
    validite: int = Field(default=30, ge=1, le=365)


class DevisUpdate(APIModel):
    vehicule_id: int | None = None
    lignes: list[LigneDevis] | None = None
    tva: float | None = Field(default=None, ge=0, le=100)
    notes: str | None = None
    validite: int | None = Field(default=None, ge=1, le=365)
    statut: str | None = None


class DevisStatutUpdate(APIModel):
    statut: str = Field(min_length=1, max_length=30)


class DevisOut(APIModel):
    id: int
    numero: str
    client_id: int
    vehicule_id: int | None = None
    lignes: str | None = None  # JSON brut
    total_ht: float | None = 0
    tva: float | None = 20.0
    total_ttc: float | None = 0
    statut: str = "brouillon"
    notes: str | None = None
    validite: int | None = 30
    date_echeance: str | None = None
    created_at: str | None = None
    nom: str | None = None
    prenom: str | None = None
    email: str | None = None
    telephone: str | None = None
    immatriculation: str | None = None
    marque: str | None = None
    modele: str | None = None


class DevisCreated(APIModel):
    ok: bool = True
    numero: str
    id: int


class EnvoyerDevis(APIModel):
    email: bool = False
    sms: bool = False
    stripe: bool = False
    email_dest: str | None = None
    telephone: str | None = None
