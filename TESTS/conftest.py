"""
Shared test fixtures for ACR-QA tests.
Provides mock Redis and mock Groq clients.
"""

import sys
from unittest.mock import MagicMock, Mock, patch


# Mock sentence_transformers globally to prevent tests from trying to download or load model weights from HF
class MockSentenceTransformer:
    def __init__(self, model_name):
        pass

    def encode(self, sentences, **kwargs):
        import numpy as np

        if isinstance(sentences, list):
            return np.zeros((len(sentences), 384))
        return np.zeros(384)


mock_st_module = MagicMock()
mock_st_module.SentenceTransformer = MockSentenceTransformer
sys.modules["sentence_transformers"] = mock_st_module


# Mock dilithium_py globally to prevent slow pure-Python PQ signing from hanging the test suite
class MockDilithium3:
    @staticmethod
    def keygen():
        return b"public_key_bytes_123", b"secret_key_bytes_123"

    @staticmethod
    def sign(sk, payload):
        return b"signature_bytes_123"


mock_dilithium_module = MagicMock()
mock_dilithium_module.Dilithium3 = MockDilithium3
sys.modules["dilithium_py"] = mock_dilithium_module
sys.modules["dilithium_py.dilithium"] = mock_dilithium_module

import pytest


def _db_reachable() -> bool:
    """Return True if PostgreSQL is reachable."""
    try:
        import os

        import psycopg2

        url = os.environ.get("DATABASE_URL", "")
        if url:
            psycopg2.connect(url, connect_timeout=2).close()
        else:
            psycopg2.connect(
                host=os.environ.get("DB_HOST", "localhost"),
                port=int(os.environ.get("DB_PORT", 5432)),
                dbname=os.environ.get("DB_NAME", "acrqa"),
                user=os.environ.get("DB_USER", "acrqa"),
                password=os.environ.get("DB_PASSWORD", ""),
                connect_timeout=2,
            ).close()
        return True
    except Exception:
        return False


_DB_AVAILABLE = None  # cached after first check


def require_db(func):
    """Decorator: skip test if PostgreSQL is unavailable."""
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        global _DB_AVAILABLE
        if _DB_AVAILABLE is None:
            _DB_AVAILABLE = _db_reachable()
        if not _DB_AVAILABLE:
            pytest.skip("PostgreSQL not available")
        return func(*args, **kwargs)

    return wrapper


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Automatically mock environment variables for all tests to prevent ValueError."""
    monkeypatch.setenv("GROQ_API_KEY_1", "test_dummy_groq_key_1")
    monkeypatch.setenv("GROQ_API_KEY", "test_dummy_groq_key")


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
def mock_groq():
    """Create a mock Groq client."""
    with patch("CORE.engines.explainer.Groq") as MockGroq:
        mock_client = Mock()
        MockGroq.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="This code violates TEST-001 because of a code quality issue."))
        ]
        mock_response.usage = Mock(total_tokens=100)
        mock_client.chat.completions.create.return_value = mock_response

        yield mock_client
