import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

SCHEMA_PATH = BACKEND_DIR / "schema.sql"

# Le chemin DOIT être posé avant tout import de `main` par les tests
# (les imports en haut des fichiers test_*.py s'exécutent à la collection,
# donc avant les fixtures à scope=session).
_TMPDIR = tempfile.mkdtemp(prefix="garageos_tests_")
_DB_PATH = Path(_TMPDIR) / "garage.db"
os.environ["GARAGE_DB"] = str(_DB_PATH)

_conn = sqlite3.connect(_DB_PATH)
_conn.executescript(SCHEMA_PATH.read_text())
_conn.commit()
_conn.close()


@pytest.fixture(scope="session")
def db_path():
    return _DB_PATH
