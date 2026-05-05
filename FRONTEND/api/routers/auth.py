"""Auth router — login, refresh, API key management, user registration."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from DATABASE.database import Database
from FRONTEND.api.deps import get_current_user, get_db, require_role
from FRONTEND.api.models import (
    ApiKeyCreatedOut,
    ApiKeyCreateRequest,
    ApiKeyOut,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserOut,
)
from FRONTEND.auth.api_key_utils import generate_api_key
from FRONTEND.auth.jwt_utils import JWTError, create_access_token, create_refresh_token, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/login", response_model=TokenResponse, summary="Exchange credentials for JWT tokens")
async def login(body: LoginRequest, db: Database = Depends(get_db)):
    rows = db.execute(
        "SELECT id, email, password_hash, role FROM users WHERE email = %s AND is_active = TRUE",
        (body.email,),
        fetch=True,
    )
    if not rows or not _pwd.verify(body.password, rows[0]["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user = rows[0]
    return TokenResponse(
        access_token=create_access_token(user["id"], user["email"], user["role"]),
        refresh_token=create_refresh_token(user["id"]),
    )


@router.post("/refresh", response_model=TokenResponse, summary="Rotate refresh token")
async def refresh(body: RefreshRequest, db: Database = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token") from None

    rows = db.execute(
        "SELECT id, email, role FROM users WHERE id = %s AND is_active = TRUE",
        (user_id,),
        fetch=True,
    )
    if not rows:
        raise HTTPException(status_code=401, detail="User not found")

    user = rows[0]
    return TokenResponse(
        access_token=create_access_token(user["id"], user["email"], user["role"]),
        refresh_token=create_refresh_token(user["id"]),
    )


@router.get("/me", response_model=UserOut, summary="Get current user profile")
async def me(user: dict = Depends(get_current_user), db: Database = Depends(get_db)):
    rows = db.execute(
        "SELECT id, email, role, created_at FROM users WHERE id = %s",
        (user["id"],),
        fetch=True,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(**dict(rows[0]))


@router.post(
    "/users",
    response_model=UserOut,
    status_code=201,
    summary="Register a new user (admin only)",
    dependencies=[Depends(require_role("admin"))],
)
async def create_user(
    email: str,
    password: str,
    role: str = "member",
    db: Database = Depends(get_db),
):
    if role not in ("admin", "member", "viewer"):
        raise HTTPException(status_code=400, detail="role must be admin, member, or viewer")

    existing = db.execute("SELECT id FROM users WHERE email = %s", (email,), fetch=True)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    row = db.execute(
        "INSERT INTO users (email, password_hash, role) VALUES (%s, %s, %s) RETURNING id, email, role, created_at",
        (email, _pwd.hash(password), role),
    )
    return UserOut(**dict(row))


@router.post(
    "/api-keys",
    response_model=ApiKeyCreatedOut,
    status_code=201,
    summary="Create an API key for CI integrations",
)
async def create_api_key(
    body: ApiKeyCreateRequest,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    raw_key, key_hash = generate_api_key()
    import json

    row = db.execute(
        "INSERT INTO api_keys (user_id, key_hash, name, scopes) VALUES (%s, %s, %s, %s) "
        "RETURNING id, name, scopes, last_used_at, created_at",
        (user["id"], key_hash, body.name, json.dumps(body.scopes)),
    )
    d = dict(row)
    d["scopes"] = d["scopes"] if isinstance(d["scopes"], list) else (d["scopes"] or [])
    return ApiKeyCreatedOut(key=raw_key, **d)


@router.get("/api-keys", response_model=list[ApiKeyOut], summary="List your API keys")
async def list_api_keys(user: dict = Depends(get_current_user), db: Database = Depends(get_db)):
    rows = db.execute(
        "SELECT id, name, scopes, last_used_at, created_at FROM api_keys WHERE user_id = %s AND is_active = TRUE",
        (user["id"],),
        fetch=True,
    )
    result = []
    for r in rows or []:
        d = dict(r)
        d["scopes"] = d["scopes"] if isinstance(d["scopes"], list) else (d["scopes"] or [])
        result.append(ApiKeyOut(**d))
    return result


@router.delete("/api-keys/{key_id}", status_code=204, summary="Revoke an API key")
async def revoke_api_key(
    key_id: int,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    db.execute(
        "UPDATE api_keys SET is_active = FALSE WHERE id = %s AND user_id = %s",
        (key_id, user["id"]),
    )
