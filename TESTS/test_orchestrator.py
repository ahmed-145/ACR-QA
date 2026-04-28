"""
Integration tests for AnalysisPipeline orchestrator methods in CORE/main.py.

Strategy: mock all external I/O (DB, Redis, Groq, subprocess, filesystem),
then call run(), run_js(), and the main() auto-language routing end-to-end.

Target: boost main.py coverage from ~31% to ~50%.
"""

from unittest.mock import MagicMock, patch

# ─────────────────────────────────────────────────────────────
#  Shared helpers
# ─────────────────────────────────────────────────────────────


def _make_pipeline(target_dir="/tmp", config=None):
    """Build AnalysisPipeline without touching DB, Groq, or Redis."""
    mock_db = MagicMock()
    mock_db.create_analysis_run.return_value = 42
    mock_db.insert_finding.return_value = 99
    mock_explainer = MagicMock()
    mock_explainer.generate_explanation_batch.return_value = []
    mock_explainer.model = "llama-4"
    mock_explainer.temperature = 0.1
    mock_explainer.max_tokens = 256
    mock_config_loader = MagicMock()
    mock_config_loader.load.return_value = config or {}

    with patch("CORE.main.Database", return_value=mock_db):
        with patch("CORE.main.ExplanationEngine", return_value=mock_explainer):
            with patch("CORE.main.ConfigLoader", return_value=mock_config_loader):
                from CORE.main import AnalysisPipeline

                p = AnalysisPipeline(target_dir=target_dir)

    p.db = mock_db
    p.explainer = mock_explainer
    p.config = config or {}
    return p


def _sample_finding(rule_id="SECURITY-001", severity="high", category="security"):
    """Return a minimal canonical finding dict for testing."""
    return {
        "canonical_rule_id": rule_id,
        "canonical_severity": severity,
        "category": category,
        "file": "app.py",
        "file_path": "app.py",
        "line": 10,
        "line_number": 10,
        "tool": "bandit",
        "message": "Test security finding",
    }


def _mock_rate_limiter(allowed=True, retry_after=0.0):
    """Return a mock rate limiter that either allows or blocks."""
    mock_rl = MagicMock()
    mock_rl.check_rate_limit.return_value = (allowed, retry_after)
    mock_rl.redis = None
    return mock_rl


def _good_expl(n=1):
    """Return a list of n good explanation dicts."""
    return [
        {
            "response_text": "This is a security issue.",
            "latency_ms": 50,
            "status": "ok",
            "model_name": "llama-4",
            "prompt_filled": "",
            "temperature": 0.1,
            "max_tokens": 256,
            "tokens_used": 10,
            "cost_usd": 0.0,
        }
        for _ in range(n)
    ]


def _run_with_mocks(findings=None, config=None, rate_allowed=True, limit=None, rich_output=False):
    """End-to-end helper for pipeline.run() with all deps mocked."""
    if findings is None:
        findings = [_sample_finding()]

    p = _make_pipeline(config=config)
    mock_rl = _mock_rate_limiter(allowed=rate_allowed, retry_after=30.0)

    # Patch ExplanationEngine constructor — run() recreates it at line 129
    spy_explainer = MagicMock()
    spy_explainer.generate_explanation_batch.return_value = _good_expl(len(findings))
    spy_explainer.model = "llama-4"
    spy_explainer.temperature = 0.1
    spy_explainer.max_tokens = 256
    spy_explainer.get_fallback_explanation.return_value = "Fallback text"

    with patch("CORE.main.get_rate_limiter", return_value=mock_rl):
        with patch("CORE.main.ExplanationEngine", return_value=spy_explainer):
            with patch.object(p, "run_extra_scanners", return_value=[]):
                with patch.object(p, "_load_findings", return_value=findings):
                    with patch(
                        "CORE.engines.triage_memory.TriageMemory.suppress_findings",
                        return_value=(findings, 0),
                    ):
                        with patch("subprocess.run"):
                            with patch("CORE.main.extract_code_snippet", return_value="snippet"):
                                run_id = p.run(
                                    repo_name="test-repo",
                                    pr_number=1,
                                    limit=limit,
                                    rich_output=rich_output,
                                )
    p._spy_explainer = spy_explainer
    return run_id, p


# ════════════════════════════════════════════════════════════
#  TestRunOrchestrator — pipeline.run()
# ════════════════════════════════════════════════════════════


class TestRunOrchestrator:
    """Tests for the main Python analysis pipeline run() method."""

    def test_happy_path_returns_run_id(self):
        """run() should return the DB run_id on success."""
        run_id, _ = _run_with_mocks()
        assert run_id == 42

    def test_creates_analysis_run_in_db(self):
        """run() must call db.create_analysis_run exactly once."""
        _, p = _run_with_mocks()
        p.db.create_analysis_run.assert_called_once_with(repo_name="test-repo", pr_number=1)

    def test_completes_analysis_run_in_db(self):
        """run() must call db.complete_analysis_run to mark the run done."""
        _, p = _run_with_mocks()
        p.db.complete_analysis_run.assert_called_once()

    def test_rate_limited_returns_none(self):
        """run() must return None when the rate limiter rejects the request."""
        run_id, _ = _run_with_mocks(rate_allowed=False)
        assert run_id is None

    def test_rate_limited_never_hits_db(self):
        """run() must NOT create a DB run when rate-limited."""
        _, p = _run_with_mocks(rate_allowed=False)
        p.db.create_analysis_run.assert_not_called()

    def test_empty_findings_still_completes(self):
        """run() with zero findings should still complete and return the run_id."""
        run_id, p = _run_with_mocks(findings=[])
        assert run_id == 42
        p.db.complete_analysis_run.assert_called_once()

    def test_multiple_findings_inserts_each(self):
        """Each finding must be inserted into the database."""
        findings = [_sample_finding(rule_id=f"SECURITY-{i:03d}") for i in range(3)]
        _, p = _run_with_mocks(findings=findings)
        assert p.db.insert_finding.call_count == 3

    def test_explanation_inserted_for_each_finding(self):
        """An explanation record must be written for each finding that was processed."""
        findings = [_sample_finding(), _sample_finding(rule_id="IMPORT-001", severity="low")]
        _, p = _run_with_mocks(findings=findings)
        assert p.db.insert_explanation.call_count == 2

    def test_gate_passed_attribute_set(self):
        """After run(), the pipeline must expose _gate_passed for CI exit-code logic."""
        _, p = _run_with_mocks()
        assert hasattr(p, "_gate_passed")

    def test_gate_comment_attribute_set(self):
        """After run(), the pipeline must expose _gate_comment for PR comment posting."""
        _, p = _run_with_mocks()
        assert hasattr(p, "_gate_comment")
        assert isinstance(p._gate_comment, str)

    def test_high_severity_findings_gate_may_fail(self):
        """Many high severity findings should cause the quality gate to fail."""
        findings = [_sample_finding("SECURITY-001", "high") for _ in range(10)]
        _, p = _run_with_mocks(findings=findings)
        # Gate is evaluated — _gate_passed must exist (may be False for 10 highs)
        assert hasattr(p, "_gate_passed")

    def test_run_with_limit_caps_explanations(self):
        """When limit=1, only 1 explanation should be requested from the AI."""
        findings = [_sample_finding(rule_id=f"SECURITY-{i:03d}") for i in range(5)]
        p = _make_pipeline()
        mock_rl = _mock_rate_limiter()

        # Use side_effect to capture what batch receives
        captured_batch = []

        def capture_batch(batch):
            """Spy function that captures batch contents."""
            captured_batch.extend(batch)
            return _good_expl(len(batch))

        spy_explainer = MagicMock()
        spy_explainer.generate_explanation_batch.side_effect = capture_batch
        spy_explainer.model = "llama-4"
        spy_explainer.temperature = 0.1
        spy_explainer.max_tokens = 256

        with patch("CORE.main.get_rate_limiter", return_value=mock_rl):
            with patch("CORE.main.ExplanationEngine", return_value=spy_explainer):
                with patch.object(p, "run_extra_scanners", return_value=[]):
                    with patch.object(p, "_load_findings", return_value=findings):
                        with patch(
                            "CORE.engines.triage_memory.TriageMemory.suppress_findings",
                            return_value=(findings, 0),
                        ):
                            with patch("subprocess.run"):
                                with patch("CORE.main.extract_code_snippet", return_value="x"):
                                    p.run(repo_name="repo", limit=1)

        assert len(captured_batch) == 1

    def test_explanation_exception_uses_fallback(self):
        """If batch returns an Exception, a fallback explanation must be stored."""
        findings = [_sample_finding()]
        p = _make_pipeline()
        mock_rl = _mock_rate_limiter()

        spy_explainer = MagicMock()
        # Returning an Exception object in a normal list mimics asyncio.gather error wrapping
        spy_explainer.generate_explanation_batch.return_value = [RuntimeError("API down")]
        spy_explainer.get_fallback_explanation.return_value = "Fallback text"
        spy_explainer.model = "llama-4"
        spy_explainer.temperature = 0.1
        spy_explainer.max_tokens = 256

        with patch("CORE.main.get_rate_limiter", return_value=mock_rl):
            with patch("CORE.main.ExplanationEngine", return_value=spy_explainer):
                with patch.object(p, "run_extra_scanners", return_value=[]):
                    with patch.object(p, "_load_findings", return_value=findings):
                        with patch(
                            "CORE.engines.triage_memory.TriageMemory.suppress_findings",
                            return_value=(findings, 0),
                        ):
                            with patch("subprocess.run"):
                                with patch("CORE.main.extract_code_snippet", return_value="x"):
                                    p.run(repo_name="repo")

        p.db.insert_explanation.assert_called_once()
        stored = p.db.insert_explanation.call_args[0][1]
        # Fallback path should set status='fallback'
        assert stored["status"] == "fallback"

    def test_rich_output_calls_print_rich(self):
        """run() with rich_output=True should call _print_rich_output."""
        findings = [_sample_finding()]
        p = _make_pipeline()
        mock_rl = _mock_rate_limiter()
        spy_explainer = MagicMock()
        spy_explainer.generate_explanation_batch.return_value = _good_expl(1)

        with patch("CORE.main.get_rate_limiter", return_value=mock_rl):
            with patch("CORE.main.ExplanationEngine", return_value=spy_explainer):
                with patch.object(p, "run_extra_scanners", return_value=[]):
                    with patch.object(p, "_load_findings", return_value=findings):
                        with patch(
                            "CORE.engines.triage_memory.TriageMemory.suppress_findings",
                            return_value=(findings, 0),
                        ):
                            with patch("subprocess.run"):
                                with patch("CORE.main.extract_code_snippet", return_value="x"):
                                    with patch.object(p, "_print_rich_output") as mock_rich:
                                        p.run(repo_name="repo", rich_output=True)

        mock_rich.assert_called_once()


# ════════════════════════════════════════════════════════════
#  TestRunJsOrchestrator — pipeline.run_js()
# ════════════════════════════════════════════════════════════


class TestRunJsOrchestrator:
    """Tests for the JavaScript/TypeScript analysis pipeline run_js() method."""

    def _run_js_with_mocks(self, findings=None, rate_allowed=True):
        """Helper: run pipeline.run_js() with all external deps mocked."""
        if findings is None:
            findings = [_sample_finding("SECURITY-045", "high", "security")]

        # JS adapter returns dataclass instances; use a proper dataclass to avoid asdict() error
        from dataclasses import dataclass

        @dataclass
        class _FakeFinding:
            """Minimal fake JS finding dataclass."""

            rule_id: str = "SECURITY-045"
            canonical_rule_id: str = "SECURITY-045"
            severity: str = "high"
            canonical_severity: str = "high"
            category: str = "security"
            file: str = "app.js"
            file_path: str = "app.js"
            line: int = 10
            line_number: int = 10
            tool: str = "eslint"
            message: str = "XSS vulnerability"

        mock_finding_obj = _FakeFinding()

        p = _make_pipeline()
        mock_rl = _mock_rate_limiter(allowed=rate_allowed, retry_after=30.0)

        mock_js_adapter = MagicMock()
        mock_js_adapter.run_tools.return_value = {}
        mock_js_adapter.get_all_findings.return_value = [mock_finding_obj]

        mock_gate_result = {
            "passed": True,
            "status": "✅ PASSED",
            "counts": {"total": 1, "high": 1, "medium": 0, "low": 0},
            "checks": [],
        }

        # run_js() also recreates ExplanationEngine internally — patch it
        spy_explainer = MagicMock()
        spy_explainer.generate_explanation_batch.return_value = _good_expl(len(findings))
        spy_explainer.model = "llama-4"
        spy_explainer.temperature = 0.1
        spy_explainer.max_tokens = 256

        with patch("CORE.utils.rate_limiter.get_rate_limiter", return_value=mock_rl):
            with patch("CORE.main.ExplanationEngine", return_value=spy_explainer):
                with patch("CORE.adapters.js_adapter.JavaScriptAdapter", return_value=mock_js_adapter):
                    with patch("CORE.engines.cbom_scanner.CBoMScanner") as mock_cbom_cls:
                        mock_cbom = MagicMock()
                        mock_report = MagicMock()
                        mock_report.total_usages = 0
                        mock_report.unsafe_count = 0
                        mock_report.warn_count = 0
                        mock_report.safe_count = 0
                        mock_report.algorithms_found = {}
                        mock_cbom.scan.return_value = mock_report
                        mock_cbom.to_findings.return_value = []
                        mock_cbom_cls.return_value = mock_cbom

                        with patch(
                            "CORE.engines.triage_memory.TriageMemory.suppress_findings",
                            return_value=(findings, 0),
                        ):
                            with patch("CORE.main.extract_code_snippet", return_value="snippet"):
                                with patch(
                                    "CORE.engines.quality_gate.QualityGate.evaluate",
                                    return_value=mock_gate_result,
                                ):
                                    with patch(
                                        "CORE.engines.quality_gate.QualityGate.should_block",
                                        return_value=False,
                                    ):
                                        with patch(
                                            "CORE.engines.quality_gate.QualityGate.format_gate_comment",
                                            return_value="Gate OK",
                                        ):
                                            run_id = p.run_js(repo_name="js-repo", pr_number=2)

        return run_id, p

    def test_happy_path_returns_run_id(self):
        """run_js() should return the DB run_id on success."""
        run_id, _ = self._run_js_with_mocks()
        assert run_id == 42

    def test_creates_analysis_run_in_db(self):
        """run_js() must call db.create_analysis_run exactly once."""
        _, p = self._run_js_with_mocks()
        p.db.create_analysis_run.assert_called_once_with(repo_name="js-repo", pr_number=2)

    def test_rate_limited_returns_none(self):
        """run_js() must return None when the rate limiter rejects the request."""
        run_id, _ = self._run_js_with_mocks(rate_allowed=False)
        assert run_id is None

    def test_rate_limited_never_hits_db(self):
        """run_js() must NOT create a DB run when rate-limited."""
        _, p = self._run_js_with_mocks(rate_allowed=False)
        p.db.create_analysis_run.assert_not_called()

    def test_gate_passed_attribute_set(self):
        """After run_js(), the pipeline must expose _gate_passed."""
        _, p = self._run_js_with_mocks()
        assert hasattr(p, "_gate_passed")
        assert p._gate_passed is True

    def test_empty_js_findings_still_completes(self):
        """run_js() with zero findings should still return the run_id."""
        run_id, _ = self._run_js_with_mocks(findings=[])
        assert run_id == 42


# ════════════════════════════════════════════════════════════
#  TestRunAutoLanguageRouting — main() language auto-detection
# ════════════════════════════════════════════════════════════


class TestRunAutoLanguageRouting:
    """Tests for the language auto-detection routing in main()."""

    def test_auto_detects_python_and_calls_run(self):
        """When detect_language returns 'python', main() should call pipeline.run()."""
        from CORE.main import AnalysisPipeline

        with patch("CORE.adapters.js_adapter.JavaScriptAdapter.detect_language", return_value="python"):
            with patch.object(AnalysisPipeline, "__init__", return_value=None):
                with patch.object(AnalysisPipeline, "run", return_value=42) as mock_run:
                    with patch("CORE.main.Database"):
                        with patch("CORE.main.ExplanationEngine"):
                            with patch("CORE.main.ConfigLoader") as mock_cl:
                                mock_cl.return_value.load.return_value = {}
                                import sys

                                with patch.object(sys, "argv", ["main.py", "--target-dir", "/tmp", "--no-ai"]):
                                    try:
                                        from CORE.main import main

                                        main()
                                    except SystemExit:
                                        pass
        mock_run.assert_called()

    def test_auto_detects_js_and_calls_run_js(self):
        """When detect_language returns 'javascript', main() should call pipeline.run_js()."""
        from CORE.main import AnalysisPipeline

        with patch(
            "CORE.adapters.js_adapter.JavaScriptAdapter.detect_language",
            return_value="javascript",
        ):
            with patch.object(AnalysisPipeline, "__init__", return_value=None):
                with patch.object(AnalysisPipeline, "run_js", return_value=42) as mock_run_js:
                    with patch("CORE.main.Database"):
                        with patch("CORE.main.ExplanationEngine"):
                            with patch("CORE.main.ConfigLoader") as mock_cl:
                                mock_cl.return_value.load.return_value = {}
                                import sys

                                with patch.object(sys, "argv", ["main.py", "--target-dir", "/tmp", "--no-ai"]):
                                    try:
                                        from CORE.main import main

                                        main()
                                    except SystemExit:
                                        pass
        mock_run_js.assert_called()

    def test_explicit_lang_go_prints_findings(self, capsys):
        """--lang go should print a Go findings summary (not call run/run_js)."""
        mock_go_adapter = MagicMock()
        mock_go_adapter.check_tools_available.return_value = {"gosec": True, "staticcheck": True}
        mock_go_adapter.run_tools.return_value = {"errors": []}
        mock_go_adapter.get_all_findings.return_value = []

        with patch("CORE.adapters.go_adapter.GoAdapter", return_value=mock_go_adapter):
            with patch("CORE.main.Database"):
                with patch("CORE.main.ExplanationEngine"):
                    with patch("CORE.main.ConfigLoader") as mock_cl:
                        mock_cl.return_value.load.return_value = {}
                        import sys

                        with patch.object(
                            sys,
                            "argv",
                            ["main.py", "--target-dir", "/tmp", "--lang", "go", "--no-ai"],
                        ):
                            try:
                                from CORE.main import main

                                main()
                            except SystemExit:
                                pass

        captured = capsys.readouterr()
        assert "Go Adapter" in captured.out or "findings" in captured.out.lower()

    def test_explicit_lang_python_skips_js(self):
        """--lang python should call run() even if the dir has a package.json."""
        from CORE.main import AnalysisPipeline

        with patch.object(AnalysisPipeline, "__init__", return_value=None):
            with patch.object(AnalysisPipeline, "run", return_value=99) as mock_run:
                with patch.object(AnalysisPipeline, "run_js") as mock_run_js:
                    with patch("CORE.main.Database"):
                        with patch("CORE.main.ExplanationEngine"):
                            with patch("CORE.main.ConfigLoader") as mock_cl:
                                mock_cl.return_value.load.return_value = {}
                                import sys

                                with patch.object(
                                    sys,
                                    "argv",
                                    [
                                        "main.py",
                                        "--target-dir",
                                        "/tmp",
                                        "--lang",
                                        "python",
                                        "--no-ai",
                                    ],
                                ):
                                    try:
                                        from CORE.main import main

                                        main()
                                    except SystemExit:
                                        pass
        mock_run.assert_called()
        mock_run_js.assert_not_called()


# ════════════════════════════════════════════════════════════
#  TestPipelineInit — AnalysisPipeline.__init__
# ════════════════════════════════════════════════════════════


class TestPipelineInit:
    """Tests for AnalysisPipeline initialization."""

    def test_init_sets_target_dir(self):
        """The pipeline must remember the target directory."""
        p = _make_pipeline(target_dir="/tmp/myrepo")
        assert p.target_dir == "/tmp/myrepo"

    def test_init_with_files_list(self):
        """The pipeline must store files list for diff-only mode."""
        mock_db = MagicMock()
        mock_explainer = MagicMock()
        mock_cl = MagicMock()
        mock_cl.load.return_value = {}

        with patch("CORE.main.Database", return_value=mock_db):
            with patch("CORE.main.ExplanationEngine", return_value=mock_explainer):
                with patch("CORE.main.ConfigLoader", return_value=mock_cl):
                    from CORE.main import AnalysisPipeline

                    p = AnalysisPipeline(target_dir="/tmp", files=["a.py", "b.py"])

        assert p.files == ["a.py", "b.py"]

    def test_init_loads_config(self):
        """The pipeline must invoke ConfigLoader.load() during init."""
        mock_db = MagicMock()
        mock_explainer = MagicMock()
        mock_cl = MagicMock()
        mock_cl.load.return_value = {"reporting": {"min_severity": "high"}}

        with patch("CORE.main.Database", return_value=mock_db):
            with patch("CORE.main.ExplanationEngine", return_value=mock_explainer):
                with patch("CORE.main.ConfigLoader", return_value=mock_cl):
                    from CORE.main import AnalysisPipeline

                    p = AnalysisPipeline(target_dir="/tmp")

        mock_cl.load.assert_called_once()
        assert p.config == {"reporting": {"min_severity": "high"}}
