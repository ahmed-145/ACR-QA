"""
Pydantic Validation Tests for ACR-QA v2.0
Tests schema validation for CanonicalFinding
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE.engines.normalizer import CanonicalFinding
from pydantic import ValidationError


class TestPydanticValidation:
    """Test Pydantic schema validation"""
    
    def test_valid_finding_creation(self):
        """Test creating a valid finding"""
        finding = CanonicalFinding.create(
            rule_id='F401',
            file='test.py',
            line=10,
            severity='warning',
            category='style',
            message='Unused import',
            tool_name='ruff',
            tool_output={'code': 'F401'}
        )
        
        assert finding.canonical_rule_id == 'IMPORT-001'
        assert finding.severity in ['high', 'medium', 'low']
        assert finding.file == 'test.py'
        assert finding.line == 10
    
    def test_valid_finding_serialization(self):
        """Test that valid findings serialize to JSON"""
        finding = CanonicalFinding.create(
            rule_id='F401',
            file='test.py',
            line=10,
            severity='info',
            category='style',
            message='Unused import',
            tool_name='ruff',
            tool_output={'code': 'F401'}
        )
        
        # Should serialize without errors
        data = finding.to_dict()
        
        assert isinstance(data, dict)
        assert 'finding_id' in data
        assert 'canonical_rule_id' in data
        assert 'severity' in data
        assert data['severity'] in ['high', 'medium', 'low']
    
    def test_invalid_severity_rejected(self):
        """Test that invalid severity values are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            CanonicalFinding(
                finding_id='test-123',
                canonical_rule_id='TEST-001',
                original_rule_id='T001',
                severity='urgent',  # INVALID!
                category='security',
                file='test.py',
                line=10,
                language='python',
                message='Test message',
                tool_raw={'tool_name': 'test'}
            )
        
        # Check error message
        assert 'severity' in str(exc_info.value).lower()
    
    def test_severity_case_insensitive(self):
        """Test that severity validation is case-insensitive"""
        # These should all work
        for severity in ['HIGH', 'High', 'high', 'MEDIUM', 'Medium', 'medium', 'LOW', 'Low', 'low']:
            finding = CanonicalFinding(
                finding_id='test-123',
                canonical_rule_id='TEST-001',
                original_rule_id='T001',
                severity=severity,
                category='security',
                file='test.py',
                line=10,
                language='python',
                message='Test message',
                tool_raw={'tool_name': 'test'}
            )
            assert finding.severity in ['high', 'medium', 'low']
    
    def test_unknown_category_warning(self):
        """Test that unknown categories log a warning but don't fail"""
        # This should work but log a warning
        finding = CanonicalFinding(
            finding_id='test-123',
            canonical_rule_id='TEST-001',
            original_rule_id='T001',
            severity='medium',
            category='unknown-category',  # Not in valid list
            file='test.py',
            line=10,
            language='python',
            message='Test message',
            tool_raw={'tool_name': 'test'}
        )
        
        # Should still create the finding
        assert finding.category == 'unknown-category'
    
    def test_missing_required_field(self):
        """Test that missing required fields are rejected"""
        with pytest.raises(ValidationError):
            CanonicalFinding(
                finding_id='test-123',
                canonical_rule_id='TEST-001',
                # Missing severity!
                category='security',
                file='test.py',
                line=10,
                language='python',
                message='Test message',
                tool_raw={'tool_name': 'test'}
            )
    
    def test_factory_method_validation(self):
        """Test that factory method applies validation"""
        # Valid creation
        finding = CanonicalFinding.create(
            rule_id='dangerous-eval-usage',
            file='test.py',
            line=10,
            severity='ERROR',
            category='security',
            message='Dangerous eval() usage',
            tool_name='semgrep',
            tool_output={'check_id': 'dangerous-eval-usage'}
        )
        
        assert finding.canonical_rule_id == 'SECURITY-001'
        assert finding.severity == 'high'  # Scored by severity scorer
    
    def test_model_dump_serialization(self):
        """Test Pydantic's model_dump() method"""
        finding = CanonicalFinding.create(
            rule_id='F841',
            file='test.py',
            line=20,
            severity='info',
            category='dead-code',
            message='Unused variable',
            tool_name='ruff',
            tool_output={'code': 'F841'}
        )
        
        # model_dump() should return a dict
        data = finding.model_dump()
        
        assert isinstance(data, dict)
        assert data['canonical_rule_id'] == 'VAR-001'
        assert 'finding_id' in data
        assert 'evidence' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
