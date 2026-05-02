"""Connexion SQLite + initialisation/migration au démarrage."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import get_settings

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"


def connect() -> sqlite3.Connection:
    """Ouvre une connexion SQLite optimisée. Le caller est responsable de close()."""
    settings = get_settings()
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-65536")
    conn.execute("PRAGMA mmap_size=268435456")
    conn.execute("PRAGMA temp_store=MEMORY")
    return conn


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    if not _table_exists(conn, table):
        return False
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    return column in cols


def _add_column_if_missing(
    conn: sqlite3.Connection, table: str, column: str, definition: str
) -> None:
    if _table_exists(conn, table) and not _column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _current_schema_version(conn: sqlite3.Connection) -> int:
    if not _table_exists(conn, "schema_version"):
        return 0
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return (row[0] if row and row[0] is not None else 0) or 0


def upgrade_to_v5(conn: sqlite3.Connection) -> None:
    """Migre une base legacy (avant v5) en place, sans perte de données.

    - Ajoute les colonnes manquantes via ALTER TABLE
    - Crée les nouvelles tables (prestations*, relances_log, schema_version)
    - Seed le catalogue par défaut si la table prestations est vide
    - Marque schema_version = 5
    """
    # Tables nouvelles (CREATE IF NOT EXISTS, sans danger)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS prestations_familles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE NOT NULL,
            icone TEXT,
            ordre INTEGER DEFAULT 0,
            actif INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS prestations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            famille_id INTEGER NOT NULL REFERENCES prestations_familles(id) ON DELETE CASCADE,
            libelle TEXT NOT NULL,
            pu_ht REAL DEFAULT 0,
            duree_min INTEGER DEFAULT 0,
            actif INTEGER DEFAULT 1,
            ordre INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS relances_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cible_type TEXT NOT NULL,
            cible_id INTEGER NOT NULL,
            canal TEXT NOT NULL,
            destinataire TEXT,
            statut TEXT NOT NULL,
            erreur TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Colonnes ajoutées au schéma v5
    _add_column_if_missing(conn, "users", "pref_relance_email", "INTEGER DEFAULT 1")
    _add_column_if_missing(conn, "users", "pref_relance_sms", "INTEGER DEFAULT 1")

    _add_column_if_missing(conn, "vehicules", "kilometrage_date", "TEXT")
    _add_column_if_missing(conn, "vehicules", "date_dernier_ct", "TEXT")
    _add_column_if_missing(conn, "vehicules", "date_prochain_ct", "TEXT")
    _add_column_if_missing(conn, "vehicules", "derniere_relance_ct", "TEXT")

    _add_column_if_missing(conn, "abonnements", "date_engagement_fin", "TEXT")

    _add_column_if_missing(conn, "factures", "derniere_relance", "TEXT")

    # Index (idempotent: CREATE IF NOT EXISTS, on ignore les erreurs si la
    # colonne référencée n'existe pas encore — ne devrait plus arriver après
    # les ALTER TABLE ci-dessus).
    for stmt in [
        "CREATE INDEX IF NOT EXISTS idx_abonnements_client ON abonnements(client_id)",
        "CREATE INDEX IF NOT EXISTS idx_abonnements_emplacement ON abonnements(emplacement_id)",
        "CREATE INDEX IF NOT EXISTS idx_abonnements_statut ON abonnements(statut)",
        "CREATE INDEX IF NOT EXISTS idx_vehicules_client ON vehicules(client_id)",
        "CREATE INDEX IF NOT EXISTS idx_vehicules_ct ON vehicules(date_prochain_ct)",
        "CREATE INDEX IF NOT EXISTS idx_interventions_client ON interventions(client_id)",
        "CREATE INDEX IF NOT EXISTS idx_interventions_statut ON interventions(statut)",
        "CREATE INDEX IF NOT EXISTS idx_devis_client ON devis(client_id)",
        "CREATE INDEX IF NOT EXISTS idx_factures_client ON factures(client_id)",
        "CREATE INDEX IF NOT EXISTS idx_factures_statut ON factures(statut)",
        "CREATE INDEX IF NOT EXISTS idx_tokens_user ON tokens(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_tokens_expires ON tokens(expires_at)",
        "CREATE INDEX IF NOT EXISTS idx_prestations_famille ON prestations(famille_id)",
        "CREATE INDEX IF NOT EXISTS idx_relances_cible ON relances_log(cible_type, cible_id)",
    ]:
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError:
            # Table absente sur cette base — pas grave, l'index sera créé à
            # la prochaine init si la table est créée entre-temps.
            pass

    # Seed du catalogue si vide
    nb = conn.execute("SELECT COUNT(*) FROM prestations").fetchone()[0]
    if nb == 0:
        from seeds.catalogue import seed as seed_catalogue
        seed_catalogue(conn)

    # Marque la version
    conn.execute("INSERT OR IGNORE INTO schema_version(version) VALUES (5)")
    conn.commit()


def init_db() -> None:
    """Initialise une base neuve OU upgrade une base legacy vers v5.

    - Si la base n'existe pas encore : applique schema.sql complet.
    - Si la base existe en legacy : exécute upgrade_to_v5() (ALTER TABLE en place).
    - Si la base est déjà en v5 : ne fait rien (idempotent).
    """
    settings = get_settings()
    db_file = Path(settings.db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    fresh = not db_file.exists() or db_file.stat().st_size == 0

    conn = connect()
    try:
        if fresh:
            conn.executescript(SCHEMA_PATH.read_text())
            conn.commit()
            return

        version = _current_schema_version(conn)
        if version >= 5:
            return  # déjà à jour

        upgrade_to_v5(conn)
    finally:
        conn.close()
