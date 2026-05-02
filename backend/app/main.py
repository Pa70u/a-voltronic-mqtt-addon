"""Point d'entrée FastAPI — monte les routers et applique le schéma au démarrage."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import connect, init_db
from .routers import (
    abonnements,
    auth,
    catalogue,
    clients,
    dashboard,
    devis,
    emplacements,
    factures,
    interventions,
    paiements,
    stripe_webhook,
    vehicules,
)
from .security import cleanup_expired_tokens


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Nettoyage des tokens expirés au démarrage
    conn = connect()
    try:
        cleanup_expired_tokens(conn)
    finally:
        conn.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=f"{settings.app_name} API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(clients.router)
    app.include_router(vehicules.router)
    app.include_router(interventions.router)
    app.include_router(devis.router)
    app.include_router(factures.router)
    app.include_router(abonnements.router)
    app.include_router(emplacements.router)
    app.include_router(paiements.router)
    app.include_router(catalogue.router)
    app.include_router(stripe_webhook.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
