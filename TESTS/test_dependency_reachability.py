"""Tests for CORE/engines/dependency_reachability.py — Feature 8"""

from __future__ import annotations

import json

from CORE.engines.dependency_reachability import (
    DependencyReachabilityChecker,
    ReachabilityResult,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _result(level="DIRECT", penalty=0, imports=None, in_pkg=True, in_dev=False):
    return ReachabilityResult(
        package_name="lodash",
        level=level,
        confidence_penalty=penalty,
        direct_imports=imports or ["src/app.js"],
        in_package_json=in_pkg,
        in_dev_dependencies=in_dev,
    )


def _make_project(tmp_path, pkg_json=None, js_files=None):
    """Create a minimal JS project in tmp_path."""
    if pkg_json is not None:
        (tmp_path / "package.json").write_text(json.dumps(pkg_json))
    for filename, content in (js_files or {}).items():
        p = tmp_path / filename
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return DependencyReachabilityChecker(str(tmp_path))


# ── ReachabilityResult ────────────────────────────────────────────────────────


class TestReachabilityResult:
    def test_is_reachable_direct(self):
        assert _result(level="DIRECT").is_reachable is True

    def test_is_reachable_transitive(self):
        assert _result(level="TRANSITIVE").is_reachable is False

    def test_is_reachable_unknown(self):
        assert _result(level="UNKNOWN").is_reachable is False

    def test_to_dict_keys(self):
        d = _result().to_dict()
        for key in [
            "reachability_level",
            "reachability_penalty",
            "reachability_direct_imports",
            "reachability_in_package_json",
            "reachability_in_dev_deps",
            "reachability_is_direct",
        ]:
            assert key in d

    def test_to_dict_values(self):
        r = _result(level="TRANSITIVE", penalty=-15, in_pkg=True, in_dev=False)
        d = r.to_dict()
        assert d["reachability_level"] == "TRANSITIVE"
        assert d["reachability_penalty"] == -15
        assert d["reachability_in_package_json"] is True
        assert d["reachability_in_dev_deps"] is False

    def test_to_dict_is_direct_false(self):
        d = _result(level="TRANSITIVE").to_dict()
        assert d["reachability_is_direct"] is False


# ── _normalise_pkg_name ───────────────────────────────────────────────────────


class TestNormalisePkgName:
    def test_simple_package(self):
        assert DependencyReachabilityChecker._normalise_pkg_name("lodash") == "lodash"

    def test_subpath_stripped(self):
        assert DependencyReachabilityChecker._normalise_pkg_name("lodash/merge") == "lodash"

    def test_scoped_package(self):
        assert DependencyReachabilityChecker._normalise_pkg_name("@org/pkg") == "@org/pkg"

    def test_scoped_package_with_subpath(self):
        assert DependencyReachabilityChecker._normalise_pkg_name("@org/pkg/utils") == "@org/pkg"

    def test_strips_whitespace(self):
        assert DependencyReachabilityChecker._normalise_pkg_name("  express  ") == "express"


# ── _extract_package_name ─────────────────────────────────────────────────────


class TestExtractPackageName:
    def test_extracts_simple_name(self):
        msg = "Vulnerable dependency: lodash (high) — Prototype pollution"
        assert DependencyReachabilityChecker._extract_package_name(msg) == "lodash"

    def test_extracts_scoped_name(self):
        msg = "Vulnerable dependency: @angular/core (critical) — XSS"
        result = DependencyReachabilityChecker._extract_package_name(msg)
        assert result == "@angular/core"

    def test_returns_none_when_no_match(self):
        assert DependencyReachabilityChecker._extract_package_name("No package here") is None

    def test_strips_version_specifier(self):
        msg = "Vulnerable dependency: express==4.18.0 (medium) — ReDOS"
        result = DependencyReachabilityChecker._extract_package_name(msg)
        assert result == "express"

    def test_empty_message(self):
        assert DependencyReachabilityChecker._extract_package_name("") is None


# ── _load_package_json ────────────────────────────────────────────────────────


class TestLoadPackageJson:
    def test_loads_valid_package_json(self, tmp_path):
        pkg = {"dependencies": {"lodash": "^4.0.0"}}
        checker = _make_project(tmp_path, pkg_json=pkg)
        data = checker._load_package_json()
        assert "lodash" in data["dependencies"]

    def test_returns_empty_when_missing(self, tmp_path):
        checker = DependencyReachabilityChecker(str(tmp_path))
        assert checker._load_package_json() == {}

    def test_returns_empty_on_invalid_json(self, tmp_path):
        (tmp_path / "package.json").write_text("not json {{{")
        checker = DependencyReachabilityChecker(str(tmp_path))
        assert checker._load_package_json() == {}

    def test_caches_result(self, tmp_path):
        pkg = {"dependencies": {"express": "^4.0.0"}}
        checker = _make_project(tmp_path, pkg_json=pkg)
        first = checker._load_package_json()
        # Delete file — second call should return cached result
        (tmp_path / "package.json").unlink()
        second = checker._load_package_json()
        assert first is second


# ── _scan_imports ─────────────────────────────────────────────────────────────


class TestScanImports:
    def test_detects_require(self, tmp_path):
        checker = _make_project(tmp_path, js_files={"src/app.js": "const x = require('lodash');\n"})
        imports = checker._scan_imports()
        assert "lodash" in imports

    def test_detects_es_import(self, tmp_path):
        checker = _make_project(tmp_path, js_files={"src/app.js": "import _ from 'lodash';\n"})
        imports = checker._scan_imports()
        assert "lodash" in imports

    def test_detects_ts_import(self, tmp_path):
        checker = _make_project(tmp_path, js_files={"src/app.ts": "import express from 'express';\n"})
        imports = checker._scan_imports()
        assert "express" in imports

    def test_skips_relative_imports(self, tmp_path):
        checker = _make_project(tmp_path, js_files={"src/app.js": "import x from './utils';\n"})
        imports = checker._scan_imports()
        assert "./utils" not in imports
        assert "utils" not in imports

    def test_excludes_node_modules(self, tmp_path):
        nm = tmp_path / "node_modules" / "lodash"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("require('lodash')\n")
        checker = DependencyReachabilityChecker(str(tmp_path))
        imports = checker._scan_imports()
        assert not imports

    def test_caches_result(self, tmp_path):
        checker = _make_project(tmp_path, js_files={"src/app.js": "require('express')\n"})
        first = checker._scan_imports()
        second = checker._scan_imports()
        assert first is second

    def test_normalises_subpath_imports(self, tmp_path):
        checker = _make_project(tmp_path, js_files={"src/app.js": "require('lodash/merge')\n"})
        imports = checker._scan_imports()
        assert "lodash" in imports

    def test_multiple_files_tracked(self, tmp_path):
        checker = _make_project(
            tmp_path,
            js_files={
                "src/a.js": "require('express')\n",
                "src/b.js": "require('express')\n",
            },
        )
        imports = checker._scan_imports()
        assert len(imports["express"]) == 2


# ── check() ───────────────────────────────────────────────────────────────────


class TestCheck:
    def test_direct_when_imported(self, tmp_path):
        pkg = {"dependencies": {"lodash": "^4.0.0"}}
        checker = _make_project(tmp_path, pkg_json=pkg, js_files={"src/app.js": "require('lodash')\n"})
        result = checker.check("lodash")
        assert result.level == "DIRECT"
        assert result.confidence_penalty == 0

    def test_transitive_when_in_pkg_not_imported(self, tmp_path):
        pkg = {"dependencies": {"lodash": "^4.0.0"}}
        checker = _make_project(tmp_path, pkg_json=pkg)
        result = checker.check("lodash")
        assert result.level == "TRANSITIVE"
        assert result.confidence_penalty == -15

    def test_unknown_when_not_in_pkg_and_not_imported(self, tmp_path):
        checker = _make_project(tmp_path, pkg_json={"dependencies": {}})
        result = checker.check("nonexistent-pkg")
        assert result.level == "UNKNOWN"
        assert result.confidence_penalty == -5

    def test_in_dev_dependencies_flagged(self, tmp_path):
        pkg = {"devDependencies": {"jest": "^29.0.0"}}
        checker = _make_project(tmp_path, pkg_json=pkg)
        result = checker.check("jest")
        assert result.in_dev_dependencies is True

    def test_direct_imports_list_populated(self, tmp_path):
        pkg = {"dependencies": {"express": "^4.0.0"}}
        checker = _make_project(tmp_path, pkg_json=pkg, js_files={"src/app.js": "require('express')\n"})
        result = checker.check("express")
        assert len(result.direct_imports) >= 1


# ── check_batch() ─────────────────────────────────────────────────────────────


class TestCheckBatch:
    def test_returns_dict_for_all_packages(self, tmp_path):
        pkg = {"dependencies": {"lodash": "^4.0.0", "express": "^4.0.0"}}
        checker = _make_project(tmp_path, pkg_json=pkg)
        results = checker.check_batch(["lodash", "express", "unknown-pkg"])
        assert set(results.keys()) == {"lodash", "express", "unknown-pkg"}

    def test_empty_list_returns_empty(self, tmp_path):
        checker = DependencyReachabilityChecker(str(tmp_path))
        assert checker.check_batch([]) == {}


# ── enrich_findings() ─────────────────────────────────────────────────────────


class TestEnrichFindings:
    def _npm_finding(self, pkg="lodash", score=None):
        f = {
            "tool": "npm-audit",
            "canonical_rule_id": "SECURITY-059",
            "message": f"Vulnerable dependency: {pkg} (high) — Prototype pollution",
            "severity": "high",
        }
        if score is not None:
            f["confidence_score"] = score
        return f

    def test_enriches_npm_finding(self, tmp_path):
        pkg = {"dependencies": {"lodash": "^4.0.0"}}
        checker = _make_project(tmp_path, pkg_json=pkg)
        findings = [self._npm_finding("lodash")]
        enriched = checker.enrich_findings(findings)
        assert "reachability_level" in enriched[0]

    def test_skips_non_npm_findings(self, tmp_path):
        checker = DependencyReachabilityChecker(str(tmp_path))
        f = {"tool": "eslint", "canonical_rule_id": "STYLE-001", "message": "unused var"}
        result = checker.enrich_findings([f])
        assert "reachability_level" not in result[0]

    def test_adjusts_confidence_score(self, tmp_path):
        pkg = {"dependencies": {"lodash": "^4.0.0"}}
        checker = _make_project(tmp_path, pkg_json=pkg)
        findings = [self._npm_finding("lodash", score=70)]
        enriched = checker.enrich_findings(findings)
        # TRANSITIVE penalty is -15
        assert enriched[0]["confidence_score"] == 55

    def test_confidence_score_not_below_zero(self, tmp_path):
        checker = DependencyReachabilityChecker(str(tmp_path))
        findings = [self._npm_finding("ghost-pkg", score=3)]
        enriched = checker.enrich_findings(findings)
        assert enriched[0].get("confidence_score", 3) >= 0

    def test_empty_findings_returns_empty(self, tmp_path):
        checker = DependencyReachabilityChecker(str(tmp_path))
        assert checker.enrich_findings([]) == []

    def test_finding_with_no_message_skipped(self, tmp_path):
        checker = DependencyReachabilityChecker(str(tmp_path))
        f = {"tool": "npm-audit", "canonical_rule_id": "SECURITY-059", "message": ""}
        result = checker.enrich_findings([f])
        assert "reachability_level" not in result[0]

    def test_enriches_by_canonical_rule_id(self, tmp_path):
        pkg = {"dependencies": {"express": "^4.0.0"}}
        checker = _make_project(tmp_path, pkg_json=pkg)
        f = {
            "tool": "unknown",
            "canonical_rule_id": "SECURITY-060",
            "message": "Vulnerable dependency: express (medium) — ReDOS",
        }
        result = checker.enrich_findings([f])
        assert "reachability_level" in result[0]
