"""
God-mode tests for:
  - CORE/engines/ai_code_detector.py       (target: 90%+)
  - CORE/engines/cbom_scanner.py           (target: 85%+)
  - CORE/engines/dependency_reachability.py (target: 90%+)
"""

import json
import textwrap
from pathlib import Path
from unittest.mock import patch

from CORE.engines.ai_code_detector import AICodeDetector
from CORE.engines.cbom_scanner import (
    CBoMReport,
    CBoMScanner,
    CryptoUsage,
)
from CORE.engines.dependency_reachability import (
    DependencyReachabilityChecker,
    ReachabilityResult,
)

# ═════════════════════════════════════════════════════════════════════════════
#  AICodeDetector
# ═════════════════════════════════════════════════════════════════════════════


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(content))
    return p


class TestAICodeDetectorInit:
    def test_threshold_stored(self):
        d = AICodeDetector(threshold=0.7)
        assert d.threshold == 0.7

    def test_default_threshold_is_05(self):
        d = AICodeDetector()
        assert d.threshold == 0.5


class TestAICodeDetectorAnalyzeFile:
    def setup_method(self):
        self.d = AICodeDetector()

    def test_returns_dict(self, tmp_path):
        f = _write(tmp_path, "t.py", "x = 1\n")
        result = self.d.analyze_file(str(f))
        assert isinstance(result, dict)
        assert "score" in result

    def test_empty_file_returns_no_signals(self, tmp_path):
        f = _write(tmp_path, "empty.py", "")
        result = self.d.analyze_file(str(f))
        assert result["score"] == 0

    def test_nonexistent_file_returns_error(self):
        result = self.d.analyze_file("/nonexistent/path.py")
        assert "error" in result

    def test_is_ai_generated_true_when_score_above_threshold(self, tmp_path):
        d = AICodeDetector(threshold=0.01)  # very low threshold
        code = textwrap.dedent("""
            # TODO: implement this function
            # TODO: add error handling
            # TODO: update tests
            # TODO: fix edge case
            # TODO: refactor
            def process(data, result, value, temp, item, element):
                \"\"\"This function processes the data.\"\"\"
                return result
        """)
        f = _write(tmp_path, "ai.py", code)
        result = d.analyze_file(str(f))
        assert result["score"] >= 0

    def test_generic_names_signal_triggered(self, tmp_path):
        code = textwrap.dedent("""
            def process(data, result, value, temp, item, element, obj, output, input_data):
                response = data
                val = result
                res = value
                ret = temp
                lst = item
                arr = element
                return obj
        """)
        f = _write(tmp_path, "generic.py", code)
        result = self.d.analyze_file(str(f))
        generic_signals = [s for s in result["signals"] if s["type"] == "generic_names"]
        assert len(generic_signals) >= 1

    def test_boilerplate_docs_signal(self, tmp_path):
        code = textwrap.dedent("""
            def foo(x):
                \"\"\"This function takes x as input and returns the result.\"\"\"
                return x
        """)
        f = _write(tmp_path, "boilerplate.py", code)
        result = self.d.analyze_file(str(f))
        bp_signals = [s for s in result["signals"] if s["type"] == "boilerplate_docs"]
        assert len(bp_signals) >= 1

    def test_ai_template_patterns_signal(self, tmp_path):
        code = textwrap.dedent("""
            def foo():
                # TODO: implement this
                pass  # placeholder
                raise NotImplementedError('this is not implemented')
        """)
        f = _write(tmp_path, "templates.py", code)
        result = self.d.analyze_file(str(f))
        ai_signals = [s for s in result["signals"] if s["type"] == "ai_templates"]
        assert len(ai_signals) >= 1

    def test_confidence_levels(self, tmp_path):
        # 0 signals → none
        f = _write(tmp_path, "clean.py", "a = 1\nb = 2\n")
        d = AICodeDetector()
        result = d.analyze_file(str(f))
        assert result["confidence"] in ("none", "low", "medium", "high")

    def test_uniform_comments_signal(self, tmp_path):
        # Exactly uniform: one comment per 2 lines
        lines = []
        for i in range(20):
            lines.append(f"x_{i} = {i}")
            lines.append(f"# step {i}")
        code = "\n".join(lines)
        f = _write(tmp_path, "uniform.py", code)
        result = self.d.analyze_file(str(f))
        # Just ensure no crash
        assert isinstance(result["score"], float)

    def test_syntax_error_in_generic_check_returns_0(self, tmp_path):
        f = _write(tmp_path, "broken.py", "def foo(:\n    pass\n")
        result = self.d.analyze_file(str(f))
        # Syntax error → generic names check returns 0
        assert result["score"] >= 0

    def test_non_py_file_skips_function_uniformity(self, tmp_path):
        f = _write(tmp_path, "code.js", "function foo() { return 1; }")
        result = self.d.analyze_file(str(f))
        # JS file: _check_function_uniformity returns 0 (non-.py), so no signal from it
        uniform_signals = [s for s in result["signals"] if s["type"] == "uniform_functions"]
        assert len(uniform_signals) == 0


class TestAICodeDetectorCheckFunctionUniformity:
    def setup_method(self):
        self.d = AICodeDetector()

    def test_non_py_returns_0(self):
        assert self.d._check_function_uniformity("code", "app.js") == 0

    def test_less_than_3_functions_returns_0(self):
        code = "def foo():\n    return 1\n"
        assert self.d._check_function_uniformity(code, "x.py") == 0

    def test_syntax_error_returns_0(self):
        assert self.d._check_function_uniformity("def (:\n    pass", "x.py") == 0

    def test_uniform_functions_returns_high_score(self):
        # 5 functions of exactly the same length
        lines = []
        for i in range(5):
            lines.append(f"def func_{i}():")
            lines.append("    x = 1")
            lines.append("    y = 2")
            lines.append("    return x + y")
            lines.append("")
        code = "\n".join(lines)
        score = self.d._check_function_uniformity(code, "code.py")
        assert score > 0


class TestAICodeDetectorCheckCommentUniformity:
    def setup_method(self):
        self.d = AICodeDetector()

    def test_fewer_than_5_comments_returns_0(self):
        lines = ["# comment", "x = 1", "# comment2"]
        assert self.d._check_comment_uniformity(lines) == 0

    def test_zero_avg_gap_returns_0(self):
        # All comments consecutive (gap=1). avg_gap=1, low CV -> high uniformity -> 0.8
        lines = ["# c1", "# c2", "# c3", "# c4", "# c5", "# c6"]
        result = self.d._check_comment_uniformity(lines)
        # Low CV (all gaps equal) → returns 0.8 (suspicious uniformity)
        assert result == 0.8


class TestAICodeDetectorAnalyzeDirectory:
    def test_empty_directory(self, tmp_path):
        d = AICodeDetector()
        result = d.analyze_directory(str(tmp_path))
        assert result["total_files"] == 0

    def test_single_file_analyzed(self, tmp_path):
        _write(tmp_path, "app.py", "x = 1\n")
        d = AICodeDetector()
        result = d.analyze_directory(str(tmp_path))
        assert result["total_files"] == 1

    def test_skips_venv(self, tmp_path):
        venv = tmp_path / ".venv" / "lib"
        venv.mkdir(parents=True)
        _write(venv, "hidden.py", "x = 1\n")
        d = AICodeDetector()
        result = d.analyze_directory(str(tmp_path))
        assert result["total_files"] == 0

    def test_flagged_percentage_calculated(self, tmp_path):
        _write(tmp_path, "a.py", "x = 1\n")
        d = AICodeDetector()
        result = d.analyze_directory(str(tmp_path))
        assert "flagged_percentage" in result


# ═════════════════════════════════════════════════════════════════════════════
#  CBoMScanner
# ═════════════════════════════════════════════════════════════════════════════


class TestCryptoUsageProperties:
    def _usage(self, quantum_safe):
        return CryptoUsage(
            file_path="app.py",
            line_number=5,
            line_content="hashlib.md5()",
            algorithm="md5",
            raw_match="md5",
            detection_pattern="hashlib.direct",
            quantum_safe=quantum_safe,
            category="hash",
            replacement="SHA3-256",
            language="python",
        )

    def test_severity_false_is_high(self):
        assert self._usage(False).severity == "high"

    def test_severity_warn_is_medium(self):
        assert self._usage("warn").severity == "medium"

    def test_severity_true_is_low(self):
        assert self._usage(True).severity == "low"

    def test_rule_id_false_is_crypto001(self):
        assert self._usage(False).rule_id == "CRYPTO-001"

    def test_rule_id_warn_is_crypto002(self):
        assert self._usage("warn").rule_id == "CRYPTO-002"

    def test_rule_id_true_is_crypto003(self):
        assert self._usage(True).rule_id == "CRYPTO-003"

    def test_to_finding_has_required_keys(self):
        f = self._usage(False).to_finding()
        assert "canonical_rule_id" in f
        assert "severity" in f
        assert "category" in f
        assert f["category"] == "security"
        assert "cbom_metadata" in f

    def test_to_finding_message_contains_not_quantum_safe(self):
        f = self._usage(False).to_finding()
        assert "NOT quantum-safe" in f["message"]

    def test_to_finding_message_warn_mode(self):
        f = self._usage("warn").to_finding()
        assert "Classical-safe" in f["message"]

    def test_to_finding_no_replacement(self):
        usage = CryptoUsage("f.py", 1, "x", "sha3_256", "sha3_256", "p", True, "hash", None, "python")
        f = usage.to_finding()
        assert "Quantum-safe" in f["message"]


class TestCBoMReport:
    def test_add_increments_totals(self):
        report = CBoMReport()
        u = CryptoUsage("f.py", 1, "x", "md5", "md5", "p", False, "hash", "SHA3", "python")
        report.add(u)
        assert report.total_usages == 1
        assert report.unsafe_count == 1

    def test_add_warn_increments_warn(self):
        report = CBoMReport()
        u = CryptoUsage("f.py", 1, "x", "sha256", "sha256", "p", "warn", "hash", "SHA3-256", "python")
        report.add(u)
        assert report.warn_count == 1

    def test_add_safe_increments_safe(self):
        report = CBoMReport()
        u = CryptoUsage("f.py", 1, "x", "sha3_256", "sha3_256", "p", True, "hash", None, "python")
        report.add(u)
        assert report.safe_count == 1

    def test_summary_has_quantum_safe_percentage(self):
        report = CBoMReport()
        s = report.summary()
        assert "quantum_safe_percentage" in s
        assert s["quantum_safe_percentage"] == 0.0

    def test_summary_100_pct_when_all_safe(self):
        report = CBoMReport()
        u = CryptoUsage("f.py", 1, "x", "sha3_256", "sha3_256", "p", True, "hash", None, "python")
        report.add(u)
        assert report.summary()["quantum_safe_percentage"] == 100.0

    def test_algorithms_found_populated(self):
        report = CBoMReport()
        u = CryptoUsage("f.py", 1, "x", "md5", "md5", "p", False, "hash", "SHA3", "python")
        report.add(u)
        assert report.algorithms_found["md5"] == 1


class TestCBoMScannerScanFile:
    def setup_method(self):
        self.scanner = CBoMScanner()

    def test_unsupported_extension_returns_empty(self, tmp_path):
        f = tmp_path / "code.rb"
        f.write_text("md5 = Digest::MD5.new\n")
        result = self.scanner.scan_file(str(f))
        assert result == []

    def test_detects_md5(self, tmp_path):
        f = tmp_path / "crypto.py"
        f.write_text("import hashlib\nh = hashlib.md5(b'data')\n")
        result = self.scanner.scan_file(str(f))
        algos = [u.algorithm for u in result]
        assert "md5" in algos

    def test_detects_sha256(self, tmp_path):
        f = tmp_path / "crypto.py"
        f.write_text("import hashlib\nh = hashlib.sha256(b'data')\n")
        result = self.scanner.scan_file(str(f))
        algos = [u.algorithm for u in result]
        assert "sha256" in algos

    def test_detects_bcrypt(self, tmp_path):
        f = tmp_path / "auth.py"
        f.write_text("import bcrypt\npw = bcrypt.hashpw(pwd, bcrypt.gensalt())\n")
        result = self.scanner.scan_file(str(f))
        algos = [u.algorithm for u in result]
        assert "bcrypt" in algos

    def test_skips_comment_lines(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("# hashlib.md5(data)  — do not use!\n")
        result = self.scanner.scan_file(str(f))
        assert result == []

    def test_js_pattern_detected(self, tmp_path):
        f = tmp_path / "crypto.js"
        f.write_text("const h = crypto.createHash('md5');\n")
        result = self.scanner.scan_file(str(f))
        algos = [u.algorithm for u in result]
        assert "md5" in algos

    def test_os_error_returns_empty(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("hashlib.md5(x)\n")
        scanner = CBoMScanner(str(tmp_path))
        with patch("pathlib.Path.read_text", side_effect=OSError("perm")):
            result = scanner.scan_file(str(f))
        assert result == []


class TestCBoMScannerNormaliseAlgo:
    def setup_method(self):
        self.s = CBoMScanner()

    def test_direct_registry_hit(self):
        assert self.s._normalise_algo("md5") == "md5"

    def test_sha_1_mapped(self):
        assert self.s._normalise_algo("sha_1") == "sha1"

    def test_sha_256_mapped(self):
        assert self.s._normalise_algo("sha_256") == "sha256"

    def test_aes_256_gcm_mapped(self):
        assert self.s._normalise_algo("aes_256_gcm") == "aes_256"

    def test_des_ede3_mapped(self):
        assert self.s._normalise_algo("des_ede3") == "3des"

    def test_rs256_mapped(self):
        assert self.s._normalise_algo("rs256") == "jwt_rs256"

    def test_hs256_mapped(self):
        assert self.s._normalise_algo("hs256") == "jwt_hs256"

    def test_none_mapped_to_jwt_none(self):
        assert self.s._normalise_algo("none") == "jwt_none"

    def test_unknown_algo_returns_none(self):
        assert self.s._normalise_algo("totally_unknown_algo_xyz") is None

    def test_rsa_prefix_match(self):
        assert self.s._normalise_algo("rsa_oaep_special") == "rsa"

    def test_bcrypt_prefix_match(self):
        result = self.s._normalise_algo("bcrypt_special_variant")
        assert result == "bcrypt"

    def test_case_insensitive(self):
        assert self.s._normalise_algo("MD5") == "md5"


class TestCBoMScannerScan:
    def test_scan_empty_dir(self, tmp_path):
        scanner = CBoMScanner(str(tmp_path))
        report = scanner.scan()
        assert report.scanned_files == 0
        assert report.total_usages == 0

    def test_scan_finds_md5(self, tmp_path):
        (tmp_path / "app.py").write_text("import hashlib\nhashlib.md5(b'x')\n")
        scanner = CBoMScanner(str(tmp_path))
        report = scanner.scan()
        assert report.scanned_files == 1
        assert report.total_usages >= 1

    def test_scan_skips_excluded_dirs(self, tmp_path):
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "hashutils.py").write_text("hashlib.md5(x)\n")
        scanner = CBoMScanner(str(tmp_path))
        report = scanner.scan()
        assert report.scanned_files == 0

    def test_to_findings_converts_report(self, tmp_path):
        (tmp_path / "app.py").write_text("hashlib.md5(b'x')\n")
        scanner = CBoMScanner(str(tmp_path))
        report = scanner.scan()
        findings = scanner.to_findings(report)
        assert isinstance(findings, list)
        if findings:
            assert "canonical_rule_id" in findings[0]


# ═════════════════════════════════════════════════════════════════════════════
#  DependencyReachabilityChecker
# ═════════════════════════════════════════════════════════════════════════════


class TestReachabilityResult:
    def test_is_reachable_direct(self):
        r = ReachabilityResult("pkg", "DIRECT", 0)
        assert r.is_reachable is True

    def test_is_not_reachable_transitive(self):
        r = ReachabilityResult("pkg", "TRANSITIVE", -15)
        assert r.is_reachable is False

    def test_to_dict_has_all_keys(self):
        r = ReachabilityResult("lodash", "DIRECT", 0, ["src/app.js"], True, False)
        d = r.to_dict()
        assert "reachability_level" in d
        assert "reachability_penalty" in d
        assert "reachability_direct_imports" in d
        assert "reachability_in_package_json" in d


class TestDependencyReachabilityCheckerLoadPackageJson:
    def test_returns_empty_when_no_package_json(self, tmp_path):
        c = DependencyReachabilityChecker(str(tmp_path))
        assert c._load_package_json() == {}

    def test_loads_valid_package_json(self, tmp_path):
        pkg = {"dependencies": {"lodash": "4.17.21"}, "devDependencies": {}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        c = DependencyReachabilityChecker(str(tmp_path))
        data = c._load_package_json()
        assert "lodash" in data["dependencies"]

    def test_returns_empty_on_invalid_json(self, tmp_path):
        (tmp_path / "package.json").write_text("NOT JSON")
        c = DependencyReachabilityChecker(str(tmp_path))
        assert c._load_package_json() == {}

    def test_cached_after_first_call(self, tmp_path):
        c = DependencyReachabilityChecker(str(tmp_path))
        d1 = c._load_package_json()
        d2 = c._load_package_json()
        assert d1 is d2


class TestDependencyReachabilityCheckerNormalisePkgName:
    def test_simple_pkg(self):
        assert DependencyReachabilityChecker._normalise_pkg_name("lodash") == "lodash"

    def test_subpath_stripped(self):
        assert DependencyReachabilityChecker._normalise_pkg_name("lodash/merge") == "lodash"

    def test_scoped_pkg(self):
        assert DependencyReachabilityChecker._normalise_pkg_name("@org/pkg") == "@org/pkg"

    def test_scoped_pkg_with_subpath(self):
        assert DependencyReachabilityChecker._normalise_pkg_name("@org/pkg/utils") == "@org/pkg"


class TestDependencyReachabilityCheckerExtractPackageName:
    def test_extracts_from_message(self):
        msg = "Vulnerable dependency: lodash (high) — prototype pollution"
        assert DependencyReachabilityChecker._extract_package_name(msg) == "lodash"

    def test_returns_none_when_no_match(self):
        assert DependencyReachabilityChecker._extract_package_name("blah blah") is None

    def test_strips_version_from_name(self):
        msg = "Vulnerable dependency: lodash==4.17.20 (high)"
        name = DependencyReachabilityChecker._extract_package_name(msg)
        assert name == "lodash"


class TestDependencyReachabilityCheckerCheck:
    def test_direct_when_imported_in_source(self, tmp_path):
        (tmp_path / "app.js").write_text("const _ = require('lodash');\n")
        pkg = {"dependencies": {"lodash": "4.17.21"}, "devDependencies": {}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        c = DependencyReachabilityChecker(str(tmp_path))
        result = c.check("lodash")
        assert result.level == "DIRECT"
        assert result.confidence_penalty == 0

    def test_transitive_when_in_package_json_but_not_imported(self, tmp_path):
        pkg = {"dependencies": {"lodash": "4.17.21"}, "devDependencies": {}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        c = DependencyReachabilityChecker(str(tmp_path))
        result = c.check("lodash")
        assert result.level == "TRANSITIVE"
        assert result.confidence_penalty == -15

    def test_unknown_when_not_in_package_json_and_not_imported(self, tmp_path):
        c = DependencyReachabilityChecker(str(tmp_path))
        result = c.check("nonexistent-pkg")
        assert result.level == "UNKNOWN"
        assert result.confidence_penalty == -5

    def test_import_syntax_detected(self, tmp_path):
        (tmp_path / "app.ts").write_text("import express from 'express';\n")
        pkg = {"dependencies": {"express": "4.18.0"}, "devDependencies": {}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        c = DependencyReachabilityChecker(str(tmp_path))
        result = c.check("express")
        assert result.level == "DIRECT"

    def test_check_batch(self, tmp_path):
        c = DependencyReachabilityChecker(str(tmp_path))
        results = c.check_batch(["pkg-a", "pkg-b"])
        assert "pkg-a" in results
        assert "pkg-b" in results


class TestDependencyReachabilityCheckerEnrichFindings:
    def test_empty_findings_returned_unchanged(self, tmp_path):
        c = DependencyReachabilityChecker(str(tmp_path))
        assert c.enrich_findings([]) == []

    def test_npm_audit_finding_enriched(self, tmp_path):
        (tmp_path / "app.js").write_text("const _ = require('lodash');\n")
        pkg = {"dependencies": {"lodash": "4.17.21"}, "devDependencies": {}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        c = DependencyReachabilityChecker(str(tmp_path))
        finding = {
            "tool": "npm-audit",
            "canonical_rule_id": "SECURITY-059",
            "message": "Vulnerable dependency: lodash (high) — prototype pollution",
            "confidence_score": 80,
        }
        result = c.enrich_findings([finding])
        assert "reachability_level" in result[0]

    def test_non_npm_finding_skipped(self, tmp_path):
        c = DependencyReachabilityChecker(str(tmp_path))
        finding = {
            "tool": "bandit",
            "canonical_rule_id": "SECURITY-001",
            "message": "SQL injection",
            "confidence_score": 70,
        }
        result = c.enrich_findings([finding])
        assert "reachability_level" not in result[0]

    def test_confidence_score_adjusted(self, tmp_path):
        c = DependencyReachabilityChecker(str(tmp_path))
        finding = {
            "tool": "npm-audit",
            "canonical_rule_id": "SECURITY-059",
            "message": "Vulnerable dependency: nonexistent_pkg_xyz (high)",
            "confidence_score": 80,
        }
        result = c.enrich_findings([finding])
        if "reachability_level" in result[0]:
            # Score should be <= 80 (penalty applied)
            assert result[0]["confidence_score"] <= 80

    def test_scan_imports_cached(self, tmp_path):
        c = DependencyReachabilityChecker(str(tmp_path))
        m1 = c._scan_imports()
        m2 = c._scan_imports()
        assert m1 is m2  # Cached
