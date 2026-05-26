"""
Custom exceptions for rate limiting module.
"""


class RateLimitError(Exception):
    """Base exception for rate limiting errors."""

    pass


class RateLimitExceeded(RateLimitError):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: float = None, message: str = None):
        self.retry_after = retry_after
        self.message = message or "Rate limit exceeded"
        super().__init__(self.message)


class RateLimitConfigError(RateLimitError):
    """Raised when rate limiter configuration is invalid."""

    pass


class RedisConnectionError(RateLimitError):
    """Raised when Redis connection fails."""

    pass
