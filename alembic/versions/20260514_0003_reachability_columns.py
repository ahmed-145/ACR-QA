"""Add reachability_status and reachability_penalty columns to findings (Feature 9).

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "findings",
        sa.Column(
            "reachability_status",
            sa.String(20),
            sa.CheckConstraint("reachability_status IN ('REACHABLE', 'UNREACHABLE', 'UNKNOWN')"),
            nullable=True,
        ),
    )
    op.add_column(
        "findings",
        sa.Column("reachability_penalty", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("findings", "reachability_penalty")
    op.drop_column("findings", "reachability_status")
