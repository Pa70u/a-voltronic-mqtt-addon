"""Tests bcrypt + compatibilité ascendante SHA-256."""
import hashlib

from app.security import hash_password, needs_rehash, verify_password


def test_bcrypt_roundtrip():
    h = hash_password("hello")
    assert verify_password("hello", h)
    assert not verify_password("wrong", h)
    assert not needs_rehash(h)


def test_legacy_sha256_still_accepted():
    legacy = hashlib.sha256(b"hello").hexdigest()
    assert verify_password("hello", legacy)
    assert not verify_password("wrong", legacy)
    assert needs_rehash(legacy)


def test_empty_hash_rejects():
    assert not verify_password("anything", "")
    assert not needs_rehash("")


def test_login_migrates_legacy_to_bcrypt(db):
    from fastapi.testclient import TestClient
    import main

    legacy_hash = hashlib.sha256(b"secret123").hexdigest()
    db.execute(
        "INSERT INTO users(nom, email, password_hash, role) "
        "VALUES (?,?,?,?)",
        ("Legacy", "legacy@test.fr", legacy_hash, "admin"),
    )
    db.commit()

    client = TestClient(main.app)
    r = client.post("/api/auth/login",
                    json={"email": "legacy@test.fr", "password": "secret123"})
    assert r.status_code == 200, r.text

    new_hash = db.execute(
        "SELECT password_hash FROM users WHERE email=?", ("legacy@test.fr",)
    ).fetchone()["password_hash"]
    assert new_hash != legacy_hash
    assert new_hash.startswith("$2")  # bcrypt
