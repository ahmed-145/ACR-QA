"""
PostgreSQL Database Interface for ACR-QA v2.0
Handles provenance storage and retrieval
"""

import json
import logging
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json, RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

# Load .env from project root
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)


class Database:
    _pool = None

    def __init__(self):
        """Initialize database connection pool"""
        self.conn_params = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432"),
            "database": os.getenv("DB_NAME", "acrqa"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", "postgres"),
        }
        self._connect()

    def _connect(self):
        """Establish database connection pool"""
        if Database._pool is None:
            try:
                Database._pool = ThreadedConnectionPool(1, 10, **self.conn_params)
            except psycopg2.Error as e:
                logger.error(f"❌ Database connection pool failed: {e}")
                Database._pool = None

    def execute(self, query, params=None, fetch=False):
        """
        Execute a query with error handling

        Args:
            query: SQL query string
            params: Query parameters (tuple or dict)
            fetch: If True, return results

        Returns:
            Query results if fetch=True, else None
        """
        if Database._pool is None:
            self._connect()
        if Database._pool is None:
            raise psycopg2.OperationalError("Database connection pool unavailable")

        conn = Database._pool.getconn()
        try:
            conn.autocommit = False
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)

                if fetch:
                    res = cur.fetchall()
                    conn.commit()
                    return res

                conn.commit()

                # Return last inserted ID if applicable
                if "INSERT" in query.upper() and "RETURNING" in query.upper():
                    return cur.fetchone()

        except psycopg2.Error as e:
            conn.rollback()
            logger.error(f"❌ Query failed: {e}")
            logger.info(f"   Query: {query}")
            raise
        finally:
            Database._pool.putconn(conn)

    # ===== ANALYSIS RUNS =====

    def create_analysis_run(self, repo_name, pr_number=None, commit_sha=None, branch=None):
        """Create a new analysis run"""
        query = """
            INSERT INTO analysis_runs (repo_name, pr_number, commit_sha, branch, status)
            VALUES (%s, %s, %s, %s, 'running')
            RETURNING id
        """
        result = self.execute(query, (repo_name, pr_number, commit_sha, branch), fetch=True)
        return result[0]["id"] if result else None

    def complete_analysis_run(self, run_id, total_findings):
        """Mark analysis run as completed"""
        query = """
            UPDATE analysis_runs
            SET status = 'completed',
                completed_at = CURRENT_TIMESTAMP,
                total_findings = %s
            WHERE id = %s
        """
        self.execute(query, (total_findings, run_id))

    def update_run_cost(self, run_id: int, tokens_used: int, cost_usd: float, requests: int) -> None:
        """Record Groq token cost telemetry for a completed run (task 12.32)."""
        query = """
            UPDATE analysis_runs
            SET groq_tokens_used = %s,
                groq_cost_usd    = %s,
                groq_requests    = %s
            WHERE id = %s
        """
        self.execute(query, (tokens_used, cost_usd, requests, run_id))

    def fail_analysis_run(self, run_id, _error_message=None):
        """Mark analysis run as failed

        Args:
            run_id: Run ID to mark as failed
            _error_message: Optional error message (reserved for future logging)
        """
        query = """
            UPDATE analysis_runs
            SET status = 'failed',
                completed_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        self.execute(query, (run_id,))

    def get_analysis_run(self, run_id):
        """Get analysis run details"""
        query = "SELECT * FROM analysis_runs WHERE id = %s"
        results = self.execute(query, (run_id,), fetch=True)
        return results[0] if results else None

    def list_analysis_runs(self, limit=50):
        """List recent analysis runs"""
        query = """
            SELECT id, repo_name, pr_number, status,
                   started_at, completed_at, total_findings
            FROM analysis_runs
            ORDER BY started_at DESC
            LIMIT %s
        """
        return self.execute(query, (limit,), fetch=True)

    # ===== ALIASES FOR COMPATIBILITY =====

    def get_run_info(self, run_id):
        """Get run metadata (alias for get_analysis_run)"""
        return self.get_analysis_run(run_id)

    def get_recent_runs(self, limit=10):
        """Get recent analysis runs (alias for list_analysis_runs)"""
        return self.list_analysis_runs(limit)

    # ===== FINDINGS =====

    def insert_finding(self, run_id, finding_dict):
        """Insert a normalized finding with confidence score."""
        from CORE.engines.confidence_scorer import ConfidenceScorer

        scorer = ConfidenceScorer()
        confidence = scorer.score(finding_dict)

        query = """
            INSERT INTO findings (
                run_id, tool, rule_id, canonical_rule_id, canonical_severity,
                file_path, line_number, column_number,
                severity, category, message, evidence, raw_output,
                confidence_score
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id
        """
        values = (
            run_id,
            finding_dict.get("tool_raw", {}).get("tool_name", "unknown")
            if not finding_dict.get("tool")
            else finding_dict.get("tool"),
            finding_dict.get("original_rule_id")
            or finding_dict.get("rule_id")
            or finding_dict.get("canonical_rule_id", "UNKNOWN"),
            finding_dict.get("canonical_rule_id") or finding_dict.get("rule_id", "UNKNOWN"),
            finding_dict.get("severity", "low"),
            finding_dict.get("file", "unknown"),
            finding_dict.get("line", 0),
            finding_dict.get("column", 0),
            finding_dict.get("severity", "low"),
            finding_dict.get("category", "unknown"),
            finding_dict.get("message", ""),
            Json(finding_dict.get("evidence", {})),
            Json(finding_dict.get("tool_raw", {})),
            confidence,
        )
        result = self.execute(query, values, fetch=True)
        return result[0]["id"] if result else None

    def update_finding_reachability(self, finding_id: int, status: str, penalty: int) -> None:
        """Persist call-graph reachability result for a finding (Feature 9)."""
        query = """
            UPDATE findings
            SET reachability_status = %s, reachability_penalty = %s
            WHERE id = %s
        """
        self.execute(query, (status, penalty, finding_id))

    def update_finding_triage(
        self,
        finding_id: int,
        verdict: str,
        reasoning: str,
        confidence_delta: float,
    ) -> None:
        """Persist triage agent verdict for a finding (Phase 3)."""
        query = """
            UPDATE findings
            SET triage_verdict = %s, triage_reasoning = %s, triage_confidence_delta = %s
            WHERE id = %s
        """
        self.execute(query, (verdict, reasoning, confidence_delta, finding_id))

    def update_finding_taint(
        self,
        finding_id: int,
        taint_source: str,
        taint_path: list,
        taint_confidence: float,
    ) -> None:
        """Persist taint analysis result for a finding (Phase 1)."""
        query = """
            UPDATE findings
            SET taint_source = %s, taint_path = %s, taint_confidence = %s
            WHERE id = %s
        """
        self.execute(query, (taint_source, Json(taint_path), taint_confidence, finding_id))

    def update_finding_correlation(self, finding_id, confidence_score, evidence):
        """Update a finding's confidence and evidence with cross-language correlation data"""
        query = """
            UPDATE findings
            SET confidence_score = %s, evidence = %s
            WHERE id = %s
        """
        self.execute(query, (confidence_score, Json(evidence), finding_id))

    def get_findings(self, run_id=None, severity=None, category=None, limit=100):
        """Query findings with filters"""
        conditions = []
        params = []

        if run_id:
            conditions.append("run_id = %s")
            params.append(run_id)

        if severity:
            conditions.append("canonical_severity = %s")
            params.append(severity)

        if category:
            conditions.append("category = %s")
            params.append(category)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
            SELECT * FROM findings
            {where_clause}
            ORDER BY
                CASE canonical_severity
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END,
                file_path, line_number
            LIMIT %s
        """

        params.append(limit)
        return self.execute(query, tuple(params), fetch=True)

    def get_findings_with_explanations(self, run_id):
        """Get all findings with their explanations for a run"""
        query = """
            SELECT
                f.id,
                f.rule_id,
                f.canonical_rule_id,
                f.file_path,
                f.line_number,
                f.canonical_severity,
                f.category,
                f.message,
                f.tool,
                f.ground_truth,
                f.confidence_score,
                e.response_text as explanation_text,
                e.latency_ms,
                e.model_name,
                e.fix_validated,
                e.fix_confidence,
                e.fix_code,
                e.fix_validation_note
            FROM findings f
            LEFT JOIN llm_explanations e ON f.id = e.finding_id
            WHERE f.run_id = %s
            ORDER BY
                CASE f.canonical_severity
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    ELSE 3
                END,
                f.file_path,
                f.line_number
        """
        return self.execute(query, (run_id,), fetch=True)

    def get_validated_fixes(self, run_id):
        """
        Return findings that have a validated AI fix ready to apply.
        Only returns rows where fix_validated=True and fix_code is not null.
        Used by create_fix_pr.py to build the autofix PR.
        """
        query = """
            SELECT
                f.id as finding_id,
                f.canonical_rule_id,
                f.file_path,
                f.line_number,
                f.canonical_severity,
                f.message,
                f.confidence_score,
                e.fix_code,
                e.fix_confidence,
                e.fix_validation_note,
                e.response_text as explanation_text
            FROM findings f
            JOIN llm_explanations e ON f.id = e.finding_id
            WHERE f.run_id = %s
              AND e.fix_validated = TRUE
              AND e.fix_code IS NOT NULL
              AND e.fix_code != ''
            ORDER BY
                CASE f.canonical_severity
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    ELSE 3
                END,
                f.file_path,
                f.line_number
        """
        return self.execute(query, (run_id,), fetch=True)

    def update_finding_ground_truth(self, finding_id, ground_truth):
        """Update ground truth label for evaluation"""
        if ground_truth not in ["TP", "FP", "TN", "FN"]:
            raise ValueError(f"Invalid ground_truth: {ground_truth}")

        query = """
            UPDATE findings
            SET ground_truth = %s
            WHERE id = %s
        """
        self.execute(query, (ground_truth, finding_id))

    # ===== LLM EXPLANATIONS =====

    def insert_explanation(self, finding_id, explanation_dict):
        """Store LLM explanation with full provenance including fix validation and feasibility."""
        query = """
            INSERT INTO llm_explanations (
                finding_id, model_name, prompt_filled, response_text,
                temperature, max_tokens, tokens_used,
                latency_ms, cost_usd, status,
                fix_validated, fix_confidence, fix_code, fix_validation_note,
                feasibility_verdict, feasibility_confidence,
                feasibility_reasoning, feasibility_latency_ms, feasibility_penalty
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            ) RETURNING id
        """
        params = (
            finding_id,
            explanation_dict.get("model_name", "unknown"),
            explanation_dict.get("prompt_filled", ""),
            explanation_dict.get("response_text", ""),
            explanation_dict.get("temperature", 0.3),
            explanation_dict.get("max_tokens", 150),
            explanation_dict.get("tokens_used"),
            explanation_dict.get("latency_ms", 0),
            explanation_dict.get("cost_usd", 0),
            explanation_dict.get("status", "success"),
            explanation_dict.get("fix_validated"),
            explanation_dict.get("fix_confidence"),
            explanation_dict.get("validated_fix"),
            explanation_dict.get("fix_validation_note"),
            explanation_dict.get("feasibility_verdict"),
            explanation_dict.get("feasibility_confidence"),
            explanation_dict.get("feasibility_reasoning"),
            explanation_dict.get("feasibility_latency_ms"),
            explanation_dict.get("feasibility_penalty"),
        )
        result = self.execute(query, params, fetch=True)
        return result[0]["id"] if result else None

    def get_explanations(self, finding_id=None, run_id=None):
        """Get explanations with optional filters"""
        if finding_id:
            query = """
                SELECT * FROM llm_explanations
                WHERE finding_id = %s
                ORDER BY created_at DESC
            """
            return self.execute(query, (finding_id,), fetch=True)

        elif run_id:
            query = """
                SELECT e.* FROM llm_explanations e
                JOIN findings f ON e.finding_id = f.id
                WHERE f.run_id = %s
                ORDER BY e.created_at DESC
            """
            return self.execute(query, (run_id,), fetch=True)

        else:
            query = """
                SELECT * FROM llm_explanations
                ORDER BY created_at DESC
                LIMIT 100
            """
            return self.execute(query, fetch=True)

    # ===== FEEDBACK =====

    def insert_feedback(
        self,
        finding_id,
        user_id,
        is_false_positive=None,
        is_helpful=None,
        clarity_rating=None,
        comment=None,
    ):
        """Store user feedback"""
        query = """
            INSERT INTO feedback (
                finding_id, user_id, is_false_positive,
                is_helpful, clarity_rating, comment
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (
            finding_id,
            user_id,
            is_false_positive,
            is_helpful,
            clarity_rating,
            comment,
        )
        result = self.execute(query, params, fetch=True)
        return result[0]["id"] if result else None

    def get_feedback_stats(self, run_id=None):
        """Get aggregated feedback statistics"""
        if run_id:
            query = """
                SELECT
                    COUNT(*) as total_feedback,
                    SUM(CASE WHEN is_false_positive THEN 1 ELSE 0 END) as false_positives,
                    AVG(clarity_rating) as avg_clarity_rating,
                    SUM(CASE WHEN is_helpful THEN 1 ELSE 0 END) as helpful_count
                FROM feedback fb
                JOIN findings f ON fb.finding_id = f.id
                WHERE f.run_id = %s
            """
            results = self.execute(query, (run_id,), fetch=True)
        else:
            query = """
                SELECT
                    COUNT(*) as total_feedback,
                    SUM(CASE WHEN is_false_positive THEN 1 ELSE 0 END) as false_positives,
                    AVG(clarity_rating) as avg_clarity_rating,
                    SUM(CASE WHEN is_helpful THEN 1 ELSE 0 END) as helpful_count
                FROM feedback
            """
            results = self.execute(query, fetch=True)

        return results[0] if results else {}

    # ===== SUPPRESSION RULES (Feature 6 — Triage Memory) =====

    def insert_suppression_rule(
        self,
        canonical_rule_id: str,
        file_pattern: str | None,
        finding_id: int | None,
    ) -> int | None:
        """Insert a learned suppression rule derived from an FP-marked finding."""
        query = """
            INSERT INTO suppression_rules
                (canonical_rule_id, file_pattern, created_from_finding_id)
            VALUES (%s, %s, %s)
            RETURNING id
        """
        result = self.execute(query, (canonical_rule_id, file_pattern, finding_id), fetch=True)
        return result[0]["id"] if result else None

    def get_suppression_rules(self, active_only: bool = True) -> list[dict]:
        """Return suppression rules, optionally filtered to active-only."""
        if active_only:
            query = """
                SELECT id, canonical_rule_id, file_pattern,
                       created_from_finding_id, created_at,
                       is_active, suppression_count
                FROM suppression_rules
                WHERE is_active = TRUE
                ORDER BY created_at DESC
            """
            results = self.execute(query, fetch=True)
        else:
            query = """
                SELECT id, canonical_rule_id, file_pattern,
                       created_from_finding_id, created_at,
                       is_active, suppression_count
                FROM suppression_rules
                ORDER BY created_at DESC
            """
            results = self.execute(query, fetch=True)
        return [dict(r) for r in results] if results else []

    def increment_suppression_count(self, rule_id: int) -> None:
        """Increment the suppression counter for a given rule."""
        self.execute(
            "UPDATE suppression_rules SET suppression_count = suppression_count + 1 WHERE id = %s",
            (rule_id,),
        )

    # ===== ANALYTICS =====

    def get_run_summary(self, run_id):
        """Get comprehensive summary for a run"""
        query = """
            SELECT
                r.*,
                COUNT(f.id) as findings_count,
                COUNT(CASE WHEN f.canonical_severity = 'high' THEN 1 END) as high_severity_count,
                COUNT(CASE WHEN f.canonical_severity = 'medium' THEN 1 END) as medium_severity_count,
                COUNT(CASE WHEN f.canonical_severity = 'low' THEN 1 END) as low_severity_count,
                COUNT(e.id) as explanations_count,
                AVG(e.latency_ms) as avg_explanation_latency,
                SUM(e.cost_usd) as total_cost
            FROM analysis_runs r
            LEFT JOIN findings f ON r.id = f.run_id
            LEFT JOIN llm_explanations e ON f.id = e.finding_id
            WHERE r.id = %s
            GROUP BY r.id
        """
        results = self.execute(query, (run_id,), fetch=True)
        return results[0] if results else None

    def get_trend_data(self, limit=30, repo_name=None):
        """
        Get trend data for analytics dashboard.
        Aggregates findings by severity, category, and confidence across recent runs.
        Optionally filter by repo_name.
        """
        where_clause = "WHERE ar.status = 'completed'"
        params: list = []
        if repo_name:
            where_clause += " AND ar.repo_name = %s"
            params.append(repo_name)
        params.append(limit)

        query = f"""
            SELECT
                ar.id as run_id,
                ar.repo_name,
                ar.started_at,
                ar.total_findings,
                COALESCE(SUM(CASE WHEN f.canonical_severity = 'high' THEN 1 ELSE 0 END), 0) as high_count,
                COALESCE(SUM(CASE WHEN f.canonical_severity = 'medium' THEN 1 ELSE 0 END), 0) as medium_count,
                COALESCE(SUM(CASE WHEN f.canonical_severity = 'low' THEN 1 ELSE 0 END), 0) as low_count,
                COALESCE(SUM(CASE WHEN f.category = 'security' THEN 1 ELSE 0 END), 0) as security_count,
                COALESCE(SUM(CASE WHEN f.category = 'style' THEN 1 ELSE 0 END), 0) as style_count,
                COALESCE(SUM(CASE WHEN f.category = 'design' THEN 1 ELSE 0 END), 0) as design_count,
                COALESCE(SUM(CASE WHEN f.category = 'best-practice' THEN 1 ELSE 0 END), 0) as best_practice_count,
                COALESCE(AVG(f.confidence_score), 0) as avg_confidence,
                COALESCE(SUM(CASE WHEN f.confidence_score >= 70 THEN 1 ELSE 0 END), 0) as high_confidence_count
            FROM analysis_runs ar
            LEFT JOIN findings f ON ar.id = f.run_id
            {where_clause}
            GROUP BY ar.id, ar.repo_name, ar.started_at, ar.total_findings
            ORDER BY ar.started_at DESC
            LIMIT %s
        """
        return self.execute(query, tuple(params), fetch=True)

    def get_repos_with_runs(self) -> list[str]:
        """Get list of distinct repo names that have completed runs."""
        query = """
            SELECT DISTINCT repo_name
            FROM analysis_runs
            WHERE status = 'completed' AND repo_name NOT LIKE 'test-%'
            ORDER BY repo_name
        """
        rows = self.execute(query, fetch=True)
        return [r["repo_name"] for r in rows] if rows else []

    # ===== FINDING EMBEDDINGS (learned suppression v2) =====

    def insert_finding_embedding(
        self,
        rule_id: str,
        embedding_json: str,
        code_context: str | None = None,
        finding_id: int | None = None,
    ) -> int | None:
        """Store a sentence-transformer embedding for a dismissed finding."""
        query = """
            INSERT INTO finding_embeddings (finding_id, rule_id, code_context, embedding_json)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        result = self.execute(query, (finding_id, rule_id, code_context, embedding_json), fetch=True)
        return result[0]["id"] if result else None

    def get_all_finding_embeddings(self) -> list[dict]:
        """Return all stored dismissal embeddings for similarity matching."""
        query = """
            SELECT id, finding_id, rule_id, code_context, embedding_json
            FROM finding_embeddings
            ORDER BY suppressed_at DESC
        """
        rows = self.execute(query, fetch=True)
        return [dict(r) for r in rows] if rows else []

    def get_finding_embeddings_by_rule(self, rule_id: str) -> list[dict]:
        """Return embeddings filtered to a specific canonical rule_id."""
        query = """
            SELECT id, finding_id, rule_id, code_context, embedding_json
            FROM finding_embeddings
            WHERE rule_id = %s
            ORDER BY suppressed_at DESC
        """
        rows = self.execute(query, (rule_id,), fetch=True)
        return [dict(r) for r in rows] if rows else []

    def delete_finding_embedding(self, embedding_id: int) -> None:
        """Remove a stored embedding (e.g. when a suppression is reverted)."""
        self.execute("DELETE FROM finding_embeddings WHERE id = %s", (embedding_id,))

    # ===== EXPLOIT VERIFICATION (Feature 12) =====

    def update_finding_exploit_status(
        self,
        finding_id: int,
        tier: str,
        proof_json: str | None = None,
        verified: bool = False,
    ) -> None:
        """Persist exploit verification result onto an existing findings row."""
        query = """
            UPDATE findings
            SET exploit_tier = %s,
                exploit_proof = %s,
                exploit_verified = %s
            WHERE id = %s
        """
        self.execute(query, (tier, proof_json, verified, finding_id))

    # ===== SCAN ATTESTATIONS (Feature 13) =====

    def store_attestation(
        self,
        run_id: int,
        attestation_json: str,
        signature: str | None = None,
        key_id: str | None = None,
    ) -> int | None:
        """Persist a signed attestation bundle for a completed scan run."""
        query = """
            INSERT INTO scan_attestations (run_id, attestation_json, signature, key_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        result = self.execute(query, (run_id, attestation_json, signature, key_id), fetch=True)
        return result[0]["id"] if result else None

    def get_attestation(self, run_id: int) -> dict | None:
        """Retrieve the most recent attestation for a run, or None."""
        query = """
            SELECT id, run_id, attestation_json, signature, key_id, created_at
            FROM scan_attestations
            WHERE run_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """
        rows = self.execute(query, (run_id,), fetch=True)
        return dict(rows[0]) if rows else None

    def insert_dependency_finding(self, run_id: int, dep: dict) -> int | None:
        """Insert one dependency finding; return the new row id."""
        query = """
            INSERT INTO dependency_findings
                (run_id, name, version, ecosystem, risk_score, risk_level,
                 cve_count, cve_ids, stars, last_commit_days, contributors,
                 archived, license, repo_url, sbom_purl)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        cve_ids = [v.get("id", "") for v in dep.get("cves", [])]
        rows = self.execute(
            query,
            (
                run_id,
                dep.get("name", ""),
                dep.get("version", "unknown"),
                dep.get("ecosystem", ""),
                dep.get("risk_score", 0),
                dep.get("risk_level", "low"),
                dep.get("cve_count", 0),
                json.dumps(cve_ids),
                dep.get("stars"),
                dep.get("last_commit_days"),
                dep.get("contributors"),
                dep.get("archived"),
                dep.get("license"),
                dep.get("repo_url"),
                dep.get("purl", ""),
            ),
            fetch=True,
        )
        return rows[0]["id"] if rows else None

    def get_dependency_findings(self, run_id: int) -> list[dict]:
        """Return all dependency findings for a run."""
        query = """
            SELECT id, run_id, name, version, ecosystem, risk_score, risk_level,
                   cve_count, cve_ids, stars, last_commit_days, contributors,
                   archived, license, repo_url, sbom_purl, created_at
            FROM dependency_findings
            WHERE run_id = %s
            ORDER BY risk_score DESC
        """
        rows = self.execute(query, (run_id,), fetch=True)
        return [dict(r) for r in rows] if rows else []

    def upsert_run_sbom(self, run_id: int, sbom_json: dict) -> None:
        """Store the CycloneDX SBOM for a run (upsert)."""
        query = """
            INSERT INTO run_sboms (run_id, sbom_json, created_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (run_id) DO UPDATE SET sbom_json = EXCLUDED.sbom_json,
                                               created_at = NOW()
        """
        self.execute(query, (run_id, json.dumps(sbom_json)))

    def get_run_sbom(self, run_id: int) -> dict | None:
        """Return the stored SBOM for a run, or None."""
        query = "SELECT sbom_json FROM run_sboms WHERE run_id = %s"
        rows = self.execute(query, (run_id,), fetch=True)
        if not rows:
            return None
        raw = rows[0]["sbom_json"]
        if isinstance(raw, str):
            return json.loads(raw)
        return raw

    def get_rule_timeline(self, limit: int = 30, repo_name: str | None = None) -> list[dict]:
        """
        Return per-(rule_id, run) presence across the last N completed runs.

        Result rows (run-ordered oldest→newest within rule):
            {rule_id, canonical_severity, run_id, started_at, repo_name, count}

        Used by GET /v1/runs/timeline (Vulnerability Timeline, v5.0.0 Phase A.1).
        """
        where_clause = "WHERE ar.status = 'completed'"
        params: list = []
        if repo_name:
            where_clause += " AND ar.repo_name = %s"
            params.append(repo_name)
        params.append(limit)

        query = f"""
            WITH recent_runs AS (
                SELECT ar.id, ar.repo_name, ar.started_at
                FROM analysis_runs ar
                {where_clause}
                ORDER BY ar.started_at DESC
                LIMIT %s
            )
            SELECT
                f.canonical_rule_id AS rule_id,
                MAX(f.canonical_severity) AS canonical_severity,
                rr.id AS run_id,
                rr.repo_name,
                rr.started_at,
                COUNT(*) AS count
            FROM findings f
            JOIN recent_runs rr ON rr.id = f.run_id
            WHERE f.canonical_rule_id IS NOT NULL
            GROUP BY f.canonical_rule_id, rr.id, rr.repo_name, rr.started_at
            ORDER BY rr.started_at ASC, f.canonical_rule_id ASC
        """
        return self.execute(query, tuple(params), fetch=True) or []

    # ===== FINDING CHAT (v5.0.0 Phase A.1) =====

    def insert_chat_message(
        self,
        finding_id: int,
        role: str,
        content: str,
        user_id: int | None = None,
        preset: str | None = None,
        model_name: str | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        latency_ms: int | None = None,
    ) -> int | None:
        """Persist one chat message for a finding. Returns inserted id."""
        query = """
            INSERT INTO finding_chat_messages
                (finding_id, user_id, role, preset, content,
                 model_name, tokens_in, tokens_out, latency_ms)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        result = self.execute(
            query,
            (
                finding_id,
                user_id,
                role,
                preset,
                content,
                model_name,
                tokens_in,
                tokens_out,
                latency_ms,
            ),
            fetch=True,
        )
        return result[0]["id"] if result else None

    def get_chat_messages(self, finding_id: int, limit: int = 200) -> list[dict]:
        """Return messages for a finding ordered oldest → newest."""
        query = """
            SELECT id, finding_id, user_id, role, preset, content,
                   model_name, tokens_in, tokens_out, latency_ms, created_at
            FROM finding_chat_messages
            WHERE finding_id = %s
            ORDER BY created_at ASC, id ASC
            LIMIT %s
        """
        rows = self.execute(query, (finding_id, limit), fetch=True) or []
        return rows

    def clear_chat_messages(self, finding_id: int) -> int:
        """Delete all chat messages for a finding. Returns count deleted."""
        query = "DELETE FROM finding_chat_messages WHERE finding_id = %s"
        rows = self.execute(query, (finding_id,), fetch=False)
        return rows if isinstance(rows, int) else 0

    def get_finding_by_id(self, finding_id: int) -> dict | None:
        """Fetch a single finding row by id (or None)."""
        query = "SELECT * FROM findings WHERE id = %s"
        rows = self.execute(query, (finding_id,), fetch=True)
        return rows[0] if rows else None

    def close(self):
        """Close database connection pool"""
        if Database._pool:
            Database._pool.closeall()
            Database._pool = None


# Test connection
if __name__ == "__main__":
    logger.info("Testing database connection...")
    try:
        db = Database()
        runs = db.get_recent_runs(limit=5)
        logger.info(f"✅ Connected! Found {len(runs)} recent analysis runs")
        db.close()
    except Exception as e:
        logger.error(f"❌ Connection failed: {e}")
