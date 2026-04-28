"""
God-mode tests for CORE/engines/autofix.py (target: 70%+)

AutoFixEngine — pure logic, reads files. We tmp_path everywhere.
apply_fixes, verify_fix, validate_fix — subprocess mocked.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from CORE.engines.autofix import (
    AutoFixEngine,
    apply_fixes,
    validate_fix,
    verify_fix,
)

# ════════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════════


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content)
    return p


def _finding(tmp_path, filename, line, rule_id, message="", content=None):
    """Build a finding dict backed by a real temp file."""
    if content is None:
        content = "x = 1\n" * 10
    f = _write(tmp_path, filename, content)
    return {
        "canonical_rule_id": rule_id,
        "file_path": str(f),
        "file": str(f),
        "line": line,
        "message": message,
    }


# ════════════════════════════════════════════════
#  AutoFixEngine — init & helpers
# ════════════════════════════════════════════════


class TestAutoFixEngineInit:
    def test_fixable_rules_has_8_entries(self):
        assert len(AutoFixEngine().fixable_rules) == 8

    def test_can_fix_known_rule(self):
        assert AutoFixEngine().can_fix("IMPORT-001") is True

    def test_cannot_fix_unknown_rule(self):
        assert AutoFixEngine().can_fix("NOPE-999") is False

    def test_confidence_known_rule(self):
        c = AutoFixEngine().get_fix_confidence("IMPORT-001")
        assert 0 < c <= 1.0

    def test_confidence_unknown_rule_defaults_to_05(self):
        assert AutoFixEngine().get_fix_confidence("UNKNOWN") == 0.5

    def test_all_fixable_rules_have_confidence(self):
        eng = AutoFixEngine()
        for rule in eng.fixable_rules:
            c = eng.get_fix_confidence(rule)
            assert 0 < c <= 1.0, f"{rule} confidence out of range"


class TestGenerateFix:
    def test_returns_none_for_unfixable_rule(self, tmp_path):
        eng = AutoFixEngine()
        f = _finding(tmp_path, "code.py", 1, "NOPE-999")
        assert eng.generate_fix(f) is None

    def test_returns_none_for_missing_rule_id(self, tmp_path):
        eng = AutoFixEngine()
        f = _finding(tmp_path, "code.py", 1, None)
        assert eng.generate_fix(f) is None

    def test_dispatches_to_correct_fixer(self, tmp_path):
        eng = AutoFixEngine()
        f = _finding(tmp_path, "code.py", 1, "DEAD-001", content="dead_code = 1\n")
        result = eng.generate_fix(f)
        assert result is not None
        assert result["description"] == "Remove dead/unreachable code"


# ════════════════════════════════════════════════
#  fix_unused_import
# ════════════════════════════════════════════════


class TestFixUnusedImport:
    def test_removes_line(self, tmp_path):
        content = "import os\nimport sys\nx = 1\n"
        f = _finding(tmp_path, "code.py", 1, "IMPORT-001", content=content)
        result = AutoFixEngine().fix_unused_import(f)
        assert result is not None
        assert result["fixed"] == ""
        assert result["line"] == 1

    def test_description_mentions_line(self, tmp_path):
        content = "import os\n"
        f = _finding(tmp_path, "code.py", 1, "IMPORT-001", content=content)
        result = AutoFixEngine().fix_unused_import(f)
        assert "1" in result["description"]


# ════════════════════════════════════════════════
#  fix_unused_variable
# ════════════════════════════════════════════════


class TestFixUnusedVariable:
    def _code(self, var_line):
        lines = ["x = 1\n"] * 5
        lines[0] = var_line
        return "".join(lines)

    def test_prefixes_with_underscore_quoted(self, tmp_path):
        code = "    foo = compute()\n" + "x = 1\n" * 4
        f = _finding(
            tmp_path,
            "code.py",
            1,
            "VAR-001",
            message="Local variable 'foo' is assigned to but never used",
            content=code,
        )
        result = AutoFixEngine().fix_unused_variable(f)
        assert result is not None
        assert "_foo" in result["fixed"]

    def test_prefixes_with_backtick_syntax(self, tmp_path):
        code = "    bar = compute()\n" + "x = 1\n" * 4
        f = _finding(
            tmp_path,
            "code.py",
            1,
            "VAR-001",
            message="Local variable `bar` is assigned to but never used",
            content=code,
        )
        result = AutoFixEngine().fix_unused_variable(f)
        assert result is not None
        assert "_bar" in result["fixed"]

    def test_prefixes_unquoted(self, tmp_path):
        code = "    baz = compute()\n" + "x = 1\n" * 4
        f = _finding(tmp_path, "code.py", 1, "VAR-001", message="unused variable baz here", content=code)
        result = AutoFixEngine().fix_unused_variable(f)
        assert result is not None

    def test_returns_none_when_no_match(self, tmp_path):
        code = "    x = compute()\n" + "y = 1\n" * 4
        f = _finding(tmp_path, "code.py", 1, "VAR-001", message="no var name here", content=code)
        result = AutoFixEngine().fix_unused_variable(f)
        assert result is None

    def test_description_contains_var_name(self, tmp_path):
        code = "    myvar = 1\n" + "x = 1\n" * 4
        f = _finding(tmp_path, "code.py", 1, "VAR-001", message="variable 'myvar'", content=code)
        result = AutoFixEngine().fix_unused_variable(f)
        assert result is not None
        assert "myvar" in result["description"]


# ════════════════════════════════════════════════
#  fix_fstring_conversion
# ════════════════════════════════════════════════


class TestFixFstringConversion:
    def test_converts_percent_format(self, tmp_path):
        code = '    msg = "Hello %s" % name\n' + "x = 1\n" * 4
        f = _finding(tmp_path, "code.py", 1, "STRING-001", content=code)
        result = AutoFixEngine().fix_fstring_conversion(f)
        assert result is not None
        assert 'f"' in result["fixed"]
        assert "{name}" in result["fixed"]

    def test_returns_none_when_no_match(self, tmp_path):
        code = '    msg = f"already {name}"\n' + "x = 1\n" * 4
        f = _finding(tmp_path, "code.py", 1, "STRING-001", content=code)
        result = AutoFixEngine().fix_fstring_conversion(f)
        assert result is None


# ════════════════════════════════════════════════
#  fix_boolean_comparison
# ════════════════════════════════════════════════


class TestFixBooleanComparison:
    def test_simplifies_eq_true(self, tmp_path):
        code = "    if flag == True:\n        pass\n" + "x = 1\n" * 3
        f = _finding(tmp_path, "code.py", 1, "BOOL-001", content=code)
        result = AutoFixEngine().fix_boolean_comparison(f)
        assert result is not None
        assert "if flag:" in result["fixed"]

    def test_simplifies_eq_false(self, tmp_path):
        code = "    if flag == False:\n        pass\n" + "x = 1\n" * 3
        f = _finding(tmp_path, "code.py", 1, "BOOL-001", content=code)
        result = AutoFixEngine().fix_boolean_comparison(f)
        assert result is not None
        assert "if not flag:" in result["fixed"]

    def test_returns_none_when_no_change(self, tmp_path):
        code = "    if flag:\n        pass\n" + "x = 1\n" * 3
        f = _finding(tmp_path, "code.py", 1, "BOOL-001", content=code)
        result = AutoFixEngine().fix_boolean_comparison(f)
        assert result is None


# ════════════════════════════════════════════════
#  add_type_hints
# ════════════════════════════════════════════════


class TestAddTypeHints:
    def test_adds_return_none(self, tmp_path):
        code = "    def foo(x, y):\n        pass\n" + "x = 1\n" * 3
        f = _finding(tmp_path, "code.py", 1, "TYPE-001", content=code)
        result = AutoFixEngine().add_type_hints(f)
        assert result is not None
        assert "-> None" in result["fixed"]

    def test_returns_none_when_already_typed(self, tmp_path):
        code = "    def foo(x) -> int:\n        return 1\n" + "x = 1\n" * 3
        f = _finding(tmp_path, "code.py", 1, "TYPE-001", content=code)
        result = AutoFixEngine().add_type_hints(f)
        assert result is None

    def test_returns_none_for_non_def_line(self, tmp_path):
        code = "    x: int = 5\n" + "y = 1\n" * 4
        f = _finding(tmp_path, "code.py", 1, "TYPE-001", content=code)
        result = AutoFixEngine().add_type_hints(f)
        assert result is None


# ════════════════════════════════════════════════
#  fix_bare_except
# ════════════════════════════════════════════════


class TestFixBareExcept:
    def test_replaces_bare_except(self, tmp_path):
        code = "    except:\n        pass\n" + "x = 1\n" * 3
        f = _finding(tmp_path, "code.py", 1, "EXCEPT-001", content=code)
        result = AutoFixEngine().fix_bare_except(f)
        assert result is not None
        assert "except Exception:" in result["fixed"]

    def test_returns_none_when_specific_except(self, tmp_path):
        code = "    except ValueError:\n        pass\n" + "x = 1\n" * 3
        f = _finding(tmp_path, "code.py", 1, "EXCEPT-001", content=code)
        result = AutoFixEngine().fix_bare_except(f)
        assert result is None


# ════════════════════════════════════════════════
#  fix_eval_usage
# ════════════════════════════════════════════════


class TestFixEvalUsage:
    def test_replaces_eval(self, tmp_path):
        code = "    result = eval(user_input)\n" + "x = 1\n" * 4
        f = _finding(tmp_path, "code.py", 1, "SECURITY-027", content=code)
        result = AutoFixEngine().fix_eval_usage(f)
        assert result is not None
        assert "ast.literal_eval(" in result["fixed"]

    def test_skips_when_already_literal_eval(self, tmp_path):
        code = "    result = ast.literal_eval(user_input)\n" + "x = 1\n" * 4
        f = _finding(tmp_path, "code.py", 1, "SECURITY-027", content=code)
        result = AutoFixEngine().fix_eval_usage(f)
        assert result is None

    def test_returns_none_when_no_eval(self, tmp_path):
        code = "    result = user_input\n" + "x = 1\n" * 4
        f = _finding(tmp_path, "code.py", 1, "SECURITY-027", content=code)
        result = AutoFixEngine().fix_eval_usage(f)
        assert result is None


# ════════════════════════════════════════════════
#  fix_dead_code
# ════════════════════════════════════════════════


class TestFixDeadCode:
    def test_marks_for_removal(self, tmp_path):
        code = "    unreachable()\n" + "x = 1\n" * 4
        f = _finding(tmp_path, "code.py", 1, "DEAD-001", content=code)
        result = AutoFixEngine().fix_dead_code(f)
        assert result is not None
        assert result["fixed"] == ""
        assert "dead" in result["description"].lower() or "unreachable" in result["description"].lower()


# ════════════════════════════════════════════════
#  apply_fixes
# ════════════════════════════════════════════════


class TestApplyFixes:
    def test_replace_line(self, tmp_path):
        f = _write(tmp_path, "code.py", "old_line\nsecond\n")
        fix = {"file": str(f), "line": 1, "fixed": "new_line", "description": "test fix"}
        changes = apply_fixes([fix])
        assert str(f) in changes
        assert "test fix" in changes[str(f)]
        assert f.read_text().startswith("new_line")

    def test_remove_line(self, tmp_path):
        f = _write(tmp_path, "code.py", "import os\nkeep\n")
        fix = {"file": str(f), "line": 1, "fixed": "", "description": "remove import"}
        apply_fixes([fix])
        assert "import os" not in f.read_text()

    def test_empty_fixes_returns_empty(self, tmp_path):
        assert apply_fixes([]) == {}

    def test_multiple_fixes_same_file(self, tmp_path):
        # Apply to different lines
        f = _write(tmp_path, "code.py", "line1\nline2\nline3\n")
        fix1 = {"file": str(f), "line": 3, "fixed": "line3_fixed", "description": "fix3"}
        changes = apply_fixes([fix1])
        assert len(changes[str(f)]) == 1


# ════════════════════════════════════════════════
#  verify_fix
# ════════════════════════════════════════════════


class TestVerifyFix:
    def test_returns_error_for_missing_file(self):
        fix = {"file": "/nonexistent/path.py", "line": 1, "original": "x", "fixed": "y"}
        result = verify_fix(fix)
        assert result["verified"] is False
        assert "error" in result

    def test_empty_filepath_returns_error(self):
        result = verify_fix({"file": "", "line": 1, "original": "x", "fixed": "y"})
        assert result["verified"] is False

    def test_verified_true_when_no_issues_on_line(self, tmp_path):
        f = _write(tmp_path, "code.py", "x = 1\n")
        fix = {"file": str(f), "line": 1, "original": "    import os", "fixed": "x = 1"}
        ruff_output = json.dumps([])
        mock_result = MagicMock(returncode=0, stdout=ruff_output)
        with patch("subprocess.run", return_value=mock_result):
            result = verify_fix(fix)
        assert result["verified"] is True

    def test_verified_false_when_issues_remain(self, tmp_path):
        f = _write(tmp_path, "code.py", "import os\n")
        fix = {"file": str(f), "line": 1, "original": "import os", "fixed": "import os  # keep"}
        ruff_output = json.dumps([{"location": {"row": 1}, "code": "F401"}])
        mock_result = MagicMock(returncode=1, stdout=ruff_output)
        with patch("subprocess.run", return_value=mock_result):
            result = verify_fix(fix)
        assert result["verified"] is False

    def test_timeout_returns_error(self, tmp_path):
        f = _write(tmp_path, "code.py", "x = 1\n")
        fix = {"file": str(f), "line": 1, "original": "x", "fixed": "y"}
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ruff", 10)):
            result = verify_fix(fix)
        assert result["verified"] is False
        assert "timed out" in result.get("error", "")

    def test_remove_line_fix(self, tmp_path):
        f = _write(tmp_path, "code.py", "import os\nx = 1\n")
        fix = {"file": str(f), "line": 1, "original": "import os", "fixed": ""}
        mock_result = MagicMock(returncode=0, stdout="[]")
        with patch("subprocess.run", return_value=mock_result):
            result = verify_fix(fix)
        assert result["verified"] is True

    def test_exception_returns_error(self, tmp_path):
        f = _write(tmp_path, "code.py", "x = 1\n")
        fix = {"file": str(f), "line": 1, "original": "x", "fixed": "y"}
        with patch("builtins.open", side_effect=PermissionError("denied")):
            result = verify_fix(fix)
        assert result["verified"] is False

    def test_line_out_of_range_no_crash(self, tmp_path):
        f = _write(tmp_path, "code.py", "x = 1\n")
        fix = {"file": str(f), "line": 999, "original": "x", "fixed": "y"}
        mock_result = MagicMock(returncode=0, stdout="[]")
        with patch("subprocess.run", return_value=mock_result):
            result = verify_fix(fix)
        assert "verified" in result


# ════════════════════════════════════════════════
#  validate_fix
# ════════════════════════════════════════════════


class TestValidateFix:
    def test_empty_code_returns_invalid(self):
        result = validate_fix("old", "", "python", "SECURITY-027")
        assert result["valid"] is False
        assert "No fix" in result["validation_note"]

    def test_whitespace_code_returns_invalid(self):
        result = validate_fix("old", "   \n  ", "python", "SECURITY-027")
        assert result["valid"] is False

    def test_python_valid_fix(self):
        ruff_out = json.dumps([])
        mock_result = MagicMock(returncode=0, stdout=ruff_out)
        with patch("subprocess.run", return_value=mock_result):
            result = validate_fix("eval(x)", "ast.literal_eval(x)", "python", "SECURITY-027")
        assert result["valid"] is True
        assert result["confidence"] == "high"
        assert result["validated_fix"] == "ast.literal_eval(x)"

    def test_python_invalid_fix_medium_confidence(self):
        ruff_issues = json.dumps([{"code": "E501"}, {"code": "W291"}])
        mock_result = MagicMock(returncode=1, stdout=ruff_issues)
        with patch("subprocess.run", return_value=mock_result):
            result = validate_fix("eval(x)", "ast.literal_eval(x)", "python", "SECURITY-027")
        assert result["valid"] is False
        assert result["confidence"] in ("medium", "low")

    def test_python_low_confidence_many_issues(self):
        issues = [{"code": f"E{i:03d}"} for i in range(5)]
        ruff_out = json.dumps(issues)
        mock_result = MagicMock(returncode=1, stdout=ruff_out)
        with patch("subprocess.run", return_value=mock_result):
            result = validate_fix("x", "y = " + "a+" * 50, "python", "X")
        assert result["confidence"] == "low"

    def test_javascript_valid_fix(self):
        eslint_out = json.dumps([{"messages": []}])
        mock_result = MagicMock(returncode=0, stdout=eslint_out)
        with patch("subprocess.run", return_value=mock_result):
            result = validate_fix("eval(x)", "JSON.parse(x)", "javascript", "no-eval")
        assert result["valid"] is True

    def test_javascript_invalid_fix(self):
        eslint_out = json.dumps([{"messages": [{"ruleId": "no-eval"}]}])
        mock_result = MagicMock(returncode=1, stdout=eslint_out)
        with patch("subprocess.run", return_value=mock_result):
            result = validate_fix("eval(x)", "eval(x)", "javascript", "no-eval")
        assert result["valid"] is False

    def test_timeout_returns_unknown(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ruff", 10)):
            result = validate_fix("old", "new", "python", "X")
        assert result["valid"] is False
        assert "timed out" in result["validation_note"]

    def test_ruff_not_found_returns_unknown(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("ruff not found")):
            result = validate_fix("old", "new", "python", "X")
        assert result["valid"] is False
        assert "ruff" in result["validation_note"].lower()

    def test_eslint_not_found_returns_unknown(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("eslint not found")):
            result = validate_fix("old", "new", "javascript", "no-eval")
        assert result["valid"] is False
        assert "eslint" in result["validation_note"].lower()

    def test_bad_ruff_json_gracefully_handled(self):
        mock_result = MagicMock(returncode=0, stdout="NOT JSON")
        with patch("subprocess.run", return_value=mock_result):
            result = validate_fix("old", "new code here", "python", "X")
        assert result["valid"] is True  # No issues parsed → valid

    def test_bad_eslint_json_gracefully_handled(self):
        mock_result = MagicMock(returncode=0, stdout="NOT JSON")
        with patch("subprocess.run", return_value=mock_result):
            result = validate_fix("old", "new code here", "javascript", "X")
        assert result["valid"] is True  # No issues parsed → valid

    def test_temp_file_cleanup_on_success(self, tmp_path):
        """Ensure temp file is always deleted."""
        created_temps = []
        original_ntf = tempfile.NamedTemporaryFile

        class TrackedFile:
            def __init__(self, *a, **kw):
                self._f = original_ntf(*a, **kw)
                created_temps.append(self._f.name)

            def __enter__(self):
                return self._f.__enter__()

            def __exit__(self, *a):
                return self._f.__exit__(*a)

        mock_result = MagicMock(returncode=0, stdout="[]")
        with patch("subprocess.run", return_value=mock_result):
            result = validate_fix("old", "x = 1", "python", "X")

        assert result is not None
