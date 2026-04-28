"""
God-mode tests for CORE/utils/code_extractor.py (target: 95%+)
Pure file I/O logic — use tmp_path for real files.
"""

from pathlib import Path

from CORE.utils.code_extractor import extract_code_snippet, extract_function_context

# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────


def _file(tmp_path: Path, content: str, name: str = "code.py") -> Path:
    p = tmp_path / name
    p.write_text(content)
    return p


# ════════════════════════════════════════════════════════════
#  extract_code_snippet
# ════════════════════════════════════════════════════════════


class TestExtractCodeSnippet:
    def test_file_not_found(self):
        result = extract_code_snippet("/nonexistent/path.py", 1)
        assert "File not found" in result

    def test_marks_issue_line_with_arrows(self, tmp_path):
        f = _file(tmp_path, "line1\nline2\nline3\n")
        result = extract_code_snippet(str(f), 2)
        assert ">>>" in result
        assert "line2" in result

    def test_context_lines_default_3(self, tmp_path):
        content = "\n".join(f"line{i}" for i in range(1, 11)) + "\n"
        f = _file(tmp_path, content)
        result = extract_code_snippet(str(f), 5)
        # Should include lines 2-8 (3 before, target, 3 after)
        assert "line2" in result
        assert "line8" in result

    def test_custom_context_lines(self, tmp_path):
        content = "\n".join(f"L{i}" for i in range(1, 11)) + "\n"
        f = _file(tmp_path, content)
        result = extract_code_snippet(str(f), 5, context_lines=1)
        assert "L4" in result
        assert "L5" in result
        assert "L6" in result
        # L2 should NOT be in a context=1 window
        assert "L2" not in result

    def test_first_line_no_underflow(self, tmp_path):
        f = _file(tmp_path, "first\nsecond\nthird\n")
        result = extract_code_snippet(str(f), 1)
        assert "first" in result
        assert "Error" not in result

    def test_last_line_no_overflow(self, tmp_path):
        f = _file(tmp_path, "a\nb\nc\n")
        result = extract_code_snippet(str(f), 3)
        assert "c" in result
        assert "Error" not in result

    def test_line_numbers_in_output(self, tmp_path):
        f = _file(tmp_path, "x = 1\ny = 2\n")
        result = extract_code_snippet(str(f), 1)
        assert "1" in result
        assert "|" in result

    def test_only_arrow_on_issue_line(self, tmp_path):
        content = "a\nb\nc\nd\ne\n"
        f = _file(tmp_path, content)
        result = extract_code_snippet(str(f), 3)
        lines = result.split("\n")
        arrow_lines = [l for l in lines if ">>>" in l]
        assert len(arrow_lines) == 1
        assert "c" in arrow_lines[0]

    def test_returns_string(self, tmp_path):
        f = _file(tmp_path, "x = 1\n")
        assert isinstance(extract_code_snippet(str(f), 1), str)

    def test_empty_file(self, tmp_path):
        f = _file(tmp_path, "")
        result = extract_code_snippet(str(f), 1)
        # Empty file: no lines in range → empty snippet or no crash
        assert isinstance(result, str)

    def test_line_beyond_file_length(self, tmp_path):
        f = _file(tmp_path, "only one line\n")
        result = extract_code_snippet(str(f), 999)
        assert isinstance(result, str)

    def test_strips_trailing_whitespace(self, tmp_path):
        f = _file(tmp_path, "x = 1   \n")
        result = extract_code_snippet(str(f), 1)
        # rstrip applied — no trailing spaces in output
        for line in result.split("\n"):
            assert not line.endswith(" ")

    def test_context_0_returns_only_issue_line(self, tmp_path):
        f = _file(tmp_path, "a\nb\nc\n")
        result = extract_code_snippet(str(f), 2, context_lines=0)
        lines = [l for l in result.split("\n") if l.strip()]
        assert len(lines) == 1
        assert "b" in lines[0]

    def test_accepts_path_object(self, tmp_path):
        f = _file(tmp_path, "hello\n")
        result = extract_code_snippet(f, 1)
        assert "hello" in result


# ════════════════════════════════════════════════════════════
#  extract_function_context
# ════════════════════════════════════════════════════════════


class TestExtractFunctionContext:
    def test_file_not_found_falls_back_to_snippet(self, tmp_path):
        # Nonexistent file → fallback to extract_code_snippet → "File not found"
        result = extract_function_context("/nonexistent/path.py", 1)
        assert "File not found" in result

    def test_extracts_enclosing_def(self, tmp_path):
        content = "def foo():\n    x = 1\n    y = eval(x)\n    return y\n"
        f = _file(tmp_path, content)
        result = extract_function_context(str(f), 3)
        assert "def foo" in result
        assert "eval" in result

    def test_marks_issue_line_with_arrow(self, tmp_path):
        content = "def bar():\n    pass\n    evil()\n"
        f = _file(tmp_path, content)
        result = extract_function_context(str(f), 3)
        assert ">>>" in result

    def test_no_def_falls_back_to_snippet(self, tmp_path):
        content = "x = 1\ny = 2\nz = 3\n"
        f = _file(tmp_path, content)
        result = extract_function_context(str(f), 2)
        # Falls back to line-based snippet
        assert "y" in result or "2" in result

    def test_class_def_also_detected(self, tmp_path):
        content = "class Foo:\n    def bar(self):\n        bad_call()\n"
        f = _file(tmp_path, content)
        result = extract_function_context(str(f), 3)
        assert "class Foo" in result or "def bar" in result

    def test_capped_at_30_lines(self, tmp_path):
        # big function
        body = "\n".join(f"    x{i} = {i}" for i in range(50))
        content = f"def big():\n{body}\n"
        f = _file(tmp_path, content)
        result = extract_function_context(str(f), 5)
        assert result.count("\n") <= 30

    def test_stops_at_next_top_level_def(self, tmp_path):
        content = "def foo():\n    x = 1\ndef bar():\n    y = 2\n"
        f = _file(tmp_path, content)
        result = extract_function_context(str(f), 2)
        # Should include foo but not bar
        assert "def foo" in result
        assert "def bar" not in result

    def test_returns_string(self, tmp_path):
        f = _file(tmp_path, "x = 1\n")
        assert isinstance(extract_function_context(str(f), 1), str)

    def test_nested_indented_def_not_split(self, tmp_path):
        content = "def outer():\n    def inner():\n        bad()\n    return inner\n"
        f = _file(tmp_path, content)
        # Issue is inside inner — def_line should be outer or inner
        result = extract_function_context(str(f), 3)
        assert isinstance(result, str)
        assert "bad" in result
