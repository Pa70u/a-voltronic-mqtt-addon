"""Tests du seed catalogue + idempotence."""
import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from seeds.catalogue import CATALOGUE_DEFAUT, seed


def _fresh_db():
    conn = sqlite3.connect(":memory:")
    schema = (BACKEND_DIR / "schema.sql").read_text()
    conn.executescript(schema)
    return conn


def test_catalogue_seed_populates_expected_counts():
    conn = _fresh_db()
    seed(conn)

    n_familles = conn.execute("SELECT COUNT(*) FROM prestations_familles").fetchone()[0]
    n_prestations = conn.execute("SELECT COUNT(*) FROM prestations").fetchone()[0]

    expected_fam = len(CATALOGUE_DEFAUT)
    expected_pres = sum(len(f["prestations"]) for f in CATALOGUE_DEFAUT)

    assert n_familles == expected_fam
    assert n_prestations == expected_pres


def test_catalogue_seed_is_idempotent():
    conn = _fresh_db()
    seed(conn)
    n1 = conn.execute("SELECT COUNT(*) FROM prestations").fetchone()[0]

    seed(conn)
    n2 = conn.execute("SELECT COUNT(*) FROM prestations").fetchone()[0]

    assert n1 == n2, "Le seed doit être idempotent (pas de duplication)"


def test_schema_version_set():
    conn = _fresh_db()
    v = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    assert v == 5
