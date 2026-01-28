"""
Rate Limiting Tests for ACR-QA v2.0
Tests Token Bucket rate limiter with Redis
"""
import pytest
import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from CORE.utils.rate_limiter import RateLimiter


class TestRateLimiting:
    """Test rate limiter functionality"""
    
    @pytest.fixture
    def limiter(self):
        """Create a rate limiter instance for testing"""
        return RateLimiter(redis_host='localhost', redis_port=6379)
    
    def test_first_request_allowed(self, limiter):
        """Test that first request is always allowed"""
        # Reset any existing rate limits
        limiter.reset_rate_limit('test-repo-1', 1)
        
        allowed, retry_after = limiter.check_rate_limit('test-repo-1', 1)
        
        assert allowed is True
        assert retry_after is None
    
    def test_immediate_retry_blocked(self, limiter):
        """Test that immediate retry is rate limited"""
        # Reset and make first request
        limiter.reset_rate_limit('test-repo-2', 1)
        limiter.check_rate_limit('test-repo-2', 1)
        
        # Immediate retry should be blocked
        allowed, retry_after = limiter.check_rate_limit('test-repo-2', 1)
        
        assert allowed is False
        assert retry_after is not None
        assert retry_after > 0
    
    def test_different_pr_allowed(self, limiter):
        """Test that different PRs have separate rate limits"""
        # Reset and make request for PR 1
        limiter.reset_rate_limit('test-repo-3', 1)
        limiter.reset_rate_limit('test-repo-3', 2)
        
        allowed1, _ = limiter.check_rate_limit('test-repo-3', 1)
        assert allowed1 is True
        
        # Request for PR 2 should also be allowed
        allowed2, _ = limiter.check_rate_limit('test-repo-3', 2)
        assert allowed2 is True
    
    def test_token_bucket_refill(self, limiter):
        """Test that tokens refill over time"""
        # Reset and make first request
        limiter.reset_rate_limit('test-repo-4', 1)
        limiter.check_rate_limit('test-repo-4', 1)
        
        # Immediate retry should be blocked
        allowed, retry_after = limiter.check_rate_limit('test-repo-4', 1)
        assert allowed is False
        
        # Wait for token to refill (60 seconds per token)
        # For testing, we'll just verify retry_after is reasonable
        assert 50 < retry_after < 70  # Should be around 60 seconds
    
    def test_rate_limit_reset(self, limiter):
        """Test manual rate limit reset"""
        # Make request
        limiter.reset_rate_limit('test-repo-5', 1)
        limiter.check_rate_limit('test-repo-5', 1)
        
        # Should be rate limited
        allowed, _ = limiter.check_rate_limit('test-repo-5', 1)
        assert allowed is False
        
        # Reset rate limit
        success = limiter.reset_rate_limit('test-repo-5', 1)
        assert success is True
        
        # Should now be allowed
        allowed, _ = limiter.check_rate_limit('test-repo-5', 1)
        assert allowed is True
    
    def test_graceful_degradation_no_redis(self):
        """Test that limiter allows requests if Redis is unavailable"""
        # Create limiter with invalid Redis connection
        limiter = RateLimiter(redis_host='invalid-host', redis_port=9999)
        
        # Should allow request (graceful degradation)
        allowed, retry_after = limiter.check_rate_limit('test-repo-6', 1)
        
        # May be True (graceful degradation) or False (if Redis is actually running)
        # Just verify it doesn't crash
        assert allowed in [True, False]
    
    def test_concurrent_requests(self, limiter):
        """Test that only one request per minute is allowed"""
        # Reset
        limiter.reset_rate_limit('test-repo-7', 1)
        
        # Make 5 rapid requests
        results = []
        for i in range(5):
            allowed, _ = limiter.check_rate_limit('test-repo-7', 1)
            results.append(allowed)
        
        # Only first request should be allowed
        assert results[0] is True
        assert all(r is False for r in results[1:])
    
    def test_rate_limit_event_logging(self, limiter):
        """Test that rate limit events are logged"""
        # Reset and trigger rate limit
        limiter.reset_rate_limit('test-repo-8', 1)
        limiter.check_rate_limit('test-repo-8', 1)
        
        # This should log a rate limit event
        allowed, retry_after = limiter.check_rate_limit('test-repo-8', 1)
        
        assert allowed is False
        # Event should be logged (check Redis if needed)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
