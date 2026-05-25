"""
Prometheus metrics for rate limiting module.

Provides observability into rate limiting behavior and Redis performance.
"""

import logging
from typing import Optional

try:
    from prometheus_client import Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)


class RateLimitMetrics:
    """Prometheus metrics for rate limiting."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled and PROMETHEUS_AVAILABLE

        if self.enabled:
            # Counter for allowed requests
            self.requests_allowed = Counter(
                "rate_limit_requests_allowed_total",
                "Total allowed requests",
                ["limit_key", "user_type"],
            )

            # Counter for blocked requests
            self.requests_blocked = Counter(
                "rate_limit_requests_blocked_total",
                "Total blocked requests",
                ["limit_key", "user_type"],
            )

            # Gauge for current token count
            self.tokens_remaining = Gauge(
                "rate_limit_tokens_remaining",
                "Current remaining tokens",
                ["limit_key", "user_type"],
            )

            # Histogram for Redis operation latency
            self.redis_latency = Histogram(
                "rate_limit_redis_latency_seconds",
                "Redis operation latency",
                ["operation"],
                buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
            )

            # Counter for Redis errors
            self.redis_errors = Counter(
                "rate_limit_redis_errors_total",
                "Total Redis errors",
                ["operation", "error_type"],
            )

            # Gauge for rate limiter failure mode switches
            self.failure_mode_active = Gauge(
                "rate_limit_failure_mode_active",
                "Active failure mode (1=open, 0=closed)",
            )
        else:
            logger.debug("Prometheus not available, metrics disabled")

    def record_request_allowed(self, limit_key: str, user_type: str) -> None:
        """Record an allowed request."""
        if self.enabled:
            self.requests_allowed.labels(limit_key=limit_key, user_type=user_type).inc()

    def record_request_blocked(self, limit_key: str, user_type: str) -> None:
        """Record a blocked request."""
        if self.enabled:
            self.requests_blocked.labels(limit_key=limit_key, user_type=user_type).inc()

    def set_tokens_remaining(
        self, limit_key: str, user_type: str, tokens: float
    ) -> None:
        """Record current token count."""
        if self.enabled:
            self.tokens_remaining.labels(
                limit_key=limit_key, user_type=user_type
            ).set(tokens)

    def record_redis_latency(self, operation: str, latency_seconds: float) -> None:
        """Record Redis operation latency."""
        if self.enabled:
            self.redis_latency.labels(operation=operation).observe(latency_seconds)

    def record_redis_error(self, operation: str, error_type: str) -> None:
        """Record Redis error."""
        if self.enabled:
            self.redis_errors.labels(operation=operation, error_type=error_type).inc()

    def set_failure_mode_open(self, is_open: bool) -> None:
        """Set failure mode (1=open, 0=closed)."""
        if self.enabled:
            self.failure_mode_active.set(1 if is_open else 0)


# Global metrics instance
_metrics_instance: Optional[RateLimitMetrics] = None


def get_metrics(enabled: bool = True) -> RateLimitMetrics:
    """Get or create global metrics instance."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = RateLimitMetrics(enabled=enabled)
    return _metrics_instance


def reset_metrics() -> None:
    """Reset global metrics instance (for testing)."""
    global _metrics_instance
    _metrics_instance = None
