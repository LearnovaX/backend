"""
Rate limiting module for Django + DRF using Redis and token bucket algorithm.

This package provides production-grade distributed rate limiting with:
- Token bucket algorithm
- Redis-backed atomic operations
- DRF integration (throttle class)
- Comprehensive logging and metrics
- Failure modes (open/closed)

Basic usage:
    from src.core.rate_limiting.service import RateLimiter

    limiter = RateLimiter()
    try:
        limiter.check(identifier="user:123", limit_key="default_authenticated")
        # Request allowed
    except RateLimitExceeded as e:
        # Request denied, retry_after = e.retry_after seconds

DRF usage:
    from src.core.rate_limiting.throttle import TokenBucketThrottle

    class MyView(APIView):
        throttle_classes = [TokenBucketThrottle]
        # Optional: throttle_limit_key = "custom_limit"

Configuration in Django settings.py:
    RATE_LIMITS = {
        "login": {
            "capacity": 5,
            "refill_rate": 0.1,  # 6 requests per minute
        },
        "default_authenticated": {
            "capacity": 1000,
            "refill_rate": 10,  # 600 requests per minute
        },
        "default_anonymous": {
            "capacity": 100,
            "refill_rate": 1,  # 60 requests per minute
        },
    }

    RATE_LIMITER_CONFIG = {
        "redis_connection": "default",
        "enable_metrics": True,
        "enable_logging": True,
        "failure_mode": "open",  # "open" = allow, "closed" = block
    }
"""

from .service import RateLimiter
from .throttle import TokenBucketThrottle, custom_exception_handler
from .exceptions import (
    RateLimitError,
    RateLimitExceeded,
    RateLimitConfigError,
    RedisConnectionError,
)
from .metrics import get_metrics

__all__ = [
    "RateLimiter",
    "TokenBucketThrottle",
    "custom_exception_handler",
    "RateLimitError",
    "RateLimitExceeded",
    "RateLimitConfigError",
    "RedisConnectionError",
    "get_metrics",
]
