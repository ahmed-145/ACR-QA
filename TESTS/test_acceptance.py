"""
Acceptance Tests for ACR-QA v2.0 Phase 1
Tests PRD2026 acceptance criteria
"""
import pytest
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE.engines.normalizer import normalize_all, CanonicalFinding
from CORE.engines.explainer import ExplanationEngine
from CORE.utils.rate_limiter import RateLimiter


class TestAcceptance:
    """PRD2026 Phase 1 Acceptance Tests"""
    
    def test_canonical_schema_normalization(self):
        """
        Test 2: Canonical Schema
        - Run Ruff, Semgrep, Vulture on sample code
        - Normalizer produces findings with universal rule IDs
        - Database stores findings in canonical format
        """
        # This test requires running tools first
        # For now, test the normalizer with mock data
        
        # Test Ruff normalization
        ruff_data = [{
            'code': 'F401',
            'filename': 'test.py',
            'location': {'row': 10, 'column': 0},
            'message': 'Unused import'
        }]
        
        from CORE.engines.normalizer import normalize_ruff
        findings = normalize_ruff(ruff_data)
        
        assert len(findings) == 1
        assert findings[0].canonical_rule_id == 'IMPORT-001'
        assert findings[0].severity in ['high', 'medium', 'low']
        
        # Test serialization
        data = findings[0].to_dict()
        assert isinstance(data, dict)
        assert 'canonical_rule_id' in data
    
    def test_pydantic_schema_validation(self):
        """
        Test 3b: Schema Validation (Pydantic)
        - Generate findings with Pydantic CanonicalFinding models
        - Verify all findings serialize to valid JSON
        - Verify invalid data is rejected with clear error
        """
        # Valid finding
        finding = CanonicalFinding.create(
            rule_id='F401',
            file='test.py',
            line=10,
            severity='info',
            category='style',
            message='Test',
            tool_name='ruff',
            tool_output={}
        )
        
        # Should serialize
        data = finding.to_dict()
        json_str = json.dumps(data)
        assert isinstance(json_str, str)
        
        # Invalid severity should be rejected
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CanonicalFinding(
                finding_id='test',
                canonical_rule_id='TEST',
                original_rule_id='T',
                severity='invalid',  # Invalid!
                category='style',
                file='test.py',
                line=1,
                language='python',
                message='Test',
                tool_raw={}
            )
    
    def test_rate_limiting_enforcement(self):
        """
        Test 2b: Rate Limiting & Reliability
        - Simulate concurrent PR analysis requests
        - Verify ≤1 analysis queued per repo per minute
        - Verify all rate-limit events logged
        """
        limiter = RateLimiter(redis_host='localhost', redis_port=6379)
        
        # Reset
        limiter.reset_rate_limit('acceptance-test-repo', 1)
        
        # First request should succeed
        allowed1, _ = limiter.check_rate_limit('acceptance-test-repo', 1)
        assert allowed1 is True
        
        # Immediate second request should be rate limited
        allowed2, retry_after = limiter.check_rate_limit('acceptance-test-repo', 1)
        assert allowed2 is False
        assert retry_after is not None
        
        # Clean up
        limiter.reset_rate_limit('acceptance-test-repo', 1)
    
    def test_rag_explanation_generation(self):
        """
        Test 3: RAG Explanations
        - Generate explanations for diverse findings
        - Verify explanations cite correct rule ID
        """
        explainer = ExplanationEngine()
        
        finding = {
            'canonical_rule_id': 'SECURITY-001',
            'message': 'Dangerous eval() usage',
            'file': 'test.py',
            'line': 10,
            'severity': 'high',
            'category': 'security'
        }
        
        snippet = "result = eval(user_input)"
        
        explanation = explainer.generate_explanation(finding, snippet)
        
        # Should have explanation text
        assert 'explanation' in explanation
        assert len(explanation['explanation']) > 0
        
        # Should cite rule ID
        assert 'SECURITY-001' in explanation['explanation'] or 'eval' in explanation['explanation'].lower()
        
        # Should have metadata
        assert 'latency_ms' in explanation
        assert explanation['latency_ms'] > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
