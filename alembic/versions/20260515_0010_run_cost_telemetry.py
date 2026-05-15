"""Add cost telemetry columns to analysis_runs — Phase 12 Week 5 (task 12.32)

Tracks per-scan Groq token usage and estimated USD cost for FinOps reporting.

Revision ID: 0010
Revises: 0009
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column("groq_tokens_used", sa.Integer(), nullable=True, comment="Total Groq tokens consumed across all explanations in this run"),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("groq_cost_usd", sa.Numeric(precision=10, scale=6), nullable=True, comment="Estimated USD cost at $0.27/1M tokens (llama3-8b-8192 rate)"),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("groq_requests", sa.Integer(), nullable=True, comment="Number of Groq API calls made during this run"),
    )

    # Index for cost reporting queries (GROUP BY date, SUM cost)
    op.create_index(
        "ix_analysis_runs_groq_cost_usd",
        "analysis_runs",
        ["groq_cost_usd"],
        postgresql_where=sa.text("groq_cost_usd IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_runs_groq_cost_usd", table_name="analysis_runs")
    op.drop_column("analysis_runs", "groq_requests")
    op.drop_column("analysis_runs", "groq_cost_usd")
    op.drop_column("analysis_runs", "groq_tokens_used")
