"""Vérifie qu'une base legacy (sans les colonnes v5) est bien migrée
en place par upgrade_to_v5()."""
import sqlite3
import tempfile
from pathlib import Path

from app.database import upgrade_to_v5


LEGACY_SCHEMA = """
CREATE TABLE users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT, prenom TEXT, email TEXT UNIQUE, password_hash TEXT,
    role TEXT DEFAULT 'client', telephone TEXT, adresse TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP, code_client TEXT
);
CREATE TABLE emplacements(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE, statut TEXT DEFAULT 'libre',
    etage INTEGER DEFAULT 0,
    prix_mensuel REAL DEFAULT 80.0, prix_journalier REAL DEFAULT 5.0
);
CREATE TABLE abonnements(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER, emplacement_id INTEGER,
    date_debut TEXT, date_fin TEXT, montant REAL,
    statut TEXT DEFAULT 'actif',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    stripe_payment_url TEXT, derniere_relance TEXT
);
CREATE TABLE vehicules(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER, immatriculation TEXT, marque TEXT, modele TEXT,
    annee INTEGER, kilometrage INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    vin TEXT, type_vehicule TEXT DEFAULT 'Voiture'
);
CREATE TABLE interventions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicule_id INTEGER, client_id INTEGER,
    date_entree TEXT, description TEXT,
    statut TEXT DEFAULT 'en_cours',
    montant_ttc REAL DEFAULT 0, technicien TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP, montant_ht REAL DEFAULT 0
);
CREATE TABLE devis(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE, client_id INTEGER, vehicule_id INTEGER,
    lignes TEXT, total_ht REAL, tva REAL DEFAULT 20.0, total_ttc REAL,
    statut TEXT DEFAULT 'brouillon', notes TEXT, validite INTEGER DEFAULT 30,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP, date_echeance TEXT
);
CREATE TABLE factures(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT UNIQUE, devis_id INTEGER, client_id INTEGER,
    vehicule_id INTEGER, lignes TEXT,
    total_ht REAL, tva REAL DEFAULT 20.0, total_ttc REAL,
    statut TEXT DEFAULT 'impayee', notes TEXT, date_echeance TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP, date_facture TEXT,
    methode_reglement TEXT, date_reglement TEXT, reference TEXT,
    stripe_payment_url TEXT, montant_ht REAL DEFAULT 0
);
CREATE TABLE paiements(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER, facture_id INTEGER,
    type TEXT, montant REAL, methode TEXT,
    statut TEXT DEFAULT 'en_attente',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE tokens(
    token TEXT PRIMARY KEY, user_id INTEGER, expires_at TEXT
);
CREATE TABLE config_garage(
    id INTEGER PRIMARY KEY, cle TEXT UNIQUE, valeur TEXT
);
"""


def _make_legacy_db() -> Path:
    tmp = Path(tempfile.mkdtemp()) / "legacy.db"
    conn = sqlite3.connect(tmp)
    conn.executescript(LEGACY_SCHEMA)
    # Quelques données réalistes
    conn.execute(
        "INSERT INTO users(id, nom, email, password_hash, role) "
        "VALUES (1, 'Admin', 'admin@x.fr', 'sha256hex', 'admin')"
    )
    conn.execute(
        "INSERT INTO emplacements(id, numero) VALUES (1, 'P01')"
    )
    conn.execute(
        "INSERT INTO vehicules(id, client_id, immatriculation, kilometrage) "
        "VALUES (1, 1, 'AB-123-CD', 50000)"
    )
    conn.commit()
    conn.close()
    return tmp


def test_upgrade_legacy_to_v5_adds_columns():
    db_path = _make_legacy_db()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    upgrade_to_v5(conn)

    veh_cols = [r[1] for r in conn.execute("PRAGMA table_info(vehicules)").fetchall()]
    assert "kilometrage_date" in veh_cols
    assert "date_dernier_ct" in veh_cols
    assert "date_prochain_ct" in veh_cols
    assert "derniere_relance_ct" in veh_cols

    user_cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    assert "pref_relance_email" in user_cols
    assert "pref_relance_sms" in user_cols

    abo_cols = [r[1] for r in conn.execute("PRAGMA table_info(abonnements)").fetchall()]
    assert "date_engagement_fin" in abo_cols

    fac_cols = [r[1] for r in conn.execute("PRAGMA table_info(factures)").fetchall()]
    assert "derniere_relance" in fac_cols

    conn.close()


def test_upgrade_creates_new_tables_and_seeds_catalogue():
    db_path = _make_legacy_db()
    conn = sqlite3.connect(db_path)
    upgrade_to_v5(conn)

    n_fam = conn.execute("SELECT COUNT(*) FROM prestations_familles").fetchone()[0]
    n_pres = conn.execute("SELECT COUNT(*) FROM prestations").fetchone()[0]
    assert n_fam == 12
    assert n_pres == 135

    v = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    assert v == 5

    # Données legacy préservées
    user = conn.execute("SELECT email FROM users WHERE id=1").fetchone()
    assert user[0] == "admin@x.fr"
    veh = conn.execute("SELECT kilometrage FROM vehicules WHERE id=1").fetchone()
    assert veh[0] == 50000

    conn.close()


def test_upgrade_is_idempotent():
    db_path = _make_legacy_db()
    conn = sqlite3.connect(db_path)
    upgrade_to_v5(conn)
    upgrade_to_v5(conn)  # 2e passage : ne doit ni planter ni dupliquer

    n_pres = conn.execute("SELECT COUNT(*) FROM prestations").fetchone()[0]
    assert n_pres == 135
    conn.close()
