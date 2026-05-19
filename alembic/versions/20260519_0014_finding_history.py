"""Add finding_history table for Time-Travel cache (v5.0.0 A2).

Revision ID: 0014
Revises: 0013
Create Date: 2026-05-19

The table is a cache; the engine re-computes on demand if the row is missing.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "finding_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "finding_id",
            sa.Integer(),
            sa.ForeignKey("findings.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("first_seen_commit", sa.String(40), nullable=True),
        sa.Column("first_seen_author", sa.String(128), nullable=True),
        sa.Column("first_seen_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("regression_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("commits_touching", sa.JSON(), nullable=True),
        sa.Column("near_fix_commits", sa.JSON(), nullable=True),
        sa.Column("max_commits", sa.Integer(), nullable=False, server_default="50"),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("finding_history")
