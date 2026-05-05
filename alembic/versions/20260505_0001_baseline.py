"""Baseline migration — captures the full ACR-QA schema as of v3.2.4.

All tables were previously managed by DATABASE/schema.sql (CREATE TABLE IF NOT EXISTS).
This migration makes Alembic aware of the existing schema so future changes can be
tracked as proper, reviewable, reversible diffs.

Run `alembic upgrade head` on a fresh database to create all tables from scratch.
On an existing database, mark this migration as applied without running SQL:
    alembic stamp 0001

Revision ID: 0001
Revises: None
Create Date: 2026-05-05 00:00:00.000000
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── analysis_runs ─────────────────────────────────────────────────────────
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("repo_name", sa.String(255), nullable=False),
        sa.Column("commit_sha", sa.String(40), nullable=True),
        sa.Column("branch", sa.String(100), nullable=True),
        sa.Column("pr_number", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("completed_at", sa.TIMESTAMP(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            sa.CheckConstraint("status IN ('running', 'completed', 'failed')"),
            server_default="running",
        ),
        sa.Column("total_findings", sa.Integer(), server_default="0"),
    )

    # ── findings ──────────────────────────────────────────────────────────────
    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("analysis_runs.id", ondelete="CASCADE")),
        sa.Column("tool", sa.String(50), nullable=False),
        sa.Column("rule_id", sa.String(100), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("column_number", sa.Integer(), server_default="0"),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("raw_output", sa.JSON(), nullable=True),
        sa.Column("canonical_rule_id", sa.String(50), nullable=True),
        sa.Column("canonical_severity", sa.String(20), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column(
            "ground_truth",
            sa.String(10),
            sa.CheckConstraint("ground_truth IN ('TP', 'FP', 'TN', 'FN')"),
            nullable=True,
        ),
        sa.Column(
            "confidence_score",
            sa.Integer(),
            sa.CheckConstraint("confidence_score BETWEEN 0 AND 100"),
            nullable=True,
        ),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_findings_run_id", "findings", ["run_id"])
    op.create_index("idx_findings_file_path", "findings", ["file_path"])
    op.create_index("idx_findings_severity", "findings", ["severity"])
    op.create_index("idx_findings_ground_truth", "findings", ["ground_truth"])

    # ── llm_explanations ─────────────────────────────────────────────────────
    op.create_table(
        "llm_explanations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("finding_id", sa.Integer(), sa.ForeignKey("findings.id", ondelete="CASCADE")),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("prompt_template", sa.Text(), nullable=True),
        sa.Column("prompt_filled", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("max_tokens", sa.Integer(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(10, 6), server_default="0"),
        sa.Column("status", sa.String(20), server_default="success"),
        sa.Column("confidence_score", sa.Float(), server_default="0.6"),
        sa.Column(
            "self_eval_score",
            sa.Integer(),
            sa.CheckConstraint("self_eval_score BETWEEN 1 AND 5"),
            nullable=True,
        ),
        sa.Column("consistency_score", sa.Float(), nullable=True),
        sa.Column("fix_validated", sa.Boolean(), nullable=True),
        sa.Column("fix_confidence", sa.String(20), nullable=True),
        sa.Column("fix_code", sa.Text(), nullable=True),
        sa.Column("fix_validation_note", sa.Text(), nullable=True),
        sa.Column("feasibility_verdict", sa.String(20), nullable=True),
        sa.Column("feasibility_confidence", sa.String(10), nullable=True),
        sa.Column("feasibility_reasoning", sa.Text(), nullable=True),
        sa.Column("feasibility_latency_ms", sa.Integer(), nullable=True),
        sa.Column("feasibility_penalty", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_llm_finding_id", "llm_explanations", ["finding_id"])

    # ── pr_comments ───────────────────────────────────────────────────────────
    op.create_table(
        "pr_comments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("finding_id", sa.Integer(), sa.ForeignKey("findings.id", ondelete="CASCADE")),
        sa.Column("pr_number", sa.Integer(), nullable=False),
        sa.Column("comment_id", sa.String(100), nullable=True),
        sa.Column(
            "platform",
            sa.String(20),
            sa.CheckConstraint("platform IN ('github', 'gitlab')"),
            nullable=False,
        ),
        sa.Column("posted_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column(
            "status",
            sa.String(20),
            sa.CheckConstraint("status IN ('posted', 'failed', 'deleted')"),
            server_default="posted",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("idx_pr_comments_finding", "pr_comments", ["finding_id"])
    op.create_index("idx_pr_comments_pr_number", "pr_comments", ["pr_number"])

    # ── feedback ──────────────────────────────────────────────────────────────
    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("finding_id", sa.Integer(), sa.ForeignKey("findings.id", ondelete="CASCADE")),
        sa.Column("user_id", sa.String(100), nullable=False),
        sa.Column("is_false_positive", sa.Boolean(), server_default="false"),
        sa.Column("is_helpful", sa.Boolean(), nullable=True),
        sa.Column(
            "clarity_rating",
            sa.Integer(),
            sa.CheckConstraint("clarity_rating BETWEEN 1 AND 5"),
            nullable=True,
        ),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_feedback_finding", "feedback", ["finding_id"])

    # ── suppression_rules ─────────────────────────────────────────────────────
    op.create_table(
        "suppression_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("canonical_rule_id", sa.String(100), nullable=False),
        sa.Column("file_pattern", sa.String(500), nullable=True),
        sa.Column(
            "created_from_finding_id",
            sa.Integer(),
            sa.ForeignKey("findings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("suppression_count", sa.Integer(), server_default="0"),
    )
    op.create_index("idx_suppression_rules_rule_id", "suppression_rules", ["canonical_rule_id"])
    op.create_index("idx_suppression_rules_active", "suppression_rules", ["is_active"])


def downgrade() -> None:
    # Drop in reverse FK order
    op.drop_table("suppression_rules")
    op.drop_table("feedback")
    op.drop_table("pr_comments")
    op.drop_table("llm_explanations")
    op.drop_table("findings")
    op.drop_table("analysis_runs")
