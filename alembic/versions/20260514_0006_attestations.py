"""Add scan_attestations table for provenance attestations (Feature 13).

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scan_attestations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attestation_json", sa.Text(), nullable=False),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("key_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_scan_attestations_run_id", "scan_attestations", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_scan_attestations_run_id", table_name="scan_attestations")
    op.drop_table("scan_attestations")
