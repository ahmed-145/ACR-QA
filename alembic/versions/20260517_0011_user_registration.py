"""Add email_verified and verification_code to users for public registration.

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), server_default="FALSE", nullable=False))
    op.add_column("users", sa.Column("verification_code", sa.String(6), nullable=True))
    op.add_column("users", sa.Column("reset_code", sa.String(6), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "reset_code")
    op.drop_column("users", "verification_code")
    op.drop_column("users", "email_verified")
