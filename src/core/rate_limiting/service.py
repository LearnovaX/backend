"""
Core rate limiting service using Redis and token bucket algorithm.

This module provides the RateLimiter class which implements the token bucket algorithm
for distributed rate limiting across multiple application instances.

Key features:
- Atomic operations using Redis Lua scripts
- No race conditions
- Distributed correctness
- Comprehensive error handling
- Observability via metrics and logging
"""

import logging
import time
from typing import Tuple, Optional, Dict, Any

from django.core.cache import caches

from .exceptions import (
    RateLimitExceeded,
    RateLimitConfigError,
    RedisConnectionError,
)
from .lua_script import get_token_bucket_script, get_token_bucket_script_with_reset
from .metrics import get_metrics
from .settings import (
    get_rate_limit_config,
    get_rate_limiter_config,
    validate_rate_limit_config,
)

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Distributed token bucket rate limiter using Redis.

    The token bucket algorithm allows for both rate limiting and burst handling:
    - Tokens are added at a constant refill_rate (tokens per second)
    - Capacity limits the maximum burst (max tokens that can accumulate)
    - Each request consumes 1 token
    - If no tokens available, request is denied

    This implementation is atomic and race-condition safe:
    - All state updates happen in Redis via Lua script
    - No GET/SET races possible
    - Works correctly across multiple application instances
    """

    def __init__(self, redis_alias: str = None):
        """
        Initialize rate limiter.

        Args:
            redis_alias: Django cache alias for Redis connection
        """
        self.config = get_rate_limiter_config()
        self.redis_alias = redis_alias or self.config["redis_connection"]
        self.redis = None
        self.lua_script_sha = None
        self.lua_script_sha_with_reset = None
        self.metrics = get_metrics()

        self._initialize_redis()
        self._initialize_lua_scripts()

    def _initialize_redis(self) -> None:
        """Initialize Redis connection."""
        try:
            try:
                from django_redis import get_redis_connection

                self.redis = get_redis_connection(self.redis_alias)
            except Exception:
                cache = caches[self.redis_alias]
                # Get the raw Redis client from Django's cache
                if hasattr(cache, "client") and hasattr(cache.client, "get_client"):
                    self.redis = cache.client.get_client()
                elif hasattr(cache, "_cache"):
                    self.redis = cache._cache
                elif hasattr(cache, "_client"):
                    self.redis = cache._client
                else:
                    # Fallback: try to access the connection directly
                    self.redis = cache

            if not self.redis or not hasattr(self.redis, "script_load"):
                logger.error(
                    "Redis client unavailable or incompatible for alias '%s'",
                    self.redis_alias,
                )
                self.redis = None
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            self.redis = None

    def _initialize_lua_scripts(self) -> None:
        """Load Lua scripts to Redis."""
        if not self.redis:
            logger.error("Redis client not initialized; skipping Lua script load")
            return

        try:
            if self.config["use_script_with_reset"]:
                script = get_token_bucket_script_with_reset()
            else:
                script = get_token_bucket_script()

            # Register script and get SHA hash
            self.lua_script_sha = self.redis.script_load(script)
            logger.debug(f"Lua script loaded with SHA: {self.lua_script_sha}")
        except Exception as e:
            logger.error(f"Failed to load Lua script: {e}")
            self.lua_script_sha = None

    def _get_rate_limit_key(
        self, identifier: str, limit_key: str = None
    ) -> str:
        """
        Generate Redis key for rate limit.

        Args:
            identifier: IP address, user ID, or other identifier
            limit_key: optional specific limit key (e.g., 'login', 'default_authenticated')

        Returns:
            Redis key like "rl:default_authenticated:user:123"
        """
        if limit_key:
            return f"rl:{limit_key}:{identifier}"
        return f"rl:{identifier}"

    def _record_metric(
        self, allowed: bool, limit_key: str, user_type: str, tokens: float
    ) -> None:
        """Record metrics for this rate limit check."""
        if allowed:
            self.metrics.record_request_allowed(limit_key, user_type)
        else:
            self.metrics.record_request_blocked(limit_key, user_type)

        self.metrics.set_tokens_remaining(limit_key, user_type, tokens)

    def _log_rate_limit_event(
        self,
        allowed: bool,
        identifier: str,
        limit_key: str,
        tokens: float,
        retry_after: float,
    ) -> None:
        """Log rate limit events."""
        if not self.config["enable_logging"]:
            return

        if allowed:
            logger.debug(
                f"Rate limit check passed: {limit_key}={identifier} "
                f"(remaining={tokens:.2f})"
            )
        else:
            log_level = getattr(logging, self.config["log_level"])
            logger.log(
                log_level,
                f"Rate limit exceeded: {limit_key}={identifier} "
                f"(remaining={tokens:.2f}, retry_after={retry_after:.2f}s)",
            )

    def is_allowed(
        self,
        identifier: str,
        limit_key: str = "default",
        token_cost: float = 1,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a request is allowed under rate limit.

        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            limit_key: Rate limit configuration key
            token_cost: Number of tokens to consume (default 1)

        Returns:
            Tuple of (allowed: bool, info: dict) where info contains:
            - tokens_remaining: Current token count
            - retry_after: Seconds until next token available (if denied)
            - limit_key: The limit key used
            - cost: Tokens consumed

        Raises:
            RateLimitConfigError: If limit_key not configured
            RedisConnectionError: If Redis unavailable and fail_closed mode
        """
        # Validate configuration
        try:
            config = get_rate_limit_config(limit_key)
            validate_rate_limit_config(config)
        except ValueError as e:
            raise RateLimitConfigError(str(e))

        capacity = config["capacity"]
        refill_rate = config["refill_rate"]

        redis_key = self._get_rate_limit_key(identifier, limit_key)
        current_time = time.time()

        info = {
            "tokens_remaining": capacity,
            "retry_after": 0,
            "limit_key": limit_key,
            "cost": token_cost,
        }

        failure_mode = self.config["failure_mode"]

        if not self.redis or not self.lua_script_sha:
            self.metrics.set_failure_mode_open(failure_mode == "open")
            if failure_mode == "closed":
                raise RedisConnectionError(
                    "Redis client unavailable or Lua script not loaded"
                )
            logger.warning(
                "Redis client unavailable or Lua script not loaded; allowing request"
            )
            return True, info

        try:
            # Execute Lua script atomically
            start_time = time.time()

            result = self.redis.evalsha(
                self.lua_script_sha,
                1,  # number of keys
                redis_key,  # KEYS[1]
                capacity,  # ARGV[1]
                refill_rate,  # ARGV[2]
                current_time,  # ARGV[3]
                token_cost,  # ARGV[4]
            )

            latency = time.time() - start_time
            self.metrics.record_redis_latency("evalsha", latency)

            # Parse result
            allowed = bool(int(result[0]))
            tokens_remaining = float(result[1])
            retry_after = float(result[2])

            info["tokens_remaining"] = tokens_remaining
            info["retry_after"] = retry_after

            # Record metrics
            user_type = "authenticated" if identifier.isdigit() else "anonymous"
            self._record_metric(allowed, limit_key, user_type, tokens_remaining)
            self._log_rate_limit_event(allowed, identifier, limit_key, tokens_remaining, retry_after)

            return allowed, info

        except Exception as e:
            # Handle Redis errors
            logger.error(f"Redis error in rate limiting: {e}")
            self.metrics.record_redis_error("evalsha", type(e).__name__)

            failure_mode = self.config["failure_mode"]
            self.metrics.set_failure_mode_open(failure_mode == "open")

            if failure_mode == "closed":
                # Fail closed: deny all requests
                raise RedisConnectionError(f"Redis unavailable and fail-closed mode: {e}")
            else:
                # Fail open: allow all requests
                logger.warning(
                    f"Redis error with fail-open mode, allowing request: {e}"
                )
                return True, info

    def check(
        self,
        identifier: str,
        limit_key: str = "default",
        token_cost: float = 1,
    ) -> Dict[str, Any]:
        """
        Check rate limit and raise exception if exceeded.

        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            limit_key: Rate limit configuration key
            token_cost: Number of tokens to consume

        Returns:
            Info dictionary (same as is_allowed)

        Raises:
            RateLimitExceeded: If rate limit is exceeded
            RateLimitConfigError: If configuration is invalid
            RedisConnectionError: If Redis unavailable and fail-closed
        """
        allowed, info = self.is_allowed(identifier, limit_key, token_cost)
        if not allowed:
            raise RateLimitExceeded(
                retry_after=info["retry_after"],
                message=f"Rate limit exceeded for {limit_key}",
            )
        return info

    def reset(self, identifier: str, limit_key: str = None) -> None:
        """
        Reset rate limit for an identifier.

        Useful for admin operations or debugging.

        Args:
            identifier: Unique identifier to reset
            limit_key: Specific limit to reset, or None for all
        """
        try:
            if limit_key:
                key = self._get_rate_limit_key(identifier, limit_key)
                self.redis.delete(key)
                logger.info(f"Reset rate limit: {key}")
            else:
                # Reset all limits for identifier
                pattern = f"rl:*:{identifier}"
                keys = self.redis.keys(pattern)
                if keys:
                    self.redis.delete(*keys)
                    logger.info(f"Reset all rate limits for {identifier}")
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")

    def get_remaining_tokens(
        self, identifier: str, limit_key: str
    ) -> Optional[float]:
        """
        Get current remaining tokens for an identifier (read-only).

        Args:
            identifier: Unique identifier
            limit_key: Rate limit key

        Returns:
            Remaining tokens or None if not found
        """
        try:
            config = get_rate_limit_config(limit_key)
            redis_key = self._get_rate_limit_key(identifier, limit_key)

            state = self.redis.hgetall(redis_key)
            if not state:
                return config["capacity"]

            current_tokens = float(state.get(b"tokens", config["capacity"]))
            last_refill = float(state.get(b"last_refill", time.time()))

            # Calculate refilled tokens
            refill_rate = config["refill_rate"]
            time_elapsed = time.time() - last_refill
            tokens_to_add = time_elapsed * refill_rate

            return min(config["capacity"], current_tokens + tokens_to_add)
        except Exception as e:
            logger.error(f"Failed to get remaining tokens: {e}")
            return None

    def get_stats(self, identifier: str, limit_key: str) -> Dict[str, Any]:
        """
        Get detailed stats about a rate limit.

        Args:
            identifier: Unique identifier
            limit_key: Rate limit key

        Returns:
            Dictionary with stats including capacity, refill_rate, remaining_tokens, etc.
        """
        try:
            config = get_rate_limit_config(limit_key)
            redis_key = self._get_rate_limit_key(identifier, limit_key)

            state = self.redis.hgetall(redis_key)
            current_tokens = config["capacity"]
            last_refill = time.time()

            if state:
                current_tokens = float(state.get(b"tokens", current_tokens))
                last_refill = float(state.get(b"last_refill", last_refill))

            # Calculate current state
            time_elapsed = time.time() - last_refill
            refill_rate = config["refill_rate"]
            tokens_to_add = time_elapsed * refill_rate
            actual_tokens = min(config["capacity"], current_tokens + tokens_to_add)

            return {
                "identifier": identifier,
                "limit_key": limit_key,
                "capacity": config["capacity"],
                "refill_rate": config["refill_rate"],
                "remaining_tokens": actual_tokens,
                "description": config.get("description", ""),
                "time_elapsed": time_elapsed,
                "next_refill_in": max(0, (1 / refill_rate - time_elapsed)) if refill_rate > 0 else 0,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
