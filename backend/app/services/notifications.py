"""Service d'envoi email + SMS + création de lien Stripe.

Implémentation minimale au jalon 3 (extrait du legacy main.py).
Sera enrichi au jalon 4 avec génération PDF + templates HTML.
"""
from __future__ import annotations

import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Sequence

import requests as http

from ..config import get_settings


def normalize_phone_fr(tel: str) -> str:
    """0612345678 → +33612345678 ; +33612345678 → inchangé."""
    n = (tel or "").strip().replace(" ", "").replace(".", "").replace("-", "")
    if n.startswith("0"):
        n = "+33" + n[1:]
    return n


# ── Stripe ─────────────────────────────────────────────────────────────────
def create_payment_link(amount_cents: int, label: str, metadata: dict) -> str:
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY non configuré")

    import stripe
    stripe.api_key = settings.stripe_secret_key
    price = stripe.Price.create(
        unit_amount=amount_cents,
        currency="eur",
        product_data={"name": label},
    )
    link = stripe.PaymentLink.create(
        line_items=[{"price": price.id, "quantity": 1}],
        metadata=metadata,
    )
    return link.url


# ── Email ──────────────────────────────────────────────────────────────────
def send_email(
    to: str,
    subject: str,
    html: str,
    attachments: Sequence[tuple[str, bytes, str]] | None = None,
) -> None:
    """Envoie un email HTML.

    `attachments` = liste de (filename, data_bytes, mime_subtype) — ex:
    `[("facture_FAC_2026_05_001.pdf", pdf_bytes, "pdf")]`.
    """
    settings = get_settings()
    if not (settings.gmail_user and settings.gmail_password):
        raise RuntimeError("GMAIL_USER / GMAIL_PASSWORD non configurés")
    if not to:
        raise RuntimeError("Destinataire vide")

    if attachments:
        msg = MIMEMultipart("mixed")
        body = MIMEMultipart("alternative")
        body.attach(MIMEText(html, "html", "utf-8"))
        msg.attach(body)
        for filename, data, subtype in attachments:
            part = MIMEApplication(data, _subtype=subtype)
            part.add_header("Content-Disposition", "attachment", filename=filename)
            msg.attach(part)
    else:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(html, "html", "utf-8"))

    msg["Subject"] = subject
    msg["From"] = f"Garage de la Montagne <{settings.gmail_user}>"
    msg["To"] = to

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as srv:
        srv.login(settings.gmail_user, settings.gmail_password)
        srv.sendmail(settings.gmail_user, to, msg.as_string())


# ── SMS Brevo ──────────────────────────────────────────────────────────────
def send_sms(to: str, content: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.brevo_api_key:
        raise RuntimeError("BREVO_API_KEY non configuré")
    if not to:
        raise RuntimeError("Téléphone vide")

    r = http.post(
        "https://api.brevo.com/v3/transactionalSMS/sms",
        headers={"api-key": settings.brevo_api_key, "Content-Type": "application/json"},
        json={
            "sender": settings.brevo_sms_from,
            "recipient": normalize_phone_fr(to),
            "content": content[:160],
        },
        timeout=10,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Brevo a renvoyé {r.status_code}: {r.text[:200]}")
    return r.json() if r.text else {}
