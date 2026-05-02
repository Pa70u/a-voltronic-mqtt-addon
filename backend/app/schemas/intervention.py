"""Schémas interventions."""
from __future__ import annotations

from pydantic import Field

from .common import APIModel


class InterventionIn(APIModel):
    vehicule_id: int | None = None
    client_id: int
    date_entree: str | None = None
    description: str | None = None
    statut: str = Field(default="en_cours")
    montant_ht: float = 0
    montant_ttc: float = 0
    technicien: str | None = None


class InterventionStatutUpdate(APIModel):
    statut: str = Field(min_length=1, max_length=30)


class InterventionOut(APIModel):
    id: int
    vehicule_id: int | None = None
    client_id: int
    date_entree: str | None = None
    description: str | None = None
    statut: str = "en_cours"
    montant_ht: float = 0
    montant_ttc: float = 0
    technicien: str | None = None
    created_at: str | None = None
    nom: str | None = None
    prenom: str | None = None
    immatriculation: str | None = None
    marque: str | None = None
    modele: str | None = None
