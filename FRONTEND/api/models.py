"""Pydantic request and response models for the ACR-QA v1 API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ── Auth ─────────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    created_at: datetime


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: list[str] = Field(default_factory=list)


class ApiKeyOut(BaseModel):
    id: int
    name: str
    scopes: list[str]
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreatedOut(ApiKeyOut):
    key: str  # shown once on creation


# ── Scans ────────────────────────────────────────────────────────────────────


class ScanRequest(BaseModel):
    target_dir: str = Field(..., description="Path to directory to scan")
    repo_name: str = "local"
    pr_number: int | None = None
    limit: int | None = None


class ScanJobOut(BaseModel):
    job_id: str
    status: str  # queued | started | completed | failed
    result: dict[str, Any] | None = None


class AnalyzeFileRequest(BaseModel):
    content: str
    filename: str = "temp.py"


class RefreshFindingsRequest(BaseModel):
    target_dir: str = "TESTS/samples/comprehensive-issues"
    repo_name: str = "quick-refresh"
    skip_detection: bool = False


class SecretsScanRequest(BaseModel):
    target_dir: str = "."


class SCAScanRequest(BaseModel):
    project_dir: str = "."


class AIDetectRequest(BaseModel):
    target: str = "."
    threshold: float = 0.5


# ── Runs ─────────────────────────────────────────────────────────────────────


class RunSummaryOut(BaseModel):
    id: int
    repo_name: str
    pr_number: int | None
    status: str
    started_at: str
    total_findings: int
    high_count: int
    medium_count: int
    low_count: int


class RunsListOut(BaseModel):
    success: bool = True
    runs: list[RunSummaryOut]


class FindingOut(BaseModel):
    id: int
    rule_id: str | None
    severity: str
    category: str | None
    file_path: str | None
    line_number: int | None
    message: str | None
    explanation_text: str | None
    model_name: str | None
    latency_ms: float | None
    tool: str | None
    confidence: float
    ground_truth: str | None


class FindingsListOut(BaseModel):
    success: bool = True
    findings: list[FindingOut]
    total: int


# ── Generic ───────────────────────────────────────────────────────────────────


class HealthOut(BaseModel):
    status: str
    version: str
