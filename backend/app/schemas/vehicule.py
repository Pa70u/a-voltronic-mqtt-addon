"""Schémas Pydantic véhicules."""
from __future__ import annotations

from pydantic import Field

from .common import APIModel


class VehiculeIn(APIModel):
    client_id: int
    immatriculation: str | None = Field(default=None, max_length=20)
    marque: str | None = Field(default=None, max_length=50)
    modele: str | None = Field(default=None, max_length=50)
    annee: int | None = Field(default=None, ge=1900, le=2100)
    kilometrage: int | None = Field(default=None, ge=0)
    vin: str | None = Field(default=None, max_length=30)
    type_vehicule: str = Field(default="Voiture", max_length=30)
    date_dernier_ct: str | None = None  # YYYY-MM-DD
    date_prochain_ct: str | None = None


class VehiculeUpdate(APIModel):
    immatriculation: str | None = Field(default=None, max_length=20)
    marque: str | None = Field(default=None, max_length=50)
    modele: str | None = Field(default=None, max_length=50)
    annee: int | None = Field(default=None, ge=1900, le=2100)
    kilometrage: int | None = Field(default=None, ge=0)
    vin: str | None = Field(default=None, max_length=30)
    type_vehicule: str | None = Field(default=None, max_length=30)
    date_dernier_ct: str | None = None
    date_prochain_ct: str | None = None


class VehiculeOut(APIModel):
    id: int
    client_id: int
    immatriculation: str | None = None
    marque: str | None = None
    modele: str | None = None
    annee: int | None = None
    kilometrage: int | None = None
    kilometrage_date: str | None = None
    vin: str | None = None
    type_vehicule: str | None = None
    date_dernier_ct: str | None = None
    date_prochain_ct: str | None = None
    created_at: str | None = None
    # Champs joints depuis users
    nom: str | None = None
    prenom: str | None = None
    email: str | None = None
    telephone: str | None = None


class KilometrageUpdate(APIModel):
    """Mise à jour du km depuis la popup d'ouverture devis/facture."""
    kilometrage: int = Field(ge=0)
