"""
Configuration for rate limiting module.

Configure rate limits in your Django settings.py using the RATE_LIMITS dictionary.
"""

from typing import Dict, Any

from django.conf import settings

# Default rate limit configurations
DEFAULT_RATE_LIMITS = {
    # Authentication endpoints
    "login": {
        "capacity": 5,
        "refill_rate": 0.1,  # 6 requests per minute
        "description": "Login attempts",
    },
    "password_reset": {
        "capacity": 3,
        "refill_rate": 0.05,  # 3 requests per 10 minutes
        "description": "Password reset requests",
    },
    "register": {
        "capacity": 10,
        "refill_rate": 0.2,  # 12 requests per minute
        "description": "User registration",
    },
    # Default limits for authenticated users
    "default_authenticated": {
        "capacity": 1000,
        "refill_rate": 10,  # 600 requests per minute
        "description": "Default authenticated user limit",
    },
    # Default limits for anonymous/unauthenticated users
    "default_anonymous": {
        "capacity": 100,
        "refill_rate": 1,  # 60 requests per minute
        "description": "Default anonymous user limit",
    },
}

# Rate limiter configuration options
DEFAULT_RATE_LIMITER_CONFIG = {
    # Redis connection key
    "redis_connection": "default",
    # Whether to use Lua script with large time gap reset
    "use_script_with_reset": False,
    # Maximum allowed time gap before bucket reset (seconds)
    "max_time_gap": 3600,
    # Failure mode: "open" (allow all) or "closed" (block all)
    "failure_mode": "open",
    # Enable Prometheus metrics
    "enable_metrics": True,
    # Enable detailed logging
    "enable_logging": True,
    # Log level for rate limit events
    "log_level": "WARNING",
    # Whether to include rate limit headers in responses
    "include_headers": True,
}


def get_rate_limits_config() -> Dict[str, Dict[str, Any]]:
    """Get rate limits configuration from Django settings."""
    return getattr(settings, "RATE_LIMITS", DEFAULT_RATE_LIMITS)


def get_rate_limiter_config() -> Dict[str, Any]:
    """Get rate limiter configuration from Django settings."""
    config = getattr(settings, "RATE_LIMITER_CONFIG", {})
    # Merge with defaults
    merged = DEFAULT_RATE_LIMITER_CONFIG.copy()
    merged.update(config)
    return merged


def get_rate_limit_config(limit_key: str) -> Dict[str, Any]:
    """Get specific rate limit configuration."""
    limits = get_rate_limits_config()
    if limit_key not in limits:
        raise ValueError(f"Rate limit '{limit_key}' not configured")
    return limits[limit_key]


def validate_rate_limit_config(config: Dict[str, Any]) -> None:
    """Validate rate limit configuration."""
    if "capacity" not in config:
        raise ValueError("Rate limit config must have 'capacity'")
    if "refill_rate" not in config:
        raise ValueError("Rate limit config must have 'refill_rate'")

    capacity = config["capacity"]
    refill_rate = config["refill_rate"]

    if not isinstance(capacity, (int, float)) or capacity <= 0:
        raise ValueError("capacity must be a positive number")
    if not isinstance(refill_rate, (int, float)) or refill_rate <= 0:
        raise ValueError("refill_rate must be a positive number")


def validate_all_rate_limits() -> None:
    """Validate all configured rate limits."""
    limits = get_rate_limits_config()
    for key, config in limits.items():
        try:
            validate_rate_limit_config(config)
        except ValueError as e:
            raise ValueError(f"Invalid config for rate limit '{key}': {e}")
