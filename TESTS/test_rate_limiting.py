"""
Rate Limiting Tests for ACR-QA v2.0
Tests Token Bucket rate limiter with Redis (mocked)
"""
import pytest
import time
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE.utils.rate_limiter import RateLimiter


def _make_limiter(mock_redis):
    """Helper to create a RateLimiter with mocked Redis."""
    with patch('CORE.utils.rate_limiter.redis.Redis', return_value=mock_redis):
        return RateLimiter(redis_host='localhost', redis_port=6379)


class TestRateLimiting:
    """Test rate limiter functionality"""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        mock = MagicMock()
        mock.ping.return_value = True
        mock.hset.return_value = True
        mock.expire.return_value = True
        mock.delete.return_value = True
        mock.lpush.return_value = True
        mock.ltrim.return_value = True
        return mock
    
    def test_first_request_allowed(self, mock_redis):
        """Test that first request is always allowed"""
        # First request: empty bucket
        mock_redis.hgetall.return_value = {}
        
        limiter = _make_limiter(mock_redis)
        allowed, retry_after = limiter.check_rate_limit('test-repo-1', 1)
        
        assert allowed is True
        assert retry_after is None
    
    def test_immediate_retry_blocked(self, mock_redis):
        """Test that immediate retry is rate limited"""
        # First call: new bucket; second call: no tokens remaining
        mock_redis.hgetall.side_effect = [
            {},  # First request
            {'tokens': '0', 'last_refill': str(time.time())},  # Second request: 0 tokens
        ]
        
        limiter = _make_limiter(mock_redis)
        
        # First request succeeds
        limiter.check_rate_limit('test-repo-2', 1)
        
        # Immediate retry should be blocked
        allowed, retry_after = limiter.check_rate_limit('test-repo-2', 1)
        
        assert allowed is False
        assert retry_after is not None
        assert retry_after > 0
    
    def test_different_pr_allowed(self, mock_redis):
        """Test that different PRs have separate rate limits"""
        # Both requests get empty bucket (first request)
        mock_redis.hgetall.return_value = {}
        
        limiter = _make_limiter(mock_redis)
        
        allowed1, _ = limiter.check_rate_limit('test-repo-3', 1)
        assert allowed1 is True
        
        # Request for PR 2 should also be allowed (different bucket key)
        allowed2, _ = limiter.check_rate_limit('test-repo-3', 2)
        assert allowed2 is True
    
    def test_token_bucket_refill(self, mock_redis):
        """Test that tokens refill over time"""
        # First call: empty; second call: no tokens
        mock_redis.hgetall.side_effect = [
            {},  # First request
            {'tokens': '0', 'last_refill': str(time.time())},  # No tokens
        ]
        
        limiter = _make_limiter(mock_redis)
        limiter.check_rate_limit('test-repo-4', 1)
        
        # Immediate retry should be blocked
        allowed, retry_after = limiter.check_rate_limit('test-repo-4', 1)
        assert allowed is False
        
        # retry_after should be reasonable (around 60 seconds for 1 token/min)
        assert retry_after is not None
        assert retry_after > 0
        assert retry_after <= 65  # Should be around 60 seconds
    
    def test_rate_limit_reset(self, mock_redis):
        """Test manual rate limit reset"""
        # Simulate: first request, then blocked, then reset works
        mock_redis.hgetall.side_effect = [
            {},  # First request
            {'tokens': '0', 'last_refill': str(time.time())},  # Blocked
            {},  # After reset: new bucket
        ]
        
        limiter = _make_limiter(mock_redis)
        
        # First request succeeds
        limiter.check_rate_limit('test-repo-5', 1)
        
        # Should be rate limited
        allowed, _ = limiter.check_rate_limit('test-repo-5', 1)
        assert allowed is False
        
        # Reset rate limit
        success = limiter.reset_rate_limit('test-repo-5', 1)
        assert success is True
        
        # Should now be allowed again
        allowed, _ = limiter.check_rate_limit('test-repo-5', 1)
        assert allowed is True
    
    def test_graceful_degradation_no_redis(self):
        """Test that limiter allows requests if Redis is unavailable"""
        # Create limiter with Redis that fails to connect
        with patch('CORE.utils.rate_limiter.redis.Redis') as MockRedisClass:
            import redis
            MockRedisClass.return_value.ping.side_effect = redis.ConnectionError("mocked")
            
            limiter = RateLimiter(redis_host='invalid-host', redis_port=9999)
        
        # Should allow request (graceful degradation)
        allowed, retry_after = limiter.check_rate_limit('test-repo-6', 1)
        
        # When Redis is unavailable, graceful degradation = allow
        assert allowed is True
    
    def test_concurrent_requests(self, mock_redis):
        """Test that only one request per minute is allowed"""
        # First call: empty; subsequent calls: 0 tokens
        current_time = str(time.time())
        mock_redis.hgetall.side_effect = [
            {},  # First request: empty bucket
            {'tokens': '0', 'last_refill': current_time},
            {'tokens': '0', 'last_refill': current_time},
            {'tokens': '0', 'last_refill': current_time},
            {'tokens': '0', 'last_refill': current_time},
        ]
        
        limiter = _make_limiter(mock_redis)
        
        # Make 5 rapid requests
        results = []
        for i in range(5):
            allowed, _ = limiter.check_rate_limit('test-repo-7', 1)
            results.append(allowed)
        
        # Only first request should be allowed
        assert results[0] is True
        assert all(r is False for r in results[1:])
    
    def test_rate_limit_event_logging(self, mock_redis):
        """Test that rate limit events are logged"""
        # First: empty; second: no tokens
        mock_redis.hgetall.side_effect = [
            {},  # First request
            {'tokens': '0', 'last_refill': str(time.time())},  # Rate limited
        ]
        
        limiter = _make_limiter(mock_redis)
        limiter.check_rate_limit('test-repo-8', 1)
        
        # This should trigger rate limit logging
        allowed, retry_after = limiter.check_rate_limit('test-repo-8', 1)
        
        assert allowed is False
        # Verify event was logged to Redis
        mock_redis.lpush.assert_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

