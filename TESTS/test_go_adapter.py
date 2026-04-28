"""Tests for CORE/adapters/go_adapter.py — Go language support"""

from __future__ import annotations

import pytest

from CORE.adapters.go_adapter import (
    GOSEC_RULE_MAPPING,
    STATICCHECK_RULE_MAPPING,
    GoAdapter,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def adapter(tmp_path):
    return GoAdapter(str(tmp_path))


SAMPLE_GOSEC = {
    "Issues": [
        {
            "severity": "MEDIUM",
            "confidence": "HIGH",
            "cwe": {"id": "78", "url": "https://cwe.mitre.org/data/definitions/78.html"},
            "rule_id": "G204",
            "details": "Subprocess launched with variable",
            "file": "/tmp/govuln/main.go",
            "line": "12",
            "column": "5",
            "nosec": False,
            "suppressions": None,
        },
        {
            "severity": "HIGH",
            "confidence": "HIGH",
            "cwe": {"id": "326", "url": "https://cwe.mitre.org/data/definitions/326.html"},
            "rule_id": "G401",
            "details": "Use of weak cryptographic primitive",
            "file": "/tmp/govuln/main.go",
            "line": "18",
            "column": "10",
            "nosec": False,
            "suppressions": None,
        },
        {
            "severity": "LOW",
            "confidence": "HIGH",
            "cwe": {"id": "703", "url": "https://cwe.mitre.org/data/definitions/703.html"},
            "rule_id": "G104",
            "details": "Errors unhandled.",
            "file": "/tmp/govuln/main.go",
            "line": "25",
            "column": "5",
            "nosec": False,
            "suppressions": None,
        },
    ],
    "Stats": {"files": 1, "lines": 26, "nosec": 0, "found": 3},
    "GosecVersion": "2.18.2",
}

SAMPLE_STATICCHECK = [
    "main.go:14:5: printf-style function with dynamic format string (SA1006)",
    "main.go:17:6: func hashIt is unused (U1000)",
]


# ── Language metadata ─────────────────────────────────────────────────────────


class TestLanguageMetadata:
    def test_language_name(self, adapter):
        assert adapter.language_name == "Go"

    def test_file_extensions(self, adapter):
        assert ".go" in adapter.file_extensions

    def test_get_tools_returns_list(self, adapter):
        tools = adapter.get_tools()
        assert isinstance(tools, list)
        assert len(tools) >= 2

    def test_get_tools_has_gosec(self, adapter):
        names = [t["name"] for t in adapter.get_tools()]
        assert "gosec" in names

    def test_get_tools_has_staticcheck(self, adapter):
        names = [t["name"] for t in adapter.get_tools()]
        assert "staticcheck" in names

    def test_get_rule_mappings_combined(self, adapter):
        mappings = adapter.get_rule_mappings()
        assert "G204" in mappings
        assert "U1000" in mappings
        assert "SA1006" in mappings


# ── detect_language ───────────────────────────────────────────────────────────


class TestDetectLanguage:
    def test_detects_go_project(self, tmp_path):
        (tmp_path / "main.go").write_text("package main\n")
        assert GoAdapter.detect_language(str(tmp_path)) == "go"

    def test_returns_unknown_for_non_go(self, tmp_path):
        (tmp_path / "app.py").write_text("print('hi')\n")
        assert GoAdapter.detect_language(str(tmp_path)) == "unknown"

    def test_returns_unknown_for_empty_dir(self, tmp_path):
        assert GoAdapter.detect_language(str(tmp_path)) == "unknown"


# ── check_tools_available ─────────────────────────────────────────────────────


class TestCheckToolsAvailable:
    def test_returns_dict_with_tool_keys(self, adapter):
        result = adapter.check_tools_available()
        assert "gosec" in result
        assert "staticcheck" in result
        assert "semgrep" in result

    def test_values_are_bool(self, adapter):
        result = adapter.check_tools_available()
        assert all(isinstance(v, bool) for v in result.values())


# ── normalize_gosec ───────────────────────────────────────────────────────────


class TestNormalizeGosec:
    def test_returns_correct_count(self, adapter):
        findings = adapter.normalize_gosec(SAMPLE_GOSEC)
        assert len(findings) == 3

    def test_maps_g204_to_security_030(self, adapter):
        findings = adapter.normalize_gosec(SAMPLE_GOSEC)
        rules = [f.canonical_rule_id for f in findings]
        assert "SECURITY-030" in rules

    def test_maps_g401_to_security_050(self, adapter):
        findings = adapter.normalize_gosec(SAMPLE_GOSEC)
        rules = [f.canonical_rule_id for f in findings]
        assert "SECURITY-050" in rules

    def test_maps_g104_to_security_003(self, adapter):
        findings = adapter.normalize_gosec(SAMPLE_GOSEC)
        rules = [f.canonical_rule_id for f in findings]
        assert "SECURITY-003" in rules

    def test_severity_mapping_high(self, adapter):
        data = {
            "Issues": [
                {
                    "severity": "HIGH",
                    "confidence": "HIGH",
                    "cwe": {},
                    "rule_id": "G401",
                    "details": "weak crypto",
                    "file": "main.go",
                    "line": "1",
                    "column": "1",
                    "nosec": False,
                    "suppressions": None,
                }
            ]
        }
        findings = adapter.normalize_gosec(data)
        assert findings[0].severity == "high"

    def test_severity_mapping_medium(self, adapter):
        data = {
            "Issues": [
                {
                    "severity": "MEDIUM",
                    "confidence": "HIGH",
                    "cwe": {},
                    "rule_id": "G204",
                    "details": "subprocess",
                    "file": "main.go",
                    "line": "1",
                    "column": "1",
                    "nosec": False,
                    "suppressions": None,
                }
            ]
        }
        findings = adapter.normalize_gosec(data)
        assert findings[0].severity == "medium"

    def test_severity_mapping_low(self, adapter):
        data = {
            "Issues": [
                {
                    "severity": "LOW",
                    "confidence": "HIGH",
                    "cwe": {},
                    "rule_id": "G104",
                    "details": "errors unhandled",
                    "file": "main.go",
                    "line": "1",
                    "column": "1",
                    "nosec": False,
                    "suppressions": None,
                }
            ]
        }
        findings = adapter.normalize_gosec(data)
        assert findings[0].severity == "low"

    def test_unknown_rule_gets_custom_prefix(self, adapter):
        data = {
            "Issues": [
                {
                    "severity": "LOW",
                    "confidence": "LOW",
                    "cwe": {},
                    "rule_id": "G999",
                    "details": "unknown rule",
                    "file": "main.go",
                    "line": "1",
                    "column": "1",
                    "nosec": False,
                    "suppressions": None,
                }
            ]
        }
        findings = adapter.normalize_gosec(data)
        assert findings[0].canonical_rule_id.startswith("CUSTOM-GO-")

    def test_language_is_go(self, adapter):
        findings = adapter.normalize_gosec(SAMPLE_GOSEC)
        assert all(f.language == "go" for f in findings)

    def test_tool_raw_contains_gosec(self, adapter):
        findings = adapter.normalize_gosec(SAMPLE_GOSEC)
        assert all(f.tool_raw["tool_name"] == "gosec" for f in findings)

    def test_cwe_id_stored_in_tool_raw(self, adapter):
        findings = adapter.normalize_gosec(SAMPLE_GOSEC)
        cwe_ids = [f.tool_raw["cwe_id"] for f in findings]
        assert "78" in cwe_ids

    def test_empty_issues_returns_empty(self, adapter):
        assert adapter.normalize_gosec({"Issues": []}) == []

    def test_missing_issues_key_returns_empty(self, adapter):
        assert adapter.normalize_gosec({}) == []

    def test_line_number_parsed_as_int(self, adapter):
        findings = adapter.normalize_gosec(SAMPLE_GOSEC)
        assert all(isinstance(f.line, int) for f in findings)


# ── normalize_staticcheck ─────────────────────────────────────────────────────


class TestNormalizeStaticcheck:
    def test_returns_correct_count(self, adapter):
        findings = adapter.normalize_staticcheck(SAMPLE_STATICCHECK)
        assert len(findings) == 2

    def test_maps_sa1006_to_style_010(self, adapter):
        findings = adapter.normalize_staticcheck(SAMPLE_STATICCHECK)
        rules = [f.canonical_rule_id for f in findings]
        assert "STYLE-010" in rules

    def test_maps_u1000_to_dead_004(self, adapter):
        findings = adapter.normalize_staticcheck(SAMPLE_STATICCHECK)
        rules = [f.canonical_rule_id for f in findings]
        assert "DEAD-004" in rules

    def test_language_is_go(self, adapter):
        findings = adapter.normalize_staticcheck(SAMPLE_STATICCHECK)
        assert all(f.language == "go" for f in findings)

    def test_tool_raw_contains_staticcheck(self, adapter):
        findings = adapter.normalize_staticcheck(SAMPLE_STATICCHECK)
        assert all(f.tool_raw["tool_name"] == "staticcheck" for f in findings)

    def test_empty_list_returns_empty(self, adapter):
        assert adapter.normalize_staticcheck([]) == []

    def test_malformed_line_skipped(self, adapter):
        findings = adapter.normalize_staticcheck(["this is not valid output"])
        assert findings == []

    def test_unknown_rule_gets_custom_prefix(self, adapter):
        findings = adapter.normalize_staticcheck(["main.go:1:1: some weird check (ZZ999)"])
        assert findings[0].canonical_rule_id.startswith("CUSTOM-GO-")

    def test_line_number_parsed_as_int(self, adapter):
        findings = adapter.normalize_staticcheck(SAMPLE_STATICCHECK)
        assert all(isinstance(f.line, int) for f in findings)

    def test_message_extracted_correctly(self, adapter):
        findings = adapter.normalize_staticcheck(["main.go:17:6: func hashIt is unused (U1000)"])
        assert "hashIt" in findings[0].message


# ── get_all_findings deduplication ────────────────────────────────────────────


class TestGetAllFindings:
    def test_combines_gosec_and_staticcheck(self, adapter):
        results = {"gosec": SAMPLE_GOSEC, "staticcheck": SAMPLE_STATICCHECK, "semgrep": {"results": []}}
        findings = adapter.get_all_findings(results)
        assert len(findings) == 5

    def test_deduplicates_same_file_line_rule(self, adapter):
        duplicate_gosec = {
            "Issues": [
                SAMPLE_GOSEC["Issues"][0],
                SAMPLE_GOSEC["Issues"][0],  # exact duplicate
            ]
        }
        results = {"gosec": duplicate_gosec, "staticcheck": [], "semgrep": {"results": []}}
        findings = adapter.get_all_findings(results)
        assert len(findings) == 1

    def test_empty_results_returns_empty(self, adapter):
        results = {"gosec": None, "staticcheck": [], "semgrep": {"results": []}}
        assert adapter.get_all_findings(results) == []

    def test_only_staticcheck_results(self, adapter):
        results = {"gosec": None, "staticcheck": SAMPLE_STATICCHECK, "semgrep": {"results": []}}
        findings = adapter.get_all_findings(results)
        assert len(findings) == 2

    def test_only_gosec_results(self, adapter):
        results = {"gosec": SAMPLE_GOSEC, "staticcheck": [], "semgrep": {"results": []}}
        findings = adapter.get_all_findings(results)
        assert len(findings) == 3


# ── _infer_category ───────────────────────────────────────────────────────────


class TestInferCategory:
    @pytest.mark.parametrize(
        "rule_id,expected",
        [
            ("SECURITY-030", "security"),
            ("HARDCODE-001", "security"),
            ("CUSTOM-GO-G999", "security"),
            ("VAR-001", "dead-code"),
            ("DEAD-004", "dead-code"),
            ("STYLE-010", "style"),
            ("UNKNOWN-999", "best-practice"),
        ],
    )
    def test_category_mapping(self, rule_id, expected):
        assert GoAdapter._infer_category(rule_id) == expected


# ── Rule registry completeness ────────────────────────────────────────────────


class TestRuleRegistry:
    def test_gosec_rules_map_to_canonical(self):
        for gosec_id, canonical in GOSEC_RULE_MAPPING.items():
            assert gosec_id.startswith("G"), f"{gosec_id} should start with G"
            assert "-" in canonical, f"{canonical} should contain hyphen"

    def test_staticcheck_rules_map_to_canonical(self):
        for sc_id, canonical in STATICCHECK_RULE_MAPPING.items():
            assert "-" in canonical, f"{canonical} should contain hyphen"

    def test_key_go_rules_present(self):
        assert "G204" in GOSEC_RULE_MAPPING  # command injection
        assert "G401" in GOSEC_RULE_MAPPING  # weak crypto
        assert "G104" in GOSEC_RULE_MAPPING  # unhandled errors
        assert "G201" in GOSEC_RULE_MAPPING  # SQL injection

    def test_key_staticcheck_rules_present(self):
        assert "U1000" in STATICCHECK_RULE_MAPPING  # unused code
        assert "SA1006" in STATICCHECK_RULE_MAPPING  # printf format
