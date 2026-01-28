"""
Rate Limiter for ACR-QA v2.0
Token Bucket algorithm with Redis backend
"""

import time
import redis
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token Bucket rate limiter with Redis backend.

    Enforces: ≤1 analysis per repo per minute

    Features:
    - Token Bucket algorithm
    - Redis connection with exponential backoff retry
    - Rate limit event logging
    - Graceful degradation if Redis unavailable
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        tokens_per_minute: int = 1,
        bucket_size: int = 1,
    ):
        """
        Initialize rate limiter.

        Args:
            redis_host: Redis server hostname
            redis_port: Redis server port
            redis_db: Redis database number
            tokens_per_minute: Number of tokens to add per minute
            bucket_size: Maximum tokens in bucket
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        self.tokens_per_minute = tokens_per_minute
        self.bucket_size = bucket_size
        self.refill_rate = 60.0 / tokens_per_minute  # Seconds per token

        # Connect to Redis (public for Phase 2 caching)
        self.redis = self._connect_redis()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def _connect_redis(self) -> Optional[redis.Redis]:
        """
        Connect to Redis with exponential backoff retry.

        Returns:
            Redis client or None if connection fails
        """
        try:
            client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                socket_connect_timeout=5,
                socket_timeout=5,
                decode_responses=True,
            )
            # Test connection
            client.ping()
            logger.info(f"✓ Connected to Redis at {self.redis_host}:{self.redis_port}")
            return client
        except redis.ConnectionError as e:
            logger.warning(f"⚠ Redis connection failed: {e}")
            logger.warning("Rate limiting will be disabled (graceful degradation)")
            return None
        except Exception as e:
            logger.error(f"✗ Unexpected Redis error: {e}")
            return None

    def _get_bucket_key(self, repo_name: str, pr_number: Optional[int] = None) -> str:
        """
        Generate Redis key for rate limit bucket.

        Args:
            repo_name: Repository name
            pr_number: Pull request number (optional)

        Returns:
            Redis key string
        """
        if pr_number:
            return f"rate_limit:{repo_name}:pr_{pr_number}"
        return f"rate_limit:{repo_name}"

    def check_rate_limit(
        self, repo_name: str, pr_number: Optional[int] = None
    ) -> tuple[bool, Optional[float]]:
        """
        Check if request is allowed under rate limit (Token Bucket algorithm).

        Args:
            repo_name: Repository name
            pr_number: Pull request number (optional)

        Returns:
            Tuple of (allowed: bool, retry_after: Optional[float])
            - allowed: True if request is allowed, False if rate limited
            - retry_after: Seconds to wait before retrying (None if allowed)
        """
        # If Redis is unavailable, allow request (graceful degradation)
        if self.redis is None:
            logger.warning(
                "⚠ Redis unavailable, allowing request without rate limiting"
            )
            return True, None

        bucket_key = self._get_bucket_key(repo_name, pr_number)
        current_time = time.time()

        try:
            # Get current bucket state
            bucket_data = self.redis.hgetall(bucket_key)

            if not bucket_data:
                # First request - initialize bucket
                tokens = self.bucket_size - 1  # Consume 1 token
                last_refill = current_time

                self.redis.hset(
                    bucket_key, mapping={"tokens": tokens, "last_refill": last_refill}
                )
                self.redis.expire(bucket_key, 120)  # Expire after 2 minutes

                logger.info(f"✓ Rate limit OK: {bucket_key} (first request)")
                return True, None

            # Parse bucket state
            tokens = float(bucket_data.get("tokens", 0))
            last_refill = float(bucket_data.get("last_refill", current_time))

            # Refill tokens based on time elapsed
            time_elapsed = current_time - last_refill
            tokens_to_add = time_elapsed / self.refill_rate
            tokens = min(self.bucket_size, tokens + tokens_to_add)

            # Check if we have enough tokens
            if tokens >= 1.0:
                # Consume 1 token
                tokens -= 1.0

                # Update bucket
                self.redis.hset(
                    bucket_key, mapping={"tokens": tokens, "last_refill": current_time}
                )
                self.redis.expire(bucket_key, 120)

                logger.info(
                    f"✓ Rate limit OK: {bucket_key} (tokens remaining: {tokens:.2f})"
                )
                return True, None
            else:
                # Rate limited - calculate retry time
                tokens_needed = 1.0 - tokens
                retry_after = tokens_needed * self.refill_rate

                logger.warning(
                    f"✗ RATE LIMITED: {bucket_key} "
                    f"(tokens: {tokens:.2f}, retry after {retry_after:.1f}s)"
                )

                # Log rate limit event
                self._log_rate_limit_event(repo_name, pr_number, retry_after)

                return False, retry_after

        except redis.RedisError as e:
            logger.error(f"✗ Redis error during rate limit check: {e}")
            # Graceful degradation - allow request
            return True, None
        except Exception as e:
            logger.error(f"✗ Unexpected error during rate limit check: {e}")
            # Graceful degradation - allow request
            return True, None

    def _log_rate_limit_event(
        self, repo_name: str, pr_number: Optional[int], retry_after: float
    ) -> None:
        """
        Log rate limit event for monitoring.

        Args:
            repo_name: Repository name
            pr_number: Pull request number
            retry_after: Seconds to wait before retrying
        """
        event = {
            "timestamp": time.time(),
            "repo_name": repo_name,
            "pr_number": pr_number,
            "retry_after": retry_after,
            "event_type": "rate_limit_exceeded",
        }

        # Log to application logs
        logger.warning(f"Rate limit event: {event}")

        # Optionally store in Redis for monitoring dashboard
        try:
            if self.redis:
                event_key = f"rate_limit_events:{repo_name}"
                self.redis.lpush(event_key, str(event))
                self.redis.ltrim(event_key, 0, 99)  # Keep last 100 events
                self.redis.expire(event_key, 86400)  # Expire after 24 hours
        except Exception as e:
            logger.error(f"Failed to log rate limit event to Redis: {e}")

    def reset_rate_limit(self, repo_name: str, pr_number: Optional[int] = None) -> bool:
        """
        Reset rate limit for a specific repo/PR (admin function).

        Args:
            repo_name: Repository name
            pr_number: Pull request number (optional)

        Returns:
            True if reset successful, False otherwise
        """
        if self.redis is None:
            return False

        bucket_key = self._get_bucket_key(repo_name, pr_number)

        try:
            self.redis.delete(bucket_key)
            logger.info(f"✓ Rate limit reset: {bucket_key}")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to reset rate limit: {e}")
            return False


# Singleton instance
_rate_limiter_instance: Optional[RateLimiter] = None


def get_rate_limiter(
    redis_host: str = "localhost", redis_port: int = 6379
) -> RateLimiter:
    """
    Get singleton rate limiter instance.

    Args:
        redis_host: Redis server hostname
        redis_port: Redis server port

    Returns:
        RateLimiter instance
    """
    global _rate_limiter_instance

    if _rate_limiter_instance is None:
        _rate_limiter_instance = RateLimiter(
            redis_host=redis_host, redis_port=redis_port
        )

    return _rate_limiter_instance


if __name__ == "__main__":
    # Test rate limiter
    print("Testing Rate Limiter...")

    limiter = RateLimiter(redis_host="localhost", redis_port=6379)

    # Test 1: First request should succeed
    allowed, retry_after = limiter.check_rate_limit("test-repo", 1)
    print(f"Test 1 - First request: allowed={allowed}, retry_after={retry_after}")
    assert allowed is True

    # Test 2: Immediate second request should be rate limited
    allowed, retry_after = limiter.check_rate_limit("test-repo", 1)
    print(f"Test 2 - Immediate retry: allowed={allowed}, retry_after={retry_after}")
    assert allowed is False
    assert retry_after is not None

    # Test 3: Different PR should succeed
    allowed, retry_after = limiter.check_rate_limit("test-repo", 2)
    print(f"Test 3 - Different PR: allowed={allowed}, retry_after={retry_after}")
    assert allowed is True

    # Clean up
    limiter.reset_rate_limit("test-repo", 1)
    limiter.reset_rate_limit("test-repo", 2)

    print("\n✅ All rate limiter tests passed!")
