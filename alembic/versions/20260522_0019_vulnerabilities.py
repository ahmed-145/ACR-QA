"""Add vulnerabilities table and vulnerability_id FK on findings (Phase 0).

Revision ID: 0019
Revises: 0018
Create Date: 2026-05-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Lifecycle states for vulnerabilities
VULN_STATUS = ("detected", "confirmed", "assigned", "in_progress", "fixed", "verified", "regressed", "dismissed")


def upgrade() -> None:
    op.create_table(
        "vulnerabilities",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("short_id", sa.String(12), nullable=False, unique=True),
        sa.Column("canonical_rule_id", sa.String(64), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(*VULN_STATUS, name="vuln_status_enum"),
            nullable=False,
            server_default="detected",
        ),
        sa.Column("owner", sa.String(255), nullable=True),
        sa.Column("severity", sa.String(16), nullable=False, server_default="low"),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        # first detection (populated from the earliest finding that maps here)
        sa.Column("first_seen_run_id", sa.Integer(), sa.ForeignKey("analysis_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        # last time this vuln was detected in a scan (updated on each run)
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_index("ix_vulnerabilities_fingerprint", "vulnerabilities", ["fingerprint"])
    op.create_index("ix_vulnerabilities_canonical_rule_id", "vulnerabilities", ["canonical_rule_id"])
    op.create_index("ix_vulnerabilities_file_path", "vulnerabilities", ["file_path"])
    op.create_index("ix_vulnerabilities_status", "vulnerabilities", ["status"])

    # FK from findings → vulnerabilities (nullable — historical findings won't have one)
    op.add_column(
        "findings",
        sa.Column(
            "vulnerability_id",
            sa.Integer(),
            sa.ForeignKey("vulnerabilities.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_findings_vulnerability_id", "findings", ["vulnerability_id"])


def downgrade() -> None:
    op.drop_index("ix_findings_vulnerability_id", table_name="findings")
    op.drop_column("findings", "vulnerability_id")

    op.drop_index("ix_vulnerabilities_status", table_name="vulnerabilities")
    op.drop_index("ix_vulnerabilities_file_path", table_name="vulnerabilities")
    op.drop_index("ix_vulnerabilities_canonical_rule_id", table_name="vulnerabilities")
    op.drop_index("ix_vulnerabilities_fingerprint", table_name="vulnerabilities")
    op.drop_table("vulnerabilities")
    op.execute("DROP TYPE IF EXISTS vuln_status_enum")
