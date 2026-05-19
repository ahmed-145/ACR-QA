"""Add iac_provider + iac_resource columns to findings for the IaC Scanner (v5.0.0 A2).

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "findings",
        sa.Column(
            "iac_provider",
            sa.String(32),
            nullable=True,
            comment="IaC provider: terraform | kubernetes | dockerfile",
        ),
    )
    op.add_column(
        "findings",
        sa.Column(
            "iac_resource",
            sa.String(256),
            nullable=True,
            comment="Best-effort IaC resource hint (e.g. aws_s3_bucket.public, container name).",
        ),
    )
    op.create_index("ix_findings_iac_provider", "findings", ["iac_provider"])


def downgrade() -> None:
    op.drop_index("ix_findings_iac_provider", table_name="findings")
    op.drop_column("findings", "iac_resource")
    op.drop_column("findings", "iac_provider")
