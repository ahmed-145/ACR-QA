"""Materialised views for hot relationship edges (Phase 3).

Materialised views refresh on demand (REFRESH MATERIALIZED VIEW CONCURRENTLY).
Caller: Database.refresh_relationship_views() called at end of each scan run.

Views created:
    mv_vuln_same_rule     — vuln pairs sharing canonical_rule_id
    mv_vuln_same_file     — vuln pairs sharing file_path (different rules)
    mv_vuln_taint_chain   — vuln pairs sharing a taint_source via findings
    mv_vuln_author        — owner → vuln_id index

Revision ID: 0020
Revises: 0019
Create Date: 2026-05-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_vuln_same_rule AS
        SELECT
            v1.id  AS vuln_id,
            v2.id  AS related_id,
            'same_rule'::text AS edge_type,
            1.0::float AS score
        FROM vulnerabilities v1
        JOIN vulnerabilities v2
            ON  v2.canonical_rule_id = v1.canonical_rule_id
            AND v2.id   <> v1.id
            AND v2.status NOT IN ('dismissed')
        WHERE v1.status NOT IN ('dismissed')
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS mv_vuln_same_rule_pk ON mv_vuln_same_rule (vuln_id, related_id)")

    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_vuln_same_file AS
        SELECT
            v1.id  AS vuln_id,
            v2.id  AS related_id,
            'same_file'::text AS edge_type,
            0.8::float AS score
        FROM vulnerabilities v1
        JOIN vulnerabilities v2
            ON  v2.file_path          = v1.file_path
            AND v2.canonical_rule_id <> v1.canonical_rule_id
            AND v2.id <> v1.id
            AND v2.status NOT IN ('dismissed')
        WHERE v1.status NOT IN ('dismissed')
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS mv_vuln_same_file_pk ON mv_vuln_same_file (vuln_id, related_id)")

    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_vuln_taint_chain AS
        SELECT DISTINCT
            f1.vulnerability_id  AS vuln_id,
            f2.vulnerability_id  AS related_id,
            'taint_chain'::text  AS edge_type,
            0.9::float           AS score
        FROM findings f1
        JOIN findings f2
            ON  f2.taint_source      = f1.taint_source
            AND f2.vulnerability_id <> f1.vulnerability_id
            AND f2.vulnerability_id  IS NOT NULL
        WHERE f1.taint_source       IS NOT NULL
          AND f1.vulnerability_id   IS NOT NULL
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS mv_vuln_taint_chain_pk ON mv_vuln_taint_chain (vuln_id, related_id)")

    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_vuln_author AS
        SELECT owner, id AS vuln_id
        FROM vulnerabilities
        WHERE owner IS NOT NULL
          AND status NOT IN ('dismissed')
    """)
    op.execute("CREATE INDEX IF NOT EXISTS mv_vuln_author_owner ON mv_vuln_author (owner)")


def downgrade() -> None:
    for view in ("mv_vuln_author", "mv_vuln_taint_chain", "mv_vuln_same_file", "mv_vuln_same_rule"):
        op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {view}")
