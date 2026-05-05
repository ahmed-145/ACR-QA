"""API key utilities — generate, hash, and verify bearer keys for CI integrations."""

import secrets

from passlib.context import CryptContext

_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

_PREFIX = "acrqa_"


def generate_api_key() -> tuple[str, str]:
    """Return (raw_key, hashed_key). Store only the hash; give the raw key to the user once."""
    raw = _PREFIX + secrets.token_urlsafe(32)
    return raw, hash_api_key(raw)


def hash_api_key(raw_key: str) -> str:
    return _ctx.hash(raw_key)


def verify_api_key(raw_key: str, hashed: str) -> bool:
    return _ctx.verify(raw_key, hashed)


__all__ = ["generate_api_key", "hash_api_key", "verify_api_key"]
