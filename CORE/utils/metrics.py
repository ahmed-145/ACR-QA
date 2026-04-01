#!/usr/bin/env python3
"""
ACR-QA Prometheus Metrics Exporter
Exposes application metrics in Prometheus format at /metrics
"""

import threading
import time
from functools import wraps


class MetricsCollector:
    """Thread-safe metrics collector for ACR-QA."""

    def __init__(self):
        self._lock = threading.Lock()
        self._counters = {}
        self._gauges = {}
        self._histograms = {}
        self._histogram_buckets = [
            0.01,
            0.025,
            0.05,
            0.1,
            0.25,
            0.5,
            1.0,
            2.5,
            5.0,
            10.0,
        ]

    def inc_counter(self, name: str, labels: dict | None = None, value: float = 1):
        """Increment a counter metric."""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value

    def set_gauge(self, name: str, value: float, labels: dict | None = None):
        """Set a gauge metric."""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def observe_histogram(self, name: str, value: float, labels: dict | None = None):
        """Observe a value for a histogram metric."""
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = {
                    "sum": 0,
                    "count": 0,
                    "buckets": {b: 0 for b in self._histogram_buckets},
                }
            self._histograms[key]["sum"] += value
            self._histograms[key]["count"] += 1
            for bucket in self._histogram_buckets:
                if value <= bucket:
                    self._histograms[key]["buckets"][bucket] += 1

    def _make_key(self, name: str, labels: dict | None = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def format_prometheus(self) -> str:
        """Export all metrics in Prometheus text format."""
        lines = []

        # Counters
        seen_counter_names = set()
        for key, value in sorted(self._counters.items()):
            name = key.split("{")[0] if "{" in key else key
            if name not in seen_counter_names:
                lines.append(f"# HELP {name} Counter metric")
                lines.append(f"# TYPE {name} counter")
                seen_counter_names.add(name)
            lines.append(f"{key} {value}")

        # Gauges
        seen_gauge_names = set()
        for key, value in sorted(self._gauges.items()):
            name = key.split("{")[0] if "{" in key else key
            if name not in seen_gauge_names:
                lines.append(f"# HELP {name} Gauge metric")
                lines.append(f"# TYPE {name} gauge")
                seen_gauge_names.add(name)
            lines.append(f"{key} {value}")

        # Histograms
        seen_hist_names = set()
        for key, data in sorted(self._histograms.items()):
            name = key.split("{")[0] if "{" in key else key
            if name not in seen_hist_names:
                lines.append(f"# HELP {name} Histogram metric")
                lines.append(f"# TYPE {name} histogram")
                seen_hist_names.add(name)

            base_labels = key[key.index("{") : key.index("}")] + "," if "{" in key else ""
            prefix = name

            cumulative = 0
            for bucket, count in sorted(data["buckets"].items()):
                cumulative += count
                if base_labels:
                    lines.append(f'{prefix}{{{base_labels}le="{bucket}"}} {cumulative}')
                else:
                    lines.append(f'{prefix}_bucket{{le="{bucket}"}} {cumulative}')

            if base_labels:
                lines.append(f'{prefix}{{{base_labels}le="+Inf"}} {data["count"]}')
            else:
                lines.append(f'{prefix}_bucket{{le="+Inf"}} {data["count"]}')
            lines.append(f"{prefix}_sum {data['sum']}")
            lines.append(f"{prefix}_count {data['count']}")

        lines.append("")
        return "\n".join(lines)


# Global metrics collector instance
metrics = MetricsCollector()


def track_request(endpoint: str):
    """Decorator to track API request metrics."""

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            start = time.time()
            metrics.inc_counter("acrqa_http_requests_total", {"endpoint": endpoint})

            try:
                result = f(*args, **kwargs)
                duration = time.time() - start
                metrics.observe_histogram(
                    "acrqa_http_request_duration_seconds",
                    duration,
                    {"endpoint": endpoint},
                )
                return result
            except Exception:
                metrics.inc_counter("acrqa_http_errors_total", {"endpoint": endpoint})
                raise

        return wrapper

    return decorator


def register_metrics_endpoint(app):
    """Register the /metrics endpoint on a Flask app."""
    from flask import Response

    @app.route("/metrics")
    def prometheus_metrics():
        """Prometheus metrics endpoint."""
        return Response(
            metrics.format_prometheus(),
            mimetype="text/plain; version=0.0.4; charset=utf-8",
        )


# Pre-define key ACR-QA metrics
def record_analysis_metrics(
    total_findings: int,
    duration_seconds: float,
    cache_hits: int = 0,
    cache_misses: int = 0,
):
    """Record metrics from an analysis run."""
    metrics.set_gauge("acrqa_last_analysis_findings_total", total_findings)
    metrics.observe_histogram("acrqa_analysis_duration_seconds", duration_seconds)
    metrics.inc_counter("acrqa_analyses_total")
    if cache_hits:
        metrics.inc_counter("acrqa_cache_hits_total", value=cache_hits)
    if cache_misses:
        metrics.inc_counter("acrqa_cache_misses_total", value=cache_misses)


def record_finding_metrics(severity: str, category: str):
    """Record per-finding metrics."""
    metrics.inc_counter("acrqa_findings_total", {"severity": severity, "category": category})


def record_explanation_metrics(latency_ms: float, model: str, tokens: int = 0):
    """Record LLM explanation metrics."""
    metrics.observe_histogram("acrqa_explanation_latency_seconds", latency_ms / 1000.0, {"model": model})
    if tokens:
        metrics.inc_counter("acrqa_llm_tokens_total", {"model": model}, value=tokens)
