"""
Unit tests for ExplanationEngine (RAG + LLM)
Tests caching, grounding, and confidence scoring
"""
import pytest
from unittest.mock import Mock, patch
from CORE.engines.explainer import ExplanationEngine


class TestExplanationEngine:
    """Test RAG-enhanced explanation generation"""

    @pytest.fixture
    def engine(self):
        """Create engine with mock Redis"""
        mock_redis = Mock()
        mock_redis.get.return_value = None  # Cache miss
        return ExplanationEngine(redis_client=mock_redis)

    def test_cache_key_generation(self, engine):
        """Test cache key is deterministic"""
        finding = {
            'canonical_rule_id': 'SECURITY-001',
            'file': 'test.py',
            'line': 42
        }
        snippet = "eval(user_input)"
        
        key1 = engine._get_cache_key(finding, snippet)
        key2 = engine._get_cache_key(finding, snippet)
        
        assert key1 == key2
        assert key1.startswith('explanation:')

    def test_cache_hit_returns_cached(self):
        """Test cache hit returns cached response"""
        mock_redis = Mock()
        cached_data = '{"response_text": "cached", "cache_hit": false}'
        mock_redis.get.return_value = cached_data
        
        engine = ExplanationEngine(redis_client=mock_redis)
        finding = {'canonical_rule_id': 'TEST-001', 'file': 'test.py', 'line': 1}
        
        result = engine.generate_explanation(finding, "code")
        
        assert result['cache_hit'] is True
        assert 'cached' in str(result)
        assert engine.cache_hits == 1

    def test_cache_miss_increments_counter(self, engine):
        """Test cache miss increments counter"""
        initial_misses = engine.cache_misses
        
        with patch.object(engine.client.chat.completions, 'create') as mock_create:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="Test explanation"))]
            mock_response.usage = Mock(total_tokens=100)
            mock_create.return_value = mock_response
            
            finding = {'canonical_rule_id': 'TEST-001', 'file': 'test.py', 'line': 1}
            engine.generate_explanation(finding, "code")
        
        assert engine.cache_misses == initial_misses + 1

    def test_confidence_high_when_cites_rule(self, engine):
        """Test confidence is 0.9 when explanation cites rule"""
        with patch.object(engine.client.chat.completions, 'create') as mock_create:
            mock_response = Mock()
            # Response that cites the rule
            mock_response.choices = [Mock(message=Mock(content="This violates SECURITY-001 because..."))]
            mock_response.usage = Mock(total_tokens=100)
            mock_create.return_value = mock_response
            
            finding = {'canonical_rule_id': 'SECURITY-001', 'file': 'test.py', 'line': 1}
            result = engine.generate_explanation(finding, "eval(x)")
        
        assert result['confidence'] == 0.9
        assert result['cites_rule'] is True

    def test_confidence_low_when_no_citation(self, engine):
        """Test confidence is 0.6 when explanation doesn't cite rule"""
        with patch.object(engine.client.chat.completions, 'create') as mock_create:
            mock_response = Mock()
            # Response without rule citation
            mock_response.choices = [Mock(message=Mock(content="This is bad code"))]
            mock_response.usage = Mock(total_tokens=100)
            mock_create.return_value = mock_response
            
            finding = {'canonical_rule_id': 'SECURITY-001', 'file': 'test.py', 'line': 1}
            result = engine.generate_explanation(finding, "eval(x)")
        
        assert result['confidence'] == 0.6
        assert result['cites_rule'] is False

    def test_rag_prompt_includes_rule_definition(self, engine):
        """Test RAG prompt includes rule from knowledge base"""
        finding = {
            'canonical_rule_id': 'SECURITY-001',
            'file': 'test.py',
            'line': 1,
            'message': 'eval() detected'
        }
        
        prompt = engine._build_evidence_grounded_prompt(finding, "eval(user_input)")
        
        assert 'SECURITY-001' in prompt
        assert 'eval()' in prompt.lower()

    def test_graceful_degradation_without_redis(self):
        """Test engine works without Redis"""
        engine = ExplanationEngine(redis_client=None)
        
        with patch.object(engine.client.chat.completions, 'create') as mock_create:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="Test"))]
            mock_response.usage = Mock(total_tokens=50)
            mock_create.return_value = mock_response
            
            finding = {'canonical_rule_id': 'TEST-001', 'file': 'test.py', 'line': 1}
            result = engine.generate_explanation(finding, "code")
        
        assert result['status'] == 'success'
        assert engine.cache_hits == 0  # No caching without Redis

    def test_cost_calculation(self, engine):
        """Test cost is calculated correctly"""
        with patch.object(engine.client.chat.completions, 'create') as mock_create:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="Test"))]
            mock_response.usage = Mock(total_tokens=1000)
            mock_create.return_value = mock_response
            
            finding = {'canonical_rule_id': 'TEST-001', 'file': 'test.py', 'line': 1}
            result = engine.generate_explanation(finding, "code")
        
        assert 'cost_usd' in result
        assert result['cost_usd'] >= 0

    def test_latency_tracking(self, engine):
        """Test latency is tracked in milliseconds"""
        with patch.object(engine.client.chat.completions, 'create') as mock_create:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="Test"))]
            mock_response.usage = Mock(total_tokens=50)
            mock_create.return_value = mock_response
            
            finding = {'canonical_rule_id': 'TEST-001', 'file': 'test.py', 'line': 1}
            result = engine.generate_explanation(finding, "code")
        
        assert 'latency_ms' in result
        assert result['latency_ms'] > 0
