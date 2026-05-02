"""Gestion des abonnements parking (avec engagement 6 mois)."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import current_admin, current_user_id, get_db
from ..schemas.common import OK
from ..schemas.parking import (
    AbonnementIn,
    AbonnementOut,
    AbonnementStatutUpdate,
    EnvoyerAbonnement,
)
from ..services import notifications

router = APIRouter(prefix="/api/abonnements", tags=["abonnements"])

_SELECT = (
    "SELECT a.id, a.client_id, a.emplacement_id, a.date_debut, a.date_fin, "
    "a.date_engagement_fin, a.montant, a.statut, a.created_at, "
    "a.stripe_payment_url, a.derniere_relance, "
    "u.nom, u.prenom, u.email, u.telephone, "
    "e.numero AS emplacement_numero, e.etage "
    "FROM abonnements a "
    "JOIN users u ON a.client_id=u.id "
    "JOIN emplacements e ON a.emplacement_id=e.id "
)


def _add_six_months(date_str: str) -> str:
    try:
        d = datetime.fromisoformat(date_str.split(" ")[0])
    except ValueError:
        return ""
    return (d + timedelta(days=180)).strftime("%Y-%m-%d")


@router.get("", response_model=list[AbonnementOut])
def list_abonnements(
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    rows = db.execute(_SELECT + "ORDER BY a.created_at DESC").fetchall()
    return [AbonnementOut(**dict(r)) for r in rows]


@router.get("/miens", response_model=list[AbonnementOut])
def my_abonnements(
    user_id: int = Depends(current_user_id),
    db: sqlite3.Connection = Depends(get_db),
):
    rows = db.execute(
        _SELECT + "WHERE a.client_id=? ORDER BY a.created_at DESC",
        (user_id,),
    ).fetchall()
    return [AbonnementOut(**dict(r)) for r in rows]


@router.post("/nouveau", response_model=OK)
def create_abonnement(
    payload: AbonnementIn,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    engagement_fin = _add_six_months(payload.date_debut) or None
    db.execute(
        "INSERT INTO abonnements(client_id, emplacement_id, date_debut, date_fin, "
        "date_engagement_fin, montant, statut) VALUES (?,?,?,?,?,?,?)",
        (
            payload.client_id, payload.emplacement_id, payload.date_debut,
            payload.date_fin, engagement_fin, payload.montant, payload.statut,
        ),
    )
    db.execute(
        "UPDATE emplacements SET statut='occupe' WHERE id=?",
        (payload.emplacement_id,),
    )
    db.commit()
    return OK()


@router.patch("/{aid}/statut", response_model=OK)
def update_statut(
    aid: int,
    payload: AbonnementStatutUpdate,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    # Si résiliation : vérifier engagement 6 mois
    if payload.statut == "resilie":
        row = db.execute(
            "SELECT date_engagement_fin FROM abonnements WHERE id=?", (aid,)
        ).fetchone()
        if row and row["date_engagement_fin"]:
            today = datetime.now().strftime("%Y-%m-%d")
            if today < row["date_engagement_fin"]:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Résiliation impossible avant {row['date_engagement_fin']} "
                    f"(engagement minimum 6 mois)",
                )

    db.execute("UPDATE abonnements SET statut=? WHERE id=?", (payload.statut, aid))
    db.commit()
    return OK()


@router.post("/{aid}/envoyer")
def envoyer_abonnement(
    aid: int,
    payload: EnvoyerAbonnement,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    row = db.execute(_SELECT + "WHERE a.id=?", (aid,)).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Abonnement introuvable")
    abon = dict(row)

    results: dict[str, Any] = {}
    payment_url = ""

    if payload.stripe:
        try:
            payment_url = notifications.create_payment_link(
                amount_cents=int((abon.get("montant") or 0) * 100),
                label=f"Abonnement parking P{abon.get('emplacement_numero','')}",
                metadata={"abonnement_id": str(aid)},
            )
            results["stripe"] = {"ok": True, "url": payment_url}
        except Exception as e:
            results["stripe"] = {"ok": False, "error": str(e)}

    if payload.email and abon.get("email"):
        try:
            montant = f"{abon.get('montant',0):.2f}".replace(".", ",")
            bouton = (
                f'<div style="text-align:center;margin:24px 0">'
                f'<a href="{payment_url}" style="background:#2563eb;color:#fff;'
                f'padding:12px 28px;border-radius:8px;text-decoration:none;'
                f'font-weight:700">💳 Régler {montant} € en ligne</a></div>'
                if payment_url else ""
            )
            html = f"""<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto">
<div style="background:#1e3a8a;padding:24px;border-radius:12px 12px 0 0">
<div style="font-size:18px;font-weight:900;color:#fff">🅿 ABONNEMENT PARKING</div>
<div style="font-size:10px;color:rgba(255,255,255,.7)">Garage de la Montagne — 94510 La Queue-en-Brie</div>
</div>
<div style="padding:24px;background:#fff;border:1px solid #e5e7eb">
<p>Bonjour <strong>{abon.get('prenom','')} {abon.get('nom','')}</strong>,</p>
<p>Rappel de votre abonnement parking — Place
<strong>{abon.get('emplacement_numero','')}</strong>.</p>
<div style="background:#f3f4f6;border-radius:8px;padding:16px;margin:16px 0">
<div style="display:flex;justify-content:space-between;font-size:18px;font-weight:700">
<span>Mensualité</span><span style="color:#2563eb">{montant} €</span></div>
</div>{bouton}
</div></div>"""
            notifications.send_email(
                to=abon["email"],
                subject="Abonnement parking — Garage de la Montagne",
                html=html,
            )
            results["email"] = {"ok": True}
        except Exception as e:
            results["email"] = {"ok": False, "error": str(e)}

    return {"ok": True, "results": results, "payment_url": payment_url}
