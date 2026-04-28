"""
God-mode tests for:
  - CORE/utils/metrics.py    (target: 90%+)
  - CORE/utils/rate_limiter.py (target: 85%+)
"""

import time
from unittest.mock import MagicMock, patch

import pytest
import redis

# ════════════════════════════════════════════════════════════
#  MetricsCollector
# ════════════════════════════════════════════════════════════
from CORE.utils.metrics import (
    MetricsCollector,
    record_analysis_metrics,
    record_explanation_metrics,
    record_finding_metrics,
    register_metrics_endpoint,
    track_request,
)


class TestMetricsCollectorInit:
    def test_starts_empty(self):
        m = MetricsCollector()
        assert m._counters == {}
        assert m._gauges == {}
        assert m._histograms == {}

    def test_has_10_histogram_buckets(self):
        assert len(MetricsCollector()._histogram_buckets) == 10

    def test_has_lock(self):
        import threading

        m = MetricsCollector()
        assert isinstance(m._lock, type(threading.Lock()))


class TestIncCounter:
    def test_increments_by_1(self):
        m = MetricsCollector()
        m.inc_counter("my_counter")
        assert m._counters["my_counter"] == 1

    def test_increments_by_custom_value(self):
        m = MetricsCollector()
        m.inc_counter("c", value=5)
        m.inc_counter("c", value=3)
        assert m._counters["c"] == 8

    def test_increments_with_labels(self):
        m = MetricsCollector()
        m.inc_counter("c", labels={"env": "prod"})
        key = 'c{env="prod"}'
        assert m._counters[key] == 1

    def test_different_labels_different_keys(self):
        m = MetricsCollector()
        m.inc_counter("c", labels={"a": "1"})
        m.inc_counter("c", labels={"a": "2"})
        assert len(m._counters) == 2

    def test_no_labels_returns_plain_name(self):
        m = MetricsCollector()
        m.inc_counter("hits")
        assert "hits" in m._counters

    def test_thread_safe_multiple_increments(self):
        import threading

        m = MetricsCollector()
        threads = [threading.Thread(target=m.inc_counter, args=("t",)) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert m._counters["t"] == 100


class TestSetGauge:
    def test_sets_value(self):
        m = MetricsCollector()
        m.set_gauge("cpu", 0.75)
        assert m._gauges["cpu"] == 0.75

    def test_overwrites_previous_value(self):
        m = MetricsCollector()
        m.set_gauge("cpu", 0.5)
        m.set_gauge("cpu", 0.9)
        assert m._gauges["cpu"] == 0.9

    def test_with_labels(self):
        m = MetricsCollector()
        m.set_gauge("g", 42.0, labels={"host": "a"})
        key = 'g{host="a"}'
        assert m._gauges[key] == 42.0

    def test_negative_value(self):
        m = MetricsCollector()
        m.set_gauge("temp", -10.0)
        assert m._gauges["temp"] == -10.0


class TestObserveHistogram:
    def test_records_sum_and_count(self):
        m = MetricsCollector()
        m.observe_histogram("latency", 0.05)
        h = m._histograms["latency"]
        assert h["sum"] == 0.05
        assert h["count"] == 1

    def test_accumulates_multiple_observations(self):
        m = MetricsCollector()
        m.observe_histogram("latency", 0.1)
        m.observe_histogram("latency", 0.2)
        assert m._histograms["latency"]["count"] == 2
        assert m._histograms["latency"]["sum"] == pytest.approx(0.3)

    def test_bucket_increment_for_small_value(self):
        m = MetricsCollector()
        m.observe_histogram("latency", 0.01)
        # All buckets >= 0.01 should be 1
        for b, cnt in m._histograms["latency"]["buckets"].items():
            assert cnt == 1

    def test_bucket_not_incremented_for_large_value(self):
        m = MetricsCollector()
        m.observe_histogram("latency", 100.0)
        # No bucket catches 100.0 (max bucket is 10.0)
        for b, cnt in m._histograms["latency"]["buckets"].items():
            assert cnt == 0

    def test_with_labels_creates_separate_key(self):
        m = MetricsCollector()
        m.observe_histogram("h", 0.5, labels={"method": "GET"})
        assert any("GET" in k for k in m._histograms)


class TestMakeKey:
    def test_no_labels_returns_name(self):
        assert MetricsCollector()._make_key("foo") == "foo"

    def test_empty_labels_returns_name(self):
        assert MetricsCollector()._make_key("foo", {}) == "foo"

    def test_single_label(self):
        key = MetricsCollector()._make_key("foo", {"a": "1"})
        assert key == 'foo{a="1"}'

    def test_labels_sorted_alphabetically(self):
        key = MetricsCollector()._make_key("foo", {"z": "2", "a": "1"})
        assert key == 'foo{a="1",z="2"}'


class TestFormatPrometheus:
    def test_empty_collector_returns_newline(self):
        m = MetricsCollector()
        output = m.format_prometheus()
        assert output.strip() == ""

    def test_counter_format(self):
        m = MetricsCollector()
        m.inc_counter("hits")
        output = m.format_prometheus()
        assert "# TYPE hits counter" in output
        assert "hits 1" in output

    def test_gauge_format(self):
        m = MetricsCollector()
        m.set_gauge("cpu", 0.75)
        output = m.format_prometheus()
        assert "# TYPE cpu gauge" in output
        assert "cpu 0.75" in output

    def test_histogram_format_includes_sum_count_inf(self):
        m = MetricsCollector()
        m.observe_histogram("latency", 0.05)
        output = m.format_prometheus()
        assert "latency_sum" in output
        assert "latency_count" in output
        assert '+Inf"} 1' in output or 'le="+Inf"} 1' in output

    def test_histogram_with_labels_format(self):
        m = MetricsCollector()
        m.observe_histogram("h", 0.1, labels={"method": "GET"})
        output = m.format_prometheus()
        assert "GET" in output

    def test_multiple_metrics_all_included(self):
        m = MetricsCollector()
        m.inc_counter("c")
        m.set_gauge("g", 1.0)
        m.observe_histogram("h", 0.5)
        output = m.format_prometheus()
        assert "counter" in output
        assert "gauge" in output
        assert "histogram" in output

    def test_counter_with_labels_format(self):
        m = MetricsCollector()
        m.inc_counter("req", labels={"endpoint": "/api"})
        output = m.format_prometheus()
        assert "/api" in output
        assert "# TYPE req counter" in output

    def test_help_line_only_appears_once_per_metric(self):
        m = MetricsCollector()
        m.inc_counter("c", labels={"a": "1"})
        m.inc_counter("c", labels={"a": "2"})
        output = m.format_prometheus()
        assert output.count("# TYPE c counter") == 1


# ════════════════════════════════════════════════════════════
#  track_request decorator
# ════════════════════════════════════════════════════════════


class TestTrackRequestDecorator:
    def test_increments_request_counter(self):
        from CORE.utils.metrics import metrics as global_metrics

        before = global_metrics._counters.get('acrqa_http_requests_total{endpoint="/test"}', 0)

        @track_request("/test")
        def handler():
            return "ok"

        handler()
        after = global_metrics._counters.get('acrqa_http_requests_total{endpoint="/test"}', 0)
        assert after == before + 1

    def test_records_duration_histogram(self):
        from CORE.utils.metrics import metrics as global_metrics

        @track_request("/timed")
        def handler():
            return "done"

        handler()
        assert any("timed" in k for k in global_metrics._histograms)

    def test_reraises_exception_and_increments_error_counter(self):
        from CORE.utils.metrics import metrics as global_metrics

        before = global_metrics._counters.get('acrqa_http_errors_total{endpoint="/err"}', 0)

        @track_request("/err")
        def failing_handler():
            raise ValueError("boom")

        with pytest.raises(ValueError):
            failing_handler()

        after = global_metrics._counters.get('acrqa_http_errors_total{endpoint="/err"}', 0)
        assert after == before + 1

    def test_return_value_passthrough(self):
        @track_request("/v")
        def handler():
            return 42

        assert handler() == 42

    def test_preserves_function_name(self):
        @track_request("/name")
        def my_handler():
            """docstring"""
            pass

        assert my_handler.__name__ == "my_handler"


# ════════════════════════════════════════════════════════════
#  Module-level helpers
# ════════════════════════════════════════════════════════════


class TestRecordAnalysisMetrics:
    def test_sets_gauge_and_counter(self):
        from CORE.utils.metrics import metrics as global_metrics

        before_analyses = global_metrics._counters.get("acrqa_analyses_total", 0)
        record_analysis_metrics(total_findings=10, duration_seconds=1.5)
        assert global_metrics._counters.get("acrqa_analyses_total", 0) == before_analyses + 1
        assert global_metrics._gauges.get("acrqa_last_analysis_findings_total") == 10

    def test_cache_hits_incremented(self):
        from CORE.utils.metrics import metrics as global_metrics

        before = global_metrics._counters.get("acrqa_cache_hits_total", 0)
        record_analysis_metrics(total_findings=0, duration_seconds=0.1, cache_hits=5)
        assert global_metrics._counters.get("acrqa_cache_hits_total", 0) == before + 5

    def test_cache_misses_incremented(self):
        from CORE.utils.metrics import metrics as global_metrics

        before = global_metrics._counters.get("acrqa_cache_misses_total", 0)
        record_analysis_metrics(total_findings=0, duration_seconds=0.1, cache_misses=3)
        assert global_metrics._counters.get("acrqa_cache_misses_total", 0) == before + 3

    def test_zero_cache_hits_not_incremented(self):
        from CORE.utils.metrics import metrics as global_metrics

        before = global_metrics._counters.get("acrqa_cache_hits_total", 0)
        record_analysis_metrics(0, 0.0, cache_hits=0)
        assert global_metrics._counters.get("acrqa_cache_hits_total", 0) == before


class TestRecordFindingMetrics:
    def test_increments_findings_counter(self):
        from CORE.utils.metrics import metrics as global_metrics

        key = 'acrqa_findings_total{category="security",severity="high"}'
        before = global_metrics._counters.get(key, 0)
        record_finding_metrics("high", "security")
        assert global_metrics._counters.get(key, 0) == before + 1


class TestRecordExplanationMetrics:
    def test_observes_latency_histogram(self):
        from CORE.utils.metrics import metrics as global_metrics

        record_explanation_metrics(latency_ms=200.0, model="llama", tokens=100)
        assert any("llama" in k for k in global_metrics._histograms)

    def test_increments_token_counter(self):
        from CORE.utils.metrics import metrics as global_metrics

        key = 'acrqa_llm_tokens_total{model="gpt4"}'
        before = global_metrics._counters.get(key, 0)
        record_explanation_metrics(500.0, "gpt4", tokens=300)
        assert global_metrics._counters.get(key, 0) == before + 300

    def test_zero_tokens_not_incremented(self):
        from CORE.utils.metrics import metrics as global_metrics

        before = dict(global_metrics._counters)
        record_explanation_metrics(100.0, "mymodel", tokens=0)
        # No new token counter added
        token_keys_before = [k for k in before if "llm_tokens" in k and "mymodel" in k]
        token_keys_after = [k for k in global_metrics._counters if "llm_tokens" in k and "mymodel" in k]
        assert token_keys_before == token_keys_after


class TestRegisterMetricsEndpoint:
    def test_registers_route(self):
        mock_app = MagicMock()
        register_metrics_endpoint(mock_app)
        mock_app.route.assert_called_once_with("/metrics")


# ════════════════════════════════════════════════════════════
#  RateLimiter
# ════════════════════════════════════════════════════════════


from CORE.utils.rate_limiter import RateLimiter, get_rate_limiter


def _limiter(tokens_per_minute=1, bucket_size=1):
    """Build a RateLimiter with a mocked Redis that passes ping."""
    mock_redis = MagicMock(spec=redis.Redis)
    with patch("CORE.utils.rate_limiter.redis.Redis", return_value=mock_redis):
        limiter = RateLimiter(tokens_per_minute=tokens_per_minute, bucket_size=bucket_size)
    limiter.redis = mock_redis
    return limiter, mock_redis


class TestRateLimiterInit:
    def test_attributes_set(self):
        limiter, _ = _limiter()
        assert limiter.redis_host == "localhost"
        assert limiter.redis_port == 6379
        assert limiter.tokens_per_minute == 1
        assert limiter.bucket_size == 1

    def test_refill_rate_is_60_for_1_per_minute(self):
        limiter, _ = _limiter()
        assert limiter.refill_rate == 60.0

    def test_refill_rate_is_30_for_2_per_minute(self):
        limiter, _ = _limiter(tokens_per_minute=2)
        assert limiter.refill_rate == 30.0

    def test_redis_none_when_connection_fails(self):
        with patch("CORE.utils.rate_limiter.redis.Redis") as mock_cls:
            mock_cls.return_value.ping.side_effect = redis.ConnectionError("no server")
            limiter = RateLimiter()
        assert limiter.redis is None


class TestGetBucketKey:
    def test_without_pr(self):
        limiter, _ = _limiter()
        assert limiter._get_bucket_key("myrepo") == "rate_limit:myrepo"

    def test_with_pr(self):
        limiter, _ = _limiter()
        assert limiter._get_bucket_key("myrepo", 42) == "rate_limit:myrepo:pr_42"


class TestCheckRateLimitNoRedis:
    def test_allows_when_redis_none(self):
        limiter, _ = _limiter()
        limiter.redis = None
        allowed, retry = limiter.check_rate_limit("repo")
        assert allowed is True
        assert retry is None


class TestCheckRateLimitFirstRequest:
    def test_first_request_allowed(self):
        limiter, mock_r = _limiter()
        mock_r.hgetall.return_value = {}
        allowed, retry = limiter.check_rate_limit("repo")
        assert allowed is True
        assert retry is None
        mock_r.hset.assert_called_once()
        mock_r.expire.assert_called()

    def test_first_request_with_pr(self):
        limiter, mock_r = _limiter()
        mock_r.hgetall.return_value = {}
        allowed, retry = limiter.check_rate_limit("repo", pr_number=5)
        assert allowed is True


class TestCheckRateLimitTokenBucket:
    def test_allows_when_enough_tokens(self):
        limiter, mock_r = _limiter()
        # Simulate bucket with 1 full token — enough to consume
        mock_r.hgetall.return_value = {
            "tokens": "1.0",
            "last_refill": str(time.time() - 0.1),
        }
        allowed, retry = limiter.check_rate_limit("repo")
        assert allowed is True
        assert retry is None

    def test_blocks_when_no_tokens(self):
        limiter, mock_r = _limiter()
        # bucket empty (0 tokens), refilled 1 second ago → very few new tokens
        mock_r.hgetall.return_value = {
            "tokens": "0.0",
            "last_refill": str(time.time() - 1.0),
        }
        allowed, retry = limiter.check_rate_limit("repo")
        # With 1 tok/min, 1 second elapsed → 1/60 tokens added: still < 1
        assert allowed is False
        assert retry is not None
        assert retry > 0

    def test_blocks_partial_tokens_not_enough(self):
        limiter, mock_r = _limiter()
        mock_r.hgetall.return_value = {
            "tokens": "0.5",
            "last_refill": str(time.time()),  # just refilled, no new tokens
        }
        allowed, retry = limiter.check_rate_limit("repo")
        assert allowed is False

    def test_retry_after_is_positive(self):
        limiter, mock_r = _limiter()
        mock_r.hgetall.return_value = {"tokens": "0.0", "last_refill": str(time.time())}
        allowed, retry = limiter.check_rate_limit("repo")
        assert not allowed
        assert isinstance(retry, float)
        assert retry > 0

    def test_token_bucket_consumed_on_success(self):
        limiter, mock_r = _limiter()
        mock_r.hgetall.return_value = {
            "tokens": "1.0",
            "last_refill": str(time.time()),
        }
        limiter.check_rate_limit("repo")
        # hset called to write updated tokens (0.0)
        mock_r.hset.assert_called()


class TestCheckRateLimitRedisErrors:
    def test_redis_error_degrades_gracefully(self):
        limiter, mock_r = _limiter()
        mock_r.hgetall.side_effect = redis.RedisError("connection lost")
        allowed, retry = limiter.check_rate_limit("repo")
        assert allowed is True
        assert retry is None

    def test_unexpected_exception_degrades_gracefully(self):
        limiter, mock_r = _limiter()
        mock_r.hgetall.side_effect = RuntimeError("unexpected")
        allowed, retry = limiter.check_rate_limit("repo")
        assert allowed is True
        assert retry is None


class TestLogRateLimitEvent:
    def test_stores_event_in_redis(self):
        limiter, mock_r = _limiter()
        limiter._log_rate_limit_event("repo", 1, 55.0)
        mock_r.lpush.assert_called_once()
        mock_r.ltrim.assert_called_once()
        mock_r.expire.assert_called()

    def test_no_redis_does_not_crash(self):
        limiter, _ = _limiter()
        limiter.redis = None
        # Should not raise
        limiter._log_rate_limit_event("repo", None, 30.0)

    def test_redis_exception_in_log_silenced(self):
        limiter, mock_r = _limiter()
        mock_r.lpush.side_effect = Exception("write fail")
        # Should not propagate
        limiter._log_rate_limit_event("repo", 1, 10.0)


class TestResetRateLimit:
    def test_returns_false_when_no_redis(self):
        limiter, _ = _limiter()
        limiter.redis = None
        assert limiter.reset_rate_limit("repo") is False

    def test_deletes_bucket_key(self):
        limiter, mock_r = _limiter()
        result = limiter.reset_rate_limit("repo", pr_number=3)
        mock_r.delete.assert_called_once_with("rate_limit:repo:pr_3")
        assert result is True

    def test_returns_false_on_exception(self):
        limiter, mock_r = _limiter()
        mock_r.delete.side_effect = Exception("delete failed")
        result = limiter.reset_rate_limit("repo")
        assert result is False

    def test_reset_without_pr(self):
        limiter, mock_r = _limiter()
        limiter.reset_rate_limit("myrepo")
        mock_r.delete.assert_called_once_with("rate_limit:myrepo")


class TestGetRateLimiter:
    def test_returns_rate_limiter_instance(self):
        import CORE.utils.rate_limiter as rl_module

        rl_module._rate_limiter_instance = None
        with patch("CORE.utils.rate_limiter.redis.Redis") as mock_cls:
            mock_cls.return_value.ping.return_value = True
            instance = get_rate_limiter()
        assert isinstance(instance, RateLimiter)

    def test_singleton_returns_same_instance(self):
        import CORE.utils.rate_limiter as rl_module

        rl_module._rate_limiter_instance = None
        with patch("CORE.utils.rate_limiter.redis.Redis") as mock_cls:
            mock_cls.return_value.ping.return_value = True
            i1 = get_rate_limiter()
            i2 = get_rate_limiter()
        assert i1 is i2
        # Reset so other tests aren't affected
        rl_module._rate_limiter_instance = None
