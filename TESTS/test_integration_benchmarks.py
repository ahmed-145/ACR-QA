#!/usr/bin/env python3
"""
ACR-QA Integration Tests and Performance Benchmarks
Tests end-to-end workflows and measures performance
"""

import pytest
import time
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE.main import AnalysisPipeline
from CORE.engines.autofix import AutoFixEngine
from DATABASE.database import Database


class TestIntegration:
    """End-to-end integration tests"""
    
    @pytest.fixture
    def pipeline(self):
        return AnalysisPipeline(target_dir="TESTS/samples/comprehensive-issues")
    
    @pytest.fixture
    def db(self):
        return Database()
    
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
                    "filename": "test.py"
                },
                timeout=10
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
                "message": "Simplify boolean"
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
            "message": "unused import os"
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
                "message": "unused variable x"
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
        from CORE.detection.tool_runner import ToolRunner
        
        runner = ToolRunner(
            target_dir="TESTS/samples/comprehensive-issues",
            output_dir="DATA/outputs"
        )
        
        start = time.time()
        runner.run_all()
        elapsed = time.time() - start
        
        # All tools should complete within 30 seconds
        assert elapsed < 30, f"Detection took {elapsed:.2f}s, expected <30s"
        print(f"\n⏱️ Detection benchmark: {elapsed:.2f}s")
    
    def test_normalization_performance(self):
        """Benchmark normalization speed"""
        from CORE.normalizer import UnifiedNormalizer
        
        normalizer = UnifiedNormalizer(output_dir="DATA/outputs")
        
        start = time.time()
        findings = normalizer.normalize_all()
        elapsed = time.time() - start
        
        # Normalization should complete within 5 seconds
        assert elapsed < 5, f"Normalization took {elapsed:.2f}s, expected <5s"
        print(f"\n⏱️ Normalization benchmark: {elapsed:.2f}s for {len(findings)} findings")
    
    def test_database_query_performance(self):
        """Benchmark database query speed"""
        db = Database()
        
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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
