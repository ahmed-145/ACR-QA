"""
God-mode tests for CORE/main.py helper methods (target: 40%+)

Strategy: instantiate AnalysisPipeline with mocked Database + ExplanationEngine,
then call pure helper methods directly without touching filesystem.
Also tests get_diff_files() with subprocess mocking.
"""

import subprocess
from unittest.mock import MagicMock, patch

# ─────────────────────────────────────────────────────────────
#  Helpers to build pipeline with minimal mocking
# ─────────────────────────────────────────────────────────────


def _make_pipeline(target_dir="/tmp", config=None):
    """Build AnalysisPipeline without touching DB, Cerebras, or Redis."""
    mock_db = MagicMock()
    mock_explainer = MagicMock()
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


def _finding(rule_id="SECURITY-001", severity="high", category="security", file="app.py", line=10, tool="bandit"):
    return {
        "canonical_rule_id": rule_id,
        "canonical_severity": severity,
        "category": category,
        "file": file,
        "file_path": file,
        "line": line,
        "line_number": line,
        "tool": tool,
        "message": "test finding",
    }


# ════════════════════════════════════════════════════════════
#  _deduplicate_findings
# ════════════════════════════════════════════════════════════


class TestDeduplicateFindings:
    def test_empty_list(self):
        p = _make_pipeline()
        assert p._deduplicate_findings([]) == []

    def test_no_duplicates_unchanged(self):
        p = _make_pipeline()
        findings = [
            _finding("SECURITY-001", file="a.py", line=1),
            _finding("SECURITY-002", file="a.py", line=2),
        ]
        result = p._deduplicate_findings(findings)
        assert len(result) == 2

    def test_exact_duplicate_kept_once(self):
        p = _make_pipeline()
        f1 = _finding("SECURITY-001", file="a.py", line=5, tool="ruff")
        f2 = _finding("SECURITY-001", file="a.py", line=5, tool="ruff")
        result = p._deduplicate_findings([f1, f2])
        assert len(result) == 1

    def test_higher_priority_tool_wins_on_exact_dup(self):
        p = _make_pipeline()
        f_ruff = _finding("SECURITY-001", file="a.py", line=5, tool="ruff")
        f_bandit = _finding("SECURITY-001", file="a.py", line=5, tool="bandit")
        result = p._deduplicate_findings([f_ruff, f_bandit])
        assert len(result) == 1
        assert result[0]["tool"] == "bandit"

    def test_different_lines_not_deduped(self):
        p = _make_pipeline()
        f1 = _finding("SECURITY-001", file="a.py", line=1)
        f2 = _finding("SECURITY-001", file="a.py", line=2)
        result = p._deduplicate_findings([f1, f2])
        assert len(result) == 2

    def test_different_files_not_deduped(self):
        p = _make_pipeline()
        f1 = _finding("SECURITY-001", file="a.py", line=1)
        f2 = _finding("SECURITY-001", file="b.py", line=1)
        result = p._deduplicate_findings([f1, f2])
        assert len(result) == 2

    def test_cross_tool_dedup_same_group(self):
        """SECURITY-020 and SECURITY-024 are both in shell-injection group."""
        p = _make_pipeline()
        f1 = {**_finding("SECURITY-020", file="a.py", line=5, tool="semgrep")}
        f2 = {**_finding("SECURITY-024", file="a.py", line=5, tool="bandit")}
        result = p._deduplicate_findings([f1, f2])
        # Both in same group → only 1 kept
        assert len(result) == 1

    def test_cross_tool_keeps_higher_priority(self):
        """Bandit (3) > semgrep (3) → first wins in cross-tool."""
        p = _make_pipeline()
        f_ruff = {**_finding("SECURITY-020", file="a.py", line=5, tool="ruff")}
        f_semgrep = {**_finding("CUSTOM-shell-injection", file="a.py", line=5, tool="semgrep")}
        result = p._deduplicate_findings([f_ruff, f_semgrep])
        assert len(result) == 1
        assert result[0]["tool"] == "semgrep"

    def test_unrelated_rules_not_cross_deduped(self):
        """SECURITY-001 and SECURITY-009 are in different groups."""
        p = _make_pipeline()
        f1 = _finding("SECURITY-001", file="a.py", line=5, tool="bandit")
        f2 = _finding("SECURITY-009", file="a.py", line=5, tool="bandit")
        result = p._deduplicate_findings([f1, f2])
        assert len(result) == 2


# ════════════════════════════════════════════════════════════
#  _cap_per_rule
# ════════════════════════════════════════════════════════════


class TestCapPerRule:
    def test_empty_returns_empty(self):
        p = _make_pipeline()
        assert p._cap_per_rule([]) == []

    def test_under_cap_unchanged(self):
        p = _make_pipeline()
        findings = [_finding("IMPORT-001", line=i) for i in range(3)]
        result = p._cap_per_rule(findings, max_per_rule=5)
        assert len(result) == 3

    def test_over_cap_trimmed(self):
        p = _make_pipeline()
        findings = [_finding("IMPORT-001", line=i) for i in range(10)]
        result = p._cap_per_rule(findings, max_per_rule=5)
        assert len(result) == 5

    def test_different_rules_independent_cap(self):
        p = _make_pipeline()
        findings = [_finding("A", line=i) for i in range(6)] + [_finding("B", line=i) for i in range(6)]
        result = p._cap_per_rule(findings, max_per_rule=5)
        assert len(result) == 10  # 5 per rule

    def test_exactly_at_cap_kept(self):
        p = _make_pipeline()
        findings = [_finding("X", line=i) for i in range(5)]
        result = p._cap_per_rule(findings, max_per_rule=5)
        assert len(result) == 5

    def test_default_max_is_5(self):
        p = _make_pipeline()
        findings = [_finding("X", line=i) for i in range(8)]
        result = p._cap_per_rule(findings)
        assert len(result) == 5


# ════════════════════════════════════════════════════════════
#  _sort_by_priority
# ════════════════════════════════════════════════════════════


class TestSortByPriority:
    def test_high_before_medium_before_low(self):
        p = _make_pipeline()
        findings = [
            _finding(severity="low"),
            _finding(severity="high"),
            _finding(severity="medium"),
        ]
        result = p._sort_by_priority(findings)
        sevs = [f["canonical_severity"] for f in result]
        assert sevs == ["high", "medium", "low"]

    def test_security_before_style_within_same_severity(self):
        p = _make_pipeline()
        findings = [
            {**_finding(severity="high", category="style")},
            {**_finding(severity="high", category="security")},
        ]
        result = p._sort_by_priority(findings)
        assert result[0]["category"] == "security"

    def test_empty_list(self):
        p = _make_pipeline()
        assert p._sort_by_priority([]) == []

    def test_all_same_severity_stable(self):
        p = _make_pipeline()
        findings = [_finding(severity="medium") for _ in range(5)]
        result = p._sort_by_priority(findings)
        assert len(result) == 5

    def test_unknown_severity_goes_last(self):
        p = _make_pipeline()
        findings = [
            {"canonical_severity": "unknown", "category": "style"},
            _finding(severity="low"),
        ]
        result = p._sort_by_priority(findings)
        sevs = [f["canonical_severity"] for f in result]
        assert sevs[0] == "low"

    def test_full_priority_order(self):
        p = _make_pipeline()
        findings = [
            {**_finding(severity="low", category="style")},
            {**_finding(severity="high", category="security")},
            {**_finding(severity="medium", category="best-practice")},
            {**_finding(severity="high", category="design")},
        ]
        result = p._sort_by_priority(findings)
        # First two should both be high
        assert result[0]["canonical_severity"] == "high"
        assert result[1]["canonical_severity"] == "high"
        # security before design
        assert result[0]["category"] == "security"
        assert result[3]["canonical_severity"] == "low"


# ════════════════════════════════════════════════════════════
#  _apply_config_filters
# ════════════════════════════════════════════════════════════


class TestApplyConfigFilters:
    """_apply_config_filters calls ConfigLoader.__new__ then calls instance methods.
    We patch the three instance methods directly using patch.object on ConfigLoader.
    """

    def test_empty_config_passes_all(self):
        p = _make_pipeline(config={})
        findings = [_finding("SECURITY-001"), _finding("IMPORT-001")]
        with patch("CORE.main.ConfigLoader.is_rule_enabled", return_value=True):
            with patch("CORE.main.ConfigLoader.should_ignore_path", return_value=False):
                with patch("CORE.main.ConfigLoader.get_severity_override", return_value=None):
                    result = p._apply_config_filters(findings)
        assert len(result) == 2

    def test_disabled_rule_removed(self):
        p = _make_pipeline(config={})
        findings = [_finding("DISABLED-001"), _finding("SECURITY-001")]
        with patch("CORE.main.ConfigLoader.is_rule_enabled", side_effect=lambda r: r != "DISABLED-001"):
            with patch("CORE.main.ConfigLoader.should_ignore_path", return_value=False):
                with patch("CORE.main.ConfigLoader.get_severity_override", return_value=None):
                    result = p._apply_config_filters(findings)
        assert len(result) == 1
        assert result[0]["canonical_rule_id"] == "SECURITY-001"

    def test_ignored_path_removed(self):
        p = _make_pipeline(config={})
        findings = [
            {**_finding("SECURITY-001", file="tests/conftest.py")},
            {**_finding("SECURITY-001", file="src/app.py")},
        ]
        with patch("CORE.main.ConfigLoader.is_rule_enabled", return_value=True):
            with patch("CORE.main.ConfigLoader.should_ignore_path", side_effect=lambda fp: "tests" in fp):
                with patch("CORE.main.ConfigLoader.get_severity_override", return_value=None):
                    result = p._apply_config_filters(findings)
        assert len(result) == 1
        assert "src" in result[0]["file_path"]

    def test_min_severity_high_removes_medium_and_low(self):
        p = _make_pipeline(config={"reporting": {"min_severity": "high"}})
        findings = [
            {**_finding("A", severity="high")},
            {**_finding("B", severity="medium")},
            {**_finding("C", severity="low")},
        ]
        with patch("CORE.main.ConfigLoader.is_rule_enabled", return_value=True):
            with patch("CORE.main.ConfigLoader.should_ignore_path", return_value=False):
                with patch("CORE.main.ConfigLoader.get_severity_override", return_value=None):
                    result = p._apply_config_filters(findings)
        assert len(result) == 1
        assert result[0]["canonical_severity"] == "high"

    def test_severity_override_applied(self):
        p = _make_pipeline(config={})
        findings = [{**_finding("STYLE-001", severity="low")}]
        with patch("CORE.main.ConfigLoader.is_rule_enabled", return_value=True):
            with patch("CORE.main.ConfigLoader.should_ignore_path", return_value=False):
                with patch("CORE.main.ConfigLoader.get_severity_override", return_value="high"):
                    result = p._apply_config_filters(findings)
        assert result[0]["canonical_severity"] == "high"


# ════════════════════════════════════════════════════════════
#  get_diff_files
# ════════════════════════════════════════════════════════════


class TestGetDiffFiles:
    def test_returns_py_files_only(self):
        from CORE.main import get_diff_files

        mock_result = MagicMock()
        mock_result.stdout = "src/app.py\nREADME.md\nCORE/main.py\n"
        with patch("subprocess.run", return_value=mock_result):
            result = get_diff_files("main")
        assert all(f.endswith(".py") for f in result)
        assert "README.md" not in result

    def test_empty_diff_returns_empty_list(self):
        from CORE.main import get_diff_files

        mock_result = MagicMock()
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            result = get_diff_files()
        assert result == []

    def test_git_error_returns_empty_list(self):
        from CORE.main import get_diff_files

        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")):
            result = get_diff_files()
        assert result == []

    def test_strips_whitespace(self):
        from CORE.main import get_diff_files

        mock_result = MagicMock()
        mock_result.stdout = "  app.py  \n  main.py  \n"
        with patch("subprocess.run", return_value=mock_result):
            result = get_diff_files()
        assert "app.py" in result
        assert "  app.py  " not in result

    def test_default_base_branch_is_main(self):
        from CORE.main import get_diff_files

        mock_result = MagicMock()
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            get_diff_files()
        call_args = mock_run.call_args[0][0]
        assert "main" in call_args


# ════════════════════════════════════════════════════════════
#  run_extra_scanners
# ════════════════════════════════════════════════════════════


class TestRunExtraScanners:
    def test_returns_list_on_success(self):
        p = _make_pipeline()
        mock_detector = MagicMock()
        mock_detector.scan_directory.return_value = {"findings": []}
        mock_scanner = MagicMock()
        mock_scanner.scan.return_value = {"vulnerabilities": []}
        mock_cbom = MagicMock()
        mock_report = MagicMock()
        mock_report.total_usages = 0
        mock_report.unsafe_count = 0
        mock_report.warn_count = 0
        mock_report.safe_count = 0
        mock_report.algorithms_found = {}
        mock_cbom.scan.return_value = mock_report
        mock_cbom.to_findings.return_value = []

        with patch("CORE.engines.secrets_detector.SecretsDetector", return_value=mock_detector):
            with patch("CORE.engines.sca_scanner.SCAScanner", return_value=mock_scanner):
                with patch("CORE.engines.cbom_scanner.CBoMScanner", return_value=mock_cbom):
                    result = p.run_extra_scanners("/tmp")
        assert isinstance(result, list)

    def test_extends_with_secrets_findings(self):
        p = _make_pipeline()
        mock_detector = MagicMock()
        mock_detector.scan_directory.return_value = {"findings": [{"rule": "hardcoded"}]}
        mock_detector.to_canonical_findings.return_value = [_finding("HARDCODE-001")]
        mock_scanner = MagicMock()
        mock_scanner.scan.return_value = {}
        mock_cbom = MagicMock()
        mock_report = MagicMock()
        mock_report.total_usages = 0
        mock_report.unsafe_count = mock_report.warn_count = mock_report.safe_count = 0
        mock_report.algorithms_found = {}
        mock_cbom.scan.return_value = mock_report
        mock_cbom.to_findings.return_value = []

        with patch("CORE.engines.secrets_detector.SecretsDetector", return_value=mock_detector):
            with patch("CORE.engines.sca_scanner.SCAScanner", return_value=mock_scanner):
                with patch("CORE.engines.cbom_scanner.CBoMScanner", return_value=mock_cbom):
                    result = p.run_extra_scanners("/tmp")
        assert any(f.get("canonical_rule_id") == "HARDCODE-001" for f in result)

    def test_exception_in_secrets_scanner_does_not_crash(self):
        p = _make_pipeline()
        with patch("CORE.engines.secrets_detector.SecretsDetector", side_effect=Exception("crash")):
            with patch("CORE.engines.sca_scanner.SCAScanner") as mock_s:
                mock_s.return_value.scan.return_value = {}
                with patch("CORE.engines.cbom_scanner.CBoMScanner") as mock_c:
                    mock_report = MagicMock()
                    mock_report.total_usages = 0
                    mock_report.unsafe_count = mock_report.warn_count = mock_report.safe_count = 0
                    mock_report.algorithms_found = {}
                    mock_c.return_value.scan.return_value = mock_report
                    mock_c.return_value.to_findings.return_value = []
                    result = p.run_extra_scanners("/tmp")
        assert isinstance(result, list)

    def test_exception_in_all_scanners_returns_empty(self):
        p = _make_pipeline()
        with patch("CORE.engines.secrets_detector.SecretsDetector", side_effect=Exception("s")):
            with patch("CORE.engines.sca_scanner.SCAScanner", side_effect=Exception("c")):
                with patch("CORE.engines.cbom_scanner.CBoMScanner", side_effect=Exception("b")):
                    result = p.run_extra_scanners("/tmp")
        assert result == []
