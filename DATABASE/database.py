"""
PostgreSQL Database Interface for ACR-QA v2.0
Handles provenance storage and retrieval
"""

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
                raise

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
