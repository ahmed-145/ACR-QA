"""Add dependency_findings and run_sboms tables for supply chain engine.

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dependency_findings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=True),
        sa.Column("ecosystem", sa.Text(), nullable=True),
        sa.Column("risk_score", sa.Integer(), nullable=True),
        sa.Column("risk_level", sa.Text(), nullable=True),
        sa.Column("cve_count", sa.Integer(), nullable=True),
        sa.Column("cve_ids", sa.JSON(), nullable=True),
        sa.Column("stars", sa.Integer(), nullable=True),
        sa.Column("last_commit_days", sa.Integer(), nullable=True),
        sa.Column("contributors", sa.Integer(), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=True),
        sa.Column("license", sa.Text(), nullable=True),
        sa.Column("repo_url", sa.Text(), nullable=True),
        sa.Column("sbom_purl", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dependency_findings_run_id", "dependency_findings", ["run_id"])

    op.create_table(
        "run_sboms",
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("sbom_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=True),
        sa.PrimaryKeyConstraint("run_id"),
    )


def downgrade() -> None:
    op.drop_table("run_sboms")
    op.drop_index("ix_dependency_findings_run_id", table_name="dependency_findings")
    op.drop_table("dependency_findings")
