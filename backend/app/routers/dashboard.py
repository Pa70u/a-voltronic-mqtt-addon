"""Statistiques du tableau de bord admin."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from ..deps import current_admin, get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def stats(
    _: int = Depends(current_admin),
    db: sqlite3.Connection = Depends(get_db),
):
    emp = db.execute(
        "SELECT COUNT(*) AS total, "
        "SUM(CASE WHEN statut='libre' THEN 1 ELSE 0 END) AS libres, "
        "SUM(CASE WHEN statut IN ('occupe','occupé') THEN 1 ELSE 0 END) AS occupes "
        "FROM emplacements"
    ).fetchone()
    total = emp["total"] or 0
    occupes = emp["occupes"] or 0
    return {
        "emplacements_total": total,
        "emplacements_libres": emp["libres"] or 0,
        "emplacements_occupes": occupes,
        "taux_occupation": round(occupes / total * 100, 1) if total else 0.0,
        "clients": db.execute(
            "SELECT COUNT(*) AS c FROM users WHERE role='client'"
        ).fetchone()["c"],
        "abonnements_actifs": db.execute(
            "SELECT COUNT(*) AS c FROM abonnements WHERE statut='actif'"
        ).fetchone()["c"],
        "interventions_en_cours": db.execute(
            "SELECT COUNT(*) AS c FROM interventions WHERE statut='en_cours'"
        ).fetchone()["c"],
        "devis_en_cours": db.execute(
            "SELECT COUNT(*) AS c FROM devis WHERE statut NOT IN ('facture','archive')"
        ).fetchone()["c"],
        "factures_impayees": db.execute(
            "SELECT COUNT(*) AS c FROM factures WHERE statut='impayee'"
        ).fetchone()["c"],
        "ca_mois": db.execute(
            "SELECT COALESCE(SUM(total_ttc), 0) AS ca FROM factures "
            "WHERE statut='payee' AND strftime('%Y-%m', created_at)=strftime('%Y-%m','now')"
        ).fetchone()["ca"],
    }
