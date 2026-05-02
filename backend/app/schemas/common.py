"""Schémas Pydantic partagés."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")


class OK(APIModel):
    ok: bool = True


class OKMessage(APIModel):
    ok: bool = True
    message: str | None = None
