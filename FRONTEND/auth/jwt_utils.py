"""JWT utilities — access (15 min) + refresh (7 days) tokens using HS256."""

import os
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

_SECRET = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-prod-acrqa-2026")
_ALGORITHM = "HS256"
_ACCESS_TTL = int(os.getenv("JWT_ACCESS_TTL_MINUTES", 15))
_REFRESH_TTL = int(os.getenv("JWT_REFRESH_TTL_DAYS", 7))


def create_access_token(user_id: int, email: str, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "type": "access",
        "exp": datetime.now(UTC) + timedelta(minutes=_ACCESS_TTL),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.now(UTC) + timedelta(days=_REFRESH_TTL),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT. Raises JWTError on failure."""
    return jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])


__all__ = ["create_access_token", "create_refresh_token", "decode_token", "JWTError"]
