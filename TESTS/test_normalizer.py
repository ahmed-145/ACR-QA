"""
Unit tests for Normalizer (tool output parsing)
Tests canonical schema mapping and rule normalization
"""
import pytest
from CORE.engines.normalizer import (
    normalize_ruff,
    normalize_semgrep,
    normalize_bandit,
    CanonicalFinding
)


class TestNormalizer:
    """Test tool output normalization to canonical schema"""

    def test_ruff_normalization(self):
        """Test Ruff JSON output is normalized correctly"""
        ruff_output = {
            "code": "E501",
            "message": "Line too long (100 > 88 characters)",
            "location": {
                "row": 42,
                "column": 1
            },
            "filename": "test.py"
        }
        
        findings = normalize_ruff([ruff_output])
        
        assert len(findings) == 1
        assert findings[0]['canonical_rule_id'] == 'STYLE-001'
        assert findings[0]['severity'] == 'low'
        assert findings[0]['file'] == 'test.py'
        assert findings[0]['line'] == 42

    def test_semgrep_normalization(self):
        """Test Semgrep output is normalized correctly"""
        semgrep_output = {
            "check_id": "python.lang.security.audit.dangerous-eval.dangerous-eval",
            "path": "app.py",
            "start": {"line": 10, "col": 5},
            "extra": {
                "message": "Dangerous use of eval()",
                "severity": "ERROR"
            }
        }
        
        findings = normalize_semgrep([semgrep_output])
        
        assert len(findings) == 1
        assert findings[0]['canonical_rule_id'] == 'SECURITY-001'
        assert findings[0]['severity'] == 'high'
        assert findings[0]['category'] == 'security'

    def test_bandit_normalization(self):
        """Test Bandit output is normalized correctly"""
        bandit_output = {
            "test_id": "B102",
            "test_name": "exec_used",
            "issue_severity": "MEDIUM",
            "issue_confidence": "HIGH",
            "issue_text": "Use of exec detected",
            "line_number": 15,
            "filename": "dangerous.py"
        }
        
        findings = normalize_bandit([bandit_output])
        
        assert len(findings) == 1
        assert findings[0]['canonical_rule_id'] == 'SECURITY-001'
        assert findings[0]['file'] == 'dangerous.py'
        assert findings[0]['line'] == 15

    def test_canonical_finding_validation(self):
        """Test CanonicalFinding Pydantic validation"""
        valid_data = {
            'canonical_rule_id': 'SECURITY-001',
            'original_rule_id': 'B102',
            'severity': 'high',
            'category': 'security',
            'file': 'test.py',
            'line': 10,
            'language': 'python',
            'message': 'Test message',
            'tool_raw': {}
        }
        
        finding = CanonicalFinding(**valid_data)
        
        assert finding.severity == 'high'
        assert finding.canonical_rule_id == 'SECURITY-001'

    def test_severity_normalization(self):
        """Test severity is normalized to high/medium/low"""
        # Test ERROR -> high
        finding1 = CanonicalFinding(
            canonical_rule_id='TEST-001',
            original_rule_id='T001',
            severity='ERROR',
            category='test',
            file='test.py',
            line=1,
            language='python',
            message='test',
            tool_raw={}
        )
        assert finding1.severity == 'high'
        
        # Test WARNING -> medium
        finding2 = CanonicalFinding(
            canonical_rule_id='TEST-001',
            original_rule_id='T001',
            severity='WARNING',
            category='test',
            file='test.py',
            line=1,
            language='python',
            message='test',
            tool_raw={}
        )
        assert finding2.severity == 'medium'

    def test_unknown_rule_mapping(self):
        """Test unknown rules get mapped to UNKNOWN"""
        ruff_output = {
            "code": "NEWRULE999",
            "message": "Unknown rule",
            "location": {"row": 1, "column": 1},
            "filename": "test.py"
        }
        
        findings = normalize_ruff([ruff_output])
        
        assert len(findings) == 1
        # Should still create finding even if rule is unknown
        assert findings[0]['original_rule_id'] == 'NEWRULE999'

    def test_category_mapping(self):
        """Test category is correctly mapped"""
        categories = {
            'SECURITY-001': 'security',
            'STYLE-001': 'style',
            'COMPLEXITY-001': 'design',
            'DUP-001': 'duplication'
        }
        
        for rule_id, expected_category in categories.items():
            finding = CanonicalFinding(
                canonical_rule_id=rule_id,
                original_rule_id='TEST',
                severity='low',
                category=expected_category,
                file='test.py',
                line=1,
                language='python',
                message='test',
                tool_raw={}
            )
            assert finding.category == expected_category
