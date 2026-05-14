"""Tests for Phase 5 — Supply Chain + SBOM engine."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from CORE.engines.supply_chain import (
    RISK_HIGH,
    RISK_MEDIUM,
    SupplyChainEngine,
    _extract_severity,
    _make_purl,
    build_cyclonedx_sbom,
    find_lockfiles,
    parse_go_mod,
    parse_package_json,
    parse_pipfile_lock,
    parse_requirements_txt,
    query_osv,
    score_dependency,
)

# ---------------------------------------------------------------------------
# Lockfile parsers
# ---------------------------------------------------------------------------


class TestParseRequirementsTxt:
    def test_simple_pinned(self):
        deps = parse_requirements_txt("requests==2.28.0\nflask==2.3.0\n")
        assert {"name": "requests", "version": "2.28.0", "ecosystem": "PyPI"} in deps
        assert {"name": "flask", "version": "2.3.0", "ecosystem": "PyPI"} in deps

    def test_unpinned_version_is_unknown(self):
        deps = parse_requirements_txt("django\n")
        assert deps[0]["version"] == "unknown"

    def test_comments_and_blank_lines_skipped(self):
        deps = parse_requirements_txt("# comment\n\nrequests==2.0.0\n")
        assert len(deps) == 1

    def test_env_marker_stripped(self):
        deps = parse_requirements_txt("pywin32==305 ; sys_platform == 'win32'\n")
        assert deps[0]["name"] == "pywin32"

    def test_extras_stripped(self):
        deps = parse_requirements_txt("requests[security]==2.28.0\n")
        assert deps[0]["name"] == "requests[security]" or deps[0]["name"] == "requests"

    def test_range_spec_version_is_unknown(self):
        deps = parse_requirements_txt("requests>=2.0,<3.0\n")
        assert deps[0]["version"] == "unknown"

    def test_dash_r_line_skipped(self):
        deps = parse_requirements_txt("-r base.txt\nrequests==2.0.0\n")
        assert len(deps) == 1


class TestParsePackageJson:
    def test_dependencies(self):
        data = json.dumps({"dependencies": {"react": "^18.2.0", "axios": "1.4.0"}})
        deps = parse_package_json(data)
        names = {d["name"] for d in deps}
        assert "react" in names and "axios" in names

    def test_dev_dependencies_included(self):
        data = json.dumps({"devDependencies": {"jest": "^29.0.0"}})
        deps = parse_package_json(data)
        assert any(d["name"] == "jest" for d in deps)

    def test_caret_stripped(self):
        data = json.dumps({"dependencies": {"lodash": "^4.17.21"}})
        deps = parse_package_json(data)
        assert deps[0]["version"] == "4.17.21"

    def test_invalid_json_returns_empty(self):
        assert parse_package_json("not json") == []

    def test_ecosystem_is_npm(self):
        data = json.dumps({"dependencies": {"express": "4.18.0"}})
        deps = parse_package_json(data)
        assert deps[0]["ecosystem"] == "npm"

    def test_empty_package_json(self):
        assert parse_package_json("{}") == []


class TestParseGoMod:
    def test_single_require(self):
        content = "module example.com/m\n\nrequire github.com/foo/bar v1.2.3\n"
        deps = parse_go_mod(content)
        assert any(d["name"] == "github.com/foo/bar" and d["version"] == "1.2.3" for d in deps)

    def test_require_block(self):
        content = "require (\n    github.com/a/b v0.1.0\n    github.com/c/d v2.0.0\n)\n"
        deps = parse_go_mod(content)
        names = {d["name"] for d in deps}
        assert "github.com/a/b" in names and "github.com/c/d" in names

    def test_ecosystem_is_go(self):
        deps = parse_go_mod("require golang.org/x/net v0.10.0\n")
        assert deps[0]["ecosystem"] == "Go"

    def test_v_prefix_stripped(self):
        deps = parse_go_mod("require github.com/x/y v1.0.0\n")
        assert deps[0]["version"] == "1.0.0"


class TestParsePipfileLock:
    def test_default_section(self):
        data = json.dumps({"default": {"requests": {"version": "==2.28.0"}}, "develop": {}})
        deps = parse_pipfile_lock(data)
        assert any(d["name"] == "requests" and d["version"] == "2.28.0" for d in deps)

    def test_develop_section_included(self):
        data = json.dumps({"default": {}, "develop": {"pytest": {"version": "==7.4.0"}}})
        deps = parse_pipfile_lock(data)
        assert any(d["name"] == "pytest" for d in deps)

    def test_invalid_json_returns_empty(self):
        assert parse_pipfile_lock("bad json") == []

    def test_ecosystem_is_pypi(self):
        data = json.dumps({"default": {"flask": {"version": "==2.3.0"}}, "develop": {}})
        deps = parse_pipfile_lock(data)
        assert deps[0]["ecosystem"] == "PyPI"


class TestFindLockfiles:
    def test_finds_requirements_txt(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
        found = find_lockfiles(tmp_path)
        assert any(f.name == "requirements.txt" for f in found)

    def test_finds_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text('{"dependencies": {}}')
        found = find_lockfiles(tmp_path)
        assert any(f.name == "package.json" for f in found)

    def test_skips_node_modules(self, tmp_path):
        nm = tmp_path / "node_modules" / "lodash"
        nm.mkdir(parents=True)
        (nm / "package.json").write_text('{"dependencies": {}}')
        (tmp_path / "package.json").write_text('{"dependencies": {}}')
        found = find_lockfiles(tmp_path)
        # Check path components relative to tmp_path, not the full string (tmp_path name may contain "node_modules")
        assert all("node_modules" not in f.relative_to(tmp_path).parts for f in found)

    def test_skips_venv(self, tmp_path):
        venv = tmp_path / ".venv" / "lib"
        venv.mkdir(parents=True)
        (venv / "requirements.txt").write_text("pip==23.0\n")
        (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
        found = find_lockfiles(tmp_path)
        assert all(".venv" not in str(f) for f in found)

    def test_recursive_discovery(self, tmp_path):
        sub = tmp_path / "backend"
        sub.mkdir()
        (sub / "requirements.txt").write_text("flask==2.3.0\n")
        found = find_lockfiles(tmp_path)
        assert any("backend" in str(f) for f in found)


# ---------------------------------------------------------------------------
# OSV query routing
# ---------------------------------------------------------------------------


class TestQueryOsv:
    def test_live_mode_calls_live(self):
        with patch("CORE.engines.supply_chain.query_osv_live", return_value=[{"id": "GHSA-x"}]) as m:
            result = query_osv("requests", "2.0.0", "PyPI", mode="live")
        m.assert_called_once()
        assert result == [{"id": "GHSA-x"}]

    def test_offline_mode_calls_offline(self):
        with patch("CORE.engines.supply_chain.query_osv_offline", return_value=[]) as m:
            query_osv("requests", "2.0.0", "PyPI", mode="offline")
        m.assert_called_once()

    def test_auto_mode_falls_back_to_live_when_offline_empty(self):
        with patch("CORE.engines.supply_chain.query_osv_offline", return_value=[]):
            with patch("CORE.engines.supply_chain.query_osv_live", return_value=[{"id": "GHSA-y"}]) as live:
                result = query_osv("requests", "2.0.0", "PyPI", mode="auto")
        live.assert_called_once()
        assert result == [{"id": "GHSA-y"}]

    def test_auto_mode_uses_offline_when_available(self):
        with patch("CORE.engines.supply_chain.query_osv_offline", return_value=[{"id": "GHSA-z"}]):
            with patch("CORE.engines.supply_chain.query_osv_live") as live:
                result = query_osv("requests", "2.0.0", "PyPI", mode="auto")
        live.assert_not_called()
        assert result == [{"id": "GHSA-z"}]


# ---------------------------------------------------------------------------
# Risk scoring
# ---------------------------------------------------------------------------


class TestScoreDependency:
    def test_no_cves_no_github_low_score(self):
        score = score_dependency([], {})
        assert score < RISK_MEDIUM

    def test_critical_cve_raises_score(self):
        vuln = {"severity": [{"score": "CRITICAL/AV:N"}]}
        score = score_dependency([vuln], {})
        assert score >= 10

    def test_archived_adds_25(self):
        score = score_dependency([], {"archived": True, "stars": 1000, "contributors": 20, "license": "MIT"})
        assert score >= 25

    def test_score_capped_at_100(self):
        critical_cves = [{"severity": [{"score": "CRITICAL/AV:N"}]} for _ in range(10)]
        score = score_dependency(critical_cves, {"archived": True})
        assert score == 100

    def test_high_stars_reduces_score(self):
        score_low = score_dependency([], {"stars": 0})
        score_high = score_dependency([], {"stars": 10000})
        assert score_high < score_low

    def test_risk_levels(self):
        assert RISK_HIGH > RISK_MEDIUM > 0

    def test_no_license_adds_score(self):
        s_no_lic = score_dependency([], {"license": None})
        s_with_lic = score_dependency([], {"license": "MIT"})
        assert s_no_lic > s_with_lic


class TestExtractSeverity:
    def test_critical_string(self):
        assert _extract_severity({"severity": [{"score": "CVSS:3.1/CRITICAL/AV:N"}]}) == "CRITICAL"

    def test_high_string(self):
        assert _extract_severity({"severity": [{"score": "HIGH/AV:N"}]}) == "HIGH"

    def test_fallback_is_medium(self):
        assert _extract_severity({}) == "MEDIUM"

    def test_database_specific_severity(self):
        vuln = {"affected": [{"database_specific": {"severity": ["HIGH"]}}]}
        assert _extract_severity(vuln) == "HIGH"


# ---------------------------------------------------------------------------
# CycloneDX SBOM builder
# ---------------------------------------------------------------------------


class TestBuildCyclonedxSbom:
    def _dep(self, name="requests", version="2.28.0", ecosystem="PyPI", cves=None):
        return {"name": name, "version": version, "ecosystem": ecosystem, "cves": cves or []}

    def test_bom_format_field(self):
        sbom = build_cyclonedx_sbom(1, "foo/bar", [self._dep()])
        assert sbom["bomFormat"] == "CycloneDX"

    def test_spec_version(self):
        sbom = build_cyclonedx_sbom(1, "foo/bar", [self._dep()])
        assert sbom["specVersion"] == "1.4"

    def test_serial_number_contains_run_id(self):
        sbom = build_cyclonedx_sbom(42, "foo/bar", [self._dep()])
        assert "42" in sbom["serialNumber"]

    def test_component_count(self):
        deps = [self._dep("requests"), self._dep("flask")]
        sbom = build_cyclonedx_sbom(1, "repo", deps)
        assert len(sbom["components"]) == 2

    def test_purl_in_component(self):
        sbom = build_cyclonedx_sbom(1, "repo", [self._dep()])
        assert sbom["components"][0]["purl"].startswith("pkg:pypi/")

    def test_vulnerabilities_populated_when_cves(self):
        cve = {"id": "GHSA-xxxx", "summary": "SQL injection", "severity": []}
        sbom = build_cyclonedx_sbom(1, "repo", [self._dep(cves=[cve])])
        assert "vulnerabilities" in sbom["components"][0]

    def test_empty_deps_produces_empty_components(self):
        sbom = build_cyclonedx_sbom(1, "repo", [])
        assert sbom["components"] == []

    def test_metadata_has_repo_name(self):
        sbom = build_cyclonedx_sbom(1, "myorg/myrepo", [self._dep()])
        assert sbom["metadata"]["component"]["name"] == "myorg/myrepo"


class TestMakePurl:
    def test_pypi(self):
        assert _make_purl({"name": "Requests", "version": "2.28.0", "ecosystem": "PyPI"}).startswith(
            "pkg:pypi/requests@"
        )

    def test_npm(self):
        assert _make_purl({"name": "lodash", "version": "4.17.21", "ecosystem": "npm"}).startswith("pkg:npm/lodash@")

    def test_go(self):
        assert _make_purl({"name": "github.com/x/y", "version": "1.0.0", "ecosystem": "Go"}).startswith("pkg:golang/")

    def test_unknown_ecosystem_generic(self):
        assert _make_purl({"name": "thing", "version": "1.0", "ecosystem": "Cargo"}).startswith("pkg:generic/")


# ---------------------------------------------------------------------------
# SupplyChainEngine integration
# ---------------------------------------------------------------------------


class TestSupplyChainEngine:
    def _make_reqs(self, tmp_path: Path) -> Path:
        f = tmp_path / "requirements.txt"
        f.write_text("requests==2.28.0\nflask==2.3.0\n")
        return f

    def test_scan_returns_required_keys(self, tmp_path):
        self._make_reqs(tmp_path)
        engine = SupplyChainEngine(osv_mode="offline", github_enabled=False)
        with patch("CORE.engines.supply_chain.query_osv_offline", return_value=[]):
            result = engine.scan(tmp_path)
        assert all(k in result for k in ("dependencies", "sbom", "summary", "lockfiles_scanned"))

    def test_scan_finds_dependencies(self, tmp_path):
        self._make_reqs(tmp_path)
        engine = SupplyChainEngine(osv_mode="offline", github_enabled=False)
        with patch("CORE.engines.supply_chain.query_osv_offline", return_value=[]):
            result = engine.scan(tmp_path)
        assert len(result["dependencies"]) == 2

    def test_scan_deduplicates(self, tmp_path):
        # Two lockfiles with same dep
        (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "requirements.txt").write_text("requests==2.28.0\n")
        engine = SupplyChainEngine(osv_mode="offline", github_enabled=False)
        with patch("CORE.engines.supply_chain.query_osv_offline", return_value=[]):
            result = engine.scan(tmp_path)
        names = [d["name"] for d in result["dependencies"]]
        assert names.count("requests") == 1

    def test_summary_counts(self, tmp_path):
        self._make_reqs(tmp_path)
        engine = SupplyChainEngine(osv_mode="offline", github_enabled=False)
        with patch("CORE.engines.supply_chain.query_osv_offline", return_value=[]):
            result = engine.scan(tmp_path)
        s = result["summary"]
        assert s["total_dependencies"] == 2
        assert s["high_risk"] + s["medium_risk"] + s["low_risk"] == s["total_dependencies"]

    def test_cves_populate_cve_count(self, tmp_path):
        self._make_reqs(tmp_path)
        cve = {"id": "GHSA-xxxx", "summary": "RCE", "severity": [{"score": "CRITICAL"}]}
        engine = SupplyChainEngine(osv_mode="offline", github_enabled=False)
        with patch("CORE.engines.supply_chain.query_osv_offline", return_value=[cve]):
            result = engine.scan(tmp_path)
        assert all(d["cve_count"] >= 1 for d in result["dependencies"])

    def test_scan_with_no_lockfiles(self, tmp_path):
        engine = SupplyChainEngine(osv_mode="offline", github_enabled=False)
        result = engine.scan(tmp_path)
        assert result["dependencies"] == []
        assert result["summary"]["total_dependencies"] == 0

    def test_sbom_is_cyclonedx(self, tmp_path):
        self._make_reqs(tmp_path)
        engine = SupplyChainEngine(osv_mode="offline", github_enabled=False)
        with patch("CORE.engines.supply_chain.query_osv_offline", return_value=[]):
            result = engine.scan(tmp_path)
        assert result["sbom"]["bomFormat"] == "CycloneDX"

    def test_github_disabled_no_signals(self, tmp_path):
        self._make_reqs(tmp_path)
        engine = SupplyChainEngine(osv_mode="offline", github_enabled=False)
        with patch("CORE.engines.supply_chain.fetch_github_signals") as gh:
            with patch("CORE.engines.supply_chain.query_osv_offline", return_value=[]):
                engine.scan(tmp_path)
        gh.assert_not_called()

    def test_risk_level_high_when_score_above_threshold(self, tmp_path):
        self._make_reqs(tmp_path)
        engine = SupplyChainEngine(osv_mode="offline", github_enabled=False)
        many_criticals = [{"severity": [{"score": "CRITICAL"}]} for _ in range(5)]
        with patch("CORE.engines.supply_chain.query_osv_offline", return_value=many_criticals):
            result = engine.scan(tmp_path)
        assert any(d["risk_level"] == "high" for d in result["dependencies"])
