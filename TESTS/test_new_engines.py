#!/usr/bin/env python3
"""
Tests for new ACR-QA engines:
- AI Code Detector
- SCA Scanner
- Secrets Detector
- Extended AutoFix (bare except, eval, dead code)
"""

import sys
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE.engines.ai_code_detector import AICodeDetector
from CORE.engines.secrets_detector import SecretsDetector
from CORE.engines.autofix import AutoFixEngine


# ─── AI Code Detector Tests ──────────────────────────────────


class TestAICodeDetector:
    """Tests for the AI code detection heuristics."""

    def setup_method(self):
        self.detector = AICodeDetector(threshold=0.4)

    def test_clean_code_not_flagged(self, tmp_path):
        """Well-written code should not be flagged as AI-generated."""
        code = '''
def calculate_fibonacci(n: int) -> list[int]:
    """Calculate Fibonacci sequence up to n terms."""
    if n <= 0:
        return []
    
    sequence = [0, 1]
    for i in range(2, n):
        next_val = sequence[i-1] + sequence[i-2]
        sequence.append(next_val)
    
    return sequence[:n]
'''
        f = tmp_path / "clean.py"
        f.write_text(code)
        result = self.detector.analyze_file(str(f))
        assert result["score"] < 0.5
        assert result["confidence"] in ("none", "low")

    def test_generic_names_detected(self, tmp_path):
        """Code with many generic variable names should trigger signal."""
        code = """
def process(data):
    result = []
    for item in data:
        value = item
        temp = value * 2
        output = temp + 1
        result.append(output)
    return result

def transform(input_data):
    res = []
    for element in input_data:
        val = element
        obj = val
        res.append(obj)
    return res
"""
        f = tmp_path / "generic.py"
        f.write_text(code)
        result = self.detector.analyze_file(str(f))
        has_generic_signal = any(
            s["type"] == "generic_names" for s in result["signals"]
        )
        assert has_generic_signal, "Should detect generic variable names"

    def test_ai_template_patterns(self, tmp_path):
        """Code with AI template patterns should trigger signal."""
        code = """
def feature_one():
    # TODO: implement this function
    pass  # placeholder

def feature_two():
    raise NotImplementedError("not implemented yet")

def feature_three():
    # TODO: add error handling
    pass  # stub
"""
        f = tmp_path / "templates.py"
        f.write_text(code)
        result = self.detector.analyze_file(str(f))
        has_template_signal = any(
            s["type"] == "ai_templates" for s in result["signals"]
        )
        assert has_template_signal, "Should detect AI template patterns"

    def test_empty_file_safe(self, tmp_path):
        """Empty file should return score 0."""
        f = tmp_path / "empty.py"
        f.write_text("")
        result = self.detector.analyze_file(str(f))
        assert result["score"] == 0
        assert result["confidence"] == "none"

    def test_nonexistent_file_safe(self):
        """Non-existent file should not crash."""
        result = self.detector.analyze_file("/nonexistent/file.py")
        assert result["score"] == 0
        assert "error" in result

    def test_directory_analysis(self, tmp_path):
        """Directory analysis should process multiple files."""
        for i in range(3):
            f = tmp_path / f"file_{i}.py"
            f.write_text(f"def func_{i}(): pass")

        result = self.detector.analyze_directory(str(tmp_path))
        assert result["total_files"] == 3
        assert "flagged_files" in result
        assert "flagged_percentage" in result


# ─── Secrets Detector Tests ──────────────────────────────────


class TestSecretsDetector:
    """Tests for the secrets detection engine."""

    def setup_method(self):
        self.detector = SecretsDetector()

    def test_detect_aws_key(self, tmp_path):
        """Should detect AWS access key patterns."""
        code = 'AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n'
        f = tmp_path / "config.py"
        f.write_text(code)
        result = self.detector.scan_file(str(f))
        assert len(result) > 0, "Should detect AWS key"

    def test_detect_hardcoded_password(self, tmp_path):
        """Should detect hardcoded passwords."""
        code = 'password = "super_secret_123"\ndb_password = "admin123"\n'
        f = tmp_path / "settings.py"
        f.write_text(code)
        result = self.detector.scan_file(str(f))
        assert len(result) > 0, "Should detect hardcoded password"

    def test_detect_jwt_token(self, tmp_path):
        """Should detect JWT tokens."""
        code = 'token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"\n'
        f = tmp_path / "auth.py"
        f.write_text(code)
        result = self.detector.scan_file(str(f))
        assert len(result) > 0, "Should detect JWT token"

    def test_clean_code_no_secrets(self, tmp_path):
        """Clean code should not trigger false positives."""
        code = """
import os

def get_config():
    api_key = os.environ.get("API_KEY")
    password = os.getenv("DB_PASSWORD")
    return {"key": api_key, "pass": password}
"""
        f = tmp_path / "clean_config.py"
        f.write_text(code)
        result = self.detector.scan_file(str(f))
        # Should have very few or no findings for env-var based code
        assert len(result) <= 1, "Should not flag environment variable usage"

    def test_directory_scan(self, tmp_path):
        """Directory scan should aggregate results."""
        (tmp_path / "file1.py").write_text('api_key = "sk-1234567890abcdef"\n')
        (tmp_path / "file2.py").write_text("def safe_func(): pass\n")

        result = self.detector.scan_directory(str(tmp_path))
        assert result["files_scanned"] >= 2
        assert "total_secrets" in result
        assert "severity_breakdown" in result

    def test_empty_file(self, tmp_path):
        """Empty file should return no findings."""
        f = tmp_path / "empty.py"
        f.write_text("")
        result = self.detector.scan_file(str(f))
        assert len(result) == 0


# ─── Extended AutoFix Tests ──────────────────────────────────


class TestExtendedAutoFix:
    """Tests for the 3 new AutoFix rules."""

    def setup_method(self):
        self.engine = AutoFixEngine()

    def test_bare_except_fix(self, tmp_path):
        """EXCEPT-001: Should replace bare except with except Exception."""
        code = "try:\n    x = 1\nexcept:\n    pass\n"
        f = tmp_path / "test.py"
        f.write_text(code)

        finding = {"file_path": str(f), "line": 3, "canonical_rule_id": "EXCEPT-001"}
        result = self.engine.fix_bare_except(finding)

        assert result is not None
        assert "except Exception:" in result["fixed"]

    def test_eval_usage_fix(self, tmp_path):
        """SECURITY-027: Should replace eval() with ast.literal_eval()."""
        code = "result = eval(user_input)\n"
        f = tmp_path / "test.py"
        f.write_text(code)

        finding = {"file_path": str(f), "line": 1, "canonical_rule_id": "SECURITY-027"}
        result = self.engine.fix_eval_usage(finding)

        assert result is not None
        assert "ast.literal_eval" in result["fixed"]

    def test_dead_code_fix(self, tmp_path):
        """DEAD-001: Should remove dead code after return."""
        code = "def func():\n    return 42\n    x = 1\n    y = 2\n"
        f = tmp_path / "test.py"
        f.write_text(code)

        finding = {"file_path": str(f), "line": 3, "canonical_rule_id": "DEAD-001"}
        result = self.engine.fix_dead_code(finding)

        assert result is not None

    def test_can_fix_new_rules(self):
        """All 3 new rules should be marked as fixable."""
        assert self.engine.can_fix("EXCEPT-001")
        assert self.engine.can_fix("SECURITY-027")
        assert self.engine.can_fix("DEAD-001")

    def test_original_rules_still_work(self):
        """Original fix rules should still be registered."""
        assert self.engine.can_fix("IMPORT-001")
        assert self.engine.can_fix("VAR-001")
        assert self.engine.can_fix("STRING-001")
        assert self.engine.can_fix("BOOL-001")
        assert self.engine.can_fix("TYPE-001")

    def test_unknown_rule_not_fixable(self):
        """Unknown rules should not be fixable."""
        assert not self.engine.can_fix("UNKNOWN-999")
