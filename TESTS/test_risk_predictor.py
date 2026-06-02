"""Tests for the Heuristic Risk Predictor (v5.0.0 Phase A.3)."""

from __future__ import annotations

import math
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from starlette.testclient import TestClient

from CORE.engines.risk_predictor import (
    AGE_CAP_DAYS,
    AUTHORS_CAP,
    CHURN_CAP,
    COMPLEXITY_CAP,
    HIGH_DENSITY_CAP,
    WEIGHTS,
    RiskFeatures,
    normalize_features,
    predict_score,
    risk_map_payload,
    score_files,
)
from FRONTEND.api.deps import get_current_user, get_db
from FRONTEND.api.main import app as fastapi_app

# ── Catalog / invariants ──────────────────────────────────────────────────────


class TestWeightInvariants:
    def test_weights_sum_to_one(self):
        assert math.isclose(sum(WEIGHTS.values()), 1.0, rel_tol=1e-9)

    def test_weight_keys_match_features(self):
        assert set(WEIGHTS.keys()) == {
            "complexity",
            "churn",
            "age",
            "authors",
            "coverage_gap",
            "high_density",
        }

    def test_high_density_is_heaviest(self):
        assert WEIGHTS["high_density"] == max(WEIGHTS.values())

    def test_age_is_lowest_weight(self):
        assert WEIGHTS["age"] == min(WEIGHTS.values())

    def test_caps_positive(self):
        for cap in (COMPLEXITY_CAP, CHURN_CAP, AGE_CAP_DAYS, AUTHORS_CAP, HIGH_DENSITY_CAP):
            assert cap > 0


# ── Normalization ─────────────────────────────────────────────────────────────


class TestNormalization:
    def test_zero_features_normalize_to_zero(self):
        n = normalize_features(RiskFeatures(file_path="x"))
        assert all(v == 0.0 for v in n.values())

    def test_max_features_normalize_to_one(self):
        n = normalize_features(
            RiskFeatures(
                file_path="x",
                complexity=COMPLEXITY_CAP * 2,
                churn_90d=CHURN_CAP * 2,
                age_days=AGE_CAP_DAYS * 2,
                author_count=AUTHORS_CAP * 2,
                test_coverage_gap=1,
                high_finding_count=999,
                loc=100,
            )
        )
        assert n["complexity"] == 1.0
        assert n["churn"] == 1.0
        assert n["age"] == 1.0
        assert n["authors"] == 1.0
        assert n["coverage_gap"] == 1.0
        assert n["high_density"] == 1.0

    def test_high_density_uses_per_100_loc(self):
        # 1 HIGH in 100 LOC = 1.0 per 100, which / 5 cap = 0.2 normalised
        n = normalize_features(
            RiskFeatures(file_path="x", high_finding_count=1, loc=100),
        )
        assert math.isclose(n["high_density"], 0.2, abs_tol=1e-6)

    def test_coverage_gap_is_binary(self):
        n0 = normalize_features(RiskFeatures(file_path="x", test_coverage_gap=0))
        n1 = normalize_features(RiskFeatures(file_path="x", test_coverage_gap=1))
        assert n0["coverage_gap"] == 0.0
        assert n1["coverage_gap"] == 1.0


# ── Score computation ────────────────────────────────────────────────────────


class TestPredictScore:
    def test_zero_features_score_zero(self):
        s = predict_score(RiskFeatures(file_path="x"))
        assert s.score == 0
        assert all(v == 0.0 for v in s.contributions.values())

    def test_all_max_features_score_100(self):
        s = predict_score(
            RiskFeatures(
                file_path="x",
                complexity=COMPLEXITY_CAP,
                churn_90d=CHURN_CAP,
                age_days=AGE_CAP_DAYS,
                author_count=AUTHORS_CAP,
                test_coverage_gap=1,
                high_finding_count=10,
                loc=100,
            )
        )
        assert s.score == 100

    def test_score_in_range_0_to_100(self):
        for c in (0, 5, 20, 40, 100):
            s = predict_score(RiskFeatures(file_path="x", complexity=c, loc=50))
            assert 0 <= s.score <= 100

    def test_contributions_sum_close_to_score_over_100(self):
        f = RiskFeatures(
            file_path="x",
            complexity=20,
            churn_90d=10,
            age_days=365,
            author_count=3,
            test_coverage_gap=0,
            high_finding_count=1,
            loc=200,
        )
        s = predict_score(f)
        assert math.isclose(s.score, round(sum(s.contributions.values()) * 100), abs_tol=1)

    def test_score_dict_shape(self):
        s = predict_score(RiskFeatures(file_path="app.py", complexity=10))
        d = s.to_dict()
        assert d["file_path"] == "app.py"
        assert "score" in d and "features" in d and "contributions" in d

    def test_changing_only_high_density_raises_score(self):
        base = predict_score(RiskFeatures(file_path="x", loc=100))
        more = predict_score(
            RiskFeatures(file_path="x", high_finding_count=5, loc=100),
        )
        assert more.score > base.score

    def test_high_density_dominates_at_extreme(self):
        # 0 LOC files (or rare files) shouldn't blow up
        s = predict_score(RiskFeatures(file_path="x", high_finding_count=100, loc=0))
        assert 0 <= s.score <= 100


# ── score_files over findings ────────────────────────────────────────────────


class TestScoreFiles:
    def test_empty_findings_returns_empty(self, tmp_path: Path):
        assert score_files(tmp_path, findings=[]) == []

    def test_groups_findings_by_file(self, tmp_path: Path):
        (tmp_path / "a.py").write_text("def f():\n    pass\n")
        (tmp_path / "b.py").write_text("def g():\n    pass\n")
        findings = [
            {"file_path": "a.py", "canonical_severity": "high"},
            {"file_path": "a.py", "canonical_severity": "medium"},
            {"file_path": "b.py", "canonical_severity": "high"},
        ]
        out = score_files(tmp_path, findings=findings)
        assert {s.file_path for s in out} == {"a.py", "b.py"}

    def test_sorted_by_score_desc(self, tmp_path: Path):
        (tmp_path / "low.py").write_text("x = 1\n")
        (tmp_path / "high.py").write_text("y = 2\n")
        findings = [
            {"file_path": "high.py", "canonical_severity": "high"},
            {"file_path": "high.py", "canonical_severity": "high"},
            {"file_path": "low.py", "canonical_severity": "low"},
        ]
        out = score_files(tmp_path, findings=findings)
        assert out[0].file_path == "high.py"
        assert out[0].score >= out[1].score

    def test_critical_severity_counts_as_high(self, tmp_path: Path):
        (tmp_path / "c.py").write_text("z = 1\n")
        findings = [{"file_path": "c.py", "canonical_severity": "critical"}]
        out = score_files(tmp_path, findings=findings)
        assert out[0].features["high_finding_count"] == 1

    def test_missing_file_falls_back_gracefully(self, tmp_path: Path):
        findings = [{"file_path": "nope.py", "canonical_severity": "high"}]
        out = score_files(tmp_path, findings=findings)
        assert out[0].file_path == "nope.py"
        assert out[0].features["loc"] == 0

    def test_explicit_paths_param(self, tmp_path: Path):
        (tmp_path / "a.py").write_text("x = 1\n")
        out = score_files(tmp_path, findings=[], paths=["a.py"])
        assert any(s.file_path == "a.py" for s in out)

    def test_coverage_gap_detected_for_untested_python(self, tmp_path: Path):
        (tmp_path / "untested.py").write_text("def f(): pass\n")
        out = score_files(tmp_path, findings=[], paths=["untested.py"])
        assert out[0].features["test_coverage_gap"] == 1

    def test_coverage_gap_zero_when_test_file_present(self, tmp_path: Path):
        (tmp_path / "tested.py").write_text("def f(): pass\n")
        (tmp_path / "test_tested.py").write_text("def test_f(): pass\n")
        out = score_files(tmp_path, findings=[], paths=["tested.py"])
        assert out[0].features["test_coverage_gap"] == 0


# ── git-backed feature extraction ────────────────────────────────────────────


def _git(repo: Path, *args: str) -> None:
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY"):
        env.pop(key, None)
    env.update(
        {
            "GIT_AUTHOR_NAME": "Tester",
            "GIT_AUTHOR_EMAIL": "t@x.local",
            "GIT_COMMITTER_NAME": "Tester",
            "GIT_COMMITTER_EMAIL": "t@x.local",
        }
    )
    subprocess.run(["git", *args], cwd=str(repo), check=True, env=env, capture_output=True)


class TestGitFeatures:
    @pytest.fixture
    def repo(self, tmp_path: Path) -> Path:
        r = tmp_path / "rp-repo"
        r.mkdir()
        _git(r, "init", "-q", "-b", "main")
        _git(r, "config", "commit.gpgsign", "false")
        (r / "app.py").write_text("def f():\n    return 1\n")
        _git(r, "add", "app.py")
        _git(r, "commit", "-q", "-m", "Initial")
        (r / "app.py").write_text("def f():\n    return 2\n")
        _git(r, "add", "app.py")
        _git(r, "commit", "-q", "-m", "Touch")
        return r

    def test_churn_and_author_count(self, repo: Path):
        out = score_files(repo, findings=[], paths=["app.py"])
        s = out[0]
        assert s.features["churn_90d"] >= 2
        assert s.features["author_count"] == 1
        assert s.features["age_days"] >= 0

    def test_non_git_dir_returns_zero_features(self, tmp_path: Path):
        (tmp_path / "x.py").write_text("a = 1\n")
        out = score_files(tmp_path, findings=[], paths=["x.py"])
        s = out[0]
        assert s.features["churn_90d"] == 0
        assert s.features["author_count"] == 0


# ── risk_map_payload ─────────────────────────────────────────────────────────


class TestRiskMapPayload:
    def test_payload_shape(self):
        scores = [predict_score(RiskFeatures(file_path="x"))]
        p = risk_map_payload(scores)
        assert set(p.keys()) >= {"weights", "caps", "files", "total_files"}
        assert p["total_files"] == 1
        assert p["weights"] == WEIGHTS

    def test_empty_payload(self):
        p = risk_map_payload([])
        assert p["total_files"] == 0
        assert p["files"] == []


# ── Endpoint ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def client():
    mock_db = MagicMock()
    mock_user = {"id": 1, "email": "u@x.local", "role": "admin"}
    fastapi_app.dependency_overrides[get_db] = lambda: mock_db
    fastapi_app.dependency_overrides[get_current_user] = lambda: mock_user
    with TestClient(fastapi_app, raise_server_exceptions=False) as c:
        yield c, mock_db
    fastapi_app.dependency_overrides.clear()


class TestRiskMapEndpoint:
    def test_returns_cached_when_available(self, client):
        c, db = client
        db.get_file_risk_scores.return_value = [
            {"file_path": "a.py", "score": 80},
            {"file_path": "b.py", "score": 20},
        ]
        r = c.get("/v1/runs/7/risk-map")
        assert r.status_code == 200
        body = r.json()
        assert body["cached"] is True
        assert body["total_files"] == 2

    def test_computes_when_no_cache(self, client, tmp_path: Path, monkeypatch):
        c, db = client
        db.get_file_risk_scores.return_value = []
        db.get_findings.return_value = []
        db.upsert_file_risk_score.return_value = 1
        monkeypatch.chdir(tmp_path)
        r = c.get("/v1/runs/7/risk-map")
        assert r.status_code == 200
        body = r.json()
        assert body["cached"] is False
        assert "weights" in body
        assert "caps" in body

    def test_refresh_forces_recompute(self, client, tmp_path: Path, monkeypatch):
        c, db = client
        # Even with cache present, refresh=true skips it
        db.get_file_risk_scores.return_value = [{"file_path": "a.py", "score": 99}]
        db.get_findings.return_value = []
        db.upsert_file_risk_score.return_value = 1
        monkeypatch.chdir(tmp_path)
        r = c.get("/v1/runs/7/risk-map?refresh=true")
        assert r.status_code == 200
        body = r.json()
        assert body["cached"] is False
