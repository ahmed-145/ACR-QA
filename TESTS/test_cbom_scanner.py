"""Tests for CORE/engines/cbom_scanner.py — Feature 2 (NIST FIPS 203/204)"""

from __future__ import annotations

from CORE.engines.cbom_scanner import ALGO_REGISTRY, CBoMReport, CBoMScanner, CryptoUsage

# ── Helpers ───────────────────────────────────────────────────────────────────


def _usage(algo="md5", qs=False, cat="hash", replacement="SHA3-256", lang="python"):
    return CryptoUsage(
        file_path="app/crypto.py",
        line_number=10,
        line_content="hashlib.md5(data)",
        algorithm=algo,
        raw_match=algo,
        detection_pattern="hashlib.direct",
        quantum_safe=qs,
        category=cat,
        replacement=replacement,
        language=lang,
    )


# ── CryptoUsage ───────────────────────────────────────────────────────────────


class TestCryptoUsage:
    def test_severity_unsafe(self):
        assert _usage(qs=False).severity == "high"

    def test_severity_warn(self):
        assert _usage(qs="warn").severity == "medium"

    def test_severity_safe(self):
        assert _usage(qs=True).severity == "low"

    def test_rule_id_unsafe(self):
        assert _usage(qs=False).rule_id == "CRYPTO-001"

    def test_rule_id_warn(self):
        assert _usage(qs="warn").rule_id == "CRYPTO-002"

    def test_rule_id_safe(self):
        assert _usage(qs=True).rule_id == "CRYPTO-003"

    def test_to_finding_keys(self):
        f = _usage().to_finding()
        for key in [
            "tool",
            "canonical_rule_id",
            "canonical_severity",
            "file_path",
            "line_number",
            "message",
            "cbom_metadata",
        ]:
            assert key in f

    def test_to_finding_unsafe_message(self):
        f = _usage(algo="md5", qs=False).to_finding()
        assert "NOT quantum-safe" in f["message"]

    def test_to_finding_warn_message(self):
        f = _usage(algo="sha256", qs="warn").to_finding()
        assert "Classical-safe" in f["message"]

    def test_to_finding_safe_message(self):
        f = _usage(algo="aes_256", qs=True, replacement=None).to_finding()
        assert "Quantum-safe" in f["message"]

    def test_to_finding_includes_replacement(self):
        f = _usage(algo="md5", qs=False, replacement="SHA3-256").to_finding()
        assert "SHA3-256" in f["message"]

    def test_to_finding_no_replacement_when_none(self):
        f = _usage(algo="aes_256", qs=True, replacement=None).to_finding()
        assert "Consider" not in f["message"]

    def test_to_finding_cbom_metadata(self):
        f = _usage(algo="rsa", qs=False, cat="asymmetric").to_finding()
        meta = f["cbom_metadata"]
        assert meta["algorithm"] == "rsa"
        assert meta["quantum_safe"] is False
        assert meta["category"] == "asymmetric"

    def test_to_finding_tool_is_cbom(self):
        assert _usage().to_finding()["tool"] == "cbom"

    def test_to_finding_category_is_security(self):
        assert _usage().to_finding()["category"] == "security"


# ── CBoMReport ────────────────────────────────────────────────────────────────


class TestCBoMReport:
    def test_initial_state(self):
        r = CBoMReport()
        assert r.total_usages == 0
        assert r.unsafe_count == 0
        assert r.warn_count == 0
        assert r.safe_count == 0

    def test_add_unsafe(self):
        r = CBoMReport()
        r.add(_usage(qs=False))
        assert r.unsafe_count == 1
        assert r.total_usages == 1

    def test_add_warn(self):
        r = CBoMReport()
        r.add(_usage(qs="warn"))
        assert r.warn_count == 1

    def test_add_safe(self):
        r = CBoMReport()
        r.add(_usage(qs=True))
        assert r.safe_count == 1

    def test_algorithms_found_tracked(self):
        r = CBoMReport()
        r.add(_usage(algo="md5"))
        r.add(_usage(algo="md5"))
        r.add(_usage(algo="sha256"))
        assert r.algorithms_found["md5"] == 2
        assert r.algorithms_found["sha256"] == 1

    def test_summary_keys(self):
        r = CBoMReport()
        s = r.summary()
        for key in [
            "scanned_files",
            "total_usages",
            "unsafe_count",
            "warn_count",
            "safe_count",
            "algorithms_found",
            "quantum_safe_percentage",
        ]:
            assert key in s

    def test_summary_percentage_zero_when_empty(self):
        assert CBoMReport().summary()["quantum_safe_percentage"] == 0.0

    def test_summary_percentage_all_safe(self):
        r = CBoMReport()
        r.add(_usage(qs=True))
        r.add(_usage(qs=True))
        assert r.summary()["quantum_safe_percentage"] == 100.0

    def test_summary_percentage_mixed(self):
        r = CBoMReport()
        r.add(_usage(qs=True))
        r.add(_usage(qs=False))
        assert r.summary()["quantum_safe_percentage"] == 50.0


# ── CBoMScanner._normalise_algo ───────────────────────────────────────────────


class TestNormaliseAlgo:
    def setup_method(self):
        self.scanner = CBoMScanner()

    def test_direct_registry_hit(self):
        assert self.scanner._normalise_algo("md5") == "md5"
        assert self.scanner._normalise_algo("sha256") == "sha256"
        assert self.scanner._normalise_algo("rsa") == "rsa"

    def test_case_insensitive(self):
        assert self.scanner._normalise_algo("MD5") == "md5"
        assert self.scanner._normalise_algo("SHA256") == "sha256"

    def test_fuzzy_mapping_sha_256(self):
        assert self.scanner._normalise_algo("SHA-256") == "sha256"

    def test_fuzzy_mapping_aes_256_gcm(self):
        assert self.scanner._normalise_algo("AES-256-GCM") == "aes_256"

    def test_fuzzy_mapping_3des(self):
        assert self.scanner._normalise_algo("DES-EDE3") == "3des"

    def test_fuzzy_mapping_rs256(self):
        assert self.scanner._normalise_algo("RS256") == "jwt_rs256"

    def test_fuzzy_mapping_hs256(self):
        assert self.scanner._normalise_algo("HS256") == "jwt_hs256"

    def test_fuzzy_mapping_none_jwt(self):
        assert self.scanner._normalise_algo("none") == "jwt_none"

    def test_prefix_rsa_variant(self):
        assert self.scanner._normalise_algo("rsa_oaep") == "rsa"

    def test_prefix_ecdsa(self):
        assert self.scanner._normalise_algo("ecdsa_with_sha256") == "ecdsa"

    def test_prefix_bcrypt(self):
        assert self.scanner._normalise_algo("bcrypt") == "bcrypt"

    def test_prefix_argon2(self):
        assert self.scanner._normalise_algo("argon2id") == "argon2"

    def test_prefix_pbkdf2(self):
        assert self.scanner._normalise_algo("pbkdf2_sha256") == "pbkdf2_sha256"

    def test_unknown_returns_none(self):
        assert self.scanner._normalise_algo("unknownalgo123") is None

    def test_strips_quotes(self):
        assert self.scanner._normalise_algo("'md5'") == "md5"
        assert self.scanner._normalise_algo('"sha256"') == "sha256"


# ── CBoMScanner._scan_file (via tmp files) ────────────────────────────────────


class TestScanFile:
    def setup_method(self):
        self.scanner = CBoMScanner()

    def _scan_python(self, code: str, tmp_path) -> list:
        f = tmp_path / "test_crypto.py"
        f.write_text(code)
        return self.scanner.scan_file(str(f))

    def _scan_js(self, code: str, tmp_path) -> list:
        f = tmp_path / "test_crypto.js"
        f.write_text(code)
        return self.scanner.scan_file(str(f))

    def test_detects_hashlib_md5(self, tmp_path):
        findings = self._scan_python("import hashlib\nhashlib.md5(data)\n", tmp_path)
        assert any(u.algorithm == "md5" for u in findings)

    def test_detects_hashlib_sha256(self, tmp_path):
        findings = self._scan_python("hashlib.sha256(data)\n", tmp_path)
        assert any(u.algorithm == "sha256" for u in findings)

    def test_detects_hashlib_new(self, tmp_path):
        findings = self._scan_python("hashlib.new('md5')\n", tmp_path)
        assert any(u.algorithm == "md5" for u in findings)

    def test_detects_rsa_import(self, tmp_path):
        findings = self._scan_python("import rsa\n", tmp_path)
        assert any(u.algorithm == "rsa" for u in findings)

    def test_detects_bcrypt(self, tmp_path):
        findings = self._scan_python("import bcrypt\nbcrypt.hashpw(pw, salt)\n", tmp_path)
        assert any(u.algorithm == "bcrypt" for u in findings)

    def test_skips_comment_lines(self, tmp_path):
        findings = self._scan_python("# hashlib.md5(data)\n", tmp_path)
        assert len(findings) == 0

    def test_js_detects_create_hash(self, tmp_path):
        findings = self._scan_js("crypto.createHash('md5')\n", tmp_path)
        assert any(u.algorithm == "md5" for u in findings)

    def test_js_detects_sha256(self, tmp_path):
        findings = self._scan_js("crypto.createHash('sha256')\n", tmp_path)
        assert any(u.algorithm == "sha256" for u in findings)

    def test_js_skips_comment(self, tmp_path):
        findings = self._scan_js("// crypto.createHash('md5')\n", tmp_path)
        assert len(findings) == 0

    def test_unsupported_extension_returns_empty(self, tmp_path):
        f = tmp_path / "test.rb"
        f.write_text("some ruby code")
        assert self.scanner.scan_file(str(f)) == []

    def test_unreadable_file_returns_empty(self, tmp_path):
        # Pass a non-existent path
        assert self.scanner.scan_file("/nonexistent/path/file.py") == []

    def test_finding_has_correct_line_number(self, tmp_path):
        code = "x = 1\ny = 2\nhashlib.md5(data)\n"
        findings = self._scan_python(code, tmp_path)
        assert any(u.line_number == 3 for u in findings)

    def test_finding_language_python(self, tmp_path):
        findings = self._scan_python("hashlib.md5(data)\n", tmp_path)
        assert all(u.language == "python" for u in findings)

    def test_finding_language_javascript(self, tmp_path):
        findings = self._scan_js("crypto.createHash('md5')\n", tmp_path)
        assert all(u.language == "javascript" for u in findings)


# ── CBoMScanner.scan (directory) ──────────────────────────────────────────────


class TestScanDirectory:
    def test_scan_empty_dir(self, tmp_path):
        scanner = CBoMScanner(target_dir=str(tmp_path))
        report = scanner.scan()
        assert report.total_usages == 0
        assert report.scanned_files == 0

    def test_scan_counts_files(self, tmp_path):
        (tmp_path / "a.py").write_text("hashlib.md5(x)\n")
        (tmp_path / "b.py").write_text("hashlib.sha256(x)\n")
        scanner = CBoMScanner(target_dir=str(tmp_path))
        report = scanner.scan()
        assert report.scanned_files == 2

    def test_scan_finds_unsafe(self, tmp_path):
        (tmp_path / "crypto.py").write_text("hashlib.md5(x)\n")
        scanner = CBoMScanner(target_dir=str(tmp_path))
        report = scanner.scan()
        assert report.unsafe_count >= 1

    def test_scan_excludes_node_modules(self, tmp_path):
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "pkg.py").write_text("hashlib.md5(x)\n")
        scanner = CBoMScanner(target_dir=str(tmp_path))
        report = scanner.scan()
        assert report.total_usages == 0

    def test_scan_excludes_venv(self, tmp_path):
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "lib.py").write_text("hashlib.md5(x)\n")
        scanner = CBoMScanner(target_dir=str(tmp_path))
        report = scanner.scan()
        assert report.total_usages == 0

    def test_to_findings_returns_dicts(self, tmp_path):
        (tmp_path / "c.py").write_text("hashlib.md5(x)\n")
        scanner = CBoMScanner(target_dir=str(tmp_path))
        report = scanner.scan()
        findings = scanner.to_findings(report)
        assert isinstance(findings, list)
        assert all(isinstance(f, dict) for f in findings)

    def test_scan_js_file(self, tmp_path):
        (tmp_path / "app.js").write_text("crypto.createHash('sha1')\n")
        scanner = CBoMScanner(target_dir=str(tmp_path))
        report = scanner.scan()
        assert report.total_usages >= 1

    def test_scan_ts_file(self, tmp_path):
        (tmp_path / "app.ts").write_text("crypto.createHash('md5')\n")
        scanner = CBoMScanner(target_dir=str(tmp_path))
        report = scanner.scan()
        assert report.total_usages >= 1


# ── ALGO_REGISTRY completeness ────────────────────────────────────────────────


class TestAlgoRegistry:
    def test_all_entries_have_required_keys(self):
        for algo, info in ALGO_REGISTRY.items():
            assert "quantum_safe" in info, f"{algo} missing quantum_safe"
            assert "category" in info, f"{algo} missing category"
            assert "replacement" in info, f"{algo} missing replacement"

    def test_quantum_safe_values_are_valid(self):
        valid = {True, False, "warn"}
        for algo, info in ALGO_REGISTRY.items():
            assert info["quantum_safe"] in valid, f"{algo} has invalid quantum_safe"

    def test_known_unsafe_algos(self):
        for algo in ["md5", "sha1", "des", "rsa", "ecdsa", "rc4"]:
            assert ALGO_REGISTRY[algo]["quantum_safe"] is False

    def test_known_safe_algos(self):
        for algo in ["sha3_256", "aes_256", "bcrypt", "argon2", "blake2b"]:
            assert ALGO_REGISTRY[algo]["quantum_safe"] is True

    def test_known_warn_algos(self):
        for algo in ["sha256", "aes_128", "pbkdf2"]:
            assert ALGO_REGISTRY[algo]["quantum_safe"] == "warn"
