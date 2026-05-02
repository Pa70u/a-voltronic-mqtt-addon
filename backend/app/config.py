"""Configuration de l'application — lue depuis variables d'environnement."""
from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "GarageOS"
    db_path: str = Field(default="/app/data/garage.db", alias="GARAGE_DB")

    # Sécurité
    cors_origins: str = Field(
        default="https://garagedelamontagne.fr,https://www.garagedelamontagne.fr",
        alias="CORS_ORIGINS",
    )
    token_lifetime_days: int = 7

    # Email (Gmail)
    gmail_user: str = Field(default="", alias="GMAIL_USER")
    gmail_password: str = Field(default="", alias="GMAIL_PASSWORD")

    # SMS (Brevo)
    brevo_api_key: str = Field(default="", alias="BREVO_API_KEY")
    brevo_sms_from: str = Field(default="GarageMtgn", alias="BREVO_SMS_FROM")

    # Paiements (Stripe)
    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
