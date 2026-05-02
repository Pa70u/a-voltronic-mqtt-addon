"""Webhook Stripe — vérifie la signature et applique les statuts de paiement."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from ..config import get_settings
from ..deps import get_db

router = APIRouter(prefix="/api/stripe", tags=["stripe"])


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: sqlite3.Connection = Depends(get_db),
):
    settings = get_settings()
    payload = await request.body()

    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "STRIPE_WEBHOOK_SECRET non configuré",
        )
    if not stripe_signature:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Signature Stripe manquante")

    import stripe
    stripe.api_key = settings.stripe_secret_key

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.stripe_webhook_secret,
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Signature invalide")
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payload invalide")

    event_type = event.get("type", "")
    obj = event.get("data", {}).get("object", {}) or {}
    metadata = obj.get("metadata", {}) or {}

    # Marque les factures payées
    if event_type in ("payment_intent.succeeded", "checkout.session.completed"):
        fid = metadata.get("facture_id")
        if fid:
            db.execute(
                "UPDATE factures SET statut='payee', date_reglement=date('now'), "
                "methode_reglement='stripe' WHERE id=?",
                (fid,),
            )
            db.commit()
        aid = metadata.get("abonnement_id")
        if aid:
            db.execute(
                "INSERT INTO paiements(client_id, type, montant, methode, statut) "
                "SELECT client_id, 'abonnement', montant, 'stripe', 'paye' "
                "FROM abonnements WHERE id=?",
                (aid,),
            )
            db.commit()

    return {"received": True}
