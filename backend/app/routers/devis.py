"""Gestion des devis."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from ..deps import current_admin, get_db
from ..schemas.common import OK
from ..schemas.devis import (
    DevisCreated,
    DevisIn,
    DevisOut,
    DevisStatutUpdate,
    DevisUpdate,
    EnvoyerDevis,
)
from ..services import notifications
from ..services.pdf import build_devis_pdf

router = APIRouter(prefix="/api/devis", tags=["devis"])

_SELECT = (
    "SELECT d.id, d.numero, d.client_id, d.vehicule_id, d.lignes, "
    "d.total_ht, d.tva, d.total_ttc, d.statut, d.notes, d.validite, "
    "d.date_echeance, d.created_at, "
    "u.nom, u.prenom, u.email, u.telephone, "
    "v.immatriculation, v.marque, v.modele "
    "FROM devis d "
    "JOIN users u ON d.client_id=u.id "
    "LEFT JOIN vehicules v ON d.vehicule_id=v.id "
)


def _next_numero(db: sqlite3.Connection) -> str:
    now = datetime.now()
    count = db.execute("SELECT COUNT(*) AS c FROM devis").fetchone()["c"]
    return f"DEV_{now.strftime('%Y_%m')}_{count + 1:03d}"


@router.get("", response_model=list[DevisOut])
def list_devis(
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    rows = db.execute(_SELECT + "ORDER BY d.created_at DESC").fetchall()
    return [DevisOut(**dict(r)) for r in rows]


@router.post("", response_model=DevisCreated)
def create_devis(
    payload: DevisIn,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    total_ht = round(sum(l.total() for l in payload.lignes), 2)
    total_ttc = round(total_ht * (1 + payload.tva / 100), 2)
    numero = _next_numero(db)
    lignes_json = json.dumps([l.model_dump() for l in payload.lignes], ensure_ascii=False)

    cur = db.execute(
        "INSERT INTO devis(numero, client_id, vehicule_id, lignes, total_ht, "
        "tva, total_ttc, statut, notes, validite) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            numero, payload.client_id, payload.vehicule_id, lignes_json,
            total_ht, payload.tva, total_ttc, "brouillon",
            payload.notes, payload.validite,
        ),
    )
    db.commit()
    return DevisCreated(numero=numero, id=cur.lastrowid)


@router.patch("/{did}/statut", response_model=OK)
def update_statut(
    did: int,
    payload: DevisStatutUpdate,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    db.execute("UPDATE devis SET statut=? WHERE id=?", (payload.statut, did))
    db.commit()
    return OK()


@router.patch("/{did}/modifier", response_model=OK)
def update_devis(
    did: int,
    payload: DevisUpdate,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    fields = payload.model_dump(exclude_unset=True)
    if "lignes" in fields and fields["lignes"] is not None:
        lignes = payload.lignes or []
        total_ht = round(sum(l.total() for l in lignes), 2)
        tva = fields.get("tva")
        if tva is None:
            existing = db.execute("SELECT tva FROM devis WHERE id=?", (did,)).fetchone()
            tva = existing["tva"] if existing else 20.0
        total_ttc = round(total_ht * (1 + tva / 100), 2)
        fields["lignes"] = json.dumps([l.model_dump() for l in lignes], ensure_ascii=False)
        fields["total_ht"] = total_ht
        fields["total_ttc"] = total_ttc

    if not fields:
        return OK()

    sets = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [did]
    db.execute(f"UPDATE devis SET {sets} WHERE id=?", values)
    db.commit()
    return OK()


@router.post("/{did}/convertir")
def convertir_devis(
    did: int,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    dev = db.execute("SELECT * FROM devis WHERE id=?", (did,)).fetchone()
    if not dev:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Devis introuvable")

    now = datetime.now()
    count = db.execute("SELECT COUNT(*) AS c FROM factures").fetchone()["c"]
    numero = f"FAC_{now.strftime('%Y_%m')}_{count + 1:03d}"
    exp = (now + timedelta(days=30)).strftime("%Y-%m-%d")

    db.execute(
        "INSERT INTO factures(numero, devis_id, client_id, vehicule_id, lignes, "
        "total_ht, tva, total_ttc, statut, notes, date_echeance, date_facture) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            numero, dev["id"], dev["client_id"], dev["vehicule_id"], dev["lignes"],
            dev["total_ht"], dev["tva"], dev["total_ttc"],
            "impayee", dev["notes"], exp, now.strftime("%Y-%m-%d"),
        ),
    )
    db.execute("UPDATE devis SET statut='facture' WHERE id=?", (did,))
    db.commit()
    return {"ok": True, "numero": numero}


def _devis_email_html(dev: dict) -> str:
    nom = f"{dev.get('prenom','') or ''} {dev.get('nom','') or ''}".strip()
    montant = f"{(dev.get('total_ttc') or 0):.2f}".replace(".", ",")
    return f"""<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto">
<div style="background:#1e3a8a;padding:24px;border-radius:12px 12px 0 0">
<div style="font-size:18px;font-weight:900;color:#fff">GARAGE DE LA MONTAGNE</div>
<div style="font-size:10px;color:rgba(255,255,255,.7);margin-top:3px">94510 La Queue-en-Brie</div>
</div>
<div style="padding:24px;background:#fff;border:1px solid #e5e7eb">
<p>Bonjour <strong>{nom}</strong>,</p>
<p>Veuillez trouver ci-joint votre devis <strong>{dev.get('numero','')}</strong>
d'un montant de <strong>{montant} €&nbsp;TTC</strong>.</p>
<div style="background:#f3f4f6;border-radius:8px;padding:16px;margin:16px 0;font-size:13px">
<div style="display:flex;justify-content:space-between;margin-bottom:6px">
<span style="color:#6b7280">Validité</span><strong>{dev.get('validite',30)} jours</strong></div>
<div style="display:flex;justify-content:space-between;font-size:16px;font-weight:700;
margin-top:8px;padding-top:8px;border-top:2px solid #1e3a8a">
<span>Total TTC</span><span style="color:#2563eb">{montant} €</span></div>
</div>
<p>N'hésitez pas à nous contacter pour toute question.</p>
<p style="font-size:12px;color:#6b7280">Garage de la Montagne · SIRET 487 723 306 00014</p>
</div></div>"""


@router.post("/{did}/envoyer")
def envoyer_devis(
    did: int,
    payload: EnvoyerDevis,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    row = db.execute(
        "SELECT d.*, u.nom, u.prenom, u.email, u.telephone "
        "FROM devis d JOIN users u ON d.client_id=u.id WHERE d.id=?",
        (did,),
    ).fetchone()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Devis introuvable")
    dev = dict(row)

    results: dict = {}

    if payload.email:
        dest = payload.email_dest or dev.get("email") or ""
        try:
            pdf_bytes, pdf_name = build_devis_pdf(db, did)
            notifications.send_email(
                to=dest,
                subject=f"Devis {dev['numero']} — Garage de la Montagne",
                html=_devis_email_html(dev),
                attachments=[(pdf_name, pdf_bytes, "pdf")],
            )
            db.execute("UPDATE devis SET statut='envoye' WHERE id=? AND statut='brouillon'",
                       (did,))
            db.commit()
            results["email"] = {"ok": True}
        except Exception as e:
            results["email"] = {"ok": False, "error": str(e)}

    if payload.sms:
        tel = payload.telephone or dev.get("telephone") or ""
        montant = f"{(dev.get('total_ttc') or 0):.2f}".replace(".", ",")
        msg = f"Garage Montagne: Devis {dev['numero']} - {montant}EUR. Voir email."
        try:
            notifications.send_sms(tel, msg)
            results["sms"] = {"ok": True}
        except Exception as e:
            results["sms"] = {"ok": False, "error": str(e)}

    return {"ok": True, "results": results, "payment_url": ""}


@router.get("/{did}/pdf")
def telecharger_pdf(
    did: int,
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    try:
        pdf_bytes, filename = build_devis_pdf(db, did)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
