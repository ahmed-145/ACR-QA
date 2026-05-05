"""FastAPI dependency injection — DB, JWT auth, API key auth, RBAC."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from DATABASE.database import Database
from FRONTEND.auth.api_key_utils import verify_api_key
from FRONTEND.auth.jwt_utils import JWTError, decode_token

# ── Singletons ────────────────────────────────────────────────────────────────

_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db


# ── Auth schemes ─────────────────────────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    api_key: str | None = Security(api_key_header),
    db: Database = Depends(get_db),
) -> dict:
    """Resolve the caller from a JWT Bearer token OR an X-API-Key header."""
    # Try JWT first
    if token:
        try:
            payload = decode_token(token)
            if payload.get("type") != "access":
                raise _CREDENTIALS_EXC
            user_id = int(payload["sub"])
            rows = db.execute(
                "SELECT id, email, role FROM users WHERE id = %s AND is_active = TRUE",
                (user_id,),
                fetch=True,
            )
            if not rows:
                raise _CREDENTIALS_EXC
            return dict(rows[0])
        except (JWTError, KeyError, ValueError):
            raise _CREDENTIALS_EXC from None

    # Try API key
    if api_key:
        rows = db.execute(
            "SELECT ak.id, ak.user_id, ak.key_hash, ak.scopes, u.email, u.role "
            "FROM api_keys ak JOIN users u ON ak.user_id = u.id "
            "WHERE u.is_active = TRUE AND ak.is_active = TRUE",
            fetch=True,
        )
        for row in rows or []:
            if verify_api_key(api_key, row["key_hash"]):
                db.execute(
                    "UPDATE api_keys SET last_used_at = NOW() WHERE id = %s",
                    (row["id"],),
                )
                return {"id": row["user_id"], "email": row["email"], "role": row["role"]}

    raise _CREDENTIALS_EXC


def require_role(*roles: str):
    """Return a dependency that enforces one of the given roles."""

    async def check(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user['role']}' is not allowed here",
            )
        return user

    return check
