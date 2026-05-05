"""Add users and api_keys tables for JWT + API key auth (v3.3.0).

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-05 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.String(20),
            sa.CheckConstraint("role IN ('admin', 'member', 'viewer')"),
            server_default="member",
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="TRUE", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("last_login_at", sa.TIMESTAMP(), nullable=True),
    )

    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("scopes", sa.JSON(), server_default="[]"),
        sa.Column("is_active", sa.Boolean(), server_default="TRUE", nullable=False),
        sa.Column("last_used_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_table("api_keys")
    op.drop_table("users")
