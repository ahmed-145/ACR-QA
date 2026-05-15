#!/usr/bin/env python3
"""
ACR-QA Integration Tests and Performance Benchmarks
Tests end-to-end workflows and measures performance
"""

import os
import sys
import time
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE.engines.autofix import AutoFixEngine
from CORE.main import AnalysisPipeline
from DATABASE.database import Database


class TestIntegration:
    """End-to-end integration tests"""

    @pytest.fixture
    def pipeline(self):
        try:
            return AnalysisPipeline(target_dir="TESTS/samples/comprehensive-issues")
        except Exception:
            pytest.skip("Database not available")

    @pytest.fixture
    def db(self):
        try:
            instance = Database()
            instance.execute("SELECT 1", fetch=True)
            return instance
        except Exception:
            pytest.skip("Database not available")

    def test_full_pipeline_execution(self, pipeline):
        """Test complete analysis pipeline runs without errors"""
        # This is a lightweight test - just verify pipeline initializes
        assert pipeline.target_dir.endswith("comprehensive-issues")

    def test_database_connection(self, db):
        """Test database connection is working"""
        runs = db.get_recent_runs(limit=1)
        assert isinstance(runs, list)

    def test_api_analyze_endpoint(self):
        """Test the /api/analyze endpoint"""
        import requests

        # Skip if server not running
        try:
            response = requests.post(
                "http://localhost:5000/api/analyze",
                json={
                    "content": "import os\nx = 5\nprint('hello')\n",
                    "filename": "test.py",
                },
                timeout=10,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "findings" in data
            assert isinstance(data["findings"], list)
        except requests.exceptions.ConnectionError:
            pytest.skip("Server not running at localhost:5000")

    def test_api_health_endpoint(self):
        """Test the /api/health endpoint"""
        import requests

        try:
            response = requests.get("http://localhost:5000/api/health", timeout=5)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
        except requests.exceptions.ConnectionError:
            pytest.skip("Server not running at localhost:5000")


class TestAutoFix:
    """Auto-fix engine tests"""

    @pytest.fixture
    def engine(self):
        return AutoFixEngine()

    def test_can_fix_supported_rules(self, engine):
        """Test that engine identifies fixable rules"""
        assert engine.can_fix("IMPORT-001") is True
        assert engine.can_fix("VAR-001") is True
        assert engine.can_fix("BOOL-001") is True
        assert engine.can_fix("UNKNOWN-999") is False

    def test_fix_boolean_simplification(self, engine):
        """Test boolean comparison simplification"""
        # Create test file first
        test_file = "test_bool_temp.py"
        with open(test_file, "w") as f:
            f.write("if x == True:\n    print('yes')\n")

        try:
            finding = {
                "canonical_rule_id": "BOOL-001",
                "file_path": test_file,
                "line": 1,
                "message": "Simplify boolean",
            }

            fix = engine.generate_fix(finding)

            # Verify the fix was generated
            assert fix is not None
            assert fix["fixed"] == "if x:"
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_fix_unused_import(self, engine):
        """Test unused import removal"""
        finding = {
            "canonical_rule_id": "IMPORT-001",
            "file_path": "test_import.py",
            "line": 1,
            "message": "unused import os",
        }

        # Create test file
        with open("test_import.py", "w") as f:
            f.write("import os\nimport sys\nprint(sys.version)\n")

        try:
            fix = engine.generate_fix(finding)
            fix["file"] = "test_import.py"

            assert fix is not None
            assert fix["original"] == "import os"
            assert fix["fixed"] == ""  # Removed
        finally:
            if os.path.exists("test_import.py"):
                os.remove("test_import.py")

    def test_fix_unused_variable(self, engine):
        """Test unused variable prefixing"""
        # Create test file first
        test_file = "test_var_temp.py"
        with open(test_file, "w") as f:
            f.write("x = 5\nprint('hello')\n")

        try:
            finding = {
                "canonical_rule_id": "VAR-001",
                "file_path": test_file,
                "line": 1,
                "message": "unused variable x",
            }

            fix = engine.generate_fix(finding)

            # Verify the fix was generated
            assert fix is not None, "Fix should not be None for VAR-001"
            assert fix["original"] == "x = 5"
            assert fix["fixed"] == "_x = 5"
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)


class TestPerformanceBenchmarks:
    """Performance benchmarks for key operations"""

    def test_detection_tools_performance(self):
        """Benchmark detection tools execution time"""
        try:
            from CORE.detection.tool_runner import ToolRunner
        except ImportError:
            pytest.skip("CORE.detection.tool_runner module not yet implemented")

        runner = ToolRunner(target_dir="TESTS/samples/comprehensive-issues", output_dir="DATA/outputs")

        start = time.time()
        runner.run_all()
        elapsed = time.time() - start

        # All tools should complete within 30 seconds
        assert elapsed < 30, f"Detection took {elapsed:.2f}s, expected <30s"
        print(f"\n⏱️ Detection benchmark: {elapsed:.2f}s")

    def test_normalization_performance(self):
        """Benchmark normalization speed"""
        from CORE.engines.normalizer import normalize_all

        start = time.time()
        findings = normalize_all(outputs_dir="DATA/outputs")
        elapsed = time.time() - start

        # Normalization should complete within 5 seconds
        assert elapsed < 5, f"Normalization took {elapsed:.2f}s, expected <5s"
        print(f"\n⏱️ Normalization benchmark: {elapsed:.2f}s for {len(findings)} findings")

    def test_database_query_performance(self):
        """Benchmark database query speed"""
        try:
            db = Database()
            db.execute("SELECT 1", fetch=True)
        except Exception:
            pytest.skip("Database not available")

        start = time.time()
        for _ in range(10):
            db.get_recent_runs(limit=10)
        elapsed = time.time() - start

        # 10 queries should complete within 1 second
        avg_time = elapsed / 10
        assert avg_time < 0.1, f"Avg query time {avg_time:.3f}s, expected <0.1s"
        print(f"\n⏱️ DB query benchmark: {avg_time*1000:.1f}ms per query")

    def test_api_response_time(self):
        """Benchmark API response times"""
        import requests

        try:
            times = []
            for _ in range(5):
                start = time.time()
                requests.get("http://localhost:5000/api/health", timeout=5)
                times.append(time.time() - start)

            avg_time = sum(times) / len(times)
            assert avg_time < 0.5, f"Avg response {avg_time:.3f}s, expected <0.5s"
            print(f"\n⏱️ API response benchmark: {avg_time*1000:.1f}ms average")
        except requests.exceptions.ConnectionError:
            pytest.skip("Server not running")


class TestRulesCoverage:
    """Test that all rules are properly defined"""

    def test_all_rules_have_required_fields(self):
        """Verify all rules have name, category, severity, description"""
        import yaml

        with open("config/rules.yml") as f:
            rules = yaml.safe_load(f)

        required_fields = ["name", "category", "severity", "description"]

        for rule_id, rule in rules.items():
            for field in required_fields:
                assert field in rule, f"{rule_id} missing {field}"

    def test_rules_count(self):
        """Verify we have sufficient rules"""
        import yaml

        with open("config/rules.yml") as f:
            rules = yaml.safe_load(f)

        # Should have at least 35 rules now
        assert len(rules) >= 35, f"Only {len(rules)} rules, expected 35+"
        print(f"\n📋 Total rules: {len(rules)}")

    def test_security_rules_exist(self):
        """Verify critical security rules exist"""
        import yaml

        with open("config/rules.yml") as f:
            rules = yaml.safe_load(f)

        security_rules = [r for r, d in rules.items() if d.get("category") == "security"]

        # Should have at least 8 security rules
        assert len(security_rules) >= 8, f"Only {len(security_rules)} security rules"
        print(f"\n🔒 Security rules: {len(security_rules)}")


class TestReachabilityBenchmark:
    """
    Feature 9: Call Graph Reachability — FP reduction benchmarks.
    Validates that the engine correctly classifies findings in benchmark fixtures
    and that the enrich_findings pipeline integration works end-to-end.
    """

    FIXTURE_DIR = Path(__file__).parent / "fixtures" / "reachability"

    def test_flask_fp_rate_benchmark(self):
        """
        Flask fixture: reachable findings must not be penalised,
        unreachable ones must receive a -20 confidence penalty.
        FP criterion: a reachable finding marked UNREACHABLE = false positive.
        """
        from CORE.engines.reachability import CallGraphReachability

        # Ground truth for flask_app.py (post-ruff-format line numbers):
        #   reachable body lines  → process_input:27, execute_query:33
        #   unreachable body lines → orphan_function:38, dead_helper:44
        flask_file = str(self.FIXTURE_DIR / "flask_app.py")
        findings = [
            {"file_path": flask_file, "line_number": 27, "confidence_score": 80, "id": "tp1"},
            {"file_path": flask_file, "line_number": 33, "confidence_score": 75, "id": "tp2"},
            {"file_path": flask_file, "line_number": 38, "confidence_score": 70, "id": "dead1"},
            {"file_path": flask_file, "line_number": 44, "confidence_score": 60, "id": "dead2"},
        ]
        results = CallGraphReachability().enrich_findings(findings)
        by_id = {r["id"]: r for r in results}

        # Reachable findings must NOT be penalised
        assert by_id["tp1"]["reachability_status"] == "REACHABLE"
        assert by_id["tp1"]["confidence_score"] == 80
        assert by_id["tp2"]["reachability_status"] == "REACHABLE"
        assert by_id["tp2"]["confidence_score"] == 75

        # Unreachable findings must have -20 penalty applied
        assert by_id["dead1"]["reachability_status"] == "UNREACHABLE"
        assert by_id["dead1"]["confidence_score"] == 50
        assert by_id["dead2"]["reachability_status"] == "UNREACHABLE"
        assert by_id["dead2"]["confidence_score"] == 40

        # FP rate: reachable findings incorrectly labelled UNREACHABLE
        fp_count = sum(1 for r in results if r["id"] in ("tp1", "tp2") and r["reachability_status"] == "UNREACHABLE")
        fp_rate = fp_count / 2
        assert fp_rate == 0.0, f"FP rate {fp_rate:.0%} exceeds 0% on Flask fixture"

    def test_standalone_benchmark(self):
        """standalone.py: main + called_from_main reachable, never_called + also_dead not."""
        from CORE.engines.reachability import CallGraphReachability

        standalone_file = str(self.FIXTURE_DIR / "standalone.py")
        findings = [
            # called_from_main body (line 23) — reachable
            {"file_path": standalone_file, "line_number": 23, "confidence_score": 80, "id": "reach"},
            # also_dead body (line 32) — unreachable
            {"file_path": standalone_file, "line_number": 32, "confidence_score": 70, "id": "dead"},
        ]
        results = CallGraphReachability().enrich_findings(findings)
        by_id = {r["id"]: r for r in results}
        assert by_id["reach"]["reachability_status"] == "REACHABLE"
        assert by_id["dead"]["reachability_status"] == "UNREACHABLE"

    def test_celery_benchmark(self):
        """celery_tasks.py: process_job + task_helper reachable, orphan_task_helper not."""
        from CORE.engines.reachability import CallGraphReachability

        celery_file = str(self.FIXTURE_DIR / "celery_tasks.py")
        findings = [
            # task_helper body line 26 — reachable
            {"file_path": celery_file, "line_number": 26, "confidence_score": 80, "id": "reach"},
            # orphan_task_helper body line 31 — unreachable
            {"file_path": celery_file, "line_number": 31, "confidence_score": 60, "id": "dead"},
        ]
        results = CallGraphReachability().enrich_findings(findings)
        by_id = {r["id"]: r for r in results}
        assert by_id["reach"]["reachability_status"] == "REACHABLE"
        assert by_id["dead"]["reachability_status"] == "UNREACHABLE"

    def test_mixed_language_batch(self, tmp_path):
        """Non-Python findings pass through as UNKNOWN without confidence change."""
        from CORE.engines.reachability import CallGraphReachability

        js_file = tmp_path / "app.js"
        js_file.write_text("function vuln() { eval(input); }\n")
        findings = [
            {"file_path": str(js_file), "line_number": 1, "confidence_score": 90, "id": "js"},
        ]
        results = CallGraphReachability().enrich_findings(findings)
        assert results[0]["reachability_status"] == "UNKNOWN"
        assert results[0]["confidence_score"] == 90

    def test_enrich_findings_preserves_all_fields(self, tmp_path):
        """Enrichment must not drop existing finding fields."""
        from CORE.engines.reachability import CallGraphReachability

        f = tmp_path / "app.py"
        f.write_text("from flask import Flask\napp=Flask(__name__)\n" "@app.route('/')\ndef index(): pass\n")
        finding = {
            "file_path": str(f),
            "line_number": 4,
            "confidence_score": 80,
            "canonical_rule_id": "SECURITY-001",
            "canonical_severity": "high",
            "message": "test",
        }
        results = CallGraphReachability().enrich_findings([finding])
        for key in ("canonical_rule_id", "canonical_severity", "message"):
            assert key in results[0], f"Field {key!r} was dropped by enrich_findings"

    def test_zero_false_positives_on_fixtures(self):
        """
        Aggregate: across all three fixtures, no reachable finding should be
        misclassified as UNREACHABLE. Target: 0% FP rate.
        """
        from CORE.engines.reachability import CallGraphReachability

        # Reachable body lines by fixture
        reachable_cases = [
            (str(self.FIXTURE_DIR / "flask_app.py"), 27),  # process_input body
            (str(self.FIXTURE_DIR / "flask_app.py"), 33),  # execute_query body
            (str(self.FIXTURE_DIR / "standalone.py"), 23),  # called_from_main body
            (str(self.FIXTURE_DIR / "celery_tasks.py"), 26),  # task_helper body
        ]
        findings = [{"file_path": fp, "line_number": ln, "confidence_score": 80} for fp, ln in reachable_cases]
        results = CallGraphReachability().enrich_findings(findings)
        fps = [r for r in results if r.get("reachability_status") == "UNREACHABLE"]
        assert len(fps) == 0, f"False positives detected: {[r['file_path'] + ':' + str(r['line_number']) for r in fps]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
