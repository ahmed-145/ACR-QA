"""Add triage agent columns to findings table.

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("findings", sa.Column("triage_verdict", sa.Text(), nullable=True))
    op.add_column("findings", sa.Column("triage_reasoning", sa.Text(), nullable=True))
    op.add_column("findings", sa.Column("triage_confidence_delta", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("findings", "triage_confidence_delta")
    op.drop_column("findings", "triage_reasoning")
    op.drop_column("findings", "triage_verdict")
