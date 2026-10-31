"""API keys: created once, stored only as a SHA-256 hash."""

import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from auditor.db import models as db

# A recognisable prefix lets secret scanners (and people) spot a leaked key, and lets
# us reject a malformed key without touching the database.
KEY_PREFIX = "baa_"


def generate_api_key() -> str:
    """32 random bytes from the OS's secure generator, URL-safe, plus the prefix."""
    return KEY_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    """SHA-256 hex digest.

    A fast hash is enough here, unlike for passwords: the key is 256 random bits, so it
    cannot be guessed or brute-forced from a leaked hash. A slow hash (bcrypt) would only
    slow down every request.
    """
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def create_api_client(session: Session, name: str) -> tuple[db.ApiClient, str]:
    """Create a client and return it with its key. The key is never stored, so this is the
    only time it can be shown. The caller commits."""
    key = generate_api_key()
    client = db.ApiClient(name=name, key_hash=hash_api_key(key))
    session.add(client)
    session.flush()
    return client, key


def find_client_by_key(session: Session, key: str) -> db.ApiClient | None:
    """Look a client up by the hash of the key it sent. Comparing hashes in the database
    leaks nothing useful through timing: an attacker cannot choose a hash's bytes."""
    if not key.startswith(KEY_PREFIX):
        return None
    return session.scalars(
        select(db.ApiClient).where(db.ApiClient.key_hash == hash_api_key(key))
    ).first()
