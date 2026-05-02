"""Schémas factures."""
from __future__ import annotations

from pydantic import Field

from .common import APIModel
from .devis import LigneDevis


class FactureIn(APIModel):
    client_id: int
    vehicule_id: int | None = None
    lignes: list[LigneDevis] = Field(default_factory=list)
    tva: float = Field(default=20.0, ge=0, le=100)
    notes: str | None = None
    date_echeance: str | None = None


class FactureStatutUpdate(APIModel):
    statut: str = Field(min_length=1, max_length=30)
    methode_reglement: str | None = None
    date_reglement: str | None = None
    reference: str | None = None


class FactureOut(APIModel):
    id: int
    numero: str
    devis_id: int | None = None
    client_id: int
    vehicule_id: int | None = None
    lignes: str | None = None
    total_ht: float | None = 0
    tva: float | None = 20.0
    total_ttc: float | None = 0
    statut: str = "impayee"
    notes: str | None = None
    date_facture: str | None = None
    date_echeance: str | None = None
    methode_reglement: str | None = None
    date_reglement: str | None = None
    reference: str | None = None
    stripe_payment_url: str | None = None
    derniere_relance: str | None = None
    created_at: str | None = None
    nom: str | None = None
    prenom: str | None = None
    email: str | None = None
    telephone: str | None = None
    adresse: str | None = None
    immatriculation: str | None = None
    marque: str | None = None
    modele: str | None = None


class FactureCreated(APIModel):
    ok: bool = True
    id: int
    numero: str


class EnvoyerFacture(APIModel):
    email: bool = False
    sms: bool = False
    stripe: bool = False
    email_dest: str | None = None
    telephone: str | None = None
