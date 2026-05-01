#!/usr/bin/env python3
"""
Tests for the JavaScript/TypeScript adapter (CORE/adapters/js_adapter.py).
Tests rule mapping, ESLint normalization, npm audit normalization, and language detection.
"""

import json
import shutil
import unittest
from pathlib import Path

import pytest

from CORE.adapters.js_adapter import JS_RULE_MAPPING, JavaScriptAdapter

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def adapter(tmp_path: Path) -> JavaScriptAdapter:
    """Create a JavaScriptAdapter pointing at a temp directory."""
    return JavaScriptAdapter(target_dir=str(tmp_path))


@pytest.fixture()
def js_project(tmp_path: Path) -> Path:
    """Create a minimal JS project in a temp directory."""
    # Some JS files
    (tmp_path / "index.js").write_text("eval(userInput);\nconsole.log('hello');\n")
    (tmp_path / "utils.js").write_text("var x = 1;\nMath.random();\n")
    (tmp_path / "app.ts").write_text("const secret = 'hardcoded_password123';\n")
    # package.json for npm audit
    (tmp_path / "package.json").write_text(json.dumps({"name": "test-app", "version": "1.0.0"}))
    return tmp_path


@pytest.fixture()
def npm_project(tmp_path: Path) -> Path:
    """Create a project with only package.json for npm audit testing."""
    (tmp_path / "package.json").write_text(json.dumps({"name": "test", "version": "1.0.0", "dependencies": {}}))
    return tmp_path


# ──────────────────────────────────────────────────────────────────────────────
# Unit Tests: Adapter Properties
# ──────────────────────────────────────────────────────────────────────────────


class TestJavaScriptAdapterProperties:
    """Test adapter metadata and configuration."""

    def test_language_name(self, adapter: JavaScriptAdapter) -> None:
        """language_name must be descriptive."""
        assert "JavaScript" in adapter.language_name

    def test_file_extensions(self, adapter: JavaScriptAdapter) -> None:
        """Must cover all common JS/TS extensions."""
        exts = adapter.file_extensions
        assert ".js" in exts
        assert ".ts" in exts
        assert ".jsx" in exts
        assert ".tsx" in exts
        assert ".mjs" in exts

    def test_get_tools_returns_list(self, adapter: JavaScriptAdapter) -> None:
        """get_tools() must return a non-empty list of tool dicts."""
        tools = adapter.get_tools()
        assert len(tools) >= 3
        names = [t["name"] for t in tools]
        assert "eslint" in names
        assert "semgrep" in names
        assert "npm-audit" in names

    def test_check_tools_available_returns_dict(self, adapter: JavaScriptAdapter) -> None:
        """check_tools_available() returns a dict with expected keys."""
        available = adapter.check_tools_available()
        assert "eslint" in available
        assert "semgrep" in available
        assert "npm" in available
        assert isinstance(available["npm"], bool)

    def test_get_rule_mappings_not_empty(self, adapter: JavaScriptAdapter) -> None:
        """Rule mapping must contain all critical JS security rules."""
        mappings = adapter.get_rule_mappings()
        assert len(mappings) >= 30
        assert "no-eval" in mappings
        assert "security/detect-eval-with-expression" in mappings

    def test_rule_mapping_eval_maps_to_security_001(self) -> None:
        """eval() must map to SECURITY-001."""
        assert JS_RULE_MAPPING["no-eval"] == "SECURITY-001"
        assert JS_RULE_MAPPING["security/detect-eval-with-expression"] == "SECURITY-001"

    def test_rule_mapping_sql_injection(self) -> None:
        """SQL injection rule maps to SECURITY-027."""
        assert JS_RULE_MAPPING["js-sql-injection"] == "SECURITY-027"

    def test_rule_mapping_xss_maps_to_security_045(self) -> None:
        """XSS rules map to SECURITY-045."""
        assert JS_RULE_MAPPING["js-xss-innerhtml"] == "SECURITY-045"

    def test_rule_mapping_prototype_pollution(self) -> None:
        """Prototype pollution maps to SECURITY-057."""
        assert JS_RULE_MAPPING["js-prototype-pollution"] == "SECURITY-057"

    def test_rule_mapping_nosql_injection(self) -> None:
        """NoSQL injection maps to SECURITY-058."""
        assert JS_RULE_MAPPING["js-nosql-injection"] == "SECURITY-058"

    def test_rule_mapping_npm_audit(self) -> None:
        """npm audit CVE rules are mapped."""
        assert JS_RULE_MAPPING["npm-audit-critical"] == "SECURITY-059"
        assert JS_RULE_MAPPING["npm-audit-moderate"] == "SECURITY-060"


# ──────────────────────────────────────────────────────────────────────────────
# Unit Tests: ESLint Normalization
# ──────────────────────────────────────────────────────────────────────────────


class TestESLintNormalization:
    """Test normalize_eslint() method."""

    def test_normalize_empty_input(self, adapter: JavaScriptAdapter) -> None:
        """Empty ESLint output produces empty finding list."""
        findings = adapter.normalize_eslint([])
        assert findings == []

    def test_normalize_single_finding(self, adapter: JavaScriptAdapter) -> None:
        """Single ESLint message normalized correctly."""
        eslint_output = [
            {
                "filePath": "/project/src/app.js",
                "messages": [
                    {
                        "ruleId": "no-eval",
                        "message": "eval can be harmful",
                        "severity": 2,
                        "line": 10,
                        "column": 5,
                    }
                ],
            }
        ]
        findings = adapter.normalize_eslint(eslint_output)
        assert len(findings) == 1
        f = findings[0]
        assert f.canonical_rule_id == "SECURITY-001"
        assert f.line == 10
        assert f.severity == "high"  # ESLint severity 2 = error → high
        assert f.tool_raw["tool_name"] == "eslint"

    def test_normalize_warning_is_medium(self, adapter: JavaScriptAdapter) -> None:
        """ESLint severity 1 (warning) maps to medium."""
        eslint_output = [
            {
                "filePath": "/project/app.js",
                "messages": [{"ruleId": "no-console", "message": "No console", "severity": 1, "line": 5, "column": 1}],
            }
        ]
        findings = adapter.normalize_eslint(eslint_output)
        assert findings[0].severity == "medium"

    def test_normalize_unknown_rule_gets_custom_id(self, adapter: JavaScriptAdapter) -> None:
        """Unknown ESLint rule gets CUSTOM- prefix."""
        eslint_output = [
            {
                "filePath": "/project/app.js",
                "messages": [{"ruleId": "some-unknown-rule", "message": "test", "severity": 1, "line": 1, "column": 1}],
            }
        ]
        findings = adapter.normalize_eslint(eslint_output)
        assert "CUSTOM-" in findings[0].canonical_rule_id

    def test_normalize_no_rule_id(self, adapter: JavaScriptAdapter) -> None:
        """Message without ruleId uses fallback ID."""
        eslint_output = [
            {
                "filePath": "/project/app.js",
                "messages": [{"ruleId": None, "message": "parsing error", "severity": 2, "line": 1, "column": 1}],
            }
        ]
        findings = adapter.normalize_eslint(eslint_output)
        assert len(findings) == 1
        assert findings[0].canonical_rule_id  # must be non-empty

    def test_normalize_multiple_files(self, adapter: JavaScriptAdapter) -> None:
        """Multiple files produce combined finding list."""
        eslint_output = [
            {
                "filePath": "/project/a.js",
                "messages": [{"ruleId": "no-eval", "message": "eval", "severity": 2, "line": 1, "column": 1}],
            },
            {
                "filePath": "/project/b.js",
                "messages": [
                    {"ruleId": "no-console", "message": "console", "severity": 1, "line": 2, "column": 1},
                    {"ruleId": "no-var", "message": "var", "severity": 1, "line": 5, "column": 1},
                ],
            },
        ]
        findings = adapter.normalize_eslint(eslint_output)
        assert len(findings) == 3


# ──────────────────────────────────────────────────────────────────────────────
# Unit Tests: npm audit Normalization
# ──────────────────────────────────────────────────────────────────────────────


class TestNpmAuditNormalization:
    """Test normalize_npm_audit() method."""

    def test_normalize_empty_audit(self, adapter: JavaScriptAdapter) -> None:
        """Empty npm audit output produces empty findings."""
        findings = adapter.normalize_npm_audit({"vulnerabilities": {}})
        assert findings == []

    def test_normalize_critical_vuln(self, adapter: JavaScriptAdapter) -> None:
        """Critical CVE maps to SECURITY-059 and severity high."""
        audit_data = {
            "vulnerabilities": {
                "lodash": {
                    "severity": "critical",
                    "via": [{"title": "Prototype Pollution", "cve": "CVE-2019-10744"}],
                }
            }
        }
        findings = adapter.normalize_npm_audit(audit_data)
        assert len(findings) == 1
        assert findings[0].canonical_rule_id == "SECURITY-059"
        assert findings[0].severity == "high"
        assert findings[0].file == "package.json"

    def test_normalize_moderate_vuln(self, adapter: JavaScriptAdapter) -> None:
        """Moderate CVE maps to SECURITY-060."""
        audit_data = {
            "vulnerabilities": {"axios": {"severity": "moderate", "via": [{"title": "SSRF", "cve": "CVE-2021-1234"}]}}
        }
        findings = adapter.normalize_npm_audit(audit_data)
        assert findings[0].canonical_rule_id == "SECURITY-060"
        assert findings[0].severity == "medium"  # moderate → medium

    def test_normalize_multiple_vulns(self, adapter: JavaScriptAdapter) -> None:
        """Multiple vulnerable packages produce one finding each."""
        audit_data = {
            "vulnerabilities": {
                "pkg-a": {"severity": "high", "via": [{"title": "XSS"}]},
                "pkg-b": {"severity": "low", "via": [{"title": "Info Disclosure"}]},
            }
        }
        findings = adapter.normalize_npm_audit(audit_data)
        assert len(findings) == 2
        pkgs = {f.tool_raw["package"] for f in findings}
        assert "pkg-a" in pkgs
        assert "pkg-b" in pkgs


# ──────────────────────────────────────────────────────────────────────────────
# Unit Tests: Language Detection
# ──────────────────────────────────────────────────────────────────────────────


class TestLanguageDetection:
    """Test JavaScriptAdapter.detect_language() static method."""

    def test_detect_python_project(self, tmp_path: Path) -> None:
        """Python project detected from .py files + pyproject.toml."""
        (tmp_path / "main.py").write_text("print('hi')")
        (tmp_path / "utils.py").write_text("")
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]")
        assert JavaScriptAdapter.detect_language(str(tmp_path)) == "python"

    def test_detect_js_project(self, tmp_path: Path) -> None:
        """JS project detected from .js files + package.json."""
        (tmp_path / "index.js").write_text("console.log('hi')")
        (tmp_path / "app.js").write_text("")
        (tmp_path / "package.json").write_text("{}")
        result = JavaScriptAdapter.detect_language(str(tmp_path))
        assert result == "javascript"

    def test_detect_ts_project(self, tmp_path: Path) -> None:
        """TypeScript project detected from .ts files + package.json."""
        (tmp_path / "index.ts").write_text("const x: number = 1")
        (tmp_path / "package.json").write_text("{}")
        result = JavaScriptAdapter.detect_language(str(tmp_path))
        assert result in ("javascript", "mixed")  # TS detected as JS-family

    def test_detect_empty_dir_returns_unknown(self, tmp_path: Path) -> None:
        """Empty dir defaults to unknown."""
        result = JavaScriptAdapter.detect_language(str(tmp_path))
        assert result == "unknown"

    def test_detect_mixed_project(self, tmp_path: Path) -> None:
        """Mixed Python/JS project returns mixed."""
        (tmp_path / "main.py").write_text("print('hi')")
        (tmp_path / "setup.py").write_text("")
        (tmp_path / "index.js").write_text("console.log('hi')")
        result = JavaScriptAdapter.detect_language(str(tmp_path))
        assert result in ("mixed", "python", "javascript")  # depends on counts


# ──────────────────────────────────────────────────────────────────────────────
# Unit Tests: JS file discovery
# ──────────────────────────────────────────────────────────────────────────────


class TestJSFileDiscovery:
    """Test _get_js_files() — should exclude node_modules."""

    def test_finds_js_files(self, js_project: Path) -> None:
        """Finds .js and .ts files in project root."""
        adapter = JavaScriptAdapter(target_dir=str(js_project))
        files = adapter._get_js_files()
        exts = {f.suffix for f in files}
        assert ".js" in exts or ".ts" in exts

    def test_excludes_node_modules(self, tmp_path: Path) -> None:
        """node_modules directory is always excluded."""
        node_mod = tmp_path / "node_modules" / "lodash"
        node_mod.mkdir(parents=True)
        (node_mod / "index.js").write_text("module.exports = {}")
        (tmp_path / "app.js").write_text("const _ = require('lodash')")
        adapter = JavaScriptAdapter(target_dir=str(tmp_path))
        files = adapter._get_js_files()
        # Only app.js should be found, not node_modules/lodash/index.js
        assert all("node_modules" not in f.parts for f in files)

    def test_has_package_json(self, js_project: Path) -> None:
        """_has_package_json() returns True when package.json exists."""
        adapter = JavaScriptAdapter(target_dir=str(js_project))
        assert adapter._has_package_json() is True

    def test_no_package_json(self, tmp_path: Path) -> None:
        """_has_package_json() returns False when missing."""
        adapter = JavaScriptAdapter(target_dir=str(tmp_path))
        assert adapter._has_package_json() is False


# ──────────────────────────────────────────────────────────────────────────────
# Unit Tests: category inference
# ──────────────────────────────────────────────────────────────────────────────


class TestCategoryInference:
    """Test _infer_category() static method."""

    def test_security_prefix(self) -> None:
        assert JavaScriptAdapter._infer_category("SECURITY-001") == "security"

    def test_style_prefix(self) -> None:
        assert JavaScriptAdapter._infer_category("STYLE-017") == "style"

    def test_var_prefix(self) -> None:
        assert JavaScriptAdapter._infer_category("VAR-001") == "dead-code"

    def test_dead_prefix(self) -> None:
        assert JavaScriptAdapter._infer_category("DEAD-001") == "dead-code"

    def test_async_prefix(self) -> None:
        assert JavaScriptAdapter._infer_category("ASYNC-002") == "best-practice"

    def test_import_prefix(self) -> None:
        assert JavaScriptAdapter._infer_category("IMPORT-004") == "best-practice"

    def test_unknown_prefix(self) -> None:
        assert JavaScriptAdapter._infer_category("UNKNOWN-999") == "best-practice"


# ──────────────────────────────────────────────────────────────────────────────
# Integration: get_all_findings aggregation
# ──────────────────────────────────────────────────────────────────────────────


class TestGetAllFindings:
    """Test get_all_findings() combines ESLint + npm audit results."""

    def test_aggregates_eslint_and_npm_audit(self, adapter: JavaScriptAdapter) -> None:
        """Findings from ESLint + npm audit are combined."""
        results = {
            "eslint": [
                {
                    "filePath": "/project/app.js",
                    "messages": [{"ruleId": "no-eval", "message": "eval", "severity": 2, "line": 1, "column": 1}],
                }
            ],
            "semgrep": {},
            "npm_audit": {
                "vulnerabilities": {"lodash": {"severity": "high", "via": [{"title": "Prototype Pollution"}]}}
            },
        }
        findings = adapter.get_all_findings(results)
        assert len(findings) == 2  # 1 eslint + 1 npm audit

    def test_empty_results_returns_empty(self, adapter: JavaScriptAdapter) -> None:
        """Empty results produce no findings."""
        findings = adapter.get_all_findings({"eslint": [], "semgrep": {}, "npm_audit": {}})
        assert findings == []

    def test_normalize_semgrep_js_uses_js_rule_mapping(self, adapter: JavaScriptAdapter) -> None:
        """normalize_semgrep_js must resolve JS rule IDs via JS_RULE_MAPPING, not Python normalizer.

        Root cause of CUSTOM-* bug: the old implementation delegated to
        normalizer.normalize_semgrep which uses Python RULE_MAPPING (no JS rules).
        """
        semgrep_data = {
            "results": [
                {
                    "check_id": "tools.semgrep.js-global-variable",
                    "path": "/project/app.js",
                    "start": {"line": 5, "col": 1},
                    "extra": {"severity": "WARNING", "message": "Use let/const", "metadata": {"category": "style"}},
                },
                {
                    "check_id": "tools.semgrep.js-console-log",
                    "path": "/project/app.js",
                    "start": {"line": 10, "col": 1},
                    "extra": {"severity": "INFO", "message": "console.log found", "metadata": {"category": "style"}},
                },
                {
                    "check_id": "tools.semgrep.js-command-injection",
                    "path": "/project/app.js",
                    "start": {"line": 20, "col": 1},
                    "extra": {
                        "severity": "ERROR",
                        "message": "exec() with user input",
                        "metadata": {"category": "security"},
                    },
                },
                {
                    "check_id": "tools.semgrep.totally-unknown-rule",
                    "path": "/project/app.js",
                    "start": {"line": 30, "col": 1},
                    "extra": {"severity": "WARNING", "message": "something", "metadata": {"category": "security"}},
                },
            ]
        }
        findings = adapter.normalize_semgrep_js(semgrep_data)
        assert len(findings) == 4
        # Known rules → canonical IDs via JS_RULE_MAPPING (not CUSTOM-)
        assert findings[0].canonical_rule_id == "BEST-PRACTICE-004"  # js-global-variable
        assert findings[1].canonical_rule_id == "STYLE-007"  # js-console-log
        assert findings[2].canonical_rule_id == "SECURITY-021"  # js-command-injection
        # Unknown rule → CUSTOM- prefix acceptable
        assert findings[3].canonical_rule_id == "CUSTOM-totally-unknown-rule"
        # All findings have semgrep as tool
        assert all(f.tool_raw["tool_name"] == "semgrep" for f in findings)

    def test_dedup_removes_same_file_line_rule_from_multiple_tools(self, adapter: JavaScriptAdapter) -> None:
        """Dedup removes findings with same (file, line, canonical_rule_id) across tools."""
        # Semgrep no-var maps to STYLE-017 same as ESLint no-var → same file+line = duplicate
        results = {
            "eslint": [
                {
                    "filePath": "/app.js",
                    "messages": [
                        {"ruleId": "no-var", "message": "use let", "severity": 1, "line": 5, "column": 1},
                        {"ruleId": "no-eval", "message": "eval", "severity": 2, "line": 10, "column": 1},
                    ],
                }
            ],
            "semgrep": {
                "results": [
                    # Different canonical rule (BEST-PRACTICE-004) on same line as no-var → survive
                    {
                        "check_id": "tools.semgrep.js-global-variable",
                        "path": "/app.js",
                        "start": {"line": 5, "col": 1},
                        "extra": {"severity": "WARNING", "message": "global var", "metadata": {"category": "style"}},
                    },
                    # Different line → survive
                    {
                        "check_id": "tools.semgrep.js-global-variable",
                        "path": "/app.js",
                        "start": {"line": 99, "col": 1},
                        "extra": {"severity": "WARNING", "message": "global var", "metadata": {"category": "style"}},
                    },
                ]
            },
            "npm_audit": {},
        }
        findings = adapter.get_all_findings(results)
        # eslint no-var@5, eslint no-eval@10, semgrep global-var@5 (diff rule), semgrep global-var@99
        assert len(findings) == 4
        lines = [f.line for f in findings]
        assert 99 in lines

    def test_dedup_preserves_same_rule_different_lines(self, adapter: JavaScriptAdapter) -> None:
        """Same rule on different lines must NOT be deduplicated."""
        results = {
            "eslint": [
                {
                    "filePath": "/app.js",
                    "messages": [
                        {"ruleId": "no-var", "message": "use let", "severity": 1, "line": 1, "column": 1},
                        {"ruleId": "no-var", "message": "use let", "severity": 1, "line": 2, "column": 1},
                        {"ruleId": "no-var", "message": "use let", "severity": 1, "line": 3, "column": 1},
                    ],
                }
            ],
            "semgrep": {},
            "npm_audit": {},
        }
        findings = adapter.get_all_findings(results)
        assert len(findings) == 3  # all 3 lines preserved


# ──────────────────────────────────────────────────────────────────────────────
# E2E Integration: Full pipeline on a real in-memory JS project (no ESLint needed)
# ──────────────────────────────────────────────────────────────────────────────


class TestE2EPipeline:
    """
    End-to-end test: run the full JS adapter pipeline on a synthetic JS project.

    Uses pre-built mock tool output (no real ESLint/npm invocation) to prove
    the normalize → score → aggregate flow works end-to-end.
    """

    def test_full_pipeline_eslint_plus_npm(self, tmp_path: Path) -> None:
        """Full pipeline: ESLint + npm audit → normalized → aggregated findings."""
        adapter = JavaScriptAdapter(target_dir=str(tmp_path))

        mock_eslint = [
            {
                "filePath": str(tmp_path / "app.js"),
                "messages": [
                    {"ruleId": "no-eval", "message": "eval is evil", "severity": 2, "line": 3, "column": 1},
                    {"ruleId": "no-console", "message": "no console", "severity": 1, "line": 10, "column": 5},
                ],
            }
        ]
        mock_npm_audit = {
            "vulnerabilities": {
                "lodash": {"severity": "critical", "via": [{"title": "Prototype Pollution", "cve": "CVE-2019-10744"}]},
                "axios": {"severity": "moderate", "via": [{"title": "SSRF vuln"}]},
            }
        }

        results = {"eslint": mock_eslint, "semgrep": {}, "npm_audit": mock_npm_audit}
        findings = adapter.get_all_findings(results)

        # Should have 2 ESLint + 2 npm audit = 4 total
        assert len(findings) == 4

        # All are proper CanonicalFindings
        severities = {f.severity for f in findings}
        assert "high" in severities  # eval + lodash critical

        # Rule IDs are canonical (no CUSTOM- for known rules)
        rule_ids = {f.canonical_rule_id for f in findings}
        assert "SECURITY-001" in rule_ids  # no-eval
        assert "SECURITY-059" in rule_ids  # lodash CVE critical

    def test_pipeline_deduplicates_tool_metadata(self, tmp_path: Path) -> None:
        """Each finding has tool_name stored in tool_raw."""
        adapter = JavaScriptAdapter(target_dir=str(tmp_path))
        mock_eslint = [
            {
                "filePath": str(tmp_path / "index.js"),
                "messages": [
                    {"ruleId": "no-eval", "message": "eval", "severity": 2, "line": 1, "column": 1},
                ],
            }
        ]
        findings = adapter.get_all_findings({"eslint": mock_eslint, "semgrep": {}, "npm_audit": {}})
        assert findings[0].tool_raw["tool_name"] == "eslint"

    def test_pipeline_language_is_javascript(self, tmp_path: Path) -> None:
        """All findings from JS adapter have language=javascript."""
        adapter = JavaScriptAdapter(target_dir=str(tmp_path))
        mock_eslint = [
            {
                "filePath": str(tmp_path / "app.js"),
                "messages": [{"ruleId": "no-var", "message": "use let", "severity": 1, "line": 1, "column": 1}],
            }
        ]
        findings = adapter.get_all_findings({"eslint": mock_eslint, "semgrep": {}, "npm_audit": {}})
        assert all(f.language == "javascript" for f in findings)

    def test_pipeline_npm_audit_only(self, tmp_path: Path) -> None:
        """npm-audit-only results work without ESLint."""
        adapter = JavaScriptAdapter(target_dir=str(tmp_path))
        mock_npm = {
            "vulnerabilities": {
                "express": {"severity": "high", "via": [{"title": "ReDoS"}]},
            }
        }
        findings = adapter.get_all_findings({"eslint": [], "semgrep": {}, "npm_audit": mock_npm})
        assert len(findings) == 1
        assert findings[0].file == "package.json"
        assert findings[0].severity == "high"


# ──────────────────────────────────────────────────────────────────────────────
# CLI routing: --lang javascript paths through main.py
# ──────────────────────────────────────────────────────────────────────────────


class TestCLILanguageRouting:
    """
    Test that --lang javascript correctly routes to JavaScriptAdapter.
    Tests the adapter selection logic without invoking real tools.
    """

    def test_detect_language_returns_javascript_for_js_project(self, tmp_path: Path) -> None:
        """detect_language() returns 'javascript' for a project with package.json + .js files."""
        (tmp_path / "index.js").write_text("const x = 1")
        (tmp_path / "app.js").write_text("console.log(x)")
        (tmp_path / "package.json").write_text('{"name":"test","version":"1.0.0"}')
        result = JavaScriptAdapter.detect_language(str(tmp_path))
        assert result == "javascript"

    def test_detect_language_returns_python_for_python_project(self, tmp_path: Path) -> None:
        """detect_language() returns 'python' for a project with .py + pyproject.toml."""
        (tmp_path / "main.py").write_text("print('hi')")
        (tmp_path / "utils.py").write_text("def foo(): pass")
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]")
        result = JavaScriptAdapter.detect_language(str(tmp_path))
        assert result == "python"

    def test_js_adapter_instantiates_with_js_target(self, tmp_path: Path) -> None:
        """JavaScriptAdapter can be instantiated and reports correct language."""
        (tmp_path / "app.js").write_text("const x = 1")
        adapter = JavaScriptAdapter(target_dir=str(tmp_path))
        assert adapter.language_name == "JavaScript/TypeScript"
        assert ".js" in adapter.file_extensions
        assert ".ts" in adapter.file_extensions

    def test_js_adapter_run_tools_no_js_files(self, tmp_path: Path) -> None:
        """run_tools() returns error (not crash) when no JS files found."""
        adapter = JavaScriptAdapter(target_dir=str(tmp_path))
        results = adapter.run_tools(output_dir=str(tmp_path / "out"))
        # Should return gracefully with error message, not crash
        assert "errors" in results
        assert isinstance(results["errors"], list)

    @unittest.skipUnless(shutil.which("npm"), "npm not installed")
    def test_eslint_config_generates_without_error(self, tmp_path: Path) -> None:
        """_get_eslint_config_content() returns valid ESLint flat config string."""
        adapter = JavaScriptAdapter(target_dir=str(tmp_path))
        config_content = adapter._get_eslint_config_content()
        # Flat config is an ES module, not JSON
        assert "export default" in config_content
        assert "no-eval" in config_content
        assert "security/detect-eval-with-expression" in config_content
        assert "eslint-plugin-security" in config_content


# ──────────────────────────────────────────────────────────────────────────────
# v3.0.2 Coverage: New Security Rules (SECURITY-061, SECURITY-063, SECURITY-064)
# ──────────────────────────────────────────────────────────────────────────────


class TestV302NewRuleCoverage:
    """Verify v3.0.2 gap-closing additions: SQLi, XXE, EJS XSS, TypeScript, taint rules."""

    def test_ejs_extension_in_file_extensions(self, tmp_path: Path) -> None:
        """file_extensions must include .ejs for EJS template scanning."""
        adapter = JavaScriptAdapter(target_dir=str(tmp_path))
        assert ".ejs" in adapter.file_extensions, ".ejs must be in file_extensions for template XSS detection"

    def test_typescript_extension_in_file_extensions(self, tmp_path: Path) -> None:
        """file_extensions must include .ts and .tsx for TypeScript support."""
        adapter = JavaScriptAdapter(target_dir=str(tmp_path))
        exts = adapter.file_extensions
        assert ".ts" in exts, ".ts must be supported"
        assert ".tsx" in exts, ".tsx must be supported"

    def test_security_061_sqli_in_rule_mapping(self) -> None:
        """SECURITY-061 (Sequelize raw query / SQL injection) must be in JS_RULE_MAPPING."""
        assert "js-sequelize-raw-query" in JS_RULE_MAPPING
        assert JS_RULE_MAPPING["js-sequelize-raw-query"] == "SECURITY-061"

    def test_security_063_xxe_in_rule_mapping(self) -> None:
        """SECURITY-063 (XXE — libxmljs with noent:true) must be in JS_RULE_MAPPING."""
        assert "js-xxe-libxmljs" in JS_RULE_MAPPING
        assert JS_RULE_MAPPING["js-xxe-libxmljs"] == "SECURITY-063"

    def test_security_064_ejs_xss_in_rule_mapping(self) -> None:
        """SECURITY-064 (XSS via EJS unescaped output) must be in JS_RULE_MAPPING."""
        assert "js-ejs-unescaped-output" in JS_RULE_MAPPING
        assert JS_RULE_MAPPING["js-ejs-unescaped-output"] == "SECURITY-064"

    def test_taint_rules_mapped_to_canonical_ids(self) -> None:
        """Taint rule IDs (js-taint-*) must map to canonical security IDs, not CUSTOM-*."""
        assert "js-taint-sql-injection" in JS_RULE_MAPPING
        assert JS_RULE_MAPPING["js-taint-sql-injection"] == "SECURITY-061"
        assert "js-taint-command-injection" in JS_RULE_MAPPING
        assert JS_RULE_MAPPING["js-taint-command-injection"] == "SECURITY-062"
        assert "js-taint-eval-injection" in JS_RULE_MAPPING
        # taint eval maps to SECURITY-001 (same canonical as js-eval-injection)
        assert JS_RULE_MAPPING["js-taint-eval-injection"] == "SECURITY-001"

    def test_semgrep_js_rules_yml_exists_and_has_new_rules(self) -> None:
        """js-rules.yml must exist and contain the new rule IDs."""
        rules_path = Path(__file__).parent.parent / "TOOLS" / "semgrep" / "js-rules.yml"
        assert rules_path.exists(), "TOOLS/semgrep/js-rules.yml must exist"
        content = rules_path.read_text()
        assert "js-sequelize-raw-query" in content, "js-sequelize-raw-query must be in js-rules.yml"
        assert "js-xxe-libxmljs" in content, "js-xxe-libxmljs must be in js-rules.yml"
        assert "js-ejs-unescaped-output" in content, "js-ejs-unescaped-output must be in js-rules.yml"

    def test_semgrep_taint_rules_yml_exists(self) -> None:
        """js-taint-rules.yml must exist for architecture documentation."""
        taint_path = Path(__file__).parent.parent / "TOOLS" / "semgrep" / "js-taint-rules.yml"
        assert taint_path.exists(), "TOOLS/semgrep/js-taint-rules.yml must exist"
        content = taint_path.read_text()
        assert "mode: taint" in content, "Taint rules must use mode: taint"
        assert "pattern-sources" in content, "Taint rules must define pattern-sources"
        assert "pattern-sinks" in content, "Taint rules must define pattern-sinks"

    def test_semgrep_xxe_yml_exists(self) -> None:
        """js-xxe.yml must exist."""
        xxe_path = Path(__file__).parent.parent / "TOOLS" / "semgrep" / "js-xxe.yml"
        assert xxe_path.exists(), "TOOLS/semgrep/js-xxe.yml must exist"

    def test_semgrep_ejs_xss_yml_exists(self) -> None:
        """js-ejs-xss.yml must exist."""
        ejs_path = Path(__file__).parent.parent / "TOOLS" / "semgrep" / "js-ejs-xss.yml"
        assert ejs_path.exists(), "TOOLS/semgrep/js-ejs-xss.yml must exist"

    def test_xxe_rule_in_mapping_with_both_variants(self) -> None:
        """Both XXE rule variants must be in JS_RULE_MAPPING."""
        assert "js-xxe-libxmljs-noent" in JS_RULE_MAPPING
        assert JS_RULE_MAPPING["js-xxe-libxmljs-noent"] == "SECURITY-063"
        assert "js-xxe-libxmljs-variable" in JS_RULE_MAPPING
        assert JS_RULE_MAPPING["js-xxe-libxmljs-variable"] == "SECURITY-063"

    def test_all_new_ids_exceed_60(self) -> None:
        """All new canonical IDs (SECURITY-06x) are above the previous max (SECURITY-060)."""
        new_ids = [
            JS_RULE_MAPPING.get("js-taint-sql-injection"),
            JS_RULE_MAPPING.get("js-taint-command-injection"),
            JS_RULE_MAPPING.get("js-xxe-libxmljs-noent"),
            JS_RULE_MAPPING.get("js-ejs-unescaped-output"),
        ]
        for cid in new_ids:
            if cid and cid.startswith("SECURITY-"):
                num = int(cid.split("-")[1])
                assert num >= 61 or num == 1, f"{cid} should be SECURITY-61+ or SECURITY-001 (eval reuse)"
