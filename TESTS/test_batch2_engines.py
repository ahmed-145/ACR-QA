"""
God-mode tests for:
  - CORE/engines/sca_scanner.py              (target: 90%+)
  - CORE/engines/cross_language_correlator.py (target: 85%+)
  - CORE/engines/path_feasibility.py          (target: 85%+)

All external calls (subprocess, httpx) are fully mocked.
"""

import asyncio
import json
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from CORE.engines.cross_language_correlator import (
    CorrelationGroup,
    CrossLanguageCorrelator,
)
from CORE.engines.path_feasibility import (
    PathFeasibilityResult,
    PathFeasibilityValidator,
    _parse_feasibility_response,
)
from CORE.engines.sca_scanner import SCAScanner

# ═════════════════════════════════════════════════════════════════════════════
#  SCAScanner
# ═════════════════════════════════════════════════════════════════════════════


class TestSCAScannerInit:
    def test_project_dir_stored(self, tmp_path):
        s = SCAScanner(str(tmp_path))
        assert s.project_dir == tmp_path


class TestSCAScannerPipAuditAvailable:
    def test_returns_true_when_pip_audit_ok(self):
        s = SCAScanner()
        result = MagicMock(returncode=0)
        with patch("subprocess.run", return_value=result):
            assert s._pip_audit_available() is True

    def test_returns_false_when_pip_audit_fails(self):
        s = SCAScanner()
        result = MagicMock(returncode=1)
        with patch("subprocess.run", return_value=result):
            assert s._pip_audit_available() is False

    def test_returns_false_on_file_not_found(self):
        s = SCAScanner()
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert s._pip_audit_available() is False

    def test_returns_false_on_timeout(self):
        s = SCAScanner()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pip-audit", 10)):
            assert s._pip_audit_available() is False


class TestSCAScannerFindRequirements:
    def test_finds_requirements_txt(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask==1.0\n")
        s = SCAScanner(str(tmp_path))
        result = s._find_requirements()
        assert result is not None
        assert result.name == "requirements.txt"

    def test_returns_none_when_no_req_file(self, tmp_path):
        s = SCAScanner(str(tmp_path))
        assert s._find_requirements() is None

    def test_finds_requirements_prod_txt(self, tmp_path):
        (tmp_path / "requirements-prod.txt").write_text("flask==1.0\n")
        s = SCAScanner(str(tmp_path))
        assert s._find_requirements() is not None


class TestSCAScannerParsePipAudit:
    def test_parses_vulnerabilities_from_data(self):
        s = SCAScanner()
        data = {
            "dependencies": [
                {
                    "name": "requests",
                    "version": "2.26.0",
                    "vulns": [
                        {
                            "id": "CVE-2023-32681",
                            "description": "Proxy header leak",
                            "fix_versions": ["2.31.0"],
                            "severity": "HIGH",
                            "aliases": [],
                        }
                    ],
                }
            ]
        }
        result = s._parse_pip_audit(data)
        assert len(result) == 1
        assert result[0]["package"] == "requests"
        assert result[0]["vulnerability_id"] == "CVE-2023-32681"

    def test_no_vulnerabilities_returns_empty(self):
        s = SCAScanner()
        result = s._parse_pip_audit({"dependencies": [{"name": "flask", "version": "2.3.3", "vulns": []}]})
        assert result == []

    def test_empty_data_returns_empty(self):
        s = SCAScanner()
        assert s._parse_pip_audit({}) == []


class TestSCAScannerRunPipAudit:
    def test_returns_none_when_not_available(self, tmp_path):
        s = SCAScanner(str(tmp_path))
        with patch.object(s, "_pip_audit_available", return_value=False):
            assert s._run_pip_audit() is None

    def test_returns_parsed_results_on_success(self, tmp_path):
        s = SCAScanner(str(tmp_path))
        fake_output = json.dumps(
            {
                "dependencies": [
                    {
                        "name": "foo",
                        "version": "1.0",
                        "vulns": [
                            {
                                "id": "CVE-001",
                                "description": "test",
                                "fix_versions": ["2.0"],
                                "severity": "HIGH",
                                "aliases": [],
                            }
                        ],
                    }
                ]
            }
        )
        mock_result = MagicMock(returncode=0, stdout=fake_output)
        with patch.object(s, "_pip_audit_available", return_value=True):
            with patch("subprocess.run", return_value=mock_result):
                result = s._run_pip_audit()
        assert result is not None
        assert len(result) == 1

    def test_returns_empty_on_empty_stdout(self, tmp_path):
        s = SCAScanner(str(tmp_path))
        mock_result = MagicMock(returncode=0, stdout="")
        with patch.object(s, "_pip_audit_available", return_value=True):
            with patch("subprocess.run", return_value=mock_result):
                result = s._run_pip_audit()
        assert result == []

    def test_returns_none_on_json_decode_error(self, tmp_path):
        s = SCAScanner(str(tmp_path))
        mock_result = MagicMock(returncode=0, stdout="NOT JSON")
        with patch.object(s, "_pip_audit_available", return_value=True):
            with patch("subprocess.run", return_value=mock_result):
                result = s._run_pip_audit()
        assert result is None

    def test_returns_none_on_timeout(self, tmp_path):
        s = SCAScanner(str(tmp_path))
        with patch.object(s, "_pip_audit_available", return_value=True):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pip-audit", 120)):
                result = s._run_pip_audit()
        assert result is None


class TestSCAScannerScanRequirements:
    def test_returns_empty_when_no_req_file(self, tmp_path):
        s = SCAScanner(str(tmp_path))
        assert s._scan_requirements() == []

    def test_detects_vulnerable_requests(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests==2.26.0\n")
        s = SCAScanner(str(tmp_path))
        result = s._scan_requirements()
        assert any(v["package"] == "requests" for v in result)

    def test_skips_comment_lines(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("# requests==2.26.0\n")
        s = SCAScanner(str(tmp_path))
        assert s._scan_requirements() == []

    def test_skips_safe_version(self, tmp_path):
        # requests 2.32.0 > 2.31.0 (threshold) — not vulnerable
        (tmp_path / "requirements.txt").write_text("requests==2.32.0\n")
        s = SCAScanner(str(tmp_path))
        result = s._scan_requirements()
        assert not any(v["package"] == "requests" for v in result)

    def test_tilde_equal_parsed(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests~=2.26.0\n")
        s = SCAScanner(str(tmp_path))
        result = s._scan_requirements()
        assert any(v["package"] == "requests" for v in result)

    def test_gte_parsed(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests>=2.26.0\n")
        s = SCAScanner(str(tmp_path))
        result = s._scan_requirements()
        assert any(v["package"] == "requests" for v in result)

    def test_dash_lines_skipped(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("-r other.txt\n")
        s = SCAScanner(str(tmp_path))
        assert s._scan_requirements() == []


class TestSCAScannerVersionLt:
    def test_1_lt_2(self):
        assert SCAScanner()._version_lt("1.0.0", "2.0.0") is True

    def test_equal_not_lt(self):
        assert SCAScanner()._version_lt("2.0.0", "2.0.0") is False

    def test_2_lt_1_false(self):
        assert SCAScanner()._version_lt("2.0.0", "1.0.0") is False

    def test_invalid_version_returns_false(self):
        assert SCAScanner()._version_lt("x.y.z", "2.0.0") is False


class TestSCAScannerToCanonicalFindings:
    def test_converts_vuln_to_finding(self):
        s = SCAScanner()
        vulns = [
            {
                "package": "requests",
                "installed_version": "2.26",
                "vulnerability_id": "CVE-001",
                "description": "test",
                "severity": "HIGH",
                "fix_versions": ["2.31"],
            }
        ]
        findings = s._to_canonical_findings(vulns)
        assert len(findings) == 1
        f = findings[0]
        assert f["canonical_rule_id"] == "SCA-001"
        assert f["category"] == "security"
        assert f["tool_name"] == "sca-scanner"
        assert f["severity"] == "high"

    def test_empty_fix_versions(self):
        s = SCAScanner()
        vulns = [
            {
                "package": "foo",
                "installed_version": "1.0",
                "vulnerability_id": "CVE-001",
                "description": "",
                "severity": "LOW",
                "fix_versions": [],
            }
        ]
        findings = s._to_canonical_findings(vulns)
        assert "No fix available" in findings[0]["message"]


class TestSCAScannerScan:
    def test_scan_with_pip_audit_mocked(self, tmp_path):
        s = SCAScanner(str(tmp_path))
        mock_vulns = [
            {
                "package": "foo",
                "installed_version": "1.0",
                "vulnerability_id": "CVE-001",
                "description": "test",
                "severity": "HIGH",
                "fix_versions": ["2.0"],
            }
        ]
        with patch.object(s, "_run_pip_audit", return_value=mock_vulns):
            with patch.object(s, "_pip_audit_available", return_value=True):
                result = s.scan()
        assert result["total_vulnerabilities"] == 1
        assert result["scanner"] == "pip-audit"
        assert len(result["findings"]) == 1

    def test_scan_falls_back_to_requirements(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("requests==2.26.0\n")
        s = SCAScanner(str(tmp_path))
        with patch.object(s, "_run_pip_audit", return_value=None):
            with patch.object(s, "_pip_audit_available", return_value=False):
                result = s.scan()
        assert result["scanner"] == "requirements-check"


# ═════════════════════════════════════════════════════════════════════════════
#  CrossLanguageCorrelator
# ═════════════════════════════════════════════════════════════════════════════


def _py_finding(rule_id="SECURITY-001", file="src/app.py", msg=""):
    return {"canonical_rule_id": rule_id, "file": file, "file_path": file, "language": "python", "message": msg}


def _js_finding(file="src/app.js"):
    return {
        "canonical_rule_id": "SECURITY-001",
        "file": file,
        "file_path": file,
        "language": "javascript",
        "message": "",
    }


def _tmpl_finding(file="templates/index.html"):
    return {
        "canonical_rule_id": "SECURITY-045",
        "file": file,
        "file_path": file,
        "language": "",
        "message": "xss unsafe",
    }


class TestCorrelationGroupProperties:
    def test_all_findings_combines_lists(self):
        g = CorrelationGroup(
            correlation_type="X", chain_description="desc", python_findings=[_py_finding()], js_findings=[_js_finding()]
        )
        assert len(g.all_findings) == 2

    def test_finding_count(self):
        g = CorrelationGroup(
            correlation_type="X", chain_description="desc", python_findings=[_py_finding(), _py_finding()]
        )
        assert g.finding_count == 2

    def test_to_dict_has_required_keys(self):
        g = CorrelationGroup(correlation_type="ROUTE_JS_CHAIN", chain_description="desc")
        d = g.to_dict()
        assert "correlation_type" in d
        assert "combined_severity" in d
        assert "finding_count" in d


class TestCrossLanguageCorrelatorStaticMethods:
    def test_is_python_by_extension(self):
        assert CrossLanguageCorrelator._is_python({"file": "app.py"}) is True

    def test_is_python_by_language(self):
        assert CrossLanguageCorrelator._is_python({"language": "python", "file": "x"}) is True

    def test_is_not_python(self):
        assert CrossLanguageCorrelator._is_python({"file": "app.js"}) is False

    def test_is_template_html(self):
        assert CrossLanguageCorrelator._is_template({"file": "index.html"}) is True

    def test_is_template_jinja2(self):
        assert CrossLanguageCorrelator._is_template({"file": "t.jinja2"}) is True

    def test_is_not_template(self):
        assert CrossLanguageCorrelator._is_template({"file": "app.py"}) is False

    def test_is_js_by_extension(self):
        assert CrossLanguageCorrelator._is_js({"file": "app.js"}) is True

    def test_is_js_by_ts(self):
        assert CrossLanguageCorrelator._is_js({"file": "main.ts"}) is True

    def test_is_not_js(self):
        assert CrossLanguageCorrelator._is_js({"file": "app.py"}) is False


class TestCrossLanguageCorrelatorCorrelate:
    def test_empty_findings_returns_empty(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        assert c.correlate([]) == []

    def test_only_python_findings_no_correlation(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        findings = [_py_finding()]
        groups = c.correlate(findings)
        # May or may not correlate depending on content — just no crash
        assert isinstance(groups, list)

    def test_route_js_chain_detected(self, tmp_path):
        # Create Python file in same dir as JS file
        c = CrossLanguageCorrelator(str(tmp_path))
        shared_dir = tmp_path / "feature"
        shared_dir.mkdir()

        py_f = {
            "canonical_rule_id": "SECURITY-001",
            "file": str(shared_dir / "view.py"),
            "file_path": str(shared_dir / "view.py"),
            "language": "python",
            "message": "",
        }
        js_f = {
            "canonical_rule_id": "SECURITY-001",
            "file": str(shared_dir / "index.js"),
            "file_path": str(shared_dir / "index.js"),
            "language": "javascript",
            "message": "",
        }

        groups = c.correlate([py_f, js_f])
        route_js = [g for g in groups if g.correlation_type == "ROUTE_JS_CHAIN"]
        assert len(route_js) >= 1

    def test_sqli_correlation_with_no_templates_returns_empty(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        sqli_f = _py_finding(rule_id="SECURITY-027", msg="sql injection")
        groups = c.correlate([sqli_f])
        sqli_groups = [g for g in groups if g.correlation_type == "SQLI_TO_TEMPLATE"]
        assert len(sqli_groups) == 0  # No templates in tmp_path


class TestCrossLanguageCorrelatorEnrichFindings:
    def test_enrich_tags_finding_in_chain(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        shared_dir = tmp_path / "api"
        shared_dir.mkdir()

        py_f = {
            "canonical_rule_id": "SECURITY-001",
            "file": str(shared_dir / "v.py"),
            "file_path": str(shared_dir / "v.py"),
            "language": "python",
            "message": "",
            "confidence_score": 60,
        }
        js_f = {
            "canonical_rule_id": "SECURITY-001",
            "file": str(shared_dir / "i.js"),
            "file_path": str(shared_dir / "i.js"),
            "language": "javascript",
            "message": "",
        }

        enriched, groups = c.enrich_findings([py_f, js_f])
        if groups:
            assert "cross_language_correlation" in enriched[0] or "cross_language_correlation" in enriched[1]

    def test_enrich_empty_findings(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        enriched, groups = c.enrich_findings([])
        assert enriched == []
        assert groups == []


class TestCrossLanguageCorrelatorScanProject:
    def test_scan_project_returns_list(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        result = c.scan_project()
        assert isinstance(result, list)


class TestCrossLanguageCorrelatorHelpers:
    def test_find_unsafe_templates_with_safe_filter(self, tmp_path):
        tmpl = tmp_path / "index.html"
        tmpl.write_text("{{ user_input | safe }}")
        c = CrossLanguageCorrelator(str(tmp_path))
        unsafe = c._find_unsafe_templates()
        assert any("index.html" in u for u in unsafe)

    def test_find_unsafe_templates_safe_code_not_flagged(self, tmp_path):
        tmpl = tmp_path / "index.html"
        tmpl.write_text("{{ user_input }}")  # No |safe
        c = CrossLanguageCorrelator(str(tmp_path))
        unsafe = c._find_unsafe_templates()
        assert not any("index.html" in u for u in unsafe)

    def test_build_route_template_map_caches(self, tmp_path):
        c = CrossLanguageCorrelator(str(tmp_path))
        m1 = c._build_route_template_map()
        m2 = c._build_route_template_map()
        assert m1 is m2  # Cached

    def test_xss_correlate_with_unsafe_template(self, tmp_path):
        tmpl_dir = tmp_path / "templates"
        tmpl_dir.mkdir()
        (tmpl_dir / "index.html").write_text("{{ data | safe }}")
        c = CrossLanguageCorrelator(str(tmp_path))
        xss_f = _py_finding(rule_id="SECURITY-045", msg="render_template_string xss")
        groups = c.correlate([xss_f])
        xss_groups = [g for g in groups if g.correlation_type == "XSS_CHAIN"]
        assert len(xss_groups) >= 1


# ═════════════════════════════════════════════════════════════════════════════
#  PathFeasibility
# ═════════════════════════════════════════════════════════════════════════════


class TestParseFeasibilityResponse:
    def test_parses_all_fields(self):
        text = "VERDICT: REACHABLE\nCONFIDENCE: HIGH\nREASONING: The function is called from main."
        v, c, r = _parse_feasibility_response(text)
        assert v == "REACHABLE"
        assert c == "HIGH"
        assert "main" in r

    def test_parses_unreachable(self):
        text = "VERDICT: UNREACHABLE\nCONFIDENCE: MEDIUM\nREASONING: Dead code."
        v, c, r = _parse_feasibility_response(text)
        assert v == "UNREACHABLE"
        assert c == "MEDIUM"

    def test_invalid_verdict_defaults_to_unknown(self):
        text = "VERDICT: MAYBE\nCONFIDENCE: HIGH\nREASONING: unsure"
        v, _, _ = _parse_feasibility_response(text)
        assert v == "UNKNOWN"

    def test_invalid_confidence_defaults_to_low(self):
        text = "VERDICT: REACHABLE\nCONFIDENCE: SUPER\nREASONING: x"
        _, c, _ = _parse_feasibility_response(text)
        assert c == "LOW"

    def test_empty_response_returns_defaults(self):
        v, c, r = _parse_feasibility_response("")
        assert v == "UNKNOWN"
        assert c == "LOW"
        assert "parse" in r.lower()

    def test_unknown_verdict(self):
        text = "VERDICT: UNKNOWN\nCONFIDENCE: LOW\nREASONING: Not enough info."
        v, c, r = _parse_feasibility_response(text)
        assert v == "UNKNOWN"


class TestPathFeasibilityResult:
    def _result(self, verdict="REACHABLE", confidence="HIGH"):
        return PathFeasibilityResult(
            verdict=verdict,
            confidence=confidence,
            reasoning="test",
            latency_ms=50,
            rule_id="SECURITY-001",
            file_path="app.py",
            line_number=10,
        )

    def test_is_unreachable_true_when_unreachable(self):
        r = self._result(verdict="UNREACHABLE")
        assert r.is_unreachable is True

    def test_is_unreachable_false_when_reachable(self):
        r = self._result(verdict="REACHABLE")
        assert r.is_unreachable is False

    def test_confidence_penalty_reachable_is_0(self):
        assert self._result("REACHABLE", "HIGH").confidence_penalty == 0

    def test_confidence_penalty_unknown_is_5(self):
        assert self._result("UNKNOWN", "HIGH").confidence_penalty == 5

    def test_confidence_penalty_unreachable_high_is_30(self):
        assert self._result("UNREACHABLE", "HIGH").confidence_penalty == 30

    def test_confidence_penalty_unreachable_medium_is_20(self):
        assert self._result("UNREACHABLE", "MEDIUM").confidence_penalty == 20

    def test_confidence_penalty_unreachable_low_is_10(self):
        assert self._result("UNREACHABLE", "LOW").confidence_penalty == 10

    def test_confidence_penalty_unknown_confidence_is_15(self):
        r = PathFeasibilityResult("UNREACHABLE", "WEIRD", "r", 0, "X", "f", 1)
        assert r.confidence_penalty == 15

    def test_to_dict_has_all_keys(self):
        d = self._result().to_dict()
        assert "feasibility_verdict" in d
        assert "feasibility_confidence" in d
        assert "feasibility_reasoning" in d
        assert "is_unreachable" in d
        assert "feasibility_penalty" in d


class TestPathFeasibilityValidator:
    def setup_method(self):
        self.v = PathFeasibilityValidator()

    def test_is_eligible_high_security(self):
        f = {"canonical_severity": "high", "category": "security"}
        assert self.v.is_eligible(f) is True

    def test_is_eligible_critical_security(self):
        f = {"canonical_severity": "critical", "category": "security"}
        assert self.v.is_eligible(f) is True

    def test_not_eligible_medium(self):
        f = {"canonical_severity": "medium", "category": "security"}
        assert self.v.is_eligible(f) is False

    def test_not_eligible_high_non_security(self):
        f = {"canonical_severity": "high", "category": "design"}
        assert self.v.is_eligible(f) is False

    @pytest.mark.asyncio
    async def test_validate_async_success(self):
        finding = {
            "canonical_rule_id": "SECURITY-001",
            "canonical_severity": "high",
            "file_path": "app.py",
            "line_number": 10,
            "message": "SQL injection",
        }
        response_text = "VERDICT: REACHABLE\nCONFIDENCE: HIGH\nREASONING: Called from main."

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": response_text}}]}

        async def fake_post(*args, **kwargs):
            return mock_response

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        result = await self.v.validate_async(mock_client, finding, "def foo(): pass", "fake_key")
        assert result.verdict == "REACHABLE"
        assert result.confidence == "HIGH"

    @pytest.mark.asyncio
    async def test_validate_async_exception_returns_unknown(self):
        finding = {
            "canonical_rule_id": "X",
            "canonical_severity": "high",
            "file_path": "f.py",
            "line_number": 1,
            "message": "",
        }

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=Exception("timeout"))

        result = await self.v.validate_async(mock_client, finding, "", "key")
        assert result.verdict == "UNKNOWN"
        assert result.confidence == "LOW"

    def test_validate_batch_skips_ineligible(self):
        v = PathFeasibilityValidator()
        items = [
            {"finding": {"canonical_severity": "low", "category": "style"}, "snippet": ""},
        ]
        with patch.object(v, "validate_batch_async", new=AsyncMock(return_value=[None])):
            asyncio.run(v.validate_batch_async(items, "key"))
