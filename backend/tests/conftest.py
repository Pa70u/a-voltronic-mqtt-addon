import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

SCHEMA_PATH = BACKEND_DIR / "schema.sql"

# Pose le chemin de la base AVANT tout import des modules de l'app
# (les imports en haut des fichiers test_*.py sont évalués à la collection,
# c-à-d avant les fixtures à scope=session).
_TMPDIR = tempfile.mkdtemp(prefix="garageos_tests_")
_DB_PATH = Path(_TMPDIR) / "garage.db"
os.environ["GARAGE_DB"] = str(_DB_PATH)
os.environ.setdefault("CORS_ORIGINS", "http://testserver")

_conn = sqlite3.connect(_DB_PATH)
_conn.executescript(SCHEMA_PATH.read_text())
_conn.commit()
_conn.close()


@pytest.fixture(scope="session")
def db_path():
    return _DB_PATH


@pytest.fixture(scope="function")
def db():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()
