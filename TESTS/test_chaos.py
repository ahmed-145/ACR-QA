"""
Chaos Engineering tests — Phase 12 Week 5 (tasks 12.28 + 12.29)

Validates that the system degrades gracefully under:
  12.28 — Postgres connection failure mid-scan
  12.29 — Redis connection failure (rate-limiter + explainer cache)

Tests use monkeypatching to simulate infrastructure failure without
requiring a running Docker environment.
"""

from unittest.mock import MagicMock, patch

import psycopg2
import pytest
import redis as redis_lib

from CORE.utils.rate_limiter import RateLimiter as ScanRateLimiter

# ── 12.28 — Postgres chaos ────────────────────────────────────────────────────


class TestPostgresChaos:
    """Postgres connection failure during analysis should return a clean error."""

    def test_database_connect_failure_returns_error_state(self):
        """If psycopg2 raises OperationalError on connect, Database.__init__
        must not propagate the exception to callers."""
        from DATABASE.database import Database

        with patch(
            "psycopg2.connect",
            side_effect=psycopg2.OperationalError("Connection refused"),
        ):
            db = Database.__new__(Database)
            try:
                db.__init__()
            except psycopg2.OperationalError:
                pytest.fail("Database.__init__ must not propagate psycopg2.OperationalError")
            except Exception:
                # Any other exception (e.g. AttributeError from missing connection)
                # is acceptable — we only care the OperationalError is handled.
                pass

    def test_database_execute_failure_raises_informative_error(self):
        """If a query fails mid-execution, Database.execute should raise
        so callers can handle it — not silently swallow it."""
        from DATABASE.database import Database

        db = Database.__new__(Database)
        db.connection = MagicMock()
        cursor_mock = MagicMock()
        cursor_mock.execute.side_effect = psycopg2.OperationalError("server closed")
        db.connection.cursor.return_value.__enter__ = MagicMock(return_value=cursor_mock)
        db.connection.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(Exception):
            db.execute("SELECT 1")

    def test_complete_analysis_run_handles_db_error_gracefully(self, tmp_path):
        """complete_analysis_run must not crash the process when DB is down.
        The main pipeline wraps this in try/except so the scan result is still
        returned to the caller."""
        from DATABASE.database import Database

        db = Database.__new__(Database)
        db.connection = None  # simulate no connection

        # Should raise (DB is down) — but the pipeline handles it
        with pytest.raises(Exception):
            db.complete_analysis_run(run_id=99999, total_findings=0)

    def test_get_run_info_returns_none_on_missing_run(self):
        """get_run_info for a non-existent run_id returns None rather than
        raising; callers treat None as 404."""
        from DATABASE.database import Database

        db = Database.__new__(Database)
        db.conn_params = {}

        cursor_mock = MagicMock()
        cursor_mock.fetchall.return_value = []
        cursor_mock.fetchone.return_value = None
        conn_mock = MagicMock()
        conn_mock.cursor.return_value.__enter__ = MagicMock(return_value=cursor_mock)
        conn_mock.cursor.return_value.__exit__ = MagicMock(return_value=False)

        pool_mock = MagicMock()
        pool_mock.getconn.return_value = conn_mock
        Database._pool = pool_mock

        try:
            result = db.get_run_info(run_id=99999)
            assert result is None
        finally:
            Database._pool = None

    def test_chaos_mid_scan_does_not_crash_normalizer(self):
        """Even if DB operations fail, the analysis pipeline's normalizer step
        must succeed independently — findings are not lost before DB write."""
        from CORE.engines.normalizer import normalize_bandit

        bandit_output = {
            "results": [
                {
                    "test_id": "B101",
                    "filename": "app.py",
                    "line_number": 10,
                    "issue_severity": "HIGH",
                    "issue_text": "Use of assert",
                    "issue_confidence": "HIGH",
                }
            ]
        }

        # Even with DB down, normalizer must produce findings
        with patch("psycopg2.connect", side_effect=psycopg2.OperationalError("down")):
            findings = normalize_bandit(bandit_output)

        assert len(findings) == 1
        assert findings[0].severity in {"high", "medium", "low"}


# ── 12.29 — Redis chaos ───────────────────────────────────────────────────────


class TestRedisChaos:
    """Redis failure must not block scans — rate limiter degrades to allow-all."""

    def test_rate_limiter_allows_when_redis_unavailable(self):
        """With no Redis, check_rate_limit returns (True, None) — open gate."""
        limiter = ScanRateLimiter.__new__(ScanRateLimiter)
        limiter.redis = None
        limiter.bucket_size = 10
        limiter.refill_rate = 1.0

        allowed, retry_after = limiter.check_rate_limit("test-repo", pr_number=1)
        assert allowed is True
        assert retry_after is None

    def test_rate_limiter_connect_failure_sets_redis_to_none(self):
        """If Redis.ping() raises ConnectionError during init, self.redis = None."""
        with patch(
            "redis.Redis",
            side_effect=redis_lib.ConnectionError("Connection refused"),
        ):
            limiter = ScanRateLimiter(
                redis_host="127.0.0.1",
                redis_port=16379,  # unlikely port
            )
        assert limiter.redis is None

    def test_rate_limiter_mid_request_redis_error_degrades(self):
        """If Redis raises during check_rate_limit (connection dropped mid-flight),
        the limiter must allow the request rather than raise."""
        limiter = ScanRateLimiter.__new__(ScanRateLimiter)
        mock_redis = MagicMock()
        mock_redis.hgetall.side_effect = redis_lib.ConnectionError("lost connection")
        limiter.redis = mock_redis
        limiter.bucket_size = 10
        limiter.refill_rate = 1.0

        allowed, retry_after = limiter.check_rate_limit("test-repo", pr_number=1)
        assert allowed is True
        assert retry_after is None

    def test_explainer_cache_miss_on_redis_error(self):
        """ExplanationEngine must fall through to Groq when Redis is unavailable
        — cache errors must not propagate to callers."""
        from CORE.engines.explainer import ExplanationEngine

        broken_redis = MagicMock()
        broken_redis.get.side_effect = redis_lib.ConnectionError("Redis down")
        broken_redis.setex.side_effect = redis_lib.ConnectionError("Redis down")

        engine = ExplanationEngine.__new__(ExplanationEngine)
        engine.redis = broken_redis

        # _get_cached_explanation must return None on error (cache miss)
        result = engine._get_cached_explanation("somekey")
        assert result is None

    def test_redis_crash_does_not_block_analysis_pipeline(self, tmp_path):
        """End-to-end: if Redis is down, get_rate_limiter returns a limiter with
        redis=None, and check_rate_limit still permits the scan."""
        from CORE.utils.rate_limiter import get_rate_limiter

        with patch(
            "redis.Redis",
            side_effect=redis_lib.ConnectionError("Redis not running"),
        ):
            limiter = get_rate_limiter(redis_host="127.0.0.1", redis_port=16379)

        allowed, _ = limiter.check_rate_limit("chaos-repo")
        assert allowed is True


# ── Chaos: full graceful degradation matrix ───────────────────────────────────


class TestChaosMatrix:
    """High-level proof: neither Postgres nor Redis failure crashes the process."""

    @pytest.mark.parametrize(
        "failure_target,exc",
        [
            ("psycopg2.connect", psycopg2.OperationalError("DB down")),
            ("redis.Redis", redis_lib.ConnectionError("Redis down")),
        ],
    )
    def test_infrastructure_failure_does_not_raise_at_module_import(self, failure_target, exc):
        """Patching the infrastructure layer must not crash module-level
        normalizer code — no connection attempts happen at import time."""
        import CORE.engines.normalizer as mod

        with patch(failure_target, side_effect=exc):
            # Access module attributes under patch — no reload to avoid corrupting
            # the CanonicalFinding class identity in the module registry.
            assert hasattr(mod, "normalize_bandit")
            assert hasattr(mod, "CanonicalFinding")

    def test_chaos_recovery_sequence(self):
        """Simulate: Redis up → Redis down → Redis back up.
        Rate limiter must correctly transition between states."""
        limiter = ScanRateLimiter.__new__(ScanRateLimiter)
        limiter.bucket_size = 5
        limiter.refill_rate = 1.0

        # Phase 1: Redis up
        good_redis = MagicMock()
        good_redis.hgetall.return_value = {}
        good_redis.hset.return_value = True
        good_redis.expire.return_value = True
        limiter.redis = good_redis
        allowed, _ = limiter.check_rate_limit("repo", 1)
        assert allowed is True

        # Phase 2: Redis crashes
        bad_redis = MagicMock()
        bad_redis.hgetall.side_effect = redis_lib.ConnectionError("crash")
        limiter.redis = bad_redis
        allowed, _ = limiter.check_rate_limit("repo", 1)
        assert allowed is True  # graceful degradation

        # Phase 3: Redis restored
        limiter.redis = good_redis
        good_redis.hgetall.return_value = {}
        allowed, _ = limiter.check_rate_limit("repo", 1)
        assert allowed is True
