"""Gestion des factures + envoi email/SMS/Stripe."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..deps import current_admin, get_db
from ..schemas.common import OK
from ..schemas.facture import (
    EnvoyerFacture,
    FactureCreated,
    FactureIn,
    FactureOut,
    FactureStatutUpdate,
)
from ..services import notifications

router = APIRouter(prefix="/api/factures", tags=["factures"])

_SELECT = (
    "SELECT f.id, f.numero, f.devis_id, f.client_id, f.vehicule_id, f.lignes, "
    "f.total_ht, f.tva, f.total_ttc, f.statut, f.notes, f.date_facture, "
    "f.date_echeance, f.methode_reglement, f.date_reglement, f.reference, "
    "f.stripe_payment_url, f.derniere_relance, f.created_at, "
    "u.nom, u.prenom, u.email, u.telephone, u.adresse, "
    "v.immatriculation, v.marque, v.modele "
    "FROM factures f "
    "JOIN users u ON f.client_id=u.id "
    "LEFT JOIN vehicules v ON f.vehicule_id=v.id "
)


def _next_numero(db: sqlite3.Connection) -> str:
    now = datetime.now()
    count = db.execute("SELECT COUNT(*) AS c FROM factures").fetchone()["c"]
    return f"FAC_{now.strftime('%Y_%m')}_{count + 1:03d}"


@router.get("", response_model=list[FactureOut])
def list_factures(
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    rows = db.execute(_SELECT + "ORDER BY f.created_at DESC").fetchall()
    return [FactureOut(**dict(r)) for r in rows]


@router.post("/nouvelle", response_model=FactureCreated)
def create_facture(
    payload: FactureIn,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    total_ht = round(sum(l.total() for l in payload.lignes), 2)
    total_ttc = round(total_ht * (1 + payload.tva / 100), 2)
    numero = _next_numero(db)
    now = datetime.now()
    exp = payload.date_echeance or (now + timedelta(days=30)).strftime("%Y-%m-%d")
    lignes_json = json.dumps([l.model_dump() for l in payload.lignes], ensure_ascii=False)

    cur = db.execute(
        "INSERT INTO factures(numero, client_id, vehicule_id, lignes, total_ht, "
        "tva, total_ttc, statut, notes, date_echeance, date_facture) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            numero, payload.client_id, payload.vehicule_id, lignes_json,
            total_ht, payload.tva, total_ttc, "impayee",
            payload.notes, exp, now.strftime("%Y-%m-%d"),
        ),
    )
    db.commit()
    return FactureCreated(id=cur.lastrowid, numero=numero)


@router.patch("/{fid}/statut", response_model=OK)
def update_statut(
    fid: int,
    payload: FactureStatutUpdate,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    db.execute(
        "UPDATE factures SET statut=?, methode_reglement=?, date_reglement=?, "
        "reference=? WHERE id=?",
        (
            payload.statut,
            payload.methode_reglement or "",
            payload.date_reglement or "",
            payload.reference or "",
            fid,
        ),
    )
    db.commit()
    return OK()


def _format_montant(v: float) -> str:
    return f"{v:.2f}".replace(".", ",")


def _email_html(fac: dict, payment_url: str = "") -> str:
    montant = _format_montant(fac.get("total_ttc") or 0)
    bouton = (
        f'<div style="text-align:center;margin:24px 0">'
        f'<a href="{payment_url}" style="background:#2563eb;color:#fff;padding:12px 28px;'
        f'border-radius:8px;text-decoration:none;font-weight:700;font-size:15px">'
        f'💳 Payer {montant} € en ligne</a></div>'
        if payment_url else ""
    )
    return f"""<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto">
<div style="background:#1e3a8a;padding:24px;border-radius:12px 12px 0 0">
<div style="font-size:18px;font-weight:900;color:#fff">GARAGE DE LA MONTAGNE</div>
<div style="font-size:10px;color:rgba(255,255,255,.7);margin-top:3px">94510 La Queue-en-Brie</div>
</div>
<div style="padding:24px;background:#fff;border:1px solid #e5e7eb">
<p>Bonjour <strong>{fac.get('prenom','')} {fac.get('nom','')}</strong>,</p>
<p>Votre facture <strong>{fac.get('numero','')}</strong> d'un montant de
<strong>{montant} €</strong> est disponible.</p>
<div style="background:#f3f4f6;border-radius:8px;padding:16px;margin:16px 0;font-size:13px">
<div style="display:flex;justify-content:space-between;margin-bottom:6px">
<span style="color:#6b7280">Numéro</span><strong>{fac.get('numero','')}</strong></div>
<div style="display:flex;justify-content:space-between;margin-bottom:6px">
<span style="color:#6b7280">Véhicule</span><span>{fac.get('immatriculation','—')}</span></div>
<div style="display:flex;justify-content:space-between;font-size:16px;font-weight:700;
margin-top:8px;padding-top:8px;border-top:2px solid #1e3a8a">
<span>Total TTC</span><span style="color:#2563eb">{montant} €</span></div>
</div>{bouton}
<p style="font-size:12px;color:#6b7280">Garage de la Montagne · SIRET 487 723 306 00014</p>
</div></div>"""


@router.post("/{fid}/envoyer")
def envoyer_facture(
    fid: int,
    payload: EnvoyerFacture,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    row = db.execute(_SELECT + "WHERE f.id=?", (fid,)).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Facture introuvable")
    fac = dict(row)

    results: dict[str, Any] = {}
    payment_url = ""

    # Stripe
    if payload.stripe:
        try:
            payment_url = notifications.create_payment_link(
                amount_cents=int((fac.get("total_ttc") or 0) * 100),
                label=f"Facture {fac['numero']}",
                metadata={"facture_id": str(fid)},
            )
            db.execute(
                "UPDATE factures SET stripe_payment_url=? WHERE id=?",
                (payment_url, fid),
            )
            db.commit()
            results["stripe"] = {"ok": True, "url": payment_url}
        except Exception as e:
            results["stripe"] = {"ok": False, "error": str(e)}

    # Email
    if payload.email:
        dest = payload.email_dest or fac.get("email") or ""
        try:
            notifications.send_email(
                to=dest,
                subject=f"Facture {fac['numero']} — Garage de la Montagne",
                html=_email_html(fac, payment_url),
            )
            results["email"] = {"ok": True}
        except Exception as e:
            results["email"] = {"ok": False, "error": str(e)}

    # SMS
    if payload.sms:
        tel = payload.telephone or fac.get("telephone") or ""
        montant = _format_montant(fac.get("total_ttc") or 0)
        msg = f"Garage Montagne: Facture {fac['numero']} - {montant}EUR"
        if payment_url:
            msg += f" Payer: {payment_url}"
        try:
            notifications.send_sms(tel, msg)
            results["sms"] = {"ok": True}
        except Exception as e:
            results["sms"] = {"ok": False, "error": str(e)}

    return {"ok": True, "results": results, "payment_url": payment_url}
