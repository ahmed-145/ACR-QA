"""
Shared test fixtures for ACR-QA tests.
Provides mock Redis and mock Cerebras clients.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


@pytest.fixture
def mock_redis():
    """Create a mock Redis client for testing."""
    redis_mock = MagicMock()
    redis_mock.get.return_value = None  # Cache miss by default
    redis_mock.ping.return_value = True
    redis_mock.hgetall.return_value = {}
    redis_mock.hset.return_value = True
    redis_mock.expire.return_value = True
    redis_mock.delete.return_value = True
    redis_mock.lpush.return_value = True
    redis_mock.ltrim.return_value = True
    redis_mock.setex.return_value = True
    return redis_mock


@pytest.fixture
def mock_redis_limiter(mock_redis):
    """Create a RateLimiter with mocked Redis."""
    with patch("CORE.utils.rate_limiter.redis.Redis", return_value=mock_redis):
        from CORE.utils.rate_limiter import RateLimiter

        limiter = RateLimiter(redis_host="localhost", redis_port=6379)
    return limiter


@pytest.fixture
def mock_cerebras():
    """Create a mock Cerebras client."""
    with patch("CORE.engines.explainer.Cerebras") as MockCerebras:
        mock_client = Mock()
        MockCerebras.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [
            Mock(
                message=Mock(
                    content="This code violates TEST-001 because of a code quality issue."
                )
            )
        ]
        mock_response.usage = Mock(total_tokens=100)
        mock_client.chat.completions.create.return_value = mock_response

        yield mock_client
