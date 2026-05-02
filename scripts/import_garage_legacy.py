"""
Import clients + factures dans GarageOS
Usage : python3 import_garage.py
Fichiers attendus dans le même dossier :
  - Export tiers V2-2.xls
  - Export des factures-2.xls
Base de données : /app/data/garage.db (Docker) ou garage.db (local)
"""
import pandas as pd
import sqlite3
import hashlib
import secrets
import json
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
DB_PATH = Path("/app/data/garage.db")  # chemin dans Docker
if not DB_PATH.exists():
    DB_PATH = Path("garage.db")        # fallback local

CLIENTS_FILE  = "Export tiers V2-2.xls"
FACTURES_FILE = "Export des factures-2.xls"

def nettoyer_tel(tel):
    if pd.isna(tel): return ""
    t = str(tel).strip().replace(" ","").replace(".","").replace("-","")
    if len(t) == 10 and t.isdigit():
        return f"{t[0:2]} {t[2:4]} {t[4:6]} {t[6:8]} {t[8:10]}"
    return str(tel).strip()

def nettoyer_montant(val):
    if pd.isna(val): return 0.0
    try:
        return float(str(val).replace(",",".").replace(" ",""))
    except:
        return 0.0

def nettoyer_date(val):
    if pd.isna(val): return None
    try:
        return datetime.strptime(str(val).strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except:
        return None

def main():
    print("=== Import GarageOS ===\n")
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    # ── Créer les tables si besoin ───────────────────────────────────────────
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT, prenom TEXT, email TEXT UNIQUE,
        password_hash TEXT, role TEXT DEFAULT 'client',
        telephone TEXT, adresse TEXT,
        code_client TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS factures(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE, devis_id INTEGER,
        client_id INTEGER, vehicule_id INTEGER,
        lignes TEXT DEFAULT '[]',
        total_ht REAL, tva REAL DEFAULT 20.0, total_ttc REAL,
        statut TEXT DEFAULT 'impayee',
        notes TEXT, date_echeance TEXT,
        date_facture TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    db.commit()

    # ── Import clients ───────────────────────────────────────────────────────
    print("📥 Lecture clients...")
    df_c = pd.read_csv(CLIENTS_FILE, sep="\t", encoding="latin1", on_bad_lines='skip')
    df_c = df_c[df_c["Client"] == 1]  # uniquement les clients (pas fournisseurs)

    ok_c = 0
    skip_c = 0
    code_to_id = {}

    for _, row in df_c.iterrows():
        code = str(row.get("Code","")).strip()
        nom  = str(row.get("Nom","")).strip() if not pd.isna(row.get("Nom")) else ""
        if not nom:
            skip_c += 1
            continue

        # Sépare prénom/nom si possible (ex: "MADAME DUPONT JEAN")
        parts = nom.replace("MONSIEUR ","").replace("MADAME ","").replace("M ","").split()
        prenom = parts[-1].capitalize() if len(parts) > 1 else ""
        nom_clean = " ".join(parts[:-1]).title() if len(parts) > 1 else nom.title()

        adresse = str(row.get("Adresse","")).strip().replace(" -","").strip() if not pd.isna(row.get("Adresse")) else ""
        cp      = str(row.get("Code postal","")).strip().replace(" ","") if not pd.isna(row.get("Code postal")) else ""
        ville   = str(row.get("Ville","")).strip() if not pd.isna(row.get("Ville")) else ""
        tel     = nettoyer_tel(row.get("Téléphone"))
        adresse_complete = f"{adresse}, {cp} {ville}".strip(", ")

        # Email généré depuis le code (pas de vrai email dans l'export)
        email = f"{code.lower()}@import.garage.fr"
        pw    = hashlib.sha256(secrets.token_hex(8).encode()).hexdigest()

        try:
            cur = db.execute(
                "INSERT OR IGNORE INTO users(nom,prenom,email,password_hash,role,telephone,adresse,code_client) VALUES(?,?,?,?,?,?,?,?)",
                (nom_clean, prenom, email, pw, "client", tel, adresse_complete, code)
            )
            uid = cur.lastrowid
            if uid:
                code_to_id[code] = uid
                ok_c += 1
            else:
                # déjà existant — récupère l'id
                r = db.execute("SELECT id FROM users WHERE code_client=?", (code,)).fetchone()
                if r: code_to_id[code] = r["id"]
                skip_c += 1
        except Exception as e:
            skip_c += 1

    db.commit()
    print(f"✅ Clients importés : {ok_c} | Ignorés : {skip_c}\n")

    # ── Import factures ──────────────────────────────────────────────────────
    print("📥 Lecture factures...")
    df_f = pd.read_csv(FACTURES_FILE, sep="\t", encoding="latin1", on_bad_lines='skip')

    ok_f = 0
    skip_f = 0

    for _, row in df_f.iterrows():
        numero      = str(row.get("Numéro de pièce","")).strip()
        code_client = str(row.get("Code client","")).strip()
        client_id   = code_to_id.get(code_client)

        if not client_id:
            # Chercher dans la DB par code
            r = db.execute("SELECT id FROM users WHERE code_client=?", (code_client,)).fetchone()
            client_id = r["id"] if r else None

        if not client_id or not numero:
            skip_f += 1
            continue

        total_ht  = nettoyer_montant(row.get("Total HT"))
        total_tva = nettoyer_montant(row.get("Total TVA"))
        total_ttc = nettoyer_montant(row.get("Total TTC"))
        tva_pct   = round(total_tva / total_ht * 100) if total_ht > 0 else 20.0

        date_f    = nettoyer_date(row.get("Date"))
        date_ech  = nettoyer_date(row.get("Date d'échéance"))

        regle     = str(row.get("Réglée","")).strip().lower()
        statut    = "payee" if regle in ["oui","yes","1"] else "impayee"

        type_piece = str(row.get("Type de pièce","")).strip()
        # On importe seulement les factures (pas devis/bons de commande)
        if type_piece in ["Devis","Bon de commande","Avoir"]:
            skip_f += 1
            continue

        try:
            db.execute(
                "INSERT OR IGNORE INTO factures(numero,client_id,total_ht,tva,total_ttc,statut,date_echeance,date_facture,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (numero, client_id, total_ht, tva_pct, total_ttc, statut, date_ech, date_f, date_f or datetime.now().strftime("%Y-%m-%d"))
            )
            ok_f += 1
        except Exception as e:
            skip_f += 1

    db.commit()
    db.close()

    print(f"✅ Factures importées : {ok_f} | Ignorées : {skip_f}\n")
    print("=== Import terminé ===")

if __name__ == "__main__":
    main()
