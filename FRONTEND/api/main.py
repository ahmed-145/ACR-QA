"""
ACR-QA v3.3.0 — FastAPI entrypoint.

Runs on port 8000 alongside the legacy Flask app (port 5000).
Start with: uvicorn FRONTEND.api.main:app --host 0.0.0.0 --port 8000 --workers 4

All data endpoints live under /v1/ and require authentication.
Public endpoints: GET /health, GET /docs, GET /openapi.json
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import Depends, FastAPI, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from CORE import __version__  # noqa: E402
from CORE.utils.metrics import metrics  # noqa: E402
from DATABASE.database import Database  # noqa: E402
from FRONTEND.api.deps import get_current_user, get_db  # noqa: E402
from FRONTEND.api.models import HealthOut  # noqa: E402
from FRONTEND.api.routers import auth, runs, scans  # noqa: E402

# OpenTelemetry — degrades silently when OTEL_EXPORTER_OTLP_ENDPOINT is not set
_otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
if _otel_endpoint:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    _resource = Resource(attributes={SERVICE_NAME: "acrqa-api"})
    _provider = TracerProvider(resource=_resource)
    _provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=_otel_endpoint)))
    trace.set_tracer_provider(_provider)

# Sentry — degrades silently when SENTRY_DSN is not set
_sentry_dsn = os.getenv("SENTRY_DSN")
if _sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=_sentry_dsn,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        traces_sample_rate=0.1,
        environment=os.getenv("RAILWAY_ENVIRONMENT", "development"),
    )

app = FastAPI(
    title="ACR-QA",
    description="Automated Code Review & Quality Analysis — async REST API",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

if _otel_endpoint:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/v1")
app.include_router(runs.router, prefix="/v1")
app.include_router(scans.router, prefix="/v1")

# ── Main UI (static HTML + vanilla JS, API-wired) ─────────────────────────────
_UI_DIR = Path(__file__).parent.parent / "static" / "ui"
if _UI_DIR.is_dir():
    from fastapi.responses import RedirectResponse
    from fastapi.staticfiles import StaticFiles

    app.mount("/ui", StaticFiles(directory=str(_UI_DIR), html=True), name="ui")

    @app.get("/", include_in_schema=False)
    async def root_redirect():
        return RedirectResponse(url="/ui/index.html")


# ── Public endpoints ──────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthOut, tags=["system"], summary="Liveness probe")
async def health():
    return HealthOut(status="healthy", version=__version__)


@app.get("/metrics", tags=["system"], summary="Prometheus metrics")
async def prometheus_metrics():
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(
        metrics.format_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# ── Misc v1 endpoints (not grouped into a router) ────────────────────────────


@app.get("/v1/repos", tags=["runs"], summary="List repos with completed runs")
async def get_repos(
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    repos = db.get_repos_with_runs()
    return {"success": True, "repos": repos}


@app.get("/v1/categories", tags=["runs"], summary="All distinct finding categories")
async def get_categories(
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    findings = db.get_findings(limit=1000)
    categories = sorted({f["category"] for f in findings if f.get("category")})
    return {"success": True, "categories": categories}


@app.get("/v1/quick-stats", tags=["runs"], summary="Aggregate stats for last 10 runs")
async def quick_stats(
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    runs = db.get_recent_runs(limit=10)
    total_findings = total_high = total_medium = total_low = 0
    for run in runs:
        s = db.get_run_summary(run["id"])
        if s:
            total_findings += s.get("findings_count", 0)
            total_high += s.get("high_severity_count", 0)
            total_medium += s.get("medium_severity_count", 0)
            total_low += s.get("low_severity_count", 0)
    return {
        "success": True,
        "stats": {
            "total_runs": len(runs),
            "total_findings": total_findings,
            "high_severity": total_high,
            "medium_severity": total_medium,
            "low_severity": total_low,
            "avg_findings_per_run": round(total_findings / len(runs), 1) if runs else 0,
        },
    }


@app.get("/v1/trends", tags=["runs"], summary="Time-series trend data across recent runs")
async def get_trends(
    limit: int = Query(30, ge=1, le=200),
    repo: str | None = None,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    trend_data = db.get_trend_data(limit=limit, repo_name=repo)
    repos = db.get_repos_with_runs()

    labels, run_ids = [], []
    severity_series: dict = {"high": [], "medium": [], "low": []}
    category_series: dict = {"security": [], "style": [], "design": [], "best_practice": []}
    confidence_series: list = []
    total_series: list = []

    for row in reversed(trend_data):
        started = row.get("started_at")
        labels.append(f"{str(started)[:10] if started else 'unknown'} ({row.get('repo_name', '?')})")
        run_ids.append(row.get("run_id"))
        severity_series["high"].append(int(row.get("high_count", 0)))
        severity_series["medium"].append(int(row.get("medium_count", 0)))
        severity_series["low"].append(int(row.get("low_count", 0)))
        category_series["security"].append(int(row.get("security_count", 0)))
        category_series["style"].append(int(row.get("style_count", 0)))
        category_series["design"].append(int(row.get("design_count", 0)))
        category_series["best_practice"].append(int(row.get("best_practice_count", 0)))
        confidence_series.append(round(float(row.get("avg_confidence", 0)), 1))
        total_series.append(int(row.get("total_findings", 0)))

    return {
        "success": True,
        "labels": labels,
        "run_ids": run_ids,
        "repos": repos,
        "severity_series": severity_series,
        "category_series": category_series,
        "confidence_series": confidence_series,
        "total_series": total_series,
        "run_count": len(trend_data),
    }


@app.get("/v1/cost-summary", tags=["runs"], summary="Aggregate LLM cost and latency")
async def cost_summary(
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    results = db.execute(
        "SELECT COUNT(*) as total_explanations, SUM(cost_usd) as total_cost, "
        "AVG(cost_usd) as avg_cost_per_finding, AVG(latency_ms) as avg_latency_ms "
        "FROM llm_explanations",
        fetch=True,
    )
    data = results[0] if results and results[0] else {}
    return {
        "success": True,
        "total_explanations": data.get("total_explanations", 0),
        "total_cost": float(data.get("total_cost", 0) or 0),
        "avg_cost_per_finding": float(data.get("avg_cost_per_finding", 0) or 0),
        "avg_latency_ms": float(data.get("avg_latency_ms", 0) or 0),
    }


@app.get("/v1/runs/{run_id}/cost", tags=["runs"], summary="Per-run Groq token cost telemetry (task 12.32)")
async def run_cost(
    run_id: int,
    user: dict = Depends(get_current_user),
    db: Database = Depends(get_db),
):
    rows = db.execute(
        "SELECT groq_tokens_used, groq_cost_usd, groq_requests FROM analysis_runs WHERE id = %s",
        (run_id,),
        fetch=True,
    )
    if not rows:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    row = rows[0]
    return {
        "success": True,
        "run_id": run_id,
        "groq_tokens_used": row.get("groq_tokens_used"),
        "groq_cost_usd": float(row.get("groq_cost_usd") or 0),
        "groq_requests": row.get("groq_requests"),
    }


@app.get("/v1/fix-confidence/{rule_id}", tags=["runs"], summary="Auto-fix confidence for a rule")
async def fix_confidence(rule_id: str, user: dict = Depends(get_current_user)):
    HIGH = {"IMPORT-001": 95, "VAR-001": 90, "BOOL-001": 95, "F401": 95, "F841": 85}
    MED = {"PATTERN-001": 75, "STYLE-001": 80, "E501": 80}
    LOW = {"SECURITY-001": 40, "COMPLEXITY-001": 30, "DUP-001": 25}
    confidence = HIGH.get(rule_id) or MED.get(rule_id) or LOW.get(rule_id) or 50
    level = "high" if confidence >= 80 else "medium" if confidence >= 60 else "low"
    return {
        "success": True,
        "rule_id": rule_id,
        "confidence": confidence,
        "level": level,
        "auto_fixable": confidence >= 70,
        "recommendation": "Safe to auto-apply"
        if confidence >= 80
        else "Review recommended"
        if confidence >= 60
        else "Manual fix recommended",
    }


@app.get("/v1/test-gaps", tags=["runs"], summary="Test gap analysis — untested functions")
async def test_gaps(
    target: str = "CORE/",
    test_dir: str = "TESTS/",
    user: dict = Depends(get_current_user),
):
    from scripts.test_gap_analyzer import get_test_gap_data

    data = get_test_gap_data(target_dir=target, test_dir=test_dir)
    return {"success": True, **data}


@app.get("/v1/policy", tags=["runs"], summary="Active .acrqa.yml policy configuration")
async def get_policy(user: dict = Depends(get_current_user)):
    import yaml

    from scripts.validate_config import SCHEMA, validate_config

    is_valid, errors, warnings = validate_config(".acrqa.yml")
    config: dict = {}
    if Path(".acrqa.yml").exists():
        with open(".acrqa.yml") as f:
            config = yaml.safe_load(f) or {}

    return {
        "success": True,
        "config_file": ".acrqa.yml",
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "active_policy": {
            "disabled_rules": config.get("rules", {}).get("disabled_rules", []),
            "severity_overrides": config.get("rules", {}).get("severity_overrides", {}),
            "ignored_paths": config.get("analysis", {}).get("ignore_paths", []),
            "min_severity": config.get("reporting", {}).get("min_severity", "low"),
            "quality_gate": config.get(
                "quality_gate", {"max_high": 0, "max_medium": 10, "max_total": 200, "max_security": 0}
            ),
            "autofix": {
                "enabled": config.get("autofix", {}).get("enabled", False),
                "min_confidence": config.get("autofix", {}).get("auto_apply_confidence", 80),
            },
            "ai_explanations": {
                "enabled": config.get("ai", {}).get("enabled", True),
                "max_explanations": config.get("ai", {}).get("max_explanations", 50),
            },
        },
        "schema_keys": list(SCHEMA.keys()),
    }
