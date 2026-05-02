#!/usr/bin/env python3
"""Migration de la base GarageOS legacy vers le schéma v5.

Usage:
    python scripts/migrate_to_v5.py <db_source> <db_destination>

Exemple:
    python scripts/migrate_to_v5.py /opt/garage/data/garage.db /opt/garage-v5/data/garage.db

Ce script ne modifie JAMAIS la base source (lecture seule).
La base destination est entièrement reconstruite (supprimée si elle existe).
"""

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from seeds.catalogue import seed as seed_catalogue

SCHEMA_PATH = BACKEND_DIR / "schema.sql"


def add_six_months(iso_date: str | None) -> str | None:
    """Ajoute 6 mois à une date ISO (YYYY-MM-DD ou YYYY-MM-DD HH:MM:SS)."""
    if not iso_date:
        return None
    try:
        d = datetime.fromisoformat(iso_date.split(" ")[0])
    except ValueError:
        return None
    # ~180 jours suffit pour notre usage (engagement 6 mois)
    return (d + timedelta(days=180)).strftime("%Y-%m-%d")


def copy_table(src: sqlite3.Connection, dst: sqlite3.Connection, table: str,
               src_cols: list[str], dst_cols: list[str], transform=None,
               skip_if=None) -> tuple[int, int]:
    """Copie les lignes de `src.table` vers `dst.table`.

    `skip_if(row) -> str | None` peut retourner une raison pour ignorer la ligne
    (ex: clé étrangère orpheline). Retourne (insérées, ignorées).
    """
    rows = src.execute(f"SELECT {', '.join(src_cols)} FROM {table}").fetchall()
    if not rows:
        return (0, 0)
    placeholders = ", ".join(["?"] * len(dst_cols))
    sql = f"INSERT INTO {table} ({', '.join(dst_cols)}) VALUES ({placeholders})"
    inserted = 0
    skipped = 0
    for r in rows:
        if skip_if:
            reason = skip_if(r)
            if reason:
                print(f"   ⚠️  {table}#{r['id']} ignoré : {reason}")
                skipped += 1
                continue
        values = transform(r) if transform else tuple(r)
        dst.execute(sql, values)
        inserted += 1
    dst.commit()
    return (inserted, skipped)


def _none_if_zero(v):
    """SQLite legacy stockait 0 pour 'pas de référence' — convertit en NULL."""
    return None if v in (0, "0", "") else v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="Chemin vers la base SQLite source (legacy)")
    ap.add_argument("destination", help="Chemin vers la base SQLite destination (v5)")
    ap.add_argument("--force", action="store_true",
                    help="Écrase la base destination si elle existe déjà")
    args = ap.parse_args()

    src_path = Path(args.source).resolve()
    dst_path = Path(args.destination).resolve()

    if not src_path.exists():
        sys.exit(f"❌ Source introuvable : {src_path}")

    if dst_path.exists():
        if not args.force:
            sys.exit(f"❌ Destination existe déjà : {dst_path} — utilise --force pour écraser")
        dst_path.unlink()

    dst_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"📂 Source       : {src_path}")
    print(f"📂 Destination  : {dst_path}")
    print()

    # Connexions
    src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    dst = sqlite3.connect(dst_path)
    dst.execute("PRAGMA foreign_keys=ON")

    # Schéma v5
    print("🔨 Création du schéma v5…")
    dst.executescript(SCHEMA_PATH.read_text())
    dst.commit()

    # Pré-charge les IDs valides côté source pour valider les clés étrangères
    user_ids = {r[0] for r in src.execute("SELECT id FROM users")}
    emp_ids = {r[0] for r in src.execute("SELECT id FROM emplacements")}
    vehicule_ids = {r[0] for r in src.execute("SELECT id FROM vehicules")}

    # ── users ───────────────────────────────────────────────────────────
    ins, skp = copy_table(
        src, dst, "users",
        ["id","nom","prenom","email","password_hash","role","telephone",
         "adresse","created_at","code_client"],
        ["id","nom","prenom","email","password_hash","role","telephone",
         "adresse","created_at","code_client",
         "pref_relance_email","pref_relance_sms"],
        transform=lambda r: tuple(r) + (1, 1),
    )
    print(f"   users          : {ins} (ignorés: {skp})")

    # ── emplacements ────────────────────────────────────────────────────
    ins, skp = copy_table(
        src, dst, "emplacements",
        ["id","numero","statut","etage","prix_mensuel","prix_journalier"],
        ["id","numero","statut","etage","prix_mensuel","prix_journalier"],
    )
    print(f"   emplacements   : {ins} (ignorés: {skp})")

    # ── abonnements (calcule date_engagement_fin = date_debut + 6 mois) ─
    def _abo_skip(r):
        if r["client_id"] not in user_ids:
            return f"client_id orphelin ({r['client_id']})"
        if r["emplacement_id"] not in emp_ids:
            return f"emplacement_id orphelin ({r['emplacement_id']})"
        return None

    ins, skp = copy_table(
        src, dst, "abonnements",
        ["id","client_id","emplacement_id","date_debut","date_fin","montant",
         "statut","created_at","stripe_payment_url","derniere_relance"],
        ["id","client_id","emplacement_id","date_debut","date_fin","montant",
         "statut","created_at","stripe_payment_url","derniere_relance",
         "date_engagement_fin"],
        transform=lambda r: tuple(r) + (add_six_months(r["date_debut"]),),
        skip_if=_abo_skip,
    )
    print(f"   abonnements    : {ins} (ignorés: {skp})")

    # ── vehicules ───────────────────────────────────────────────────────
    def _veh_skip(r):
        if r["client_id"] not in user_ids:
            return f"client_id orphelin ({r['client_id']})"
        return None

    ins, skp = copy_table(
        src, dst, "vehicules",
        ["id","client_id","immatriculation","marque","modele","annee",
         "kilometrage","created_at","vin","type_vehicule"],
        ["id","client_id","immatriculation","marque","modele","annee",
         "kilometrage","created_at","vin","type_vehicule",
         "kilometrage_date","date_dernier_ct","date_prochain_ct","derniere_relance_ct"],
        transform=lambda r: tuple(r) + (
            r["created_at"][:10] if r["created_at"] else None, None, None, None,
        ),
        skip_if=_veh_skip,
    )
    print(f"   vehicules      : {ins} (ignorés: {skp})")

    # ── interventions ───────────────────────────────────────────────────
    def _int_skip(r):
        if r["client_id"] not in user_ids:
            return f"client_id orphelin ({r['client_id']})"
        return None

    ins, skp = copy_table(
        src, dst, "interventions",
        ["id","vehicule_id","client_id","date_entree","description","statut",
         "montant_ttc","technicien","created_at","montant_ht"],
        ["id","vehicule_id","client_id","date_entree","description","statut",
         "montant_ttc","technicien","created_at","montant_ht"],
        transform=lambda r: (
            r["id"],
            _none_if_zero(r["vehicule_id"]) if _none_if_zero(r["vehicule_id"]) in vehicule_ids else None,
            r["client_id"], r["date_entree"], r["description"], r["statut"],
            r["montant_ttc"], r["technicien"], r["created_at"], r["montant_ht"],
        ),
        skip_if=_int_skip,
    )
    print(f"   interventions  : {ins} (ignorés: {skp})")

    # ── devis ───────────────────────────────────────────────────────────
    def _dev_skip(r):
        if r["client_id"] not in user_ids:
            return f"client_id orphelin ({r['client_id']})"
        return None

    ins, skp = copy_table(
        src, dst, "devis",
        ["id","numero","client_id","vehicule_id","lignes","total_ht","tva",
         "total_ttc","statut","notes","validite","created_at","date_echeance"],
        ["id","numero","client_id","vehicule_id","lignes","total_ht","tva",
         "total_ttc","statut","notes","validite","created_at","date_echeance"],
        transform=lambda r: (
            r["id"], r["numero"], r["client_id"],
            _none_if_zero(r["vehicule_id"]) if _none_if_zero(r["vehicule_id"]) in vehicule_ids else None,
            r["lignes"], r["total_ht"], r["tva"], r["total_ttc"],
            r["statut"], r["notes"], r["validite"], r["created_at"], r["date_echeance"],
        ),
        skip_if=_dev_skip,
    )
    print(f"   devis          : {ins} (ignorés: {skp})")

    # ── factures ────────────────────────────────────────────────────────
    devis_ids = {r[0] for r in dst.execute("SELECT id FROM devis")}

    def _fac_skip(r):
        if r["client_id"] not in user_ids:
            return f"client_id orphelin ({r['client_id']})"
        return None

    ins, skp = copy_table(
        src, dst, "factures",
        ["id","numero","devis_id","client_id","vehicule_id","lignes",
         "total_ht","tva","total_ttc","statut","notes","date_echeance",
         "created_at","date_facture","methode_reglement","date_reglement",
         "reference","stripe_payment_url","montant_ht"],
        ["id","numero","devis_id","client_id","vehicule_id","lignes",
         "total_ht","tva","total_ttc","statut","notes","date_echeance",
         "created_at","date_facture","methode_reglement","date_reglement",
         "reference","stripe_payment_url","derniere_relance"],
        transform=lambda r: (
            r["id"], r["numero"],
            _none_if_zero(r["devis_id"]) if _none_if_zero(r["devis_id"]) in devis_ids else None,
            r["client_id"],
            _none_if_zero(r["vehicule_id"]) if _none_if_zero(r["vehicule_id"]) in vehicule_ids else None,
            r["lignes"], r["total_ht"], r["tva"], r["total_ttc"], r["statut"],
            r["notes"], r["date_echeance"], r["created_at"], r["date_facture"],
            r["methode_reglement"], r["date_reglement"], r["reference"],
            r["stripe_payment_url"], None,
        ),
        skip_if=_fac_skip,
    )
    print(f"   factures       : {ins} (ignorés: {skp})")

    # ── paiements ───────────────────────────────────────────────────────
    facture_ids = {r[0] for r in dst.execute("SELECT id FROM factures")}

    def _pay_skip(r):
        if r["client_id"] is not None and r["client_id"] not in user_ids:
            return f"client_id orphelin ({r['client_id']})"
        return None

    ins, skp = copy_table(
        src, dst, "paiements",
        ["id","client_id","facture_id","type","montant","methode","statut","created_at"],
        ["id","client_id","facture_id","type","montant","methode","statut","created_at"],
        transform=lambda r: (
            r["id"], r["client_id"],
            r["facture_id"] if (r["facture_id"] in facture_ids) else None,
            r["type"], r["montant"], r["methode"], r["statut"], r["created_at"],
        ),
        skip_if=_pay_skip,
    )
    print(f"   paiements      : {ins} (ignorés: {skp})")

    # ── tokens (on saute les expirés) ───────────────────────────────────
    rows = src.execute(
        "SELECT token, user_id, expires_at FROM tokens WHERE expires_at > datetime('now')"
    ).fetchall()
    for r in rows:
        dst.execute(
            "INSERT INTO tokens(token, user_id, expires_at) VALUES (?,?,?)",
            (r["token"], r["user_id"], r["expires_at"]),
        )
    dst.commit()
    print(f"   tokens (actifs): {len(rows)}")

    # ── config_garage ───────────────────────────────────────────────────
    ins, skp = copy_table(
        src, dst, "config_garage",
        ["id","cle","valeur"],
        ["id","cle","valeur"],
    )
    print(f"   config_garage  : {ins} (ignorés: {skp})")

    # ── catalogue ───────────────────────────────────────────────────────
    print("🌱 Seed catalogue prestations…")
    seed_catalogue(dst)
    fam_n = dst.execute("SELECT COUNT(*) FROM prestations_familles").fetchone()[0]
    pres_n = dst.execute("SELECT COUNT(*) FROM prestations").fetchone()[0]
    print(f"   familles       : {fam_n}")
    print(f"   prestations    : {pres_n}")

    # ── Resync sequences (pour AUTOINCREMENT) ───────────────────────────
    for table in ["users", "emplacements", "abonnements", "vehicules",
                  "interventions", "devis", "factures", "paiements"]:
        max_id = dst.execute(f"SELECT MAX(id) FROM {table}").fetchone()[0] or 0
        dst.execute(
            "INSERT OR REPLACE INTO sqlite_sequence(name, seq) VALUES (?,?)",
            (table, max_id),
        )
    dst.commit()

    src.close()
    dst.close()

    print()
    print(f"✅ Migration terminée → {dst_path}")
    print(f"   Taille : {dst_path.stat().st_size / 1024:.1f} Ko")


if __name__ == "__main__":
    main()
