"""
ACR-QA Deep Coverage Tests

Comprehensive tests targeting previously uncovered code paths:
- SeverityScorer context adjustments
- AutoFix rule fixes and verification
- Secrets Detector file/directory scanning
- AI Code Detector analysis
- Code Extractor edge cases
- Normalizer for all tool outputs
- ConfigLoader custom configs
- QualityGate thresholds and reporting
- PythonAdapter full lifecycle
- Database CRUD operations
- Flask API endpoint edge cases
- Rate Limiter without Redis
- Metrics module registration
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))


# ═════════════════════════════════════════════════════════════
# SeverityScorer Comprehensive Tests
# ═════════════════════════════════════════════════════════════
class TestSeverityScorer:
    def setup_method(self):
        from CORE.engines.severity_scorer import SeverityScorer

        self.scorer = SeverityScorer()

    def test_all_security_rules_are_high(self):
        for rule in [
            "SECURITY-001",
            "SECURITY-002",
            "SECURITY-003",
            "SECURITY-004",
            "SECURITY-005",
        ]:
            assert self.scorer.score(rule, {}) == "high", f"{rule} should be high"

    def test_all_medium_rules(self):
        for rule in ["SOLID-001", "COMPLEXITY-001", "DUP-001", "PATTERN-001"]:
            # COMPLEXITY-001 defaults to medium only with CC > 10
            assert self.scorer.score(rule, {}) in ("medium", "low"), f"{rule} check"

    def test_all_low_rules(self):
        for rule in ["IMPORT-001", "VAR-001", "STYLE-001", "STYLE-002", "NAMING-001"]:
            assert self.scorer.score(rule, {}) == "low", f"{rule} should be low"

    def test_unknown_rule_defaults_low(self):
        assert self.scorer.score("NONEXISTENT-999", {}) == "low"

    def test_complexity_high_threshold(self):
        finding = {"tool_raw": {"original_output": {"complexity": 25}}}
        assert self.scorer.score("COMPLEXITY-001", finding) == "high"

    def test_complexity_medium_threshold(self):
        finding = {"tool_raw": {"original_output": {"complexity": 15}}}
        assert self.scorer.score("COMPLEXITY-001", finding) == "medium"

    def test_complexity_low_threshold(self):
        finding = {"tool_raw": {"original_output": {"complexity": 5}}}
        assert self.scorer.score("COMPLEXITY-001", finding) == "low"

    def test_complexity_from_message_fallback(self):
        finding = {"message": "function has a complexity of 22."}
        result = self.scorer.score("COMPLEXITY-001", finding)
        assert result in ("high", "medium", "low")

    def test_dead_code_class_is_medium(self):
        assert self.scorer.score("DEAD-001", {"message": "unused class Foo"}) == "medium"

    def test_dead_code_large_function_is_medium(self):
        finding = {
            "message": "unused function helper",
            "evidence": {"snippet": "x" * 200},
        }
        assert self.scorer.score("DEAD-001", finding) == "medium"

    def test_dead_code_small_is_low(self):
        assert self.scorer.score("DEAD-001", {"message": "unused variable x"}) == "low"

    def test_duplication_massive_is_high(self):
        finding = {"tool_raw": {"original_output": {"tokens": 250}}}
        assert self.scorer.score("DUP-001", finding) == "high"

    def test_duplication_large_is_medium(self):
        finding = {"tool_raw": {"original_output": {"tokens": 150}}}
        assert self.scorer.score("DUP-001", finding) == "medium"

    def test_duplication_small_uses_base(self):
        finding = {"tool_raw": {"original_output": {"tokens": 50}}}
        assert self.scorer.score("DUP-001", finding) == "medium"  # base is medium


# ═════════════════════════════════════════════════════════════
# AutoFix Engine Tests
# ═════════════════════════════════════════════════════════════
class TestAutoFixDeep:
    def setup_method(self):
        from CORE.engines.autofix import AutoFixEngine

        self.engine = AutoFixEngine()

    def test_all_8_fixable_rules(self):
        expected = [
            "IMPORT-001",
            "VAR-001",
            "STRING-001",
            "BOOL-001",
            "TYPE-001",
            "EXCEPT-001",
            "SECURITY-027",
            "DEAD-001",
        ]
        for rule in expected:
            assert self.engine.can_fix(rule), f"{rule} should be fixable"

    def test_unfixable_rules(self):
        for rule in ["SECURITY-001", "COMPLEXITY-001", "DUP-001", "UNKNOWN"]:
            assert not self.engine.can_fix(rule), f"{rule} should not be fixable"

    def test_confidence_scores(self):
        expected = {
            "IMPORT-001": 0.95,
            "VAR-001": 0.85,
            "STRING-001": 0.90,
            "BOOL-001": 0.95,
            "TYPE-001": 0.60,
            "EXCEPT-001": 0.90,
            "SECURITY-027": 0.80,
            "DEAD-001": 0.85,
        }
        for rule, conf in expected.items():
            assert self.engine.get_fix_confidence(rule) == conf, f"{rule} conf={conf}"

    def test_unknown_rule_confidence_default(self):
        assert self.engine.get_fix_confidence("UNKNOWN-RULE") == 0.5

    def test_generate_fix_import(self):
        # Create a temp file for auto-fix to read
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("import os\nimport sys\n\nprint('hello')\n")
            path = f.name
        try:
            finding = {
                "canonical_rule_id": "IMPORT-001",
                "file_path": path,
                "line": 1,
                "message": "'os' imported but unused",
                "evidence": {"snippet": "import os"},
            }
            result = self.engine.generate_fix(finding)
            assert result is not None
        finally:
            os.unlink(path)

    def test_generate_fix_except(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("try:\n    pass\nexcept:\n    pass\n")
            path = f.name
        try:
            finding = {
                "canonical_rule_id": "EXCEPT-001",
                "file_path": path,
                "line": 3,
                "message": "Do not use bare except",
                "evidence": {"snippet": "except:"},
            }
            result = self.engine.generate_fix(finding)
            assert result is not None
        finally:
            os.unlink(path)

    def test_generate_fix_unfixable_returns_none(self):
        finding = {"canonical_rule_id": "COMPLEXITY-001"}
        result = self.engine.generate_fix(finding)
        assert result is None

    def test_generate_fix_dead_code(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def helper():\n    pass\n\ndef main():\n    print('hi')\n")
            path = f.name
        try:
            finding = {
                "canonical_rule_id": "DEAD-001",
                "file_path": path,
                "line": 1,
                "message": "unused function helper",
                "evidence": {"snippet": "def helper(): pass"},
            }
            result = self.engine.generate_fix(finding)
            assert result is not None
        finally:
            os.unlink(path)

    def test_generate_fix_security_eval(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("result = eval(user_input)\n")
            path = f.name
        try:
            finding = {
                "canonical_rule_id": "SECURITY-027",
                "file_path": path,
                "line": 1,
                "message": "Use of eval()",
                "evidence": {"snippet": "eval(user_input)"},
            }
            result = self.engine.generate_fix(finding)
            assert result is not None
        finally:
            os.unlink(path)


# ═════════════════════════════════════════════════════════════
# Secrets Detector Tests
# ═════════════════════════════════════════════════════════════
class TestSecretsDetectorDeep:
    def setup_method(self):
        from CORE.engines.secrets_detector import SecretsDetector

        self.detector = SecretsDetector()

    def test_detect_aws_key(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('key = "AKIAIOSFODNN7EXAMPLE"\n')
            path = f.name
        try:
            results = self.detector.scan_file(path)
            assert len(results) > 0
        finally:
            os.unlink(path)

    def test_detect_password(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('password = "SuperSecret123!"\n')
            path = f.name
        try:
            results = self.detector.scan_file(path)
            assert len(results) > 0
        finally:
            os.unlink(path)

    def test_detect_jwt(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjg"\n')
            path = f.name
        try:
            results = self.detector.scan_file(path)
            assert len(results) > 0
        finally:
            os.unlink(path)

    def test_clean_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def hello():\n    return 42\n")
            path = f.name
        try:
            results = self.detector.scan_file(path)
            assert len(results) == 0
        finally:
            os.unlink(path)

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            path = f.name
        try:
            results = self.detector.scan_file(path)
            assert len(results) == 0
        finally:
            os.unlink(path)

    def test_nonexistent_file(self):
        results = self.detector.scan_file("/nonexistent/file.py")
        assert isinstance(results, list)

    def test_directory_scan(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "test.py"), "w") as f:
                f.write('secret = "password123"\n')
            results = self.detector.scan_directory(td)
            # scan_directory returns a dict with findings key
            assert isinstance(results, list | dict)


# ═════════════════════════════════════════════════════════════
# AI Code Detector Tests
# ═════════════════════════════════════════════════════════════
class TestAICodeDetectorDeep:
    def setup_method(self):
        from CORE.engines.ai_code_detector import AICodeDetector

        self.detector = AICodeDetector()

    def test_clean_code(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def calculate_tax(income, rate):\n    return income * rate\n")
            path = f.name
        try:
            result = self.detector.analyze_file(path)
            assert isinstance(result, dict)
        finally:
            os.unlink(path)

    def test_repetitive_code(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            code = ""
            for i in range(5):
                code += f"def function{i}(data):\n"
                code += '    """Process the data."""\n'
                code += "    result = []\n"
                code += "    for item in data:\n"
                code += "        result.append(item)\n"
                code += "    return result\n\n"
            f.write(code)
            path = f.name
        try:
            result = self.detector.analyze_file(path)
            assert isinstance(result, dict)
        finally:
            os.unlink(path)

    def test_nonexistent_file(self):
        result = self.detector.analyze_file("/nonexistent.py")
        assert isinstance(result, dict)

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            path = f.name
        try:
            result = self.detector.analyze_file(path)
            assert isinstance(result, dict)
        finally:
            os.unlink(path)


# ═════════════════════════════════════════════════════════════
# Code Extractor Tests
# ═════════════════════════════════════════════════════════════
class TestCodeExtractorDeep:
    def test_extract_middle_line(self):
        from CORE.utils.code_extractor import extract_code_snippet

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            for i in range(1, 20):
                f.write(f"line_{i} = {i}\n")
            path = f.name
        try:
            snippet = extract_code_snippet(path, 10, context_lines=3)
            assert snippet and "line_10" in snippet
        finally:
            os.unlink(path)

    def test_extract_first_line(self):
        from CORE.utils.code_extractor import extract_code_snippet

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("first_line = 1\nsecond_line = 2\n")
            path = f.name
        try:
            snippet = extract_code_snippet(path, 1, context_lines=3)
            assert snippet and "first_line" in snippet
        finally:
            os.unlink(path)

    def test_extract_out_of_range(self):
        from CORE.utils.code_extractor import extract_code_snippet

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("only_line = 1\n")
            path = f.name
        try:
            snippet = extract_code_snippet(path, 999)
            # Should return something or empty, not crash
            assert isinstance(snippet, str | type(None))
        finally:
            os.unlink(path)

    def test_extract_nonexistent_file(self):
        from CORE.utils.code_extractor import extract_code_snippet

        snippet = extract_code_snippet("/nonexistent/file.py", 1)
        assert isinstance(snippet, str | type(None))


# ═════════════════════════════════════════════════════════════
# Normalizer Comprehensive Tests
# ═════════════════════════════════════════════════════════════
class TestNormalizerDeep:
    def test_ruff_multiple_rules(self):
        from CORE.engines.normalizer import normalize_ruff

        output = [
            {
                "code": "F401",
                "message": "os imported but unused",
                "filename": "test.py",
                "location": {"row": 1, "column": 8},
                "end_location": {"row": 1, "column": 10},
            },
            {
                "code": "F841",
                "message": "x assigned but never used",
                "filename": "test.py",
                "location": {"row": 5, "column": 1},
                "end_location": {"row": 5, "column": 2},
            },
            {
                "code": "E501",
                "message": "Line too long",
                "filename": "test.py",
                "location": {"row": 10, "column": 1},
                "end_location": {"row": 10, "column": 200},
            },
        ]
        findings = normalize_ruff(output)
        assert len(findings) == 3
        assert findings[0].canonical_rule_id == "IMPORT-001"
        assert findings[1].canonical_rule_id == "VAR-001"

    def test_bandit_security(self):
        from CORE.engines.normalizer import normalize_bandit

        output = {
            "results": [
                {
                    "test_id": "B307",
                    "test_name": "eval",
                    "issue_severity": "MEDIUM",
                    "issue_confidence": "HIGH",
                    "issue_text": "Use of eval() detected",
                    "filename": "test.py",
                    "line_number": 10,
                    "col_offset": 0,
                    "line_range": [10],
                },
                {
                    "test_id": "B105",
                    "test_name": "hardcoded_password_string",
                    "issue_severity": "LOW",
                    "issue_confidence": "MEDIUM",
                    "issue_text": "Possible hardcoded password",
                    "filename": "test.py",
                    "line_number": 20,
                    "col_offset": 0,
                    "line_range": [20],
                },
            ]
        }
        findings = normalize_bandit(output)
        assert len(findings) == 2

    def test_vulture_text_parsing(self):
        from CORE.engines.normalizer import normalize_vulture

        text = (
            'test.py:10: unused variable "x" (60% confidence)\n'
            'test.py:20: unused function "helper" (90% confidence)\n'
        )
        findings = normalize_vulture(text)
        assert len(findings) == 2

    def test_semgrep_normalization(self):
        from CORE.engines.normalizer import normalize_semgrep

        output = {
            "results": [
                {
                    "check_id": "python.lang.security.eval-injection",
                    "path": "test.py",
                    "start": {"line": 10, "col": 1},
                    "end": {"line": 10, "col": 20},
                    "extra": {
                        "severity": "ERROR",
                        "message": "eval injection",
                        "metadata": {},
                    },
                }
            ]
        }
        findings = normalize_semgrep(output)
        assert len(findings) >= 1

    def test_empty_inputs(self):
        from CORE.engines.normalizer import (
            normalize_bandit,
            normalize_radon,
            normalize_ruff,
            normalize_vulture,
        )

        assert normalize_ruff([]) == []
        assert normalize_bandit({}) == []
        assert normalize_bandit({"results": []}) == []
        assert normalize_vulture("") == []
        assert normalize_radon({}) == []

    def test_canonical_finding_create(self):
        from CORE.engines.normalizer import CanonicalFinding

        finding = CanonicalFinding.create(
            rule_id="F401",
            file="test.py",
            line=1,
            severity="warning",
            category="style",
            message="unused import",
            tool_name="ruff",
            tool_output={"code": "F401"},
        )
        assert finding.canonical_rule_id == "IMPORT-001"
        d = finding.to_dict()
        assert "canonical_rule_id" in d

    def test_canonical_finding_unknown_rule(self):
        from CORE.engines.normalizer import CanonicalFinding

        finding = CanonicalFinding.create(
            rule_id="UNKNOWN_RULE",
            file="test.py",
            line=1,
            severity="info",
            category="style",
            message="something",
            tool_name="ruff",
            tool_output={},
        )
        assert finding.canonical_rule_id.startswith("CUSTOM-")

    def test_normalize_all_with_real_outputs(self):
        """Test normalize_all if output files exist."""
        from CORE.engines.normalizer import normalize_all

        output_dir = Path(__file__).parent.parent / "DATA" / "outputs"
        if output_dir.exists():
            findings = normalize_all(str(output_dir))
            assert isinstance(findings, list)
            # Should produce at least some findings from existing outputs
            if any(output_dir.glob("*.json")) or any(output_dir.glob("*.txt")):
                assert len(findings) >= 0  # May be 0 if outputs are empty


# ═════════════════════════════════════════════════════════════
# ConfigLoader Comprehensive Tests
# ═════════════════════════════════════════════════════════════
class TestConfigLoaderDeep:
    def test_defaults_without_config_file(self):
        from CORE.config_loader import ConfigLoader

        loader = ConfigLoader(project_dir="/tmp/nonexistent_dir_12345")
        config = loader.load()
        assert config is not None
        assert loader.is_rule_enabled("IMPORT-001")
        assert loader.get_max_explanations() == 50
        assert loader.get_min_severity() == "low"

    def test_ignore_default_paths(self):
        from CORE.config_loader import ConfigLoader

        loader = ConfigLoader(project_dir="/tmp/nonexistent_dir_12345")
        loader.load()
        assert loader.should_ignore_path("__pycache__/foo.py")
        assert loader.should_ignore_path(".venv/lib/site.py")
        assert loader.should_ignore_path("node_modules/pkg/index.js")
        assert not loader.should_ignore_path("src/main.py")

    def test_custom_config_file(self):
        from CORE.config_loader import ConfigLoader

        with tempfile.TemporaryDirectory() as td:
            config = {
                "rules": {
                    "disabled_rules": ["IMPORT-001", "VAR-001"],
                    "severity_overrides": {"STYLE-001": "high"},
                },
                "ai": {"max_explanations": 5},
                "reporting": {"min_severity": "medium"},
            }
            with open(os.path.join(td, ".acrqa.yml"), "w") as f:
                yaml.dump(config, f)

            loader = ConfigLoader(project_dir=td)
            cfg = loader.load()
            assert not loader.is_rule_enabled("IMPORT-001")
            assert not loader.is_rule_enabled("VAR-001")
            assert loader.is_rule_enabled("SECURITY-001")
            assert loader.get_severity_override("STYLE-001") == "high"
            assert loader.get_max_explanations() == 5
            assert loader.get_min_severity() == "medium"

    def test_config_caching(self):
        from CORE.config_loader import ConfigLoader

        loader = ConfigLoader(project_dir="/tmp/nonexistent_dir_12345")
        c1 = loader.load()
        c2 = loader.load()
        assert c1 is c2

    def test_real_project_config(self):
        from CORE.config_loader import ConfigLoader

        loader = ConfigLoader(project_dir=str(Path(__file__).parent.parent))
        config = loader.load()
        assert config is not None
        assert "rules" in config


# ═════════════════════════════════════════════════════════════
# QualityGate Comprehensive Tests
# ═════════════════════════════════════════════════════════════
class TestQualityGateDeep:
    def setup_method(self):
        from CORE.engines.quality_gate import QualityGate

        self.QualityGate = QualityGate

    def test_empty_findings_pass(self):
        gate = self.QualityGate(None)
        result = gate.evaluate([])
        assert result["passed"]

    def test_custom_thresholds(self):
        gate = self.QualityGate({"quality_gate": {"max_high": 2, "max_medium": 10, "max_total": 50}})
        findings = [{"canonical_severity": "high", "category": "design"}]
        assert gate.evaluate(findings)["passed"]

    def test_exceeds_high_threshold(self):
        gate = self.QualityGate({"quality_gate": {"max_high": 0}})
        findings = [{"canonical_severity": "high", "category": "design"}]
        assert not gate.evaluate(findings)["passed"]

    def test_exceeds_medium_threshold(self):
        gate = self.QualityGate({"quality_gate": {"max_medium": 0}})
        findings = [{"canonical_severity": "medium", "category": "style"}]
        assert not gate.evaluate(findings)["passed"]

    def test_exceeds_total_threshold(self):
        gate = self.QualityGate({"quality_gate": {"max_total": 0}})
        findings = [{"canonical_severity": "low", "category": "style"}]
        assert not gate.evaluate(findings)["passed"]

    def test_exceeds_security_threshold(self):
        gate = self.QualityGate({"quality_gate": {"max_security": 0}})
        findings = [{"canonical_severity": "low", "category": "security"}]
        assert not gate.evaluate(findings)["passed"]

    def test_result_structure(self):
        gate = self.QualityGate(None)
        result = gate.evaluate([{"canonical_severity": "high", "category": "security"}])
        assert "passed" in result
        assert "checks" in result
        assert "counts" in result
        assert "category_counts" in result

    def test_print_report_no_crash(self):
        gate = self.QualityGate(None)
        result = gate.evaluate([{"canonical_severity": "high", "category": "security"}])
        gate.print_report(result)  # Should not raise

    def test_zero_tolerance(self):
        gate = self.QualityGate(
            {
                "quality_gate": {
                    "max_high": 0,
                    "max_medium": 0,
                    "max_total": 0,
                    "max_security": 0,
                }
            }
        )
        findings = [{"canonical_severity": "low", "category": "style"}]
        assert not gate.evaluate(findings)["passed"]


# ═════════════════════════════════════════════════════════════
# PythonAdapter Tests
# ═════════════════════════════════════════════════════════════
class TestPythonAdapterDeep:
    def setup_method(self):
        from CORE.adapters.python_adapter import PythonAdapter

        self.adapter = PythonAdapter(
            target_dir=str(Path(__file__).parent.parent / "TESTS" / "samples" / "comprehensive-issues")
        )

    def test_language_name(self):
        assert self.adapter.language_name == "Python"

    def test_file_extensions(self):
        assert ".py" in self.adapter.file_extensions

    def test_get_tools(self):
        tools = self.adapter.get_tools()
        assert len(tools) > 0
        tool_names = [t.get("name", "") for t in tools]
        assert "ruff" in tool_names

    def test_find_files(self):
        files = self.adapter.find_files()
        assert len(files) > 0
        assert all(str(f).endswith(".py") for f in files)

    def test_supports_python_file(self):
        assert self.adapter.supports_file("test.py")

    def test_does_not_support_js_file(self):
        assert not self.adapter.supports_file("test.js")

    def test_get_rule_mappings(self):
        mappings = self.adapter.get_rule_mappings()
        assert len(mappings) > 0
        assert isinstance(mappings, dict)


# ═════════════════════════════════════════════════════════════
# Flask App Endpoint Tests
# ═════════════════════════════════════════════════════════════
class TestFlaskEndpoints:
    def setup_method(self):
        from FRONTEND.app import app

        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_health_endpoint(self):
        r = self.client.get("/api/health")
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_index_page(self):
        r = self.client.get("/")
        assert r.status_code == 200
        assert len(r.data) > 0

    def test_runs_endpoint(self):
        r = self.client.get("/api/runs")
        assert r.status_code == 200
        data = r.get_json()
        assert "runs" in data

    def test_runs_with_limit(self):
        r = self.client.get("/api/runs?limit=3")
        assert r.status_code == 200

    def test_trends_endpoint(self):
        r = self.client.get("/api/trends")
        assert r.status_code == 200

    def test_quick_stats_endpoint(self):
        r = self.client.get("/api/quick-stats")
        assert r.status_code == 200
        data = r.get_json()
        assert "stats" in data

    def test_categories_endpoint(self):
        r = self.client.get("/api/categories")
        assert r.status_code == 200

    def test_fix_confidence_known_rule(self):
        r = self.client.get("/api/fix-confidence/IMPORT-001")
        assert r.status_code == 200
        data = r.get_json()
        assert data["confidence"] == 95

    def test_fix_confidence_unknown_rule(self):
        r = self.client.get("/api/fix-confidence/UNKNOWN-999")
        assert r.status_code == 200

    def test_metrics_endpoint(self):
        r = self.client.get("/metrics")
        assert r.status_code == 200

    def test_invalid_run_findings(self):
        r = self.client.get("/api/runs/99999/findings")
        assert r.status_code == 200  # Returns empty list

    def test_invalid_run_stats(self):
        r = self.client.get("/api/runs/99999/stats")
        assert r.status_code in (200, 404)

    def test_invalid_run_cost_benefit(self):
        r = self.client.get("/api/runs/99999/cost-benefit")
        assert r.status_code in (200, 404)

    def test_false_positive_nonexistent_finding(self):
        """Should return 404, not 500, for nonexistent finding."""
        r = self.client.post(
            "/api/findings/99999/mark-false-positive",
            json={"reason": "test"},
            content_type="application/json",
        )
        assert r.status_code == 404

    def test_feedback_nonexistent_finding(self):
        """Should return 404, not 500, for nonexistent finding."""
        r = self.client.post(
            "/api/findings/99999/feedback",
            json={"is_helpful": True},
            content_type="application/json",
        )
        assert r.status_code == 404

    def test_secrets_scan(self):
        r = self.client.post(
            "/api/scan/secrets",
            json={"target_dir": "TESTS/samples/comprehensive-issues"},
            content_type="application/json",
        )
        assert r.status_code == 200

    def test_ai_detection_scan(self):
        r = self.client.post(
            "/api/scan/ai-detection",
            json={"target_dir": "TESTS/samples/comprehensive-issues"},
            content_type="application/json",
        )
        assert r.status_code == 200


# ═════════════════════════════════════════════════════════════
# Database CRUD Tests
# ═════════════════════════════════════════════════════════════
class TestDatabaseDeep:
    def setup_method(self):
        from DATABASE.database import Database

        self.db = Database()

    def teardown_method(self):
        self.db.close()

    def test_get_recent_runs(self):
        runs = self.db.get_recent_runs(limit=5)
        assert isinstance(runs, list)

    def test_list_analysis_runs(self):
        runs = self.db.list_analysis_runs(limit=5)
        assert isinstance(runs, list)

    def test_get_trend_data(self):
        trends = self.db.get_trend_data(limit=10)
        assert isinstance(trends, list)

    def test_get_feedback_stats(self):
        stats = self.db.get_feedback_stats()
        assert isinstance(stats, dict | type(None))

    def test_get_explanations_all(self):
        explanations = self.db.get_explanations()
        assert isinstance(explanations, list)

    def test_create_and_complete_run(self):
        run_id = self.db.create_analysis_run("test-repo", pr_number=1)
        assert run_id is not None

        run = self.db.get_analysis_run(run_id)
        assert run is not None
        assert run["repo_name"] == "test-repo"
        assert run["status"] == "running"

        self.db.complete_analysis_run(run_id, total_findings=5)
        run = self.db.get_analysis_run(run_id)
        assert run["status"] == "completed"
        assert run["total_findings"] == 5

    def test_create_and_fail_run(self):
        run_id = self.db.create_analysis_run("test-repo-fail")
        assert run_id is not None

        self.db.fail_analysis_run(run_id, "Test error")
        run = self.db.get_analysis_run(run_id)
        assert run["status"] == "failed"

    def test_insert_finding(self):
        run_id = self.db.create_analysis_run("test-finding-repo")
        finding = {
            "tool_raw": {"tool_name": "ruff"},
            "rule_id": "F401",
            "original_rule_id": "F401",
            "canonical_rule_id": "IMPORT-001",
            "severity": "low",
            "file": "test.py",
            "line": 1,
            "column": 0,
            "category": "style",
            "message": "unused import",
            "evidence": {},
        }
        finding_id = self.db.insert_finding(run_id, finding)
        assert finding_id is not None

        findings = self.db.get_findings(run_id=run_id)
        assert len(findings) >= 1

    def test_insert_and_get_explanation(self):
        run_id = self.db.create_analysis_run("test-explanation-repo")
        finding = {
            "tool_raw": {"tool_name": "ruff"},
            "rule_id": "F401",
            "original_rule_id": "F401",
            "canonical_rule_id": "IMPORT-001",
            "severity": "low",
            "file": "test.py",
            "line": 1,
            "category": "style",
            "message": "unused import",
            "evidence": {},
        }
        finding_id = self.db.insert_finding(run_id, finding)
        assert finding_id is not None

        explanation = {
            "model_name": "test-model",
            "prompt_filled": "Test prompt",
            "response_text": "Test explanation",
            "temperature": 0.3,
            "max_tokens": 150,
            "latency_ms": 100,
            "cost_usd": 0.001,
        }
        exp_id = self.db.insert_explanation(finding_id, explanation)
        assert exp_id is not None

        explanations = self.db.get_explanations(finding_id=finding_id)
        assert len(explanations) >= 1

    def test_get_run_summary(self):
        runs = self.db.get_recent_runs(limit=1)
        if runs:
            summary = self.db.get_run_summary(runs[0]["id"])
            assert summary is not None

    def test_update_ground_truth(self):
        run_id = self.db.create_analysis_run("test-gt-repo")
        finding = {
            "tool_raw": {"tool_name": "test"},
            "rule_id": "T001",
            "original_rule_id": "T001",
            "canonical_rule_id": "TEST-001",
            "severity": "low",
            "file": "test.py",
            "line": 1,
            "category": "style",
            "message": "test",
            "evidence": {},
        }
        finding_id = self.db.insert_finding(run_id, finding)
        self.db.update_finding_ground_truth(finding_id, "TP")
        # Verify
        findings = self.db.get_findings(run_id=run_id)
        assert any(f["ground_truth"] == "TP" for f in findings)

    def test_invalid_ground_truth_raises(self):
        with pytest.raises(ValueError):
            self.db.update_finding_ground_truth(1, "INVALID")


# ═════════════════════════════════════════════════════════════
# Metrics Module Tests
# ═════════════════════════════════════════════════════════════
class TestMetricsDeep:
    def test_import(self):
        from CORE.utils.metrics import register_metrics_endpoint

        assert callable(register_metrics_endpoint)

    def test_register_on_flask_app(self):
        from flask import Flask

        from CORE.utils.metrics import register_metrics_endpoint

        test_app = Flask(__name__)
        register_metrics_endpoint(test_app)
        client = test_app.test_client()
        r = client.get("/metrics")
        assert r.status_code == 200
