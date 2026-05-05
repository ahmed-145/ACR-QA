#!/usr/bin/env python3
"""
Bootstrap the first admin user.

Usage:
    python3 scripts/seed_admin.py
    ADMIN_EMAIL=ops@example.com ADMIN_PASSWORD=secure python3 scripts/seed_admin.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from passlib.context import CryptContext

from DATABASE.database import Database

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

email = os.getenv("ADMIN_EMAIL", "admin@acrqa.local")
password = os.getenv("ADMIN_PASSWORD", "changeme123!")

if password == "changeme123!":
    print("⚠️  Using default password. Set ADMIN_PASSWORD env var before running in production.")

db = Database()

existing = db.execute("SELECT id FROM users WHERE email = %s", (email,), fetch=True)
if existing:
    print(f"✓ Admin user {email!r} already exists (id={existing[0]['id']})")
    sys.exit(0)

row = db.execute(
    "INSERT INTO users (email, password_hash, role) VALUES (%s, %s, 'admin') RETURNING id",
    (email, _pwd.hash(password)),
)
print(f"✓ Created admin user {email!r} (id={row['id']})")
print(f'  Login at POST /v1/auth/login with {{"email": "{email}", "password": "<your-password>"}}')
