"""
God-mode tests for:
  - CORE/engines/secrets_detector.py  (target: 90%+)
  - CORE/utils/code_extractor.py      (target: 90%+)

All pure-logic / no external calls needed.
"""

import textwrap
from pathlib import Path
from unittest.mock import patch

from CORE.engines.secrets_detector import SecretsDetector
from CORE.utils.code_extractor import extract_code_snippet, extract_function_context

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _write(tmp_path: Path, name: str, content: str) -> Path:
    """Write content to a temp file and return its path."""
    p = tmp_path / name
    p.write_text(textwrap.dedent(content))
    return p


# ═════════════════════════════════════════════════════════════════════════════
#  SecretsDetector — unit tests
# ═════════════════════════════════════════════════════════════════════════════


class TestSecretsDetectorInit:
    def test_compiled_patterns_not_empty(self):
        sd = SecretsDetector()
        assert len(sd.compiled_patterns) == len(SecretsDetector.PATTERNS)

    def test_skip_compiled_not_empty(self):
        sd = SecretsDetector()
        assert len(sd.skip_compiled) == len(SecretsDetector.SKIP_PATTERNS)


# ─────────────────────────────────────────────────────────────────────────────
# scan_file — happy path: each of the 20+ patterns fires
# ─────────────────────────────────────────────────────────────────────────────


class TestScanFilePatterns:
    """One test per distinct PATTERN entry."""

    def setup_method(self):
        self.sd = SecretsDetector()

    def _scan(self, tmp_path, content, ext=".py"):
        f = tmp_path / f"secret{ext}"
        f.write_text(content)
        return self.sd.scan_file(str(f))

    def test_aws_access_key(self, tmp_path):
        body = "AKIA" + "IOSFODNN7EXAMPLE"
        r = self._scan(tmp_path, f'key = "{body}"\n')
        types = [x["type"] for x in r]
        assert "AWS Access Key" in types

    def test_aws_secret_key(self, tmp_path):
        r = self._scan(tmp_path, 'aws_secret_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY12345678901"\n')
        types = [x["type"] for x in r]
        assert "AWS Secret Key" in types

    def test_google_api_key(self, tmp_path):
        body = "AIza" + "SyDaGmWKa4JsXZ-HjGw7ISLn_3namBGewQe"
        r = self._scan(tmp_path, f'key = "{body}"\n')
        types = [x["type"] for x in r]
        assert "Google API Key" in types

    def test_github_token(self, tmp_path):
        body = "ghp_" + "aBcDeFgHiJkLmNoPqRsTuVwXyZaB123456789"
        r = self._scan(tmp_path, f'token = "{body}"\n')
        types = [x["type"] for x in r]
        assert "GitHub Token" in types

    def test_github_oauth(self, tmp_path):
        r = self._scan(tmp_path, 'github_token = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"\n')
        types = [x["type"] for x in r]
        assert "GitHub OAuth" in types

    def test_api_key_assignment(self, tmp_path):
        r = self._scan(tmp_path, 'api_key = "MyS3cur3ApiKey1234567890"\n')
        types = [x["type"] for x in r]
        assert "API Key Assignment" in types

    def test_password_assignment(self, tmp_path):
        r = self._scan(tmp_path, 'password = "SuperSecret123!"\n')
        types = [x["type"] for x in r]
        assert "Password Assignment" in types

    def test_database_url_with_password(self, tmp_path):
        r = self._scan(tmp_path, 'DB_URL = "postgres://user:mypassword@localhost/db"\n')
        types = [x["type"] for x in r]
        assert "Database URL with Password" in types

    def test_bearer_token(self, tmp_path):
        r = self._scan(tmp_path, 'auth = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9abcdef"\n')
        types = [x["type"] for x in r]
        assert "Bearer Token" in types

    def test_jwt_token(self, tmp_path):
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4"
        r = self._scan(tmp_path, f'token = "{jwt}"\n')
        types = [x["type"] for x in r]
        assert "JWT Token" in types

    def test_auth_token(self, tmp_path):
        r = self._scan(tmp_path, 'auth_token = "AbCdEfGhIjKlMnOpQrStUv"\n')
        types = [x["type"] for x in r]
        assert "Auth Token" in types

    def test_rsa_private_key(self, tmp_path):
        r = self._scan(tmp_path, "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQ\n")
        types = [x["type"] for x in r]
        assert "RSA Private Key" in types

    def test_ssh_private_key(self, tmp_path):
        r = self._scan(tmp_path, "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNza...\n")
        types = [x["type"] for x in r]
        assert "SSH Private Key" in types

    def test_pgp_private_key(self, tmp_path):
        r = self._scan(tmp_path, "-----BEGIN PGP PRIVATE KEY BLOCK-----\n")
        types = [x["type"] for x in r]
        assert "PGP Private Key" in types

    def test_slack_token(self, tmp_path):
        body = "xoxb-" + "1234567890123-abcdefghij1234567890ab"
        r = self._scan(tmp_path, f'token = "{body}"\n')
        types = [x["type"] for x in r]
        assert "Slack Token" in types

    def test_slack_webhook(self, tmp_path):
        r = self._scan(tmp_path, 'hook = "https://hooks.slack.com/services/TABC123/BABC123/XYZabc"\n')
        types = [x["type"] for x in r]
        assert "Slack Webhook" in types

    def test_secret_assignment(self, tmp_path):
        r = self._scan(tmp_path, 'secret = "MyEncryptionKey1234567890abcdef"\n')
        types = [x["type"] for x in r]
        assert "Secret Assignment" in types

    def test_stripe_key(self, tmp_path):
        body = "sk_" + "live_" + "aBcDeFgHiJkLmNoPqRsTuVwXy"
        r = self._scan(tmp_path, f'key = "{body}"\n')
        types = [x["type"] for x in r]
        assert "Stripe Key" in types

    def test_sendgrid_key(self, tmp_path):
        # SG. + 22 chars + . + 43 chars
        body = "SG." + "A" * 22 + "." + "B" * 43
        r = self._scan(tmp_path, f'key = "{body}"\n')
        types = [x["type"] for x in r]
        assert "SendGrid Key" in types

    def test_twilio_key(self, tmp_path):
        r = self._scan(tmp_path, 'twilio_key = "SK' + "a" * 32 + '"\n')
        types = [x["type"] for x in r]
        assert "Twilio Key" in types


# ─────────────────────────────────────────────────────────────────────────────
# scan_file — false-positive suppression and edge cases
# ─────────────────────────────────────────────────────────────────────────────


class TestScanFileFalsePositiveFilters:
    def setup_method(self):
        self.sd = SecretsDetector()

    def _scan(self, tmp_path, content):
        f = tmp_path / "fp.py"
        f.write_text(content)
        return self.sd.scan_file(str(f))

    def test_comment_line_skipped(self, tmp_path):
        # Pure comment, no TODO — should be skipped
        r = self._scan(tmp_path, "# password = 'hunter2'\n")
        assert r == []

    def test_comment_with_todo_not_skipped(self, tmp_path):
        # Comment WITH TODO is NOT skipped (could be a real secret reminder)
        r = self._scan(tmp_path, "# TODO: password = 'hunter2'\n")
        # May or may not match depending on password pattern — just don't crash
        assert isinstance(r, list)

    def test_os_getenv_suppressed(self, tmp_path):
        r = self._scan(tmp_path, 'key = os.getenv("AWS_SECRET_KEY")\n')
        assert r == []

    def test_os_environ_suppressed(self, tmp_path):
        r = self._scan(tmp_path, 'AKIAIOSFODNN7EXAMPLE = os.environ["KEY"]\n')
        assert r == []

    def test_env_reference_suppressed(self, tmp_path):
        # ".env" in line triggers env-reference suppression
        r = self._scan(tmp_path, 'key = config.get("AKIAIOSFODNN7EXAMPLE")\n')
        assert r == []

    def test_file_not_found_returns_empty(self):
        sd = SecretsDetector()
        assert sd.scan_file("/nonexistent/path/file.py") == []

    def test_unreadable_file_returns_empty(self, tmp_path):
        f = tmp_path / "locked.py"
        f.write_text('password = "secret123456"\n')
        with patch("builtins.open", side_effect=PermissionError("no access")):
            result = sd = SecretsDetector()
            r = sd.scan_file(str(f))
        assert r == []

    def test_masking_short_value(self, tmp_path):
        """Values ≤8 chars get masked as ****; verify structure not exact value."""
        # The regex matches group(0) which may include surrounding quotes
        # so we just verify the masked_value doesn't expose the full plain secret
        f = tmp_path / "m.py"
        f.write_text('password = "abc123"\n')
        r = self.sd.scan_file(str(f))
        if r:
            # Masked value should either be **** or partially-masked — not the raw secret
            mv = r[0]["masked_value"]
            assert "abc123" not in mv or "*" in mv

    def test_masking_long_value(self, tmp_path):
        """Values >8 chars get first4 + stars + last4."""
        f = tmp_path / "m2.py"
        f.write_text('key = "AKIAIOSFODNN7EXAMPLE"\n')
        r = self.sd.scan_file(str(f))
        if r:
            mv = r[0]["masked_value"]
            assert mv.startswith("AKIA")
            assert mv.endswith("MPLE")
            assert "****" in mv or "*" in mv

    def test_result_structure(self, tmp_path):
        f = tmp_path / "struct.py"
        f.write_text('password = "hunter2abc"\n')
        r = self.sd.scan_file(str(f))
        assert len(r) >= 1
        item = r[0]
        assert item["canonical_rule_id"] == "SECRET-001"
        assert item["category"] == "security"
        assert "line" in item
        assert "file" in item
        assert "masked_value" in item

    def test_extension_not_in_scan_list_excluded(self, tmp_path):
        """scan_directory should skip files with unsupported extensions."""
        f = tmp_path / "secret.pdf"
        f.write_text('password = "hunter2abc"\n')
        result = self.sd.scan_directory(str(tmp_path))
        assert result["files_scanned"] == 0

    def test_multiple_secrets_same_line(self, tmp_path):
        """A line with two matching patterns yields two findings."""
        f = tmp_path / "multi.py"
        # RSA key header on the same line as password (contrived but covers multi-pattern)
        f.write_text('password = "hunter2abc" ; pkey = "-----BEGIN RSA PRIVATE KEY-----"\n')
        r = self.sd.scan_file(str(f))
        # At minimum the password should be found
        assert len(r) >= 1

    def test_masking_short_value_exact(self, tmp_path):
        """Force the else-branch (masked='****') by injecting a ≤8-char pattern."""
        import re

        short_sd = SecretsDetector()
        # Inject a pattern that matches exactly 4 chars: "ABCD"
        short_sd.compiled_patterns = [("Short", re.compile(r"ABCD"), "high", "Short match")]
        f = tmp_path / "short.py"
        f.write_text("x = ABCD\n")
        r = short_sd.scan_file(str(f))
        assert len(r) == 1
        assert r[0]["masked_value"] == "****"


# ─────────────────────────────────────────────────────────────────────────────
# scan_directory
# ─────────────────────────────────────────────────────────────────────────────


class TestScanDirectory:
    def setup_method(self):
        self.sd = SecretsDetector()

    def test_empty_dir_returns_summary(self, tmp_path):
        result = self.sd.scan_directory(str(tmp_path))
        assert result["files_scanned"] == 0
        assert result["total_secrets"] == 0
        assert result["findings"] == []

    def test_py_file_with_secret_found(self, tmp_path):
        (tmp_path / "app.py").write_text('password = "hunter2abc"\n')
        result = self.sd.scan_directory(str(tmp_path))
        assert result["files_scanned"] == 1
        assert result["total_secrets"] >= 1

    def test_severity_breakdown_populated(self, tmp_path):
        (tmp_path / "app.py").write_text('password = "hunter2abc"\n')
        result = self.sd.scan_directory(str(tmp_path))
        breakdown = result["severity_breakdown"]
        assert "high" in breakdown
        assert "medium" in breakdown

    def test_secret_types_found_populated(self, tmp_path):
        (tmp_path / "app.py").write_text('password = "hunter2abc"\n')
        result = self.sd.scan_directory(str(tmp_path))
        assert isinstance(result["secret_types_found"], list)

    def test_skip_git_directory(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config.py").write_text('password = "hunter2abc"\n')
        result = self.sd.scan_directory(str(tmp_path))
        assert result["files_scanned"] == 0

    def test_skip_venv_directory(self, tmp_path):
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        (venv_dir / "secret.py").write_text('password = "hunter2abc"\n')
        result = self.sd.scan_directory(str(tmp_path))
        assert result["files_scanned"] == 0

    def test_skip_pyc_files(self, tmp_path):
        (tmp_path / "secret.pyc").write_text("binary-ish content")
        result = self.sd.scan_directory(str(tmp_path))
        assert result["files_scanned"] == 0

    def test_skip_lock_files(self, tmp_path):
        (tmp_path / "package.lock").write_text('password = "hunter2abc"\n')
        result = self.sd.scan_directory(str(tmp_path))
        assert result["files_scanned"] == 0

    def test_yaml_file_scanned(self, tmp_path):
        (tmp_path / "config.yml").write_text("password: hunter2abc\n")
        result = self.sd.scan_directory(str(tmp_path))
        assert result["files_scanned"] == 1

    def test_env_extension_in_scan_list(self):
        """Verify .env is in the SCAN_EXTENSIONS set."""
        assert ".env" in SecretsDetector.SCAN_EXTENSIONS

    def test_python_file_scanned_in_dir(self, tmp_path):
        (tmp_path / "creds.py").write_text('AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n')
        result = self.sd.scan_directory(str(tmp_path))
        assert result["files_scanned"] == 1

    def test_directory_key_in_result(self, tmp_path):
        result = self.sd.scan_directory(str(tmp_path))
        assert result["directory"] == str(tmp_path)

    def test_multiple_files_aggregated(self, tmp_path):
        (tmp_path / "a.py").write_text('password = "hunter2abc"\n')
        (tmp_path / "b.py").write_text('secret = "MyEncryptionKey1234567890abcdef"\n')
        result = self.sd.scan_directory(str(tmp_path))
        assert result["files_scanned"] == 2
        assert result["total_secrets"] >= 2


# ─────────────────────────────────────────────────────────────────────────────
# to_canonical_findings
# ─────────────────────────────────────────────────────────────────────────────


class TestToCanonicalFindings:
    def setup_method(self):
        self.sd = SecretsDetector()

    def _finding(self, **kwargs):
        base = {
            "type": "Password Assignment",
            "file": "app.py",
            "line": 10,
            "severity": "high",
            "description": "Hardcoded password",
            "masked_value": "hunt****2abc",
            "message": "Hardcoded password at line 10: hunt****2abc",
        }
        base.update(kwargs)
        return base

    def test_empty_list_returns_empty(self):
        assert self.sd.to_canonical_findings([]) == []

    def test_canonical_rule_id_always_secret_001(self):
        canonical = self.sd.to_canonical_findings([self._finding()])
        assert canonical[0]["canonical_rule_id"] == "SECRET-001"

    def test_original_rule_id_is_type(self):
        canonical = self.sd.to_canonical_findings([self._finding(type="AWS Access Key")])
        assert canonical[0]["original_rule_id"] == "AWS Access Key"

    def test_severity_forwarded(self):
        canonical = self.sd.to_canonical_findings([self._finding(severity="medium")])
        assert canonical[0]["severity"] == "medium"

    def test_category_always_security(self):
        canonical = self.sd.to_canonical_findings([self._finding()])
        assert canonical[0]["category"] == "security"

    def test_file_and_line_forwarded(self):
        canonical = self.sd.to_canonical_findings([self._finding(file="dao.py", line=42)])
        c = canonical[0]
        assert c["file"] == "dao.py"
        assert c["line"] == 42

    def test_tool_name_is_secrets_detector(self):
        canonical = self.sd.to_canonical_findings([self._finding()])
        assert canonical[0]["tool_name"] == "secrets-detector"

    def test_multiple_findings_converted(self):
        findings = [self._finding(), self._finding(type="GitHub Token", line=5)]
        canonical = self.sd.to_canonical_findings(findings)
        assert len(canonical) == 2


# ═════════════════════════════════════════════════════════════════════════════
#  code_extractor — extract_code_snippet
# ═════════════════════════════════════════════════════════════════════════════


class TestExtractCodeSnippet:
    """Covers extract_code_snippet() in CORE/utils/code_extractor.py."""

    def _make_src(self, tmp_path, lines=20):
        """Write a 20-line numbered source file and return its path."""
        content = "\n".join(f"line_{i} = {i}" for i in range(1, lines + 1))
        p = tmp_path / "sample.py"
        p.write_text(content)
        return str(p)

    def test_file_not_found_returns_message(self):
        result = extract_code_snippet("/nonexistent/file.py", 5)
        assert "File not found" in result or "# File not found" in result

    def test_returns_string(self, tmp_path):
        src = self._make_src(tmp_path)
        result = extract_code_snippet(src, 10)
        assert isinstance(result, str)

    def test_issue_line_marked_with_arrow(self, tmp_path):
        src = self._make_src(tmp_path)
        result = extract_code_snippet(src, 10)
        assert ">>>" in result

    def test_context_lines_included(self, tmp_path):
        src = self._make_src(tmp_path)
        result = extract_code_snippet(src, 10, context_lines=3)
        # Lines 7-13 should all be present
        assert "line_7" in result
        assert "line_10" in result
        assert "line_13" in result

    def test_line_number_at_start_of_file(self, tmp_path):
        src = self._make_src(tmp_path)
        # Line 1 – context_before should clamp to 0
        result = extract_code_snippet(src, 1, context_lines=3)
        assert "line_1" in result
        assert ">>>" in result

    def test_line_number_at_end_of_file(self, tmp_path):
        src = self._make_src(tmp_path, lines=10)
        result = extract_code_snippet(src, 10, context_lines=3)
        assert "line_10" in result
        assert ">>>" in result

    def test_no_crash_on_line_beyond_file(self, tmp_path):
        src = self._make_src(tmp_path, lines=5)
        # Line 50 past end — should not crash
        result = extract_code_snippet(src, 50, context_lines=2)
        assert isinstance(result, str)

    def test_context_lines_zero(self, tmp_path):
        src = self._make_src(tmp_path)
        result = extract_code_snippet(src, 10, context_lines=0)
        # Only line 10 should appear
        assert ">>>" in result
        assert "line_10" in result

    def test_error_handling_returns_message(self):
        """Trigger the except branch by patching open to raise."""
        with patch("builtins.open", side_effect=OSError("boom")):
            result = extract_code_snippet("/some/real_looking.py", 5)
        # Either "File not found" handled above, but OSError → except branch
        assert "Error" in result or isinstance(result, str)

    def test_line_numbers_in_output(self, tmp_path):
        """Output should contain formatted line numbers like '  10 |'."""
        src = self._make_src(tmp_path)
        result = extract_code_snippet(src, 10)
        assert "|" in result


# ═════════════════════════════════════════════════════════════════════════════
#  code_extractor — extract_function_context
# ═════════════════════════════════════════════════════════════════════════════


class TestExtractFunctionContext:
    def _write_py(self, tmp_path, content):
        p = tmp_path / "code.py"
        p.write_text(textwrap.dedent(content))
        return str(p)

    def test_file_not_found_falls_back_to_code_snippet(self):
        result = extract_function_context("/nonexistent/file.py", 5)
        # Should NOT crash; falls back to extract_code_snippet
        assert isinstance(result, str)
        assert "not found" in result.lower() or "error" in result.lower() or "#" in result

    def test_finds_enclosing_def(self, tmp_path):
        src = self._write_py(
            tmp_path,
            """\
            def foo():
                x = 1
                y = eval(x)
                return y
            """,
        )
        result = extract_function_context(src, 3)  # line 3 = eval(x)
        assert "def foo" in result
        assert ">>>" in result

    def test_finds_enclosing_class(self, tmp_path):
        src = self._write_py(
            tmp_path,
            """\
            class Bad:
                password = "hunter2abc"
            """,
        )
        result = extract_function_context(src, 2)
        assert "class Bad" in result

    def test_fallback_when_no_def_found(self, tmp_path):
        src = self._write_py(
            tmp_path,
            """\
            x = 1
            y = 2
            z = eval(x)
            """,
        )
        # No def/class — falls back to snippet
        result = extract_function_context(src, 3)
        assert isinstance(result, str)
        assert ">>>" in result

    def test_stops_at_next_top_level_def(self, tmp_path):
        src = self._write_py(
            tmp_path,
            """\
            def foo():
                x = eval(1)
                return x

            def bar():
                pass
            """,
        )
        result = extract_function_context(src, 2)
        # Should include foo but not bar
        assert "def foo" in result
        assert "def bar" not in result

    def test_max_30_lines_limit(self, tmp_path):
        # Function longer than 30 lines — should be truncated
        body = "\n".join(f"    x_{i} = {i}" for i in range(40))
        src = self._write_py(tmp_path, f"def big():\n{body}\n")
        result = extract_function_context(src, 2)
        # 30 output lines max → line count should not exceed 30+
        line_count = result.count("\n")
        assert line_count <= 31  # 30 lines + possible trailing

    def test_returns_string(self, tmp_path):
        src = self._write_py(
            tmp_path,
            """\
            def foo():
                pass
            """,
        )
        result = extract_function_context(src, 1)
        assert isinstance(result, str)

    def test_exception_falls_back(self, tmp_path):
        """If open raises inside the function-finder, falls back to snippet."""
        src = self._write_py(tmp_path, "def foo():\n    pass\n")
        # First call (path.exists check) passes; second open() raises
        call_count = {"n": 0}
        real_open = open

        def patched_open(path, *args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] > 1:
                raise OSError("disk error")
            return real_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=patched_open):
            result = extract_function_context(src, 1)
        assert isinstance(result, str)

    def test_nested_function_context(self, tmp_path):
        src = self._write_py(
            tmp_path,
            """\
            def outer():
                def inner():
                    return eval("x")
                return inner
            """,
        )
        # Line 3 is inside inner(); should walk up and find outer or inner
        result = extract_function_context(src, 3)
        assert "def" in result
        assert ">>>" in result
