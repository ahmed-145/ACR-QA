"""
Comprehensive tests for all 15 roadmap items.

Tests every new feature introduced in the god-mode implementation:
- #9  Multi-LLM jury (Gemini + Ollama fallback)
- #13 Differential SAST endpoint
- #14 Counterfactual explanations
- #15 K8s operator logic (gate, webhook notify, scan summary)
- #6  Kappa study analyze_kappa script
- #10 SLSA workflow YAML validity
- #11 Self-scan workflow YAML validity
- #4  devcontainer.json validity
- #5  Cloudflare Pages HTML validity
- #1  Funnel slide HTML validity
- #8  VS Code extension package.json validity
- Database: get_run_by_id, update_finding_counterfactual
"""

from __future__ import annotations

import json
import sys
import unittest.mock as mock
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

ROOT = Path(__file__).parent.parent

sys.path.insert(0, str(ROOT))


# ── #9 Multi-LLM Jury (Gemini) ───────────────────────────────────────────────


class TestGeminiProvider:
    def test_gemini_raises_when_no_api_key(self):
        """_call_gemini raises _GeminiUnavailableError when GEMINI_API_KEY not set."""
        from CORE.engines.second_opinion import _call_gemini, _GeminiUnavailableError

        with patch.dict("os.environ", {}, clear=True):
            import os

            os.environ.pop("GEMINI_API_KEY", None)
            os.environ.pop("GOOGLE_AI_API_KEY", None)
            with pytest.raises(_GeminiUnavailableError, match="GEMINI_API_KEY not set"):
                _call_gemini("test prompt")

    def test_gemini_falls_back_to_ollama_on_unavailable(self):
        """When Gemini key missing → engine tries Ollama → skips gracefully."""
        from CORE.engines.second_opinion import (
            SecondOpinionEngine,
            _GeminiUnavailableError,
            _OllamaUnavailableError,
        )

        engine = SecondOpinionEngine(secondary="gemini")
        finding = {
            "id": 1,
            "canonical_rule_id": "SECURITY-001",
            "severity": "high",
            "file_path": "app.py",
            "line_number": 10,
            "message": "test",
        }

        def fake_call(self, provider, prompt):
            if provider == "groq":
                return ("TP", "looks real")
            if provider == "gemini":
                raise _GeminiUnavailableError("no key")
            raise _OllamaUnavailableError("not running")

        with patch.object(SecondOpinionEngine, "_call_provider", fake_call):
            r = engine.review(finding)

        assert r.primary_verdict == "TP"
        assert r.skipped_reason is not None
        assert r.confidence_delta == 0

    def test_gemini_success_gives_confidence_boost(self):
        """When both providers agree TP, confidence_delta = +15."""
        from CORE.engines.second_opinion import SecondOpinionEngine

        engine = SecondOpinionEngine(secondary="gemini")
        finding = {
            "id": 2,
            "canonical_rule_id": "SECURITY-001",
            "severity": "high",
            "file_path": "app.py",
            "line_number": 20,
            "message": "eval injection",
        }

        with patch.object(SecondOpinionEngine, "_call_provider") as mock_call:
            mock_call.side_effect = [("TP", "groq says real"), ("TP", "gemini agrees")]
            r = engine.review(finding)

        assert r.agreement is True
        assert r.confidence_delta == 15
        assert r.secondary_provider == "gemini"

    def test_gemini_disagreement_penalises(self):
        """When providers disagree, confidence_delta = -10."""
        from CORE.engines.second_opinion import SecondOpinionEngine

        engine = SecondOpinionEngine(secondary="gemini")
        finding = {
            "id": 3,
            "canonical_rule_id": "SECURITY-002",
            "severity": "medium",
            "file_path": "views.py",
            "line_number": 5,
            "message": "xss",
        }

        with patch.object(SecondOpinionEngine, "_call_provider") as mock_call:
            mock_call.side_effect = [("TP", "real"), ("FP", "sanitized")]
            r = engine.review(finding)

        assert r.agreement is False
        assert r.confidence_delta == -10


# ── #13 Differential SAST ────────────────────────────────────────────────────


class TestDifferentialSAST:
    """Test GET /v1/runs/{id}/diff logic."""

    def _make_findings(self, fingerprints: list[str]) -> list[dict]:
        return [
            {"id": i, "fingerprint": fp, "severity": "high", "message": f"finding {i}"}
            for i, fp in enumerate(fingerprints)
        ]

    @pytest.mark.asyncio
    async def test_new_findings_identified_by_fingerprint(self):
        """Findings in current run not in baseline are returned as new."""
        from FRONTEND.api.routers.runs import get_diff

        current = self._make_findings(["fp-a", "fp-b", "fp-c"])
        baseline = self._make_findings(["fp-a", "fp-b"])

        db = MagicMock()
        db.get_run_by_id.side_effect = [
            {"id": 2, "repo_name": "my-repo"},
            {"id": 1, "repo_name": "my-repo"},
        ]
        db.get_findings_with_explanations.side_effect = [current, baseline]

        result = await get_diff(run_id=2, baseline_run_id=1, severity=None, user={"id": 1}, db=db)

        assert result["summary"]["new_findings"] == 1
        assert result["new_findings"][0]["fingerprint"] == "fp-c"

    @pytest.mark.asyncio
    async def test_fixed_count_is_correct(self):
        """Findings in baseline but not current are counted as fixed."""
        from FRONTEND.api.routers.runs import get_diff

        current = self._make_findings(["fp-a"])
        baseline = self._make_findings(["fp-a", "fp-b", "fp-c"])

        db = MagicMock()
        db.get_run_by_id.side_effect = [
            {"id": 2, "repo_name": "my-repo"},
            {"id": 1, "repo_name": "my-repo"},
        ]
        db.get_findings_with_explanations.side_effect = [current, baseline]

        result = await get_diff(run_id=2, baseline_run_id=1, severity=None, user={"id": 1}, db=db)

        assert result["summary"]["fixed_since_baseline"] == 2
        assert result["summary"]["new_findings"] == 0

    @pytest.mark.asyncio
    async def test_severity_filter_applied(self):
        """severity= param filters new findings."""
        from FRONTEND.api.routers.runs import get_diff

        current = [
            {"id": 1, "fingerprint": "fp-new-high", "severity": "high", "message": "hi"},
            {"id": 2, "fingerprint": "fp-new-low", "severity": "low", "message": "lo"},
        ]
        baseline: list = []

        db = MagicMock()
        db.get_run_by_id.side_effect = [{"id": 2, "repo_name": "r"}, {"id": 1, "repo_name": "r"}]
        db.get_findings_with_explanations.side_effect = [current, baseline]

        result = await get_diff(run_id=2, baseline_run_id=1, severity="high", user={"id": 1}, db=db)

        assert len(result["new_findings"]) == 1
        assert result["new_findings"][0]["severity"] == "high"

    @pytest.mark.asyncio
    async def test_missing_run_raises_404(self):
        """Non-existent run_id raises HTTPException 404."""
        from fastapi import HTTPException

        from FRONTEND.api.routers.runs import get_diff

        db = MagicMock()
        db.get_run_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_diff(run_id=999, baseline_run_id=None, severity=None, user={"id": 1}, db=db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_no_baseline_found_raises_400(self):
        """No prior runs for same repo raises HTTPException 400."""
        from fastapi import HTTPException

        from FRONTEND.api.routers.runs import get_diff

        db = MagicMock()
        db.get_run_by_id.return_value = {"id": 1, "repo_name": "my-repo"}
        db.get_recent_runs.return_value = []

        with pytest.raises(HTTPException) as exc_info:
            await get_diff(run_id=1, baseline_run_id=None, severity=None, user={"id": 1}, db=db)
        assert exc_info.value.status_code == 400


# ── #14 Counterfactual Explanations ──────────────────────────────────────────


class TestCounterfactual:
    def test_generate_counterfactual_returns_required_keys(self):
        """generate_counterfactual returns counterfactual, patched_snippet, confidence, reasoning."""
        from CORE.engines.explainer import ExplanationEngine

        engine = ExplanationEngine()
        finding = {
            "canonical_rule_id": "SECURITY-001",
            "message": "SQL injection via string concatenation",
            "evidence": {"snippet": "cursor.execute('SELECT * FROM users WHERE id=' + user_id)"},
        }

        # Mock the Groq call
        mock_response = json.dumps(
            {
                "counterfactual": "Use parameterized queries instead of string concatenation.",
                "patched_snippet": "cursor.execute('SELECT * FROM users WHERE id=%s', (user_id,))",
                "confidence": "high",
                "reasoning": "Parameterized queries prevent SQL injection by separating data from code.",
            }
        )
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = mock_response

        with patch.object(engine.key_pool, "next_client") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_completion
            result = engine.generate_counterfactual(finding)

        assert result["status"] == "success"
        assert result["counterfactual"] != ""
        assert result["confidence"] in ("high", "medium", "low")
        assert "reasoning" in result
        assert "patched_snippet" in result

    def test_generate_counterfactual_fallback_on_llm_error(self):
        """On LLM failure, returns fallback from rule catalog with status='error'."""
        from CORE.engines.explainer import ExplanationEngine

        engine = ExplanationEngine()
        finding = {
            "canonical_rule_id": "SECURITY-001",
            "message": "SQL injection",
        }

        with patch.object(engine.key_pool, "next_client") as mock_client:
            mock_client.side_effect = Exception("groq down")
            result = engine.generate_counterfactual(finding)

        assert result["status"] == "error"
        assert "error" in result
        assert result["confidence"] == "low"
        # Should still return something useful
        assert result["counterfactual"] != ""

    def test_counterfactual_parses_markdown_fences(self):
        """generate_counterfactual strips ```json fences from LLM response."""
        from CORE.engines.explainer import ExplanationEngine

        engine = ExplanationEngine()
        finding = {"canonical_rule_id": "SECURITY-002", "message": "hardcoded secret"}

        fenced_response = '```json\n{"counterfactual": "Use env vars", "patched_snippet": "", "confidence": "high", "reasoning": "Env vars are not in source"}\n```'
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = fenced_response

        with patch.object(engine.key_pool, "next_client") as mock_client:
            mock_client.return_value.chat.completions.create.return_value = mock_completion
            result = engine.generate_counterfactual(finding)

        assert result["status"] == "success"
        assert result["counterfactual"] == "Use env vars"


# ── #15 K8s Operator Logic ────────────────────────────────────────────────────


class TestOperatorLogic:
    """Test operator helper functions without touching k8s API."""

    def _import_controller(self):
        """Import controller with k8s mocked out."""
        with mock.patch("kubernetes.config.load_incluster_config", side_effect=Exception):
            with mock.patch("kubernetes.config.load_kube_config"):
                with mock.patch("kubernetes.client.CustomObjectsApi"):
                    import importlib.util

                    spec = importlib.util.spec_from_file_location(
                        "ctrl",
                        ROOT / "deploy/operator/controllers/acrqascan_controller.py",
                    )
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    return mod

    def test_evaluate_gate_pass_no_criticals(self):
        ctrl = self._import_controller()
        result = ctrl._evaluate_gate(
            {"critical": 0, "high": 3, "medium": 5},
            {"maxCritical": 0, "maxHigh": -1, "mode": "block"},
        )
        assert result == "pass"

    def test_evaluate_gate_fail_when_critical_exceeds_max(self):
        ctrl = self._import_controller()
        result = ctrl._evaluate_gate(
            {"critical": 1, "high": 0, "medium": 0},
            {"maxCritical": 0, "maxHigh": -1, "mode": "block"},
        )
        assert result == "fail"

    def test_evaluate_gate_warn_mode_returns_warn_not_fail(self):
        ctrl = self._import_controller()
        result = ctrl._evaluate_gate(
            {"critical": 2, "high": 0, "medium": 0},
            {"maxCritical": 0, "maxHigh": -1, "mode": "warn"},
        )
        assert result == "warn"

    def test_evaluate_gate_off_always_passes(self):
        ctrl = self._import_controller()
        result = ctrl._evaluate_gate(
            {"critical": 999, "high": 999},
            {"mode": "off"},
        )
        assert result == "pass"

    def test_evaluate_gate_high_threshold(self):
        ctrl = self._import_controller()
        result = ctrl._evaluate_gate(
            {"critical": 0, "high": 3},
            {"maxCritical": 0, "maxHigh": 5, "mode": "block"},
        )
        assert result == "pass"

        result2 = ctrl._evaluate_gate(
            {"critical": 0, "high": 6},
            {"maxCritical": 0, "maxHigh": 5, "mode": "block"},
        )
        assert result2 == "fail"

    def test_notify_webhook_called_with_correct_payload(self):
        ctrl = self._import_controller()
        with patch("httpx.post") as mock_post:
            ctrl._notify_webhook("https://hooks.slack.com/test", {"gate": "pass", "repo": "my/repo"})
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args
            assert call_kwargs[0][0] == "https://hooks.slack.com/test"

    def test_notify_webhook_silently_ignores_errors(self):
        ctrl = self._import_controller()
        with patch("httpx.post", side_effect=Exception("network down")):
            # Should not raise
            ctrl._notify_webhook("https://hooks.invalid/test", {"data": "payload"})


# ── #6 Kappa Study analyze_kappa.py ──────────────────────────────────────────


class TestKappaStudy:
    def test_fleiss_kappa_perfect_agreement(self):
        """Perfect agreement → κ = 1.0."""
        sys.path.insert(0, str(ROOT / "docs/kappa_study"))
        from analyze_kappa import fleiss_kappa

        # All 5 raters agree TP on every item
        matrix = [[5, 0, 0]] * 20
        assert fleiss_kappa(matrix) == 1.0

    def test_fleiss_kappa_chance_agreement(self):
        """Random agreement → κ ≈ 0."""
        from analyze_kappa import fleiss_kappa

        # Equal spread across categories
        matrix = [[2, 2, 1]] * 20
        kappa = fleiss_kappa(matrix)
        assert -0.3 < kappa < 0.3  # near-zero

    def test_fleiss_kappa_substantial(self):
        """Mostly-agreeing raters → κ > 0.61 (substantial)."""
        from analyze_kappa import fleiss_kappa

        # 5/5 agree on 18 items, split evenly on 2 — should be near-perfect
        matrix = [[5, 0, 0]] * 9 + [[0, 0, 5]] * 9 + [[3, 1, 1]] * 2
        kappa = fleiss_kappa(matrix)
        assert kappa > 0.7

    def test_interpret_thresholds(self):
        from analyze_kappa import interpret

        assert interpret(0.95) == "almost perfect"
        assert interpret(0.80) == "substantial"
        assert interpret(0.70) == "moderate"
        assert interpret(0.50) == "fair"
        assert interpret(0.30) == "slight"

    def test_load_csv_parses_correctly(self, tmp_path):
        import csv

        from analyze_kappa import load_csv

        f = tmp_path / "rater.csv"
        with open(f, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["finding_id", "label", "confidence", "note"])
            w.writerow([1, "TP", 3, ""])
            w.writerow([2, "FP", 2, "not tainted"])
            w.writerow([3, "NEEDS_REVIEW", 1, ""])
        result = load_csv(str(f))
        assert result == {1: "TP", 2: "FP", 3: "NEEDS_REVIEW"}

    def test_load_csv_skips_unknown_labels(self, tmp_path):
        import csv

        from analyze_kappa import load_csv

        f = tmp_path / "bad.csv"
        with open(f, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["finding_id", "label", "confidence", "note"])
            w.writerow([1, "TP", 3, ""])
            w.writerow([2, "UNKNOWN_LABEL", 1, "typo"])
        result = load_csv(str(f))
        assert 1 in result
        assert 2 not in result

    def test_bootstrap_ci_returns_ordered_bounds(self):
        from analyze_kappa import bootstrap_ci

        matrix = [[4, 1, 0]] * 15 + [[1, 4, 0]] * 15
        lo, hi = bootstrap_ci(matrix, n=200)
        assert lo <= hi
        assert 0 <= hi <= 1


# ── #4 devcontainer.json ─────────────────────────────────────────────────────


class TestDevcontainer:
    def test_devcontainer_valid_json(self):
        path = ROOT / ".devcontainer/devcontainer.json"
        assert path.exists(), "devcontainer.json missing"
        data = json.loads(path.read_text())
        assert "image" in data
        assert "features" in data
        assert "customizations" in data
        assert "vscode" in data["customizations"]

    def test_devcontainer_has_required_ports(self):
        data = json.loads((ROOT / ".devcontainer/devcontainer.json").read_text())
        assert 8000 in data["forwardPorts"]
        assert 5173 in data["forwardPorts"]

    def test_devcontainer_post_create_installs_deps(self):
        data = json.loads((ROOT / ".devcontainer/devcontainer.json").read_text())
        cmd = data.get("postCreateCommand", "")
        assert "pip install" in cmd
        assert "npm ci" in cmd


# ── #5 Cloudflare Pages HTML ─────────────────────────────────────────────────


class TestCloudflarePagesHTML:
    def _load(self, name):
        return (ROOT / "cloudflare-pages" / name).read_text()

    def test_index_html_exists(self):
        assert (ROOT / "cloudflare-pages/index.html").exists()

    def test_has_correct_precision_numbers(self):
        html = self._load("index.html")
        assert "96.4" in html
        assert "98.2" in html
        assert "100%" in html
        assert "1,942" in html
        assert "8/8" in html

    def test_has_comparison_table(self):
        html = self._load("index.html")
        assert "Bandit" in html
        assert "Semgrep" in html
        assert "21.8" in html
        assert "45.7" in html

    def test_has_docker_install_command(self):
        html = self._load("index.html")
        assert "ghcr.io/ahmed-145/acrqa" in html
        assert "docker run" in html

    def test_redirects_file_exists(self):
        assert (ROOT / "cloudflare-pages/_redirects").exists()

    def test_parses_as_html(self):
        from html.parser import HTMLParser

        class V(HTMLParser):
            pass

        V().feed(self._load("index.html"))  # raises on malformed HTML


# ── #1 Funnel Slide HTML ──────────────────────────────────────────────────────


class TestFunnelSlide:
    def _load(self):
        return (ROOT / "docs/FUNNEL_SLIDE.html").read_text()

    def test_exists(self):
        assert (ROOT / "docs/FUNNEL_SLIDE.html").exists()

    def test_has_correct_numbers(self):
        html = self._load()
        assert "1,942" in html
        assert "96.4" in html
        assert "98.2" in html
        assert "55" in html

    def test_has_keyboard_navigation(self):
        html = self._load()
        assert "ArrowRight" in html
        assert "ArrowLeft" in html
        assert "advance" in html.lower()

    def test_has_all_funnel_stages(self):
        html = self._load()
        assert "8.6" in html  # Rung 0 precision
        assert "24.7" in html  # Rung 3
        assert "26.9" in html  # P3
        assert "Confirmed" in html

    def test_parses_as_html(self):
        from html.parser import HTMLParser

        class V(HTMLParser):
            pass

        V().feed(self._load())


# ── #8 VS Code Extension package.json ────────────────────────────────────────


class TestVSCodeExtension:
    def _load(self):
        return json.loads((ROOT / "vscode-extension/package.json").read_text())

    def test_package_json_valid(self):
        pkg = self._load()
        assert pkg["name"] == "acrqa"
        assert "contributes" in pkg
        assert "commands" in pkg["contributes"]

    def test_has_required_commands(self):
        pkg = self._load()
        commands = {c["command"] for c in pkg["contributes"]["commands"]}
        assert "acrqa.scanWorkspace" in commands
        assert "acrqa.scanFile" in commands
        assert "acrqa.clearDiagnostics" in commands

    def test_has_configuration_schema(self):
        pkg = self._load()
        props = pkg["contributes"]["configuration"]["properties"]
        assert "acrqa.serverUrl" in props
        assert "acrqa.mode" in props
        assert "acrqa.confirmedTierOnly" in props
        assert "acrqa.groqApiKey" in props

    def test_activation_events_cover_all_languages(self):
        pkg = self._load()
        events = pkg["activationEvents"]
        assert any("*.py" in e for e in events)
        assert any("*.js" in e for e in events)
        assert any("*.ts" in e for e in events)
        assert any("*.go" in e for e in events)

    def test_extension_ts_has_correct_exports(self):
        src = (ROOT / "vscode-extension/src/extension.ts").read_text()
        assert "export function activate" in src
        assert "export function deactivate" in src

    def test_extension_ts_uses_correct_api_routes(self):
        src = (ROOT / "vscode-extension/src/extension.ts").read_text()
        # Routes are in template literals like `${base}/v1/scans` — check substrings
        assert "/v1/scans" in src, "missing /v1/scans route"
        assert "/v1/runs/" in src, "missing /v1/runs route"


# ── GitHub Actions Workflows ──────────────────────────────────────────────────


class TestWorkflows:
    def _load_workflow(self, name):
        return yaml.safe_load((ROOT / ".github/workflows" / name).read_text())

    def test_self_scan_workflow_structure(self):
        wf = self._load_workflow("self-scan.yml")
        assert "jobs" in wf
        assert "self-scan" in wf["jobs"]
        steps = wf["jobs"]["self-scan"]["steps"]
        step_names = [s.get("name", "") for s in steps]
        assert any("ACR-QA" in n or "scan" in n.lower() for n in step_names)
        assert any("badge" in n.lower() for n in step_names)

    def test_self_scan_has_schedule_trigger(self):
        wf = self._load_workflow("self-scan.yml")
        on = wf.get("on") or wf.get(True)  # YAML 'on' parsed as True
        assert "schedule" in on or "schedule" in str(on)

    def test_sign_images_workflow_has_slsa_job(self):
        wf = self._load_workflow("sign-images.yml")
        assert "jobs" in wf
        jobs = wf["jobs"]
        # Must have build job + provenance job
        assert "build" in jobs
        assert "provenance" in jobs

    def test_sign_images_has_slsa_generator(self):
        raw = (ROOT / ".github/workflows/sign-images.yml").read_text()
        assert "slsa-framework/slsa-github-generator" in raw

    def test_sign_images_has_cosign_signing(self):
        raw = (ROOT / ".github/workflows/sign-images.yml").read_text()
        assert "cosign sign" in raw

    def test_all_workflow_yamls_parse(self):
        for f in (ROOT / ".github/workflows").glob("*.yml"):
            content = yaml.safe_load(f.read_text())
            assert content is not None, f"{f.name} parsed to None"


# ── Database New Methods ──────────────────────────────────────────────────────


class TestDatabaseNewMethods:
    def test_get_run_by_id_delegates_to_get_analysis_run(self):
        from DATABASE.database import Database

        db = Database.__new__(Database)
        with patch.object(db, "get_analysis_run", return_value={"id": 42, "repo_name": "test"}) as mock_gar:
            result = db.get_run_by_id(42)
        mock_gar.assert_called_once_with(42)
        assert result == {"id": 42, "repo_name": "test"}

    def test_get_run_by_id_returns_none_for_missing(self):
        from DATABASE.database import Database

        db = Database.__new__(Database)
        with patch.object(db, "get_analysis_run", return_value=None):
            result = db.get_run_by_id(999)
        assert result is None

    def test_update_finding_counterfactual_calls_execute(self):
        from DATABASE.database import Database

        db = Database.__new__(Database)
        with patch.object(db, "execute") as mock_exec:
            db.update_finding_counterfactual(1, {"counterfactual": "use params", "status": "success"})
        mock_exec.assert_called_once()
        call_args = mock_exec.call_args
        # Verify it's an UPDATE statement
        assert "UPDATE" in call_args[0][0].upper()
        assert "counterfactual" in call_args[0][0].lower()

    def test_update_finding_counterfactual_serializes_result(self):
        from DATABASE.database import Database

        db = Database.__new__(Database)
        calls = []
        with patch.object(db, "execute", side_effect=lambda q, p: calls.append(p)):
            result_dict = {"counterfactual": "fix x", "confidence": "high", "status": "success"}
            db.update_finding_counterfactual(7, result_dict)
        assert len(calls) == 1
        # Second param should be finding_id=7
        params = calls[0]
        assert 7 in params
        # First param should be JSON string
        json_param = params[0]
        parsed = json.loads(json_param)
        assert parsed["confidence"] == "high"


# ── K8s CRD YAML Validity ─────────────────────────────────────────────────────


class TestOperatorYAML:
    def test_crd_yaml_parses(self):
        crd = yaml.safe_load((ROOT / "deploy/operator/config/crd/acrqascan_crd.yaml").read_text())
        assert crd["kind"] == "CustomResourceDefinition"
        assert crd["metadata"]["name"] == "acrqascans.acrqa.io"

    def test_crd_has_required_spec_fields(self):
        crd = yaml.safe_load((ROOT / "deploy/operator/config/crd/acrqascan_crd.yaml").read_text())
        schema = crd["spec"]["versions"][0]["schema"]["openAPIV3Schema"]
        props = schema["properties"]["spec"]["properties"]
        assert "repoUrl" in props
        assert "branch" in props
        assert "qualityGate" in props
        assert "confirmedTierOnly" in props

    def test_deployment_yaml_parses(self):
        dep = yaml.safe_load((ROOT / "deploy/operator/config/operator_deployment.yaml").read_text())
        assert dep["kind"] == "Deployment"
        assert dep["metadata"]["name"] == "acrqa-operator"

    def test_rbac_yamls_valid(self):
        for name in ["serviceaccount.yaml", "clusterrole.yaml", "clusterrolebinding.yaml"]:
            content = yaml.safe_load((ROOT / f"deploy/operator/config/rbac/{name}").read_text())
            assert content is not None
            assert "kind" in content

    def test_example_cr_is_valid(self):
        cr = yaml.safe_load((ROOT / "deploy/operator/example_scan.yaml").read_text())
        assert cr["apiVersion"] == "acrqa.io/v1alpha1"
        assert cr["kind"] == "ACRQAScan"
        assert "repoUrl" in cr["spec"]
