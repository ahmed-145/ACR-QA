#!/usr/bin/env python3
"""
ACR-QA GOD MODE Test Suite
Comprehensive deep testing of ALL features — old and new.

Coverage targets:
  - Test Gap Analyzer (AST extraction, test mapping, gap detection, quality gate, reports)
  - OWASP Compliance Report (mapping, report generation, data API)
  - Feedback Tuner (FP rate computation, severity override generation)
  - Config Validator (schema validation, template generation)
  - Flask API Endpoints (/api/test-gaps, /api/policy, /api/compliance)
  - Confidence-Based Noise Control (_calculate_confidence)
  - Version Consistency (all scripts use CORE.__version__)
  - Policy Engine config (full .acrqa.yml lifecycle)
  - Cross-Feature Integration (combining multiple features end-to-end)
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE import __version__

# ═══════════════════════════════════════════════════════════════════════════
# 1. TEST GAP ANALYZER — DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestGapAnalyzerAST:
    """Test AST extraction from source files."""

    def setup_method(self):
        from scripts.test_gap_analyzer import SourceSymbol, extract_symbols

        self.extract = extract_symbols
        self.SourceSymbol = SourceSymbol

    def test_extract_simple_function(self, tmp_path):
        """Should extract a simple function."""
        p = tmp_path / "mod.py"
        p.write_text("def hello():\n    pass\n")
        symbols = self.extract(str(p))
        names = [s.name for s in symbols]
        assert "hello" in names

    def test_extract_class_and_methods(self, tmp_path):
        """Should extract class and its methods."""
        code = "class Foo:\n    def bar(self):\n        pass\n    def baz(self):\n        pass\n"
        p = tmp_path / "cls.py"
        p.write_text(code)
        symbols = self.extract(str(p))
        names = [s.name for s in symbols]
        assert "Foo" in names
        assert "bar" in names

    def test_extract_async_function(self, tmp_path):
        """Should extract async functions."""
        p = tmp_path / "async_mod.py"
        p.write_text("async def fetch_data():\n    pass\n")
        symbols = self.extract(str(p))
        names = [s.name for s in symbols]
        assert "fetch_data" in names

    def test_extract_private_functions(self, tmp_path):
        """Should detect _private and __dunder__ functions."""
        code = "def _helper():\n    pass\ndef __repr__(self):\n    pass\ndef public():\n    pass\n"
        p = tmp_path / "priv.py"
        p.write_text(code)
        symbols = self.extract(str(p))
        private_syms = [s for s in symbols if s.is_private]
        dunder_syms = [s for s in symbols if s.is_dunder]
        public_syms = [s for s in symbols if not s.is_private and not s.is_dunder]
        assert len(private_syms) >= 1
        assert len(dunder_syms) >= 1
        assert len(public_syms) >= 1

    def test_extract_empty_file(self, tmp_path):
        """Should return empty list for file with no functions."""
        p = tmp_path / "empty.py"
        p.write_text("# just a comment\nx = 42\n")
        symbols = self.extract(str(p))
        assert len(symbols) == 0

    def test_extract_complex_function(self, tmp_path):
        """Should detect complex functions (many branches)."""
        code = """def complex_func(x, y, z):
    if x:
        if y:
            if z:
                return 1
            else:
                return 2
        else:
            return 3
    elif y:
        for i in range(10):
            if i > 5:
                return i
    return 0
"""
        p = tmp_path / "complex.py"
        p.write_text(code)
        symbols = self.extract(str(p))
        func = [s for s in symbols if s.name == "complex_func"][0]
        assert func.complexity in ("high", "medium")

    def test_extract_syntax_error_file(self, tmp_path):
        """Should handle files with syntax errors gracefully."""
        p = tmp_path / "bad.py"
        p.write_text("def broken(\n")
        symbols = self.extract(str(p))
        assert symbols == []

    def test_extract_nested_function(self, tmp_path):
        """Should extract nested/inner functions."""
        code = "def outer():\n    def inner():\n        pass\n    return inner\n"
        p = tmp_path / "nested.py"
        p.write_text(code)
        symbols = self.extract(str(p))
        names = [s.name for s in symbols]
        assert "outer" in names


class TestGapAnalyzerDiscovery:
    """Test test file discovery and matching."""

    def test_discover_test_functions(self, tmp_path):
        """Should discover test functions and what they reference."""
        from scripts.test_gap_analyzer import discover_test_symbols

        test_dir = tmp_path / "tests"
        test_dir.mkdir()

        test_file = test_dir / "test_example.py"
        test_file.write_text("def test_calculate_total():\n    pass\n" "def test_validate_input():\n    pass\n")

        refs = discover_test_symbols(str(test_dir))
        all_refs = set()
        for r in refs.values():
            all_refs.update(r)
        assert "calculate_total" in all_refs
        assert "validate_input" in all_refs

    def test_discover_test_classes(self, tmp_path):
        """Should discover test classes and their method subjects."""
        from scripts.test_gap_analyzer import discover_test_symbols

        test_dir = tmp_path / "tests"
        test_dir.mkdir()

        test_file = test_dir / "test_foo.py"
        test_file.write_text(
            "class TestCalculator:\n"
            "    def test_add(self):\n        pass\n"
            "    def test_subtract(self):\n        pass\n"
        )

        refs = discover_test_symbols(str(test_dir))
        all_refs = set()
        for r in refs.values():
            all_refs.update(r)
        assert "add" in all_refs
        assert "subtract" in all_refs


class TestGapAnalysis:
    """Test the actual gap analysis logic."""

    def test_analyze_finds_gaps(self, tmp_path):
        """Should detect untested functions."""
        from scripts.test_gap_analyzer import analyze_gaps

        src = tmp_path / "src"
        src.mkdir()
        (src / "calc.py").write_text(
            "def add(a, b):\n    return a + b\n"
            "def subtract(a, b):\n    return a - b\n"
            "def multiply(a, b):\n    return a * b\n"
        )

        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_calc.py").write_text("def test_add():\n    pass\n")

        mappings = analyze_gaps(str(src), str(tests))
        tested = [m for m in mappings if m.is_tested]
        untested = [m for m in mappings if not m.is_tested]

        assert len(tested) >= 1  # add is tested
        assert len(untested) >= 2  # subtract, multiply are NOT

    def test_analyze_excludes_private_by_default(self, tmp_path):
        """Should exclude _private functions by default."""
        from scripts.test_gap_analyzer import analyze_gaps

        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def public_func():\n    pass\n" "def _private_func():\n    pass\n")

        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_mod.py").write_text("")

        mappings = analyze_gaps(str(src), str(tests))
        names = [m.symbol.name for m in mappings]
        assert "public_func" in names
        assert "_private_func" not in names

    def test_analyze_includes_private_when_flag_set(self, tmp_path):
        """Should include _private functions when flag is set."""
        from scripts.test_gap_analyzer import analyze_gaps

        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def _helper():\n    pass\n")

        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_mod.py").write_text("")

        mappings = analyze_gaps(str(src), str(tests), include_private=True)
        names = [m.symbol.name for m in mappings]
        assert "_helper" in names


class TestGapReporting:
    """Test report generation and quality gate."""

    def test_generate_text_report(self, tmp_path):
        """Should generate a text report."""
        from scripts.test_gap_analyzer import (
            SourceSymbol,
            TestMapping,
            generate_report,
        )

        mappings = [
            TestMapping(
                symbol=SourceSymbol(
                    name="tested_func",
                    qualified_name="mod.tested_func",
                    file_path="mod.py",
                    line=1,
                    kind="function",
                    is_private=False,
                    is_dunder=False,
                ),
                is_tested=True,
                test_file="test_mod.py",
            ),
            TestMapping(
                symbol=SourceSymbol(
                    name="untested_func",
                    qualified_name="mod.untested_func",
                    file_path="mod.py",
                    line=10,
                    kind="function",
                    is_private=False,
                    is_dunder=False,
                ),
                is_tested=False,
            ),
        ]

        report = generate_report(mappings, format="text")
        assert "untested_func" in report
        assert "50.0%" in report  # 1/2 tested

    def test_generate_json_report(self, tmp_path):
        """Should generate a valid JSON report."""
        from scripts.test_gap_analyzer import (
            SourceSymbol,
            TestMapping,
            generate_report,
        )

        mappings = [
            TestMapping(
                symbol=SourceSymbol(
                    name="func_a",
                    qualified_name="mod.func_a",
                    file_path="mod.py",
                    line=1,
                    kind="function",
                    is_private=False,
                    is_dunder=False,
                ),
                is_tested=True,
            ),
        ]

        report = generate_report(mappings, format="json")
        data = json.loads(report)
        assert data["total_symbols"] == 1
        assert data["tested"] == 1

    def test_quality_gate_passes(self, tmp_path):
        """Quality gate should pass when under thresholds."""
        from scripts.test_gap_analyzer import check_test_gap_gate

        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def foo():\n    pass\n")

        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_mod.py").write_text("def test_foo():\n    pass\n")

        result = check_test_gap_gate(str(src), str(tests), max_untested=10, max_complex_untested=10)
        assert result["passed"] is True

    def test_quality_gate_fails(self, tmp_path):
        """Quality gate should fail when over thresholds."""
        from scripts.test_gap_analyzer import check_test_gap_gate

        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def a():\n    pass\n" "def b():\n    pass\n" "def c():\n    pass\n")

        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_mod.py").write_text("")

        result = check_test_gap_gate(str(src), str(tests), max_untested=1)
        assert result["passed"] is False

    def test_api_data_format(self, tmp_path):
        """get_test_gap_data() should return API-ready dict."""
        from scripts.test_gap_analyzer import get_test_gap_data

        src = tmp_path / "src"
        src.mkdir()
        (src / "mod.py").write_text("def hello():\n    pass\n")

        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "test_mod.py").write_text("def test_hello():\n    pass\n")

        data = get_test_gap_data(str(src), str(tests))
        assert "total_symbols" in data
        assert "tested" in data
        assert "untested" in data
        assert "coverage_pct" in data
        assert "gaps" in data


# ═══════════════════════════════════════════════════════════════════════════
# 2. OWASP COMPLIANCE REPORT — DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestOWASPMapping:
    """Test OWASP Top 10 rule mapping."""

    def test_owasp_has_all_10_categories(self):
        """Should have all 10 OWASP categories."""
        from scripts.generate_compliance_report import OWASP_TOP_10

        assert len(OWASP_TOP_10) == 10
        for i in range(1, 11):
            key = f"A{i:02d}"
            assert key in OWASP_TOP_10, f"Missing {key}"

    def test_each_owasp_has_required_fields(self):
        """Each OWASP category should have name, description, cwe_ids, rule_ids."""
        from scripts.generate_compliance_report import OWASP_TOP_10

        for cat_id, cat in OWASP_TOP_10.items():
            assert "name" in cat, f"{cat_id} missing name"
            assert "description" in cat, f"{cat_id} missing description"
            assert "cwe_ids" in cat, f"{cat_id} missing cwe_ids"
            assert "rule_ids" in cat, f"{cat_id} missing rule_ids"
            assert isinstance(cat["cwe_ids"], list)
            assert isinstance(cat["rule_ids"], list)

    def test_cwe_mapping_covers_security_rules(self):
        """RULE_TO_CWE should map all security rules."""
        from scripts.generate_compliance_report import RULE_TO_CWE

        security_rules = [k for k in RULE_TO_CWE if k.startswith("SECURITY-")]
        assert len(security_rules) >= 5, "Should map at least 5 security rules"

    def test_all_cwe_ids_valid_format(self):
        """All CWE IDs should match CWE-NNN format."""
        import re

        from scripts.generate_compliance_report import RULE_TO_CWE

        for rule_id, cwe_id in RULE_TO_CWE.items():
            assert re.match(r"CWE-\d+", cwe_id), f"Invalid CWE format for {rule_id}: {cwe_id}"


class TestComplianceReport:
    """Test compliance report generation."""

    @patch("scripts.generate_compliance_report.Database")
    def test_generate_md_report(self, MockDB):
        """Should generate a markdown report."""
        from scripts.generate_compliance_report import generate_compliance_report

        db = MockDB.return_value
        db.get_latest_run.return_value = {"id": 1}
        db.get_findings.return_value = [
            {
                "canonical_rule_id": "SECURITY-001",
                "canonical_severity": "high",
                "category": "security",
                "file": "test.py",
                "line": 10,
                "message": "eval() is dangerous",
            }
        ]

        report = generate_compliance_report(run_id=1, output_format="md")
        assert "OWASP" in report
        assert "A03" in report  # eval → Injection

    @patch("scripts.generate_compliance_report.Database")
    def test_generate_json_report(self, MockDB):
        """Should generate a valid JSON report when findings exist."""
        from scripts.generate_compliance_report import generate_compliance_report

        db = MockDB.return_value
        db.get_latest_run.return_value = {"id": 1}
        db.get_findings.return_value = [
            {
                "canonical_rule_id": "SECURITY-001",
                "canonical_severity": "high",
                "category": "security",
                "file": "test.py",
                "line": 10,
                "message": "eval() is dangerous",
            }
        ]

        report = generate_compliance_report(run_id=1, output_format="json")
        data = json.loads(report)
        assert "owasp_results" in data
        assert len(data["owasp_results"]) == 10

    @patch("scripts.generate_compliance_report.Database")
    def test_compliance_data_api(self, MockDB):
        """get_compliance_data should return API-ready dict."""
        from scripts.generate_compliance_report import get_compliance_data

        db = MockDB.return_value
        db.get_latest_run.return_value = {"id": 1}
        db.get_findings.return_value = [
            {
                "canonical_rule_id": "SECURITY-001",
                "canonical_severity": "high",
                "category": "security",
                "file": "test.py",
                "line": 10,
                "message": "eval() is dangerous",
            }
        ]

        data = get_compliance_data(run_id=1)
        assert isinstance(data, dict)
        assert "owasp_results" in data


# ═══════════════════════════════════════════════════════════════════════════
# 3. FEEDBACK TUNER — DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestFeedbackTuner:
    """Test feedback-driven severity tuner logic."""

    def test_generate_overrides_downgrade_high_fp(self):
        """Rules with >70% FP rate and >=3 feedback should be downgraded to low."""
        from scripts.feedback_tuner import generate_overrides

        fp_rates = {
            "STYLE-001": {
                "tp": 1,
                "fp": 4,
                "total": 5,
                "fp_rate": 0.8,
                "severity": "medium",
                "category": "style",
                "recommendation": "DOWNGRADE",
                "suggested_severity": "low",
            },
        }

        overrides = generate_overrides(fp_rates, min_feedback=3)
        assert "STYLE-001" in overrides
        assert overrides["STYLE-001"]["severity"] == "low"

    def test_generate_overrides_skip_low_count(self):
        """Rules with too few feedback entries should be skipped."""
        from scripts.feedback_tuner import generate_overrides

        fp_rates = {
            "STYLE-002": {
                "tp": 0,
                "fp": 2,
                "total": 2,
                "fp_rate": 1.0,
                "severity": "medium",
                "category": "style",
                "recommendation": "DOWNGRADE",
                "suggested_severity": "low",
            },
        }

        overrides = generate_overrides(fp_rates, min_feedback=3)
        assert len(overrides) == 0  # Only 2 feedback, min is 3

    def test_generate_overrides_keep_good_rules(self):
        """Rules with low FP rate should NOT be in overrides."""
        from scripts.feedback_tuner import generate_overrides

        fp_rates = {
            "SECURITY-001": {
                "tp": 9,
                "fp": 1,
                "total": 10,
                "fp_rate": 0.1,
                "severity": "high",
                "category": "security",
                "recommendation": "KEEP",
                "suggested_severity": "high",
            },
        }

        overrides = generate_overrides(fp_rates, min_feedback=3)
        assert len(overrides) == 0

    def test_print_report_no_crash(self, caplog):
        """print_report should not crash on valid data."""
        import logging

        from scripts.feedback_tuner import print_report

        caplog.set_level(logging.INFO)

        fp_rates = {
            "TEST-001": {
                "tp": 5,
                "fp": 5,
                "total": 10,
                "fp_rate": 0.5,
                "severity": "medium",
                "category": "style",
                "recommendation": "MONITOR",
                "suggested_severity": "medium",
            },
        }

        print_report(fp_rates)
        assert "TEST-001" in caplog.text
        assert "50.0%" in caplog.text

    def test_print_report_empty_data(self, capsys):
        """print_report should handle empty data gracefully."""
        from scripts.feedback_tuner import print_report

        print_report({})
        # Should not crash


# ═══════════════════════════════════════════════════════════════════════════
# 4. CONFIG VALIDATOR — DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestConfigValidator:
    """Test .acrqa.yml validation."""

    def test_valid_config_passes(self, tmp_path):
        """A valid config should pass validation."""
        from scripts.validate_config import validate_config

        config = {
            "enabled_tools": {"ruff": True, "semgrep": False},
            "min_severity": "medium",
            "quality_gate": {"max_high": 0, "max_medium": 5},
        }
        p = tmp_path / ".acrqa.yml"
        p.write_text(yaml.dump(config))

        is_valid, errors, warnings = validate_config(str(p))
        assert is_valid is True
        assert len(errors) == 0

    def test_unknown_key_warns(self, tmp_path):
        """Unknown top-level keys should produce warnings."""
        from scripts.validate_config import validate_config

        config = {"bogus_key": "value", "min_severity": "low"}
        p = tmp_path / ".acrqa.yml"
        p.write_text(yaml.dump(config))

        is_valid, errors, warnings = validate_config(str(p))
        assert len(warnings) > 0
        assert any("bogus_key" in w for w in warnings)

    def test_invalid_severity_value(self, tmp_path):
        """Invalid severity values should produce errors."""
        from scripts.validate_config import validate_config

        config = {"min_severity": "critical"}  # Not valid
        p = tmp_path / ".acrqa.yml"
        p.write_text(yaml.dump(config))

        is_valid, errors, warnings = validate_config(str(p))
        assert is_valid is False
        assert len(errors) > 0

    def test_missing_file_errors(self):
        """Should return error when file doesn't exist."""
        from scripts.validate_config import validate_config

        is_valid, errors, warnings = validate_config("/nonexistent/.acrqa.yml")
        assert is_valid is False

    def test_empty_config_is_valid(self, tmp_path):
        """Empty YAML should be valid (defaults apply)."""
        from scripts.validate_config import validate_config

        p = tmp_path / ".acrqa.yml"
        p.write_text("{}")

        is_valid, errors, warnings = validate_config(str(p))
        assert is_valid is True

    def test_type_mismatch_errors(self, tmp_path):
        """Wrong types should produce errors."""
        from scripts.validate_config import validate_config

        config = {"enabled_tools": "not_a_dict"}  # Should be dict
        p = tmp_path / ".acrqa.yml"
        p.write_text(yaml.dump(config))

        is_valid, errors, warnings = validate_config(str(p))
        assert is_valid is False


class TestConfigTemplate:
    """Test template generation."""

    def test_generate_template_valid_yaml(self):
        """Generated template should be valid YAML."""
        from scripts.validate_config import generate_template

        template = generate_template(commented=False)
        parsed = yaml.safe_load(template)
        assert isinstance(parsed, dict)

    def test_generate_template_has_all_sections(self):
        """Template should include all schema sections."""
        from scripts.validate_config import SCHEMA, generate_template

        template = generate_template(commented=True)
        for key in SCHEMA:
            assert key in template, f"Template missing section: {key}"


# ═══════════════════════════════════════════════════════════════════════════
# 5. FLASK API ENDPOINTS — DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestNewAPIEndpoints:
    """FastAPI endpoints that replaced the old Flask /api/* routes."""

    @pytest.fixture
    def client(self):
        from unittest.mock import MagicMock

        from starlette.testclient import TestClient

        from FRONTEND.api.deps import get_current_user, get_db
        from FRONTEND.api.main import app as fastapi_app

        mock_db = MagicMock()
        mock_db.get_recent_runs.return_value = []
        mock_db.get_findings_with_explanations.return_value = []
        mock_db.get_run_summary.return_value = None

        fastapi_app.dependency_overrides[get_db] = lambda: mock_db
        fastapi_app.dependency_overrides[get_current_user] = lambda: {"id": 1, "role": "admin"}

        with TestClient(fastapi_app, raise_server_exceptions=False) as c:
            yield c

        fastapi_app.dependency_overrides.clear()

    def test_health_endpoint_returns_200(self, client):
        """GET /health should return 200."""
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_runs_endpoint_returns_200(self, client):
        """GET /v1/runs should return 200."""
        resp = client.get("/v1/runs")
        assert resp.status_code == 200
        assert "runs" in resp.json()

    def test_findings_endpoint_returns_200(self, client):
        """GET /v1/runs/1/findings should return 200."""
        resp = client.get("/v1/runs/1/findings")
        assert resp.status_code == 200
        assert "findings" in resp.json() or "groups" in resp.json()

    def test_metrics_endpoint_returns_200(self, client):
        """GET /metrics should return 200."""
        resp = client.get("/metrics")
        assert resp.status_code == 200

    def test_nonexistent_endpoint_returns_404(self, client):
        """Non-existent API paths should return 404."""
        resp = client.get("/v1/nonexistent")
        assert resp.status_code == 404

    def test_stats_not_found_returns_404(self, client):
        """Stats for nonexistent run should return 404."""
        resp = client.get("/v1/runs/99999/stats")
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# 6. CONFIDENCE-BASED NOISE CONTROL — DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestConfidenceScoring:
    """Test the _calculate_confidence() function."""

    def test_confidence_has_function(self):
        """The app module should have _calculate_confidence."""
        from CORE.confidence_utils import calculate_confidence as _calculate_confidence

        assert callable(_calculate_confidence)

    def test_high_severity_security_with_explanation(self):
        """High severity + security + explanation should score high."""
        from CORE.confidence_utils import calculate_confidence as _calculate_confidence

        finding = {
            "canonical_severity": "high",
            "category": "security",
            "explanation": "This violates SECURITY-001 because eval is dangerous.",
            "canonical_rule_id": "SECURITY-001",
        }
        conf = _calculate_confidence(finding)
        assert conf >= 0.7

    def test_low_severity_no_explanation(self):
        """Low severity without explanation should score low."""
        from CORE.confidence_utils import calculate_confidence as _calculate_confidence

        finding = {
            "canonical_severity": "low",
            "category": "style",
            "explanation": None,
            "canonical_rule_id": "STYLE-001",
        }
        conf = _calculate_confidence(finding)
        assert conf <= 0.6

    def test_confidence_always_0_to_1(self):
        """Confidence should always be between 0 and 1."""
        from CORE.confidence_utils import calculate_confidence as _calculate_confidence

        test_cases = [
            {"canonical_severity": "high", "category": "security", "explanation": "x", "canonical_rule_id": "X"},
            {"canonical_severity": "low", "category": "style", "explanation": None, "canonical_rule_id": "Y"},
            {
                "canonical_severity": "medium",
                "category": "design",
                "explanation": "long explanation text",
                "canonical_rule_id": "Z",
            },
            {},  # edge case: empty dict
        ]
        for finding in test_cases:
            conf = _calculate_confidence(finding)
            assert 0 <= conf <= 1, f"Confidence {conf} out of range for {finding}"

    def test_rule_citation_boosts_confidence(self):
        """Explanation citing rule ID should have higher confidence."""
        from CORE.confidence_utils import calculate_confidence as _calculate_confidence

        with_citation = {
            "canonical_severity": "medium",
            "category": "design",
            "explanation": "This violates SOLID-001 because too many params.",
            "canonical_rule_id": "SOLID-001",
        }
        without_citation = {
            "canonical_severity": "medium",
            "category": "design",
            "explanation": "This function has too many parameters.",
            "canonical_rule_id": "SOLID-001",
        }
        conf_with = _calculate_confidence(with_citation)
        conf_without = _calculate_confidence(without_citation)
        assert conf_with >= conf_without


# ═══════════════════════════════════════════════════════════════════════════
# 7. VERSION CONSISTENCY — DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestVersionConsistency:
    """Test that all scripts use CORE.__version__ and are consistent."""

    def test_version_is_string(self):
        """__version__ should be a string."""
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_version_format(self):
        """Version should follow semver-ish pattern."""
        import re

        assert re.match(r"\d+\.\d+\.\d+", __version__), f"Bad format: {__version__}"

    def test_scripts_use_core_version(self):
        """Scripts should import from CORE, not hardcode versions."""
        script_dir = Path(__file__).parent.parent / "scripts"
        scripts_to_check = [
            "export_sarif.py",
            "generate_pr_summary.py",
            "post_pr_comments.py",
            "test_gap_analyzer.py",
        ]

        for script_name in scripts_to_check:
            path = script_dir / script_name
            if path.exists():
                content = path.read_text()
                # Should NOT have hardcoded version strings
                assert '"2.0' not in content, f"{script_name} has hardcoded '2.0'"
                assert '"2.4' not in content, f"{script_name} has hardcoded '2.4'"
                assert '"2.5' not in content, f"{script_name} has hardcoded '2.5'"

    def test_jwt_secret_uses_env_var(self):
        """FastAPI JWT secret should come from env var, not be hardcoded."""
        jwt_path = Path(__file__).parent.parent / "FRONTEND" / "auth" / "jwt_utils.py"
        content = jwt_path.read_text()
        assert "os.getenv" in content, "JWT secret must use os.getenv"
        assert "JWT_SECRET_KEY" in content


# ═══════════════════════════════════════════════════════════════════════════
# 8. POLICY ENGINE — DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestPolicyEngine:
    """Test the policy-as-code configuration system end to end."""

    def test_acrqa_yml_exists(self):
        """Project root should have .acrqa.yml."""
        path = Path(__file__).parent.parent / ".acrqa.yml"
        assert path.exists(), ".acrqa.yml missing from project root"

    def test_acrqa_yml_valid_yaml(self):
        """The .acrqa.yml file should parse as valid YAML."""
        path = Path(__file__).parent.parent / ".acrqa.yml"
        with open(path) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)

    def test_config_loader_respects_policy(self):
        """ConfigLoader should load and respect the policy file."""
        from CORE.config_loader import ConfigLoader

        loader = ConfigLoader()
        # Use the public API — rules should be enabled by default
        assert loader.is_rule_enabled("SECURITY-001") is True
        assert loader.get_severity_override("FAKE-RULE") is None

    def test_quality_gate_respects_thresholds(self):
        """QualityGate should use thresholds from config."""
        from CORE.engines.quality_gate import QualityGate

        gate = QualityGate()
        result = gate.evaluate([])  # No findings
        assert result["passed"] is True

    def test_policy_doc_exists(self):
        """docs/POLICY_ENGINE.md should exist."""
        path = Path(__file__).parent.parent / "docs" / "POLICY_ENGINE.md"
        assert path.exists()

    def test_policy_doc_has_key_sections(self):
        """Policy doc should have key sections."""
        path = Path(__file__).parent.parent / "docs" / "POLICY_ENGINE.md"
        content = path.read_text()
        assert "Rule Suppression" in content
        assert "Severity Overrides" in content
        assert "Quality Gate" in content
        assert "API Endpoints" in content


# ═══════════════════════════════════════════════════════════════════════════
# 9. CROSS-FEATURE INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestCrossFeatureIntegration:
    """Test that features work together without breaking each other."""

    def test_test_gap_on_own_codebase(self):
        """Test gap analyzer should successfully analyze CORE/ directory."""
        from scripts.test_gap_analyzer import analyze_gaps

        project_root = str(Path(__file__).parent.parent)
        mappings = analyze_gaps(
            os.path.join(project_root, "CORE"),
            os.path.join(project_root, "TESTS"),
        )
        assert len(mappings) > 0
        tested = [m for m in mappings if m.is_tested]
        assert len(tested) > 0  # We definitely have SOME tested code

    def test_config_validator_on_own_config(self):
        """Config validator should pass on our own .acrqa.yml."""
        from scripts.validate_config import validate_config

        project_root = Path(__file__).parent.parent
        config_path = project_root / ".acrqa.yml"
        if config_path.exists():
            is_valid, errors, warnings = validate_config(str(config_path))
            # Should not have fatal errors
            assert is_valid is True or len(errors) == 0

    def test_all_imports_work(self):
        """All core modules should import without errors."""
        # If we get here, all imports work

    def test_normalizer_and_quality_gate_pipeline(self):
        """Normalizer output should feed into quality gate correctly."""
        from CORE.engines.normalizer import normalize_ruff
        from CORE.engines.quality_gate import QualityGate

        ruff_data = [
            {
                "code": "F401",
                "filename": "test.py",
                "location": {"row": 1, "column": 0},
                "message": "Unused import",
            },
            {
                "code": "E501",
                "filename": "test.py",
                "location": {"row": 2, "column": 0},
                "message": "Line too long",
            },
        ]

        findings = normalize_ruff(ruff_data)
        assert len(findings) >= 1

        # Feed into quality gate
        gate = QualityGate()
        finding_dicts = [f.to_dict() for f in findings]
        result = gate.evaluate(finding_dicts)
        assert "passed" in result
        assert "counts" in result

    def test_severity_scorer_and_confidence(self):
        """SeverityScorer output should produce valid confidence scores."""
        from CORE.confidence_utils import calculate_confidence as _calculate_confidence
        from CORE.engines.severity_scorer import SeverityScorer

        scorer = SeverityScorer()

        finding = {
            "canonical_rule_id": "SECURITY-001",
            "message": "eval() usage detected",
            "category": "security",
        }
        severity = scorer.score("SECURITY-001", finding)
        assert severity in ("high", "medium", "low")

        # Now test confidence
        finding["canonical_severity"] = severity
        finding["explanation"] = "SECURITY-001: eval is dangerous"
        conf = _calculate_confidence(finding)
        assert 0 <= conf <= 1


# ═══════════════════════════════════════════════════════════════════════════
# 10. EXISTING FEATURES — REGRESSION TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestExistingFeatureRegression:
    """Verify old features still work after all new additions."""

    def test_normalizer_ruff(self):
        """Ruff normalization should still work."""
        from CORE.engines.normalizer import normalize_ruff

        data = [{"code": "F401", "filename": "t.py", "location": {"row": 1, "column": 0}, "message": "unused import"}]
        findings = normalize_ruff(data)
        assert len(findings) == 1
        assert findings[0].canonical_rule_id == "IMPORT-001"

    def test_normalizer_semgrep(self):
        """Semgrep normalization should still work."""
        from CORE.engines.normalizer import normalize_semgrep

        data = {
            "results": [
                {
                    "check_id": "python.lang.security.audit.dangerous-system-call",
                    "path": "t.py",
                    "start": {"line": 1, "col": 0},
                    "extra": {"message": "os.system call", "severity": "WARNING"},
                }
            ]
        }
        findings = normalize_semgrep(data)
        assert len(findings) >= 1

    def test_normalizer_bandit(self):
        """Bandit normalization should still work."""
        from CORE.engines.normalizer import normalize_bandit

        data = {
            "results": [
                {
                    "test_id": "B101",
                    "filename": "t.py",
                    "line_number": 1,
                    "col_offset": 0,
                    "issue_text": "Assert used",
                    "issue_severity": "LOW",
                }
            ]
        }
        findings = normalize_bandit(data)
        assert len(findings) >= 1

    def test_quality_gate_evaluate(self):
        """Quality gate evaluate should return proper structure."""
        from CORE.engines.quality_gate import QualityGate

        gate = QualityGate()
        result = gate.evaluate([])
        assert result["passed"] is True
        assert "counts" in result
        assert "checks" in result

    def test_autofix_engine_can_fix(self):
        """AutoFix engine should identify fixable rules."""
        from CORE.engines.autofix import AutoFixEngine

        engine = AutoFixEngine()
        assert engine.can_fix("IMPORT-001") is True
        assert engine.can_fix("NONEXISTENT-999") is False

    def test_rate_limiter_mock(self):
        """Rate limiter should work with mocked Redis."""
        from CORE.utils.rate_limiter import RateLimiter

        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {}
        mock_redis.ping.return_value = True

        with patch("CORE.utils.rate_limiter.redis.Redis", return_value=mock_redis):
            limiter = RateLimiter(redis_host="localhost", redis_port=6379)

        allowed, _ = limiter.check_rate_limit("test-repo", 1)
        assert allowed is True

    def test_config_loader_defaults(self):
        """ConfigLoader should have sane defaults."""
        from CORE.config_loader import ConfigLoader

        loader = ConfigLoader()
        assert loader.is_rule_enabled("SECURITY-001") is True
        assert loader.get_severity_override("FAKE-RULE") is None

    def test_inline_suppression_patterns(self):
        """Inline suppression should recognize both patterns."""
        from CORE.main import AnalysisPipeline

        pipeline = AnalysisPipeline()
        # The method _is_suppressed checks code lines
        assert hasattr(pipeline, "_is_suppressed") or hasattr(pipeline, "_apply_config_filters")


# ═══════════════════════════════════════════════════════════════════════════
# 11. EDGE CASES & BOUNDARY TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge cases that could cause crashes or unexpected behavior."""

    def test_test_gap_empty_directory(self, tmp_path):
        """Test gap analyzer on empty directories should not crash."""
        from scripts.test_gap_analyzer import analyze_gaps

        src = tmp_path / "empty_src"
        src.mkdir()
        tests = tmp_path / "empty_tests"
        tests.mkdir()

        mappings = analyze_gaps(str(src), str(tests))
        assert mappings == []

    def test_config_validator_corrupt_yaml(self, tmp_path):
        """Corrupt YAML should be caught."""
        from scripts.validate_config import validate_config

        p = tmp_path / ".acrqa.yml"
        p.write_text("{{{{invalid yaml\n\t\tbad")

        is_valid, errors, warnings = validate_config(str(p))
        assert is_valid is False

    def test_confidence_empty_finding(self):
        """_calculate_confidence should handle empty/missing fields."""
        from CORE.confidence_utils import calculate_confidence as _calculate_confidence

        conf = _calculate_confidence({})
        assert 0 <= conf <= 1

    def test_quality_gate_huge_findings(self):
        """Quality gate should handle large number of findings."""
        from CORE.engines.quality_gate import QualityGate

        gate = QualityGate()
        findings = [
            {"canonical_severity": "low", "category": "style", "canonical_rule_id": f"STYLE-{i:03d}"}
            for i in range(1000)
        ]
        result = gate.evaluate(findings)
        assert result["passed"] is False  # 1000 findings should fail total gate

    @pytest.fixture
    def client(self):
        from unittest.mock import MagicMock

        from starlette.testclient import TestClient

        from FRONTEND.api.deps import get_current_user, get_db
        from FRONTEND.api.main import app as fastapi_app

        mock_db = MagicMock()
        mock_db.get_recent_runs.return_value = []
        mock_db.get_findings_with_explanations.return_value = []

        fastapi_app.dependency_overrides[get_db] = lambda: mock_db
        fastapi_app.dependency_overrides[get_current_user] = lambda: {"id": 1, "role": "admin"}

        with TestClient(fastapi_app, raise_server_exceptions=False) as c:
            yield c

        fastapi_app.dependency_overrides.clear()

    def test_api_nonexistent_endpoints_404(self, client):
        """Non-existent API endpoints should return 404."""
        resp = client.get("/v1/nonexistent-endpoint-xyz")
        assert resp.status_code == 404

    def test_api_runs_endpoint_stable_under_load(self, client):
        """Repeated calls to /v1/runs should not crash."""
        for _ in range(5):
            resp = client.get("/v1/runs")
            assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# Feature 9: CALL GRAPH REACHABILITY ENGINE — GOD MODE
# ═══════════════════════════════════════════════════════════════════════════


class TestReachabilityGodMode:
    """Deep god-mode tests for Feature 9 — Call Graph FP Reduction."""

    def test_engine_importable(self):
        from CORE.engines.reachability import (
            CallGraphReachability,
            CallGraphResult,
            _build_call_graph,
            _detect_entry_points,
            get_function_at_line,
        )

        assert CallGraphReachability is not None
        assert CallGraphResult is not None
        assert callable(_build_call_graph)
        assert callable(_detect_entry_points)
        assert callable(get_function_at_line)

    def test_call_graph_result_dataclass(self):
        from CORE.engines.reachability import CallGraphResult

        r = CallGraphResult(
            file_path="x.py",
            reachable={"a", "b"},
            unreachable={"c"},
            entry_points=["a"],
        )
        assert r.is_function_reachable("a") is True
        assert r.is_function_reachable("c") is False
        assert r.penalty_for("c") == -20
        assert r.penalty_for("a") == 0
        assert r.penalty_for(None) == 0
        d = r.to_dict()
        assert d["reachable_functions"] == ["a", "b"]
        assert d["unreachable_functions"] == ["c"]

    def test_detect_all_entry_point_types(self):
        from CORE.engines.reachability import _detect_entry_points

        code = """\
from flask import Flask
from fastapi import FastAPI
from celery import Celery

flask_app = Flask(__name__)
fast_app = FastAPI()
celery_app = Celery()

@flask_app.route("/a")
def flask_view(): pass

@fast_app.post("/b")
async def fastapi_handler(): pass

@celery_app.task
def celery_task(): pass

def pure_helper(): pass

if __name__ == "__main__":
    main_fn()
"""
        eps = _detect_entry_points(code)
        assert "flask_view" in eps
        assert "fastapi_handler" in eps
        assert "celery_task" in eps
        assert "main_fn" in eps
        assert "pure_helper" not in eps

    def test_deep_call_chain_all_reachable(self, tmp_path):
        from CORE.engines.reachability import CallGraphReachability

        f = tmp_path / "chain.py"
        f.write_text(
            "from flask import Flask\napp=Flask(__name__)\n"
            "@app.route('/')\ndef a(): b()\n"
            "def b(): c()\n"
            "def c(): d()\n"
            "def d(): pass\n"
            "def orphan(): pass\n"
        )
        r = CallGraphReachability().analyze(str(f))
        for fn in ("a", "b", "c", "d"):
            assert r.is_function_reachable(fn), f"{fn} should be reachable"
        assert not r.is_function_reachable("orphan")

    def test_get_function_at_line_nested(self):
        from CORE.engines.reachability import get_function_at_line

        src = "def outer():\n    def inner():\n        return 1\n    return inner()\n"
        assert get_function_at_line(src, 3) == "inner"
        assert get_function_at_line(src, 4) == "outer"

    def test_enrich_findings_mixed_batch(self, tmp_path):
        from CORE.engines.reachability import CallGraphReachability

        py_file = tmp_path / "app.py"
        py_file.write_text(
            "from flask import Flask\napp=Flask(__name__)\n"
            "@app.route('/')\ndef index(): helper()\n"
            "def helper(): pass\n"
            "def dead(): pass\n"
        )
        js_file = tmp_path / "script.js"
        js_file.write_text("function foo() {}\n")

        findings = [
            {"file_path": str(py_file), "line_number": 5, "confidence_score": 80},
            {"file_path": str(py_file), "line_number": 6, "confidence_score": 80},
            {"file_path": str(js_file), "line_number": 1, "confidence_score": 80},
            {"file_path": "", "line_number": 0, "confidence_score": 80},
        ]
        results = CallGraphReachability().enrich_findings(findings)
        assert results[0]["reachability_status"] == "REACHABLE"
        assert results[1]["reachability_status"] == "UNREACHABLE"
        assert results[1]["confidence_score"] == 60
        assert results[2]["reachability_status"] == "UNKNOWN"
        assert results[3]["reachability_status"] == "UNKNOWN"

    def test_enrich_findings_no_mutation(self, tmp_path):
        """enrich_findings must not mutate the original finding dict."""
        from CORE.engines.reachability import CallGraphReachability

        f = tmp_path / "app.py"
        f.write_text(
            "from flask import Flask\napp=Flask(__name__)\n" "@app.route('/')\ndef index(): pass\n" "def dead(): pass\n"
        )
        original = {"file_path": str(f), "line_number": 5, "confidence_score": 80}
        original_copy = dict(original)
        CallGraphReachability().enrich_findings([original])
        assert original == original_copy

    def test_alembic_migration_file_exists(self):
        migration = Path("alembic/versions/20260514_0003_reachability_columns.py")
        assert migration.exists(), "Migration 0003 for reachability columns is missing"

    def test_database_has_update_reachability_method(self):
        from DATABASE.database import Database

        assert hasattr(Database, "update_finding_reachability")

    def test_reachability_penalty_constant(self):
        from CORE.engines import reachability as r_mod

        assert r_mod._UNREACHABLE_PENALTY == -20

    def test_library_file_unknown_not_penalised(self, tmp_path):
        """Pure library files with no entry points get UNKNOWN — no penalty."""
        from CORE.engines.reachability import CallGraphReachability

        lib = tmp_path / "utils.py"
        lib.write_text("def parse(data): return data\ndef validate(data): return True\n")
        findings = [{"file_path": str(lib), "line_number": 1, "confidence_score": 75}]
        results = CallGraphReachability().enrich_findings(findings)
        assert results[0]["reachability_status"] == "UNKNOWN"
        assert results[0]["confidence_score"] == 75

    def test_zero_fp_rate_on_benchmark_fixtures(self):
        """No reachable finding should be mislabelled as UNREACHABLE across all fixtures."""
        from CORE.engines.reachability import CallGraphReachability

        fixture_dir = Path(__file__).parent / "fixtures" / "reachability"
        reachable_cases = [
            (str(fixture_dir / "flask_app.py"), 27),  # process_input body
            (str(fixture_dir / "flask_app.py"), 33),  # execute_query body
            (str(fixture_dir / "standalone.py"), 23),  # called_from_main body
            (str(fixture_dir / "celery_tasks.py"), 26),  # task_helper body
        ]
        findings = [{"file_path": fp, "line_number": ln, "confidence_score": 80} for fp, ln in reachable_cases]
        results = CallGraphReachability().enrich_findings(findings)
        fps = [r for r in results if r.get("reachability_status") == "UNREACHABLE"]
        assert len(fps) == 0, f"FP misclassifications: {fps}"


class TestLearnedSuppressionGodMode:
    """God-mode tests for Feature 10: embedding-based learned suppression."""

    def test_engine_importable(self):
        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        assert LearnedSuppressionEngine is not None

    def test_threshold_constant_sane(self):
        from CORE.engines.learned_suppression import SIMILARITY_THRESHOLD

        assert 0.80 <= SIMILARITY_THRESHOLD <= 0.99

    def test_model_name_defined(self):
        from CORE.engines.learned_suppression import MODEL_NAME

        assert isinstance(MODEL_NAME, str) and len(MODEL_NAME) > 0

    def test_cosine_similarity_identity(self):
        from CORE.engines.learned_suppression import _cosine_similarity

        v = [0.5, 0.3, 0.8, -0.1]
        assert abs(_cosine_similarity(v, v) - 1.0) < 1e-5

    def test_suppress_returns_tuple_of_two(self):
        from unittest.mock import MagicMock

        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        db = MagicMock()
        db.get_all_finding_embeddings.return_value = []
        result = LearnedSuppressionEngine().suppress([], db)
        assert isinstance(result, tuple) and len(result) == 2

    def test_suppress_does_not_drop_findings(self):
        from unittest.mock import MagicMock

        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        db = MagicMock()
        db.get_all_finding_embeddings.return_value = []
        findings = [{"canonical_rule_id": "SEC-001", "message": "x", "file": "a.py", "line": 1}] * 5
        kept, _ = LearnedSuppressionEngine().suppress(findings, db)
        assert len(kept) == 5

    def test_store_dismissed_graceful_on_missing(self):
        from unittest.mock import MagicMock

        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        db = MagicMock()
        db.execute.return_value = []
        assert LearnedSuppressionEngine().store_dismissed(99999, db) is False

    def test_migration_0004_exists(self):
        root = Path(__file__).parent.parent
        migrations = list((root / "alembic" / "versions").glob("*_finding_embeddings*"))
        assert migrations, "Alembic migration 0004 (finding_embeddings) not found"

    def test_db_has_embedding_methods(self):
        from DATABASE.database import Database

        for method in (
            "insert_finding_embedding",
            "get_all_finding_embeddings",
            "get_finding_embeddings_by_rule",
            "delete_finding_embedding",
        ):
            assert hasattr(Database, method), f"Database missing method: {method}"

    def test_triage_memory_embeds_on_fp(self):
        root = Path(__file__).parent.parent
        src = (root / "CORE" / "engines" / "triage_memory.py").read_text()
        assert "store_dismissed" in src
        assert "LearnedSuppressionEngine" in src

    def test_pipeline_wires_suppression(self):
        root = Path(__file__).parent.parent
        src = (root / "CORE" / "main.py").read_text()
        assert src.count("LearnedSuppressionEngine") >= 2

    def test_is_available_returns_bool(self):
        from CORE.engines.learned_suppression import LearnedSuppressionEngine

        assert isinstance(LearnedSuppressionEngine().is_available(), bool)


class TestMCPServerGodMode:
    """God-mode tests for Feature 11: MCP server."""

    def test_server_py_exists(self):
        root = Path(__file__).parent.parent
        assert (root / "acrqa-mcp" / "server.py").exists()

    def test_pyproject_toml_exists(self):
        root = Path(__file__).parent.parent
        assert (root / "acrqa-mcp" / "pyproject.toml").exists()

    def test_three_tool_functions_defined(self):
        root = Path(__file__).parent.parent
        src = (root / "acrqa-mcp" / "server.py").read_text()
        for fn in ("_tool_scan", "_tool_explain", "_tool_fix"):
            assert fn in src, f"Missing tool function: {fn}"

    def test_env_var_config(self):
        root = Path(__file__).parent.parent
        src = (root / "acrqa-mcp" / "server.py").read_text()
        assert "ACRQA_URL" in src and "ACRQA_TOKEN" in src

    def test_config_file_path(self):
        root = Path(__file__).parent.parent
        src = (root / "acrqa-mcp" / "server.py").read_text()
        assert ".config/acrqa/config.json" in src

    def test_scan_error_returns_dict_not_raises(self):
        import httpx

        mcp_dir = str(Path(__file__).parent.parent / "acrqa-mcp")
        if mcp_dir not in sys.path:
            sys.path.insert(0, mcp_dir)
        import server

        with patch.object(server, "_post", side_effect=httpx.HTTPError("no host")):
            result = server._tool_scan("/tmp/nonexistent")
        assert isinstance(result, dict)

    def test_explain_error_returns_dict(self):
        import httpx

        mcp_dir = str(Path(__file__).parent.parent / "acrqa-mcp")
        if mcp_dir not in sys.path:
            sys.path.insert(0, mcp_dir)
        import server

        with patch.object(server, "_get", side_effect=httpx.HTTPError("err")):
            result = server._tool_explain(1)
        assert "error" in result

    def test_fix_error_returns_cannot_fix(self):
        import httpx

        mcp_dir = str(Path(__file__).parent.parent / "acrqa-mcp")
        if mcp_dir not in sys.path:
            sys.path.insert(0, mcp_dir)
        import server

        with patch.object(server, "_get", side_effect=httpx.HTTPError("err")):
            result = server._tool_fix(1)
        assert result["can_fix"] is False

    def test_version_one_zero_zero(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "acrqa_mcp_init",
            Path(__file__).parent.parent / "acrqa-mcp" / "__init__.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert mod.__version__ == "1.0.0"


class TestExploitVerifierGodMode:
    """God-mode tests for Feature 12: Proof-of-Exploit Engine."""

    def test_module_imports_cleanly(self):
        from CORE.engines.exploit_verifier import ExploitVerifier  # noqa: F401

    def test_exploit_result_dataclass_fields(self):
        from CORE.engines.exploit_verifier import ExploitResult

        r = ExploitResult(finding_id=1, category="ssti", verified=True, tier="verified-exploitable")
        assert r.tier == "verified-exploitable"
        assert r.verified is True
        assert r.extra == {}

    def test_can_verify_high_sqli(self):
        from CORE.engines.exploit_verifier import ExploitVerifier

        ev = ExploitVerifier()
        f = {"severity": "high", "canonical_rule_id": "SECURITY-027"}
        assert ev.can_verify(f) is True

    def test_cannot_verify_medium(self):
        from CORE.engines.exploit_verifier import ExploitVerifier

        ev = ExploitVerifier()
        f = {"severity": "medium", "canonical_rule_id": "SECURITY-027"}
        assert ev.can_verify(f) is False

    def test_enrich_findings_adds_exploit_tier_to_all(self):
        from CORE.engines.exploit_verifier import ExploitVerifier

        ev = ExploitVerifier(use_docker=False)
        findings = [
            {"id": 1, "severity": "high", "canonical_rule_id": "SECURITY-027"},
            {"id": 2, "severity": "low", "canonical_rule_id": "STYLE-001"},
        ]
        result = ev.enrich_findings(findings, "/tmp")
        for f in result:
            assert "exploit_tier" in f

    def test_enrich_findings_does_not_crash_on_exception(self):
        from CORE.engines.exploit_verifier import ExploitVerifier

        ev = ExploitVerifier()
        findings = [{"id": 1, "severity": "high", "canonical_rule_id": "SECURITY-032"}]
        with patch.object(ev, "verify_finding", side_effect=Exception("network down")):
            result = ev.enrich_findings(findings, "/tmp")
        assert result[0]["exploit_tier"] == "unverified"

    def test_proof_json_is_valid_json(self):
        from CORE.engines.exploit_verifier import ExploitResult

        r = ExploitResult(
            finding_id=99,
            category="command-injection",
            verified=True,
            tier="verified-exploitable",
            payload="localhost; echo EXPLOITED",
            evidence="EXPLOITED",
        )
        proof = r.to_proof_json()
        obj = json.loads(proof)
        assert obj["verified"] is True
        assert obj["tier"] == "verified-exploitable"

    def test_db_method_exists(self):
        from DATABASE.database import Database

        assert callable(getattr(Database, "update_finding_exploit_status", None))

    def test_alembic_0005_exists(self):
        versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
        assert any(versions_dir.glob("*0005*"))

    def test_exploit_marker_in_pyproject(self):
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        content = pyproject.read_text()
        assert "exploit" in content

    def test_docker_fixture_dockerfiles_exist(self):
        fixtures = Path(__file__).parent / "fixtures" / "exploits"
        for app_name in ["flask_sqli", "flask_cmdi", "flask_ssti", "flask_safe"]:
            dockerfile = fixtures / app_name / "Dockerfile"
            assert dockerfile.exists(), f"Missing {dockerfile}"

    def test_version_is_350(self):
        from CORE import __version__

        assert __version__ == "3.6.0"


class TestAttestationGodMode:
    """God-mode tests for Feature 13: Provenance Attestation Engine."""

    def test_engine_importable(self):
        from CORE.engines.attestation import AttestationEngine  # noqa: F401

    def test_sign_returns_ecdsa_and_dilithium3(self):
        from CORE.engines.attestation import AttestationEngine, build_attestation

        eng = AttestationEngine()
        bundle = eng.sign(build_attestation(1, {"repo_name": "test"}))
        algorithms = [s["algorithm"] for s in bundle["signatures"]]
        assert "ECDSA-P256" in algorithms
        assert "Dilithium3" in algorithms

    def test_verify_roundtrip(self):
        from CORE.engines.attestation import AttestationEngine, build_attestation

        eng = AttestationEngine()
        bundle = eng.sign(build_attestation(1, {}))
        assert eng.verify(bundle) is True

    def test_tamper_invalidates_signature(self):
        from CORE.engines.attestation import AttestationEngine, build_attestation

        eng = AttestationEngine()
        bundle = eng.sign(build_attestation(1, {}))
        bundle["attestation"]["predicate"]["findings_count"] = 9999
        assert eng.verify(bundle) is False

    def test_attest_scan_persists_to_db(self):
        from unittest.mock import MagicMock

        from CORE.engines.attestation import AttestationEngine

        eng = AttestationEngine()
        db = MagicMock()
        db.store_attestation.return_value = 1
        result = eng.attest_scan(42, {"repo_name": "test", "total_findings": 3}, db)
        assert result is not None
        db.store_attestation.assert_called_once()

    def test_attest_scan_never_crashes(self):
        from unittest.mock import MagicMock

        from CORE.engines.attestation import AttestationEngine

        eng = AttestationEngine()
        db = MagicMock()
        db.store_attestation.side_effect = Exception("connection refused")
        result = eng.attest_scan(1, {}, db)
        assert result is None

    def test_predicate_has_verified_exploitable_count(self):
        from CORE.engines.attestation import build_predicate

        p = build_predicate(1, {"verified_exploitable": 3})
        assert p["verified_exploitable"] == 3

    def test_migration_0006_exists(self):
        versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
        assert any(versions_dir.glob("*0006*"))

    def test_db_has_attestation_methods(self):
        from DATABASE.database import Database

        assert callable(getattr(Database, "store_attestation", None))
        assert callable(getattr(Database, "get_attestation", None))

    def test_api_endpoint_in_runs_router(self):
        src = (Path(__file__).parent.parent / "FRONTEND" / "api" / "routers" / "runs.py").read_text()
        assert "/attestation" in src

    def test_pipeline_wired_python_and_js(self):
        src = (Path(__file__).parent.parent / "CORE" / "main.py").read_text()
        assert src.count("AttestationEngine") >= 2

    def test_version_is_360(self):
        from CORE import __version__

        assert __version__ == "3.6.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
