"""Schémas catalogue de prestations."""
from __future__ import annotations

from pydantic import Field

from .common import APIModel


class FamilleIn(APIModel):
    nom: str = Field(min_length=1, max_length=100)
    icone: str | None = Field(default=None, max_length=10)
    ordre: int = 0
    actif: int = Field(default=1, ge=0, le=1)


class FamilleUpdate(APIModel):
    nom: str | None = Field(default=None, max_length=100)
    icone: str | None = Field(default=None, max_length=10)
    ordre: int | None = None
    actif: int | None = Field(default=None, ge=0, le=1)


class FamilleOut(APIModel):
    id: int
    nom: str
    icone: str | None = None
    ordre: int = 0
    actif: int = 1


class PrestationIn(APIModel):
    famille_id: int
    libelle: str = Field(min_length=1, max_length=200)
    pu_ht: float = Field(ge=0)
    duree_min: int = Field(default=0, ge=0)
    actif: int = Field(default=1, ge=0, le=1)
    ordre: int = 0


class PrestationUpdate(APIModel):
    famille_id: int | None = None
    libelle: str | None = Field(default=None, max_length=200)
    pu_ht: float | None = Field(default=None, ge=0)
    duree_min: int | None = Field(default=None, ge=0)
    actif: int | None = Field(default=None, ge=0, le=1)
    ordre: int | None = None


class PrestationOut(APIModel):
    id: int
    famille_id: int
    libelle: str
    pu_ht: float = 0
    duree_min: int = 0
    actif: int = 1
    ordre: int = 0
    famille_nom: str | None = None


class CatalogueResponse(APIModel):
    """Format de réponse pour la vue 2 colonnes (familles + prestations)."""
    familles: list[FamilleOut]
    prestations: list[PrestationOut]
