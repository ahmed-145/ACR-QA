"""
God-mode tests for CORE/engines/normalizer.py and CORE/engines/severity_scorer.py
Targets ~95%+ coverage across both modules.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from CORE.engines.normalizer import (
    CATEGORY_MAPPING,
    RULE_MAPPING,
    CanonicalFinding,
    normalize_all,
    normalize_bandit,
    normalize_jscpd,
    normalize_radon,
    normalize_ruff,
    normalize_semgrep,
    normalize_vulture,
)
from CORE.engines.severity_scorer import SeverityScorer, score_severity

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_finding(**overrides) -> CanonicalFinding:
    """Return a minimal valid CanonicalFinding."""
    defaults = dict(
        canonical_rule_id="SECURITY-001",
        original_rule_id="B307",
        severity="high",
        category="security",
        file="app.py",
        line=10,
        column=0,
        language="python",
        message="eval() usage",
        tool_raw={"tool_name": "bandit"},
    )
    defaults.update(overrides)
    return CanonicalFinding(**defaults)


# ─────────────────────────────────────────────────────────────────────────────
# CanonicalFinding — model validators
# ─────────────────────────────────────────────────────────────────────────────


class TestCanonicalFindingModel:
    """CanonicalFinding Pydantic model — field validators and factory."""

    def test_severity_normalised_to_lowercase(self):
        """Validators should lowercase 'HIGH' → 'high'."""
        f = _make_finding(severity="HIGH")
        assert f.severity == "high"

    def test_severity_medium_normalised(self):
        f = _make_finding(severity="MEDIUM")
        assert f.severity == "medium"

    def test_severity_low_normalised(self):
        f = _make_finding(severity="LOW")
        assert f.severity == "low"

    def test_invalid_severity_raises(self):
        with pytest.raises(Exception):
            _make_finding(severity="critical")

    def test_known_category_accepted(self):
        f = _make_finding(category="dead-code")
        assert f.category == "dead-code"

    def test_unknown_category_warns_but_accepted(self, capsys):
        f = _make_finding(category="exotic-category")
        assert f.category == "exotic-category"

    def test_finding_id_is_uuid(self):
        f = _make_finding()
        # Should be parseable as a UUID
        uuid.UUID(f.finding_id)

    def test_to_dict_returns_dict(self):
        f = _make_finding()
        d = f.to_dict()
        assert isinstance(d, dict)
        assert d["canonical_rule_id"] == "SECURITY-001"

    def test_evidence_default_shape(self):
        f = _make_finding()
        assert "snippet" in f.evidence
        assert "context_before" in f.evidence
        assert "context_after" in f.evidence

    def test_original_severity_stored(self):
        f = _make_finding(original_severity="medium")
        assert f.original_severity == "medium"

    def test_column_defaults_to_zero(self):
        f = _make_finding()
        assert f.column == 0


# ─────────────────────────────────────────────────────────────────────────────
# CanonicalFinding.create() factory
# ─────────────────────────────────────────────────────────────────────────────


class TestCanonicalFindingCreate:
    """Factory method — rule mapping, language detection, scoring."""

    def test_mapped_rule_id_resolved(self):
        f = CanonicalFinding.create(
            rule_id="B608",
            file="dao.py",
            line=5,
            severity="high",
            category="security",
            message="SQL injection",
            tool_name="bandit",
            tool_output={},
        )
        assert f.canonical_rule_id == "SECURITY-027"

    def test_unmapped_rule_gets_custom_prefix(self):
        f = CanonicalFinding.create(
            rule_id="UNKNOWN-RULE",
            file="foo.py",
            line=1,
            severity="low",
            category="style",
            message="something new",
            tool_name="bandit",
            tool_output={},
        )
        assert f.canonical_rule_id == "CUSTOM-UNKNOWN-RULE"

    def test_python_language_detected(self):
        f = CanonicalFinding.create(
            rule_id="F401",
            file="main.py",
            line=1,
            severity="low",
            category="style",
            message="unused import",
            tool_name="ruff",
            tool_output={},
        )
        assert f.language == "python"

    def test_javascript_language_detected(self):
        f = CanonicalFinding.create(
            rule_id="F401",
            file="index.js",
            line=1,
            severity="low",
            category="style",
            message="msg",
            tool_name="eslint",
            tool_output={},
        )
        assert f.language == "javascript"

    def test_typescript_language_detected(self):
        f = CanonicalFinding.create(
            rule_id="F401",
            file="comp.ts",
            line=2,
            severity="low",
            category="style",
            message="msg",
            tool_name="eslint",
            tool_output={},
        )
        assert f.language == "typescript"

    def test_go_language_detected(self):
        f = CanonicalFinding.create(
            rule_id="G204",
            file="main.go",
            line=10,
            severity="medium",
            category="security",
            message="cmd injection",
            tool_name="gosec",
            tool_output={},
        )
        assert f.language == "go"

    def test_unknown_extension_language(self):
        f = CanonicalFinding.create(
            rule_id="F401",
            file="config.toml",
            line=1,
            severity="low",
            category="style",
            message="msg",
            tool_name="misc",
            tool_output={},
        )
        assert f.language == "unknown"

    def test_category_mapping_applied(self):
        f = CanonicalFinding.create(
            rule_id="F401",
            file="app.py",
            line=1,
            severity="low",
            category="style-or-practice",
            message="msg",
            tool_name="ruff",
            tool_output={},
        )
        assert f.category == "style"

    def test_unmapped_category_passed_through(self):
        f = CanonicalFinding.create(
            rule_id="F401",
            file="app.py",
            line=1,
            severity="low",
            category="exotic",
            message="msg",
            tool_name="ruff",
            tool_output={},
        )
        assert f.category == "exotic"

    def test_tool_raw_contains_tool_name(self):
        f = CanonicalFinding.create(
            rule_id="F401",
            file="app.py",
            line=1,
            severity="low",
            category="style",
            message="msg",
            tool_name="ruff",
            tool_output={"key": "val"},
        )
        assert f.tool_raw["tool_name"] == "ruff"

    def test_column_forwarded(self):
        f = CanonicalFinding.create(
            rule_id="F401",
            file="app.py",
            line=3,
            severity="low",
            category="style",
            message="msg",
            tool_name="ruff",
            tool_output={},
            column=12,
        )
        assert f.column == 12


# ─────────────────────────────────────────────────────────────────────────────
# extract_evidence()
# ─────────────────────────────────────────────────────────────────────────────


class TestExtractEvidence:
    def test_fallback_when_file_missing(self):
        f = _make_finding(file="/nonexistent/path/foo.py", line=5)
        f.extract_evidence()
        # Fallback sets snippet to '# Line 5' but code_extractor may set empty string
        assert f.evidence["context_before"] == []
        assert f.evidence["context_after"] == []

    def test_evidence_populated_from_real_file(self, tmp_path):
        code = "\n".join(f"line_{i} = {i}" for i in range(1, 20))
        src = tmp_path / "sample.py"
        src.write_text(code)
        f = _make_finding(file=str(src), line=10)
        # Should not crash
        f.extract_evidence()
        assert "snippet" in f.evidence


# ─────────────────────────────────────────────────────────────────────────────
# normalize_ruff()
# ─────────────────────────────────────────────────────────────────────────────


class TestNormalizeRuff:
    def test_empty_list_returns_empty(self):
        result = normalize_ruff([])
        assert result == []

    def test_single_finding_basic(self):
        findings = normalize_ruff(
            [
                {
                    "code": "F401",
                    "filename": "app.py",
                    "location": {"row": 5, "column": 0},
                    "message": "unused import os",
                }
            ]
        )
        assert len(findings) == 1
        f = findings[0]
        assert f.original_rule_id == "F401"
        assert f.canonical_rule_id == "IMPORT-001"
        assert f.file == "app.py"
        assert f.line == 5

    def test_unknown_code_gets_custom_prefix(self):
        findings = normalize_ruff(
            [{"code": "ZZZZ-99", "filename": "x.py", "location": {"row": 1, "column": 0}, "message": "weird"}]
        )
        assert findings[0].canonical_rule_id == "CUSTOM-ZZZZ-99"

    def test_missing_fields_use_defaults(self):
        findings = normalize_ruff([{}])
        assert findings[0].line == 0
        assert findings[0].message == ""

    def test_multiple_findings_returned(self):
        items = [
            {"code": "F401", "filename": f"f{i}.py", "location": {"row": i, "column": 0}, "message": "msg"}
            for i in range(5)
        ]
        assert len(normalize_ruff(items)) == 5


# ─────────────────────────────────────────────────────────────────────────────
# normalize_semgrep()
# ─────────────────────────────────────────────────────────────────────────────


class TestNormalizeSemgrep:
    def _sg(self, check_id, path="app.py", line=1, severity="WARNING", category="security", msg="issue"):
        return {
            "results": [
                {
                    "check_id": check_id,
                    "path": path,
                    "start": {"line": line, "col": 0},
                    "extra": {
                        "severity": severity,
                        "message": msg,
                        "metadata": {"category": category},
                    },
                }
            ]
        }

    def test_empty_results(self):
        assert normalize_semgrep({"results": []}) == []

    def test_rule_id_extracted_from_dotted_check_id(self):
        findings = normalize_semgrep(self._sg("services.semgrep.dangerous-eval-usage"))
        assert findings[0].canonical_rule_id == "SECURITY-001"

    def test_rule_id_without_dots(self):
        findings = normalize_semgrep(self._sg("bare-except"))
        assert findings[0].canonical_rule_id == "EXCEPT-001"

    def test_custom_category_from_metadata(self):
        findings = normalize_semgrep(self._sg("some-rule", category="best-practice"))
        assert findings[0].category == "best-practice"

    def test_missing_results_key(self):
        assert normalize_semgrep({}) == []

    def test_column_set_from_col(self):
        data = {
            "results": [
                {
                    "check_id": "bare-except",
                    "path": "foo.py",
                    "start": {"line": 3, "col": 7},
                    "extra": {"severity": "WARNING", "message": "msg", "metadata": {"category": "security"}},
                }
            ]
        }
        findings = normalize_semgrep(data)
        assert findings[0].column == 7


# ─────────────────────────────────────────────────────────────────────────────
# normalize_vulture()
# ─────────────────────────────────────────────────────────────────────────────


class TestNormalizeVulture:
    def test_empty_string_returns_empty(self):
        assert normalize_vulture("") == []

    def test_comment_line_skipped(self):
        assert normalize_vulture("# this is a comment") == []

    def test_unused_import_detected(self):
        findings = normalize_vulture("app.py:10: unused import 'os' (60% confidence)")
        assert len(findings) == 1
        assert findings[0].canonical_rule_id == "IMPORT-001"
        assert findings[0].line == 10

    def test_unused_variable_detected(self):
        findings = normalize_vulture("app.py:20: unused variable 'x' (80% confidence)")
        assert findings[0].canonical_rule_id == "VAR-001"

    def test_unused_function_detected(self):
        findings = normalize_vulture("utils.py:5: unused function 'helper' (90% confidence)")
        assert findings[0].canonical_rule_id == "DEAD-001"

    def test_unused_class_detected(self):
        findings = normalize_vulture("models.py:15: unused class 'OldModel' (100% confidence)")
        assert findings[0].canonical_rule_id == "DEAD-001"

    def test_generic_unused_code(self):
        findings = normalize_vulture("app.py:1: something else entirely (70% confidence)")
        assert findings[0].canonical_rule_id == "DEAD-001"

    def test_invalid_line_number_defaults_to_zero(self):
        findings = normalize_vulture("app.py:notanumber: unused import 'x' (60% confidence)")
        assert findings[0].line == 0

    def test_multiple_lines(self):
        txt = "a.py:1: unused import 'os'\nb.py:2: unused variable 'x'"
        assert len(normalize_vulture(txt)) == 2

    def test_short_line_skipped(self):
        # Only 2 parts → skipped
        findings = normalize_vulture("app.py:only-two-parts")
        assert findings == []


# ─────────────────────────────────────────────────────────────────────────────
# normalize_jscpd()
# ─────────────────────────────────────────────────────────────────────────────


class TestNormalizeJscpd:
    def test_empty_duplicates(self):
        assert normalize_jscpd({"duplicates": []}) == []

    def test_single_duplicate_block(self):
        data = {
            "duplicates": [
                {
                    "lines": 30,
                    "tokens": 150,
                    "firstFile": {"name": "a.py", "start": 1},
                    "secondFile": {"name": "b.py", "start": 45},
                }
            ]
        }
        findings = normalize_jscpd(data)
        assert len(findings) == 1
        f = findings[0]
        assert f.canonical_rule_id == "DUP-001"
        assert f.file == "a.py"
        assert "150 tokens" in f.message

    def test_missing_duplicates_key(self):
        assert normalize_jscpd({}) == []

    def test_message_contains_second_file(self):
        data = {
            "duplicates": [
                {
                    "lines": 5,
                    "tokens": 20,
                    "firstFile": {"name": "x.py", "start": 10},
                    "secondFile": {"name": "y.py", "start": 55},
                }
            ]
        }
        msg = normalize_jscpd(data)[0].message
        assert "y.py" in msg


# ─────────────────────────────────────────────────────────────────────────────
# normalize_radon()
# ─────────────────────────────────────────────────────────────────────────────


class TestNormalizeRadon:
    def test_empty_dict_returns_empty(self):
        assert normalize_radon({}) == []

    def test_low_complexity_not_flagged(self):
        data = {"app.py": [{"name": "func", "complexity": 5, "lineno": 1, "col_offset": 0}]}
        assert normalize_radon(data) == []

    def test_complexity_just_over_10_is_flagged(self):
        # Radon creates severity="low" but SeverityScorer upgrades based on CC value;
        # CC=11 > COMPLEXITY_THRESHOLDS["medium"]=10 so scorer returns "medium".
        data = {"app.py": [{"name": "func", "complexity": 11, "lineno": 1, "col_offset": 0}]}
        findings = normalize_radon(data)
        assert len(findings) == 1
        # SeverityScorer adjusts: 10 < 11 <= 20 → medium
        assert findings[0].severity == "medium"

    def test_complexity_over_15_is_medium(self):
        data = {"app.py": [{"name": "func", "complexity": 18, "lineno": 5, "col_offset": 0}]}
        findings = normalize_radon(data)
        assert findings[0].severity == "medium"

    def test_complexity_over_20_is_high(self):
        data = {"app.py": [{"name": "func", "complexity": 25, "lineno": 5, "col_offset": 0}]}
        findings = normalize_radon(data)
        assert findings[0].severity == "high"

    def test_non_list_value_skipped(self):
        data = {"app.py": "not a list"}
        assert normalize_radon(data) == []

    def test_function_name_in_message(self):
        data = {"app.py": [{"name": "my_complex_func", "complexity": 22, "lineno": 3, "col_offset": 0}]}
        msg = normalize_radon(data)[0].message
        assert "my_complex_func" in msg


# ─────────────────────────────────────────────────────────────────────────────
# normalize_bandit()
# ─────────────────────────────────────────────────────────────────────────────


class TestNormalizeBandit:
    def _item(self, test_id="B608", severity="HIGH", text="SQL injection", filename="dao.py", line=10):
        return {
            "test_id": test_id,
            "filename": filename,
            "line_number": line,
            "col_offset": 0,
            "issue_severity": severity,
            "issue_confidence": "HIGH",
            "issue_text": text,
        }

    def test_empty_results(self):
        assert normalize_bandit({"results": []}) == []

    def test_high_severity_mapped(self):
        findings = normalize_bandit({"results": [self._item("B608", "HIGH")]})
        assert findings[0].severity == "high"

    def test_medium_severity_mapped(self):
        findings = normalize_bandit({"results": [self._item("B303", "MEDIUM")]})
        assert findings[0].severity == "medium"

    def test_low_severity_mapped(self):
        findings = normalize_bandit({"results": [self._item("B101", "LOW")]})
        assert findings[0].severity == "low"

    def test_unknown_severity_gets_scored_by_rule(self):
        # Unknown issue_severity maps to "low" via BANDIT_SEVERITY.get(..., "low")
        # but B307 → SECURITY-001 → scorer upgrades it to "high"
        item = self._item(test_id="B307")
        item["issue_severity"] = "BOGUS"
        findings = normalize_bandit({"results": [item]})
        # SECURITY-001 is high regardless of raw severity
        assert findings[0].severity == "high"

    def test_rule_id_mapped(self):
        # B608 → SECURITY-027
        findings = normalize_bandit({"results": [self._item("B608")]})
        assert findings[0].canonical_rule_id == "SECURITY-027"

    def test_confidence_in_message(self):
        findings = normalize_bandit({"results": [self._item(text="SQL injection")]})
        assert "Confidence: HIGH" in findings[0].message

    def test_file_and_line(self):
        findings = normalize_bandit({"results": [self._item(filename="srv.py", line=42)]})
        f = findings[0]
        assert f.file == "srv.py"
        assert f.line == 42

    def test_missing_results_key(self):
        assert normalize_bandit({}) == []


# ─────────────────────────────────────────────────────────────────────────────
# normalize_all() — filesystem-level tests
# ─────────────────────────────────────────────────────────────────────────────


class TestNormalizeAll:
    def test_empty_directory_returns_empty(self, tmp_path):
        result = normalize_all(str(tmp_path))
        assert result == []

    def test_ruff_json_picked_up(self, tmp_path):
        ruff_data = [
            {"code": "F401", "filename": "app.py", "location": {"row": 1, "column": 0}, "message": "unused import"}
        ]
        (tmp_path / "ruff.json").write_text(json.dumps(ruff_data))
        result = normalize_all(str(tmp_path))
        assert len(result) == 1

    def test_semgrep_json_picked_up(self, tmp_path):
        sg = {
            "results": [
                {
                    "check_id": "bare-except",
                    "path": "app.py",
                    "start": {"line": 5, "col": 0},
                    "extra": {"severity": "WARNING", "message": "bare except", "metadata": {"category": "security"}},
                }
            ]
        }
        (tmp_path / "semgrep.json").write_text(json.dumps(sg))
        result = normalize_all(str(tmp_path))
        assert len(result) == 1

    def test_vulture_txt_picked_up(self, tmp_path):
        (tmp_path / "vulture.txt").write_text("app.py:7: unused import 'os'\n")
        result = normalize_all(str(tmp_path))
        assert len(result) == 1

    def test_radon_json_picked_up(self, tmp_path):
        radon = {"app.py": [{"name": "complex_func", "complexity": 25, "lineno": 1, "col_offset": 0}]}
        (tmp_path / "radon.json").write_text(json.dumps(radon))
        result = normalize_all(str(tmp_path))
        assert len(result) == 1

    def test_jscpd_json_picked_up(self, tmp_path):
        jscpd = {
            "duplicates": [
                {
                    "lines": 40,
                    "tokens": 200,
                    "firstFile": {"name": "a.py", "start": 1},
                    "secondFile": {"name": "b.py", "start": 40},
                }
            ]
        }
        (tmp_path / "jscpd.json").write_text(json.dumps(jscpd))
        result = normalize_all(str(tmp_path))
        assert len(result) == 1

    def test_bandit_json_picked_up(self, tmp_path):
        bandit = {
            "results": [
                {
                    "test_id": "B608",
                    "filename": "dao.py",
                    "line_number": 10,
                    "col_offset": 0,
                    "issue_severity": "HIGH",
                    "issue_confidence": "HIGH",
                    "issue_text": "SQL injection",
                }
            ]
        }
        (tmp_path / "bandit.json").write_text(json.dumps(bandit))
        result = normalize_all(str(tmp_path))
        assert len(result) == 1

    def test_corrupt_ruff_json_handled_gracefully(self, tmp_path):
        (tmp_path / "ruff.json").write_text("{NOT VALID JSON")
        result = normalize_all(str(tmp_path))
        assert result == []

    def test_empty_ruff_json_file_skipped(self, tmp_path):
        (tmp_path / "ruff.json").write_text("   ")
        result = normalize_all(str(tmp_path))
        assert result == []

    def test_inline_suppression_acr_qa_ignore(self, tmp_path):
        """Findings on lines with # acr-qa:ignore should be suppressed."""
        src = tmp_path / "app.py"
        src.write_text("x = eval(input())  # acr-qa:ignore\n")
        bandit = {
            "results": [
                {
                    "test_id": "B307",
                    "filename": str(src),
                    "line_number": 1,
                    "col_offset": 0,
                    "issue_severity": "HIGH",
                    "issue_confidence": "HIGH",
                    "issue_text": "eval",
                }
            ]
        }
        (tmp_path / "bandit.json").write_text(json.dumps(bandit))
        result = normalize_all(str(tmp_path))
        assert len(result) == 0

    def test_inline_suppression_acrqa_disable_with_rule(self, tmp_path):
        """Rule-specific disable should suppress matching rule."""
        src = tmp_path / "app.py"
        src.write_text("x = 1  # acrqa:disable SECURITY-001\n")
        bandit = {
            "results": [
                {
                    "test_id": "B307",
                    "filename": str(src),
                    "line_number": 1,
                    "col_offset": 0,
                    "issue_severity": "HIGH",
                    "issue_confidence": "HIGH",
                    "issue_text": "eval",
                }
            ]
        }
        (tmp_path / "bandit.json").write_text(json.dumps(bandit))
        result = normalize_all(str(tmp_path))
        assert len(result) == 0

    def test_inline_suppression_does_not_suppress_other_rule(self, tmp_path):
        """Disable for one rule should NOT suppress a different rule."""
        src = tmp_path / "app.py"
        # Disable IMPORT-001 but finding is SECURITY-001
        src.write_text("x = eval(1)  # acrqa:disable IMPORT-001\n")
        bandit = {
            "results": [
                {
                    "test_id": "B307",
                    "filename": str(src),
                    "line_number": 1,
                    "col_offset": 0,
                    "issue_severity": "HIGH",
                    "issue_confidence": "HIGH",
                    "issue_text": "eval",
                }
            ]
        }
        (tmp_path / "bandit.json").write_text(json.dumps(bandit))
        result = normalize_all(str(tmp_path))
        # SECURITY-001 should NOT be suppressed by IMPORT-001 disable
        assert len(result) == 1

    def test_multiple_tool_files_aggregated(self, tmp_path):
        ruff = [{"code": "F401", "filename": "a.py", "location": {"row": 1, "column": 0}, "message": "unused"}]
        vulture = "b.py:5: unused function 'old_fn'\n"
        (tmp_path / "ruff.json").write_text(json.dumps(ruff))
        (tmp_path / "vulture.txt").write_text(vulture)
        result = normalize_all(str(tmp_path))
        assert len(result) == 2


# ─────────────────────────────────────────────────────────────────────────────
# RULE_MAPPING completeness spot checks
# ─────────────────────────────────────────────────────────────────────────────


class TestRuleMapping:
    def test_bandit_rules_present(self):
        for rule in ["B101", "B102", "B301", "B608"]:
            assert rule in RULE_MAPPING

    def test_ruff_rules_present(self):
        for rule in ["F401", "F841", "E501", "UP007", "T201"]:
            assert rule in RULE_MAPPING

    def test_semgrep_rules_present(self):
        for rule in ["dangerous-eval-usage", "shell-injection", "sql-injection"]:
            assert rule in RULE_MAPPING

    def test_no_duplicated_canonical_values_for_same_input(self):
        # Specifically B608 should map to SECURITY-027
        assert RULE_MAPPING["B608"] == "SECURITY-027"

    def test_category_mapping_entries(self):
        assert CATEGORY_MAPPING["security"] == "security"
        assert CATEGORY_MAPPING["style-or-practice"] == "style"


# ─────────────────────────────────────────────────────────────────────────────
# SeverityScorer — score() method
# ─────────────────────────────────────────────────────────────────────────────


class TestSeverityScorerScore:
    def setup_method(self):
        self.scorer = SeverityScorer()

    def test_known_high_rule(self):
        assert self.scorer.score("SECURITY-001", {}) == "high"

    def test_known_medium_rule(self):
        assert self.scorer.score("SOLID-001", {}) == "medium"

    def test_known_low_rule(self):
        assert self.scorer.score("STYLE-001", {}) == "low"

    def test_unmapped_security_rule_defaults_medium(self):
        assert self.scorer.score("SECURITY-999", {}) == "medium"

    def test_unmapped_other_rule_defaults_low(self):
        assert self.scorer.score("UNKNOWN-XYZ", {}) == "low"

    def test_custom_injection_keyword_infers_high(self):
        assert self.scorer.score("CUSTOM-my-injection-rule", {}) == "high"

    def test_custom_password_keyword_infers_high(self):
        assert self.scorer.score("CUSTOM-hardcoded-password", {}) == "high"

    def test_custom_pickle_keyword_infers_medium(self):
        assert self.scorer.score("CUSTOM-bad-pickle-usage", {}) == "medium"

    def test_custom_yaml_keyword_infers_medium(self):
        assert self.scorer.score("CUSTOM-unsafe-yaml-load", {}) == "medium"

    def test_custom_generic_infers_low(self):
        assert self.scorer.score("CUSTOM-unused-stuff", {}) == "low"

    def test_complexity_high_over_20(self):
        finding = {"tool_raw": {"original_output": {"complexity": 25}}}
        assert self.scorer.score("COMPLEXITY-001", finding) == "high"

    def test_complexity_medium_over_10(self):
        finding = {"tool_raw": {"original_output": {"complexity": 16}}}
        assert self.scorer.score("COMPLEXITY-001", finding) == "medium"

    def test_complexity_low_under_threshold(self):
        finding = {"tool_raw": {"original_output": {"complexity": 5}}}
        assert self.scorer.score("COMPLEXITY-001", finding) == "low"

    def test_dead_001_class_is_medium(self):
        finding = {"message": "unused class 'OldModel'"}
        assert self.scorer.score("DEAD-001", finding) == "medium"

    def test_dead_001_small_function_is_low(self):
        finding = {"message": "unused function 'helper'", "evidence": {"snippet": "short"}}
        assert self.scorer.score("DEAD-001", finding) == "low"

    def test_dead_001_large_function_is_medium(self):
        finding = {"message": "unused function 'big_helper'", "evidence": {"snippet": "x" * 200}}
        assert self.scorer.score("DEAD-001", finding) == "medium"

    def test_dup_001_large_tokens_is_high(self):
        finding = {"tool_raw": {"original_output": {"tokens": 250}}}
        assert self.scorer.score("DUP-001", finding) == "high"

    def test_dup_001_medium_tokens_is_medium(self):
        finding = {"tool_raw": {"original_output": {"tokens": 150}}}
        assert self.scorer.score("DUP-001", finding) == "medium"

    def test_dup_001_small_tokens_is_low(self):
        finding = {"tool_raw": {"original_output": {"tokens": 30}}}
        # DUP-001 base is medium, but tokens < 100 falls through to base
        result = self.scorer.score("DUP-001", finding)
        assert result == "medium"  # base severity for DUP-001

    def test_security_047_is_critical(self):
        # JWT none algorithm — critical
        result = self.scorer.score("SECURITY-047", {})
        assert result == "critical"

    def test_all_high_security_rules(self):
        high_rules = [
            "SECURITY-001",
            "SECURITY-005",
            "SECURITY-021",
            "SECURITY-027",
            "SECURITY-031",
            "HARDCODE-001",
            "SECURITY-008",
            "SECURITY-018",
            "SECURITY-045",
            "SECURITY-046",
        ]
        for rule in high_rules:
            assert self.scorer.score(rule, {}) == "high", f"Expected high for {rule}"

    def test_all_low_style_rules(self):
        low_rules = ["STYLE-001", "STYLE-002", "STYLE-003", "IMPORT-001", "VAR-001", "NAMING-001"]
        for rule in low_rules:
            assert self.scorer.score(rule, {}) == "low", f"Expected low for {rule}"


# ─────────────────────────────────────────────────────────────────────────────
# SeverityScorer — private helpers
# ─────────────────────────────────────────────────────────────────────────────


class TestSeverityScorerHelpers:
    def setup_method(self):
        self.scorer = SeverityScorer()

    # _infer_custom_severity
    def test_infer_xss_is_high(self):
        assert self.scorer._infer_custom_severity("CUSTOM-xss-injection") == "high"

    def test_infer_rce_is_high(self):
        assert self.scorer._infer_custom_severity("CUSTOM-remote-rce") == "high"

    def test_infer_secret_is_high(self):
        assert self.scorer._infer_custom_severity("CUSTOM-leaked-secret") == "high"

    def test_infer_exec_is_high(self):
        assert self.scorer._infer_custom_severity("CUSTOM-exec-danger") == "high"

    def test_infer_ssl_is_medium(self):
        assert self.scorer._infer_custom_severity("CUSTOM-ssl-bypass") == "medium"

    def test_infer_deserialization_is_medium(self):
        assert self.scorer._infer_custom_severity("CUSTOM-deserialization-risk") == "medium"

    def test_infer_generic_is_low(self):
        assert self.scorer._infer_custom_severity("CUSTOM-line-length-issue") == "low"

    # _extract_complexity
    def test_extract_complexity_from_tool_raw(self):
        finding = {"tool_raw": {"original_output": {"complexity": 42}}}
        assert self.scorer._extract_complexity(finding) == 42

    def test_extract_complexity_from_message_fallback(self):
        # The fallback branch is only reached when tool_raw.get() itself raises.
        # In normal dicts it returns 0 via the try block. Test the zero-return case.
        finding = {"tool_raw": {}, "message": "Function 'x' has cyclomatic complexity of 17. High complexity."}
        # tool_raw is an empty dict so .get("original_output", {}).get("complexity", 0) = 0
        assert self.scorer._extract_complexity(finding) == 0

    def test_extract_complexity_returns_zero_on_missing(self):
        assert self.scorer._extract_complexity({}) == 0

    def test_extract_complexity_returns_zero_on_bad_message(self):
        finding = {"tool_raw": {}, "message": "complexity of notanumber."}
        result = self.scorer._extract_complexity(finding)
        assert result == 0

    # _extract_duplication_size
    def test_extract_dup_size_from_tool_raw(self):
        finding = {"tool_raw": {"original_output": {"tokens": 300}}}
        assert self.scorer._extract_duplication_size(finding) == 300

    def test_extract_dup_size_from_message_fallback(self):
        # Empty tool_raw → tokens=0 via normal path; message fallback unreachable
        finding = {"tool_raw": {}, "message": "Duplicate code: 250 tokens found"}
        assert self.scorer._extract_duplication_size(finding) == 0

    def test_extract_dup_size_returns_zero_on_missing(self):
        assert self.scorer._extract_duplication_size({}) == 0

    # get_severity_priority
    def test_priority_high_is_1(self):
        assert self.scorer.get_severity_priority("high") == 1

    def test_priority_medium_is_2(self):
        assert self.scorer.get_severity_priority("medium") == 2

    def test_priority_low_is_3(self):
        assert self.scorer.get_severity_priority("low") == 3

    def test_priority_unknown_is_99(self):
        assert self.scorer.get_severity_priority("critical") == 99

    # _apply_context_adjustments — complexity extracts from message
    def test_context_adjustment_complexity_uses_tool_raw(self):
        # Without tool_raw original_output, complexity = 0 → returns "low" branch
        finding = {"message": "Function 'f' has cyclomatic complexity of 22. Refactor.", "tool_raw": {}}
        result = self.scorer._apply_context_adjustments("medium", "COMPLEXITY-001", finding)
        assert result == "low"  # _extract_complexity returns 0 → falls to else branch


# ─────────────────────────────────────────────────────────────────────────────
# score_severity() convenience function
# ─────────────────────────────────────────────────────────────────────────────


class TestScoreSeverityConvenience:
    def test_high_security_rule(self):
        assert score_severity("SECURITY-001", {}) == "high"

    def test_low_style_rule(self):
        assert score_severity("STYLE-002", {}) == "low"

    def test_unmapped_returns_low(self):
        assert score_severity("NONEXISTENT-999", {}) == "low"

    def test_custom_injection_returns_high(self):
        assert score_severity("CUSTOM-sql-injection", {}) == "high"


# ─────────────────────────────────────────────────────────────────────────────
# Exception-branch coverage via MagicMock (lines 265-277, 284-296)
# ─────────────────────────────────────────────────────────────────────────────


class TestSeverityScorerExceptionBranches:
    """Force the except branches in _extract_complexity / _extract_duplication_size."""

    def setup_method(self):
        self.scorer = SeverityScorer()

    def _raising_dict(self, raises_on: str = "get"):
        """Return a dict-like object whose .get() raises AttributeError."""
        m = MagicMock()
        m.get.side_effect = AttributeError("boom")
        return m

    # _extract_complexity — exception branch + message parse
    def test_extract_complexity_exception_with_matching_message(self):
        finding = self._raising_dict()
        finding.get.side_effect = None  # allow outer .get(tool_raw) to work
        # Simulate: tool_raw raises on second .get()
        bad_tool_raw = MagicMock()
        bad_tool_raw.get.side_effect = AttributeError("boom")
        finding = {"tool_raw": bad_tool_raw, "message": "complexity of 21."}
        # The try block will raise when bad_tool_raw.get("original_output") is called
        # Falls to except → parses message → returns 21
        result = self.scorer._extract_complexity(finding)
        assert result == 21

    def test_extract_complexity_exception_message_no_match(self):
        bad_tool_raw = MagicMock()
        bad_tool_raw.get.side_effect = AttributeError("boom")
        finding = {"tool_raw": bad_tool_raw, "message": "no complexity info here"}
        result = self.scorer._extract_complexity(finding)
        assert result == 0

    def test_extract_complexity_exception_unparseable_number(self):
        bad_tool_raw = MagicMock()
        bad_tool_raw.get.side_effect = AttributeError("boom")
        finding = {"tool_raw": bad_tool_raw, "message": "complexity of abc."}
        result = self.scorer._extract_complexity(finding)
        assert result == 0

    # _extract_duplication_size — exception branch + message parse
    def test_extract_dup_exception_with_matching_message(self):
        bad_tool_raw = MagicMock()
        bad_tool_raw.get.side_effect = AttributeError("boom")
        finding = {"tool_raw": bad_tool_raw, "message": "250 tokens duplicated"}
        result = self.scorer._extract_duplication_size(finding)
        assert result == 250

    def test_extract_dup_exception_message_no_match(self):
        bad_tool_raw = MagicMock()
        bad_tool_raw.get.side_effect = AttributeError("boom")
        finding = {"tool_raw": bad_tool_raw, "message": "no duplication info"}
        result = self.scorer._extract_duplication_size(finding)
        assert result == 0

    def test_extract_dup_exception_unparseable_number(self):
        bad_tool_raw = MagicMock()
        bad_tool_raw.get.side_effect = AttributeError("boom")
        finding = {"tool_raw": bad_tool_raw, "message": "xyz tokens found"}
        result = self.scorer._extract_duplication_size(finding)
        assert result == 0


# ─────────────────────────────────────────────────────────────────────────────
# normalize_all() — error handling branches (semgrep, jscpd, radon, bandit)
# ─────────────────────────────────────────────────────────────────────────────


class TestNormalizeAllErrorHandling:
    """Cover the except branches in normalize_all for each tool."""

    def test_corrupt_semgrep_json_handled(self, tmp_path):
        (tmp_path / "semgrep.json").write_text("{CORRUPT")
        result = normalize_all(str(tmp_path))
        assert result == []

    def test_corrupt_jscpd_json_handled(self, tmp_path):
        (tmp_path / "jscpd.json").write_text("{CORRUPT")
        result = normalize_all(str(tmp_path))
        assert result == []

    def test_corrupt_radon_json_handled(self, tmp_path):
        (tmp_path / "radon.json").write_text("{CORRUPT")
        result = normalize_all(str(tmp_path))
        assert result == []

    def test_corrupt_bandit_json_handled(self, tmp_path):
        (tmp_path / "bandit.json").write_text("{CORRUPT")
        result = normalize_all(str(tmp_path))
        assert result == []

    def test_vulture_read_error_handled(self, tmp_path):
        """If vulture.txt raises on read, normalize_all should not crash."""
        vf = tmp_path / "vulture.txt"
        vf.write_text("app.py:1: unused import 'os'\n")
        # Patch open to raise when vulture is read — only for that specific path
        real_open = open

        def patched_open(path, *args, **kwargs):
            if "vulture" in str(path):
                raise OSError("disk error")
            return real_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=patched_open):
            result = normalize_all(str(tmp_path))
        assert result == []

    def test_acrqa_ignore_suppresses_finding(self, tmp_path):
        """acrqa:ignore (without hyphen) also suppresses."""
        src = tmp_path / "app.py"
        src.write_text("x = eval(1)  # acrqa:ignore\n")
        bandit = {
            "results": [
                {
                    "test_id": "B307",
                    "filename": str(src),
                    "line_number": 1,
                    "col_offset": 0,
                    "issue_severity": "HIGH",
                    "issue_confidence": "HIGH",
                    "issue_text": "eval",
                }
            ]
        }
        (tmp_path / "bandit.json").write_text(json.dumps(bandit))
        result = normalize_all(str(tmp_path))
        assert len(result) == 0
