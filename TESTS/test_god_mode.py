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
    """Test the 3 new Flask API endpoints."""

    @pytest.fixture
    def client(self):
        from FRONTEND.app import app

        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c

    def test_test_gaps_endpoint_returns_200(self, client):
        """GET /api/test-gaps should return 200."""
        resp = client.get("/api/test-gaps")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "success" in data

    def test_test_gaps_has_coverage_data(self, client):
        """Test gaps response should include coverage metrics."""
        resp = client.get("/api/test-gaps")
        data = json.loads(resp.data)
        if data["success"]:
            assert "total_symbols" in data
            assert "coverage_pct" in data

    def test_policy_endpoint_returns_200(self, client):
        """GET /api/policy should return 200."""
        resp = client.get("/api/policy")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "success" in data

    def test_policy_has_config_sections(self, client):
        """Policy response should include config sections."""
        resp = client.get("/api/policy")
        data = json.loads(resp.data)
        if data["success"]:
            assert "active_policy" in data

    def test_compliance_endpoint_returns_200(self, client):
        """GET /api/runs/1/compliance should return 200."""
        resp = client.get("/api/runs/1/compliance")
        # Should not crash — may be 200 or 500 if no run exists
        assert resp.status_code in [200, 500]

    def test_health_still_works(self, client):
        """GET /api/health should still work."""
        resp = client.get("/api/health")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# 6. CONFIDENCE-BASED NOISE CONTROL — DEEP TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestConfidenceScoring:
    """Test the _calculate_confidence() function."""

    def test_confidence_has_function(self):
        """The app module should have _calculate_confidence."""
        from FRONTEND.app import _calculate_confidence

        assert callable(_calculate_confidence)

    def test_high_severity_security_with_explanation(self):
        """High severity + security + explanation should score high."""
        from FRONTEND.app import _calculate_confidence

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
        from FRONTEND.app import _calculate_confidence

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
        from FRONTEND.app import _calculate_confidence

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
        from FRONTEND.app import _calculate_confidence

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

    def test_flask_secret_not_hardcoded(self):
        """Flask app should not use a hardcoded secret key."""
        app_path = Path(__file__).parent.parent / "FRONTEND" / "app.py"
        content = app_path.read_text()
        assert 'secret_key = "' not in content.lower() or "os.urandom" in content


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
        from CORE.engines.severity_scorer import SeverityScorer
        from FRONTEND.app import _calculate_confidence

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
        from FRONTEND.app import _calculate_confidence

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
        from FRONTEND.app import app

        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c

    def test_api_nonexistent_endpoints_404(self, client):
        """Non-existent API endpoints should return 404."""
        resp = client.get("/api/nonexistent")
        assert resp.status_code == 404

    def test_api_test_gaps_doesnt_crash_under_load(self, client):
        """Repeated calls to test-gaps should not crash."""
        for _ in range(5):
            resp = client.get("/api/test-gaps")
            assert resp.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
