"""Schémas parking (abonnements + emplacements + paiements)."""
from __future__ import annotations

from pydantic import Field

from .common import APIModel


class EmplacementIn(APIModel):
    numero: str = Field(min_length=1, max_length=20)
    statut: str = Field(default="libre")
    etage: int = Field(default=0)
    prix_mensuel: float = Field(default=80.0, ge=0)
    prix_journalier: float = Field(default=5.0, ge=0)


class EmplacementStatutUpdate(APIModel):
    statut: str = Field(min_length=1, max_length=20)


class EmplacementRenameIn(APIModel):
    numero: str = Field(min_length=1, max_length=20)


class EmplacementOut(APIModel):
    id: int
    numero: str
    statut: str = "libre"
    etage: int = 0
    prix_mensuel: float = 80.0
    prix_journalier: float = 5.0


class AbonnementIn(APIModel):
    client_id: int
    emplacement_id: int
    date_debut: str
    date_fin: str | None = None
    montant: float = Field(ge=0)
    statut: str = "actif"


class AbonnementStatutUpdate(APIModel):
    statut: str = Field(min_length=1, max_length=30)


class AbonnementOut(APIModel):
    id: int
    client_id: int
    emplacement_id: int
    date_debut: str | None = None
    date_fin: str | None = None
    date_engagement_fin: str | None = None
    montant: float | None = 0
    statut: str = "actif"
    created_at: str | None = None
    stripe_payment_url: str | None = None
    derniere_relance: str | None = None
    nom: str | None = None
    prenom: str | None = None
    email: str | None = None
    telephone: str | None = None
    emplacement_numero: str | None = None
    etage: int | None = None


class EnvoyerAbonnement(APIModel):
    email: bool = False
    sms: bool = False
    stripe: bool = False


class PaiementSimuler(APIModel):
    type: str = "abonnement"
    montant: float = 0
    methode: str = "cb"
