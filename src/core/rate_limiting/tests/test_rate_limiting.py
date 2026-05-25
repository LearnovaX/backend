"""
Comprehensive test suite for rate limiting module.

Tests cover:
- Token bucket algorithm correctness
- Concurrency and race conditions
- Refill behavior
- Burst support
- Distributed multi-instance correctness
- Configuration validation
- Redis failure modes
- DRF throttle integration
"""

import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework.response import Response
from rest_framework.views import APIView

from ..service import RateLimiter
from ..exceptions import (
    RateLimitExceeded,
    RateLimitConfigError,
    RedisConnectionError,
)
from ..throttle import TokenBucketThrottle
from ..settings import validate_rate_limit_config, get_rate_limit_config

User = get_user_model()


# Test configurations
TEST_RATE_LIMITS = {
    "test_tight": {"capacity": 3, "refill_rate": 0.1},  # 3 burst, ~6/min
    "test_burst": {"capacity": 10, "refill_rate": 0.1},  # 10 burst, ~6/min
    "test_loose": {"capacity": 100, "refill_rate": 10},  # 100 burst, 600/min
}

TEST_RATE_LIMITER_CONFIG = {
    "redis_connection": "default",
    "use_script_with_reset": False,
    "failure_mode": "open",
    "enable_metrics": True,
    "enable_logging": False,  # Disable logging in tests
}


@pytest.fixture
def rate_limiter():
    """Create a rate limiter instance for testing."""
    return RateLimiter()


@pytest.fixture
def request_factory():
    """Create a DRF request factory."""
    return APIRequestFactory()


class TestRateLimiterBasics:
    """Test basic rate limiting functionality."""

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_single_request_allowed(self, rate_limiter):
        """Test that a single request is allowed."""
        allowed, info = rate_limiter.is_allowed(
            identifier="test:user",
            limit_key="test_tight",
        )
        assert allowed is True
        assert info["tokens_remaining"] == 2  # 3 - 1

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_burst_within_capacity(self, rate_limiter):
        """Test that burst within capacity is allowed."""
        identifier = "test:burst_user"

        # Use all capacity
        for i in range(3):
            allowed, info = rate_limiter.is_allowed(
                identifier=identifier,
                limit_key="test_tight",
            )
            assert allowed is True
            assert info["tokens_remaining"] == 3 - (i + 1)

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_exceeds_capacity(self, rate_limiter):
        """Test that requests exceed capacity are denied."""
        identifier = "test:exceed_user"

        # Use all capacity
        for i in range(3):
            allowed, info = rate_limiter.is_allowed(
                identifier=identifier,
                limit_key="test_tight",
            )
            assert allowed is True

        # Next request should be denied
        allowed, info = rate_limiter.is_allowed(
            identifier=identifier,
            limit_key="test_tight",
        )
        assert allowed is False
        assert info["retry_after"] > 0

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_check_method_raises_on_exceeded(self, rate_limiter):
        """Test that check() raises RateLimitExceeded."""
        identifier = "test:check_user"

        # Use up capacity
        for _ in range(3):
            rate_limiter.check(identifier=identifier, limit_key="test_tight")

        # Next should raise
        with pytest.raises(RateLimitExceeded) as exc_info:
            rate_limiter.check(identifier=identifier, limit_key="test_tight")

        assert exc_info.value.retry_after > 0


class TestTokenRefill:
    """Test token refill behavior."""

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_tokens_refill_over_time(self, rate_limiter):
        """Test that tokens are refilled over time."""
        identifier = "test:refill_user"
        
        # Use all tokens
        for _ in range(3):
            rate_limiter.check(identifier=identifier, limit_key="test_tight")

        # Should be denied immediately
        allowed, info = rate_limiter.is_allowed(
            identifier=identifier,
            limit_key="test_tight",
        )
        assert allowed is False
        assert info["tokens_remaining"] == 0

        # Wait for refill (0.1 tokens/sec, so ~10 seconds for 1 token)
        # For testing, wait less and check partial refill
        time.sleep(1.1)  # ~0.1 tokens should refill

        allowed, info = rate_limiter.is_allowed(
            identifier=identifier,
            limit_key="test_tight",
        )
        # Should have approximately 0.1 tokens, not enough for 1
        assert allowed is False
        assert info["tokens_remaining"] < 1

        # Wait more for full refill of 1 token
        time.sleep(9)  # Total ~10 seconds

        allowed, info = rate_limiter.is_allowed(
            identifier=identifier,
            limit_key="test_tight",
        )
        # Should have at least 1 token now
        assert allowed is True

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_tokens_clamped_to_capacity(self, rate_limiter):
        """Test that tokens don't exceed capacity."""
        identifier = "test:clamp_user"

        # Make a request (consume 1 token)
        rate_limiter.check(identifier=identifier, limit_key="test_tight")

        # Wait a long time (should refill but not exceed capacity)
        time.sleep(1)

        tokens = rate_limiter.get_remaining_tokens(identifier, "test_tight")
        assert tokens <= 3  # Should not exceed capacity


class TestConfigValidation:
    """Test configuration validation."""

    def test_valid_config(self):
        """Test that valid configs pass validation."""
        config = {"capacity": 100, "refill_rate": 1}
        validate_rate_limit_config(config)  # Should not raise

    def test_missing_capacity(self):
        """Test that missing capacity raises error."""
        config = {"refill_rate": 1}
        with pytest.raises(ValueError):
            validate_rate_limit_config(config)

    def test_missing_refill_rate(self):
        """Test that missing refill_rate raises error."""
        config = {"capacity": 100}
        with pytest.raises(ValueError):
            validate_rate_limit_config(config)

    def test_invalid_capacity_zero(self):
        """Test that zero capacity raises error."""
        config = {"capacity": 0, "refill_rate": 1}
        with pytest.raises(ValueError):
            validate_rate_limit_config(config)

    def test_invalid_refill_rate_negative(self):
        """Test that negative refill rate raises error."""
        config = {"capacity": 100, "refill_rate": -1}
        with pytest.raises(ValueError):
            validate_rate_limit_config(config)


class TestConcurrency:
    """Test concurrent access and race conditions."""

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_concurrent_requests_single_thread(self, rate_limiter):
        """Test that concurrent requests from same identifier are atomic."""
        identifier = "test:concurrent_user"

        # Make 5 rapid requests (capacity is 3)
        results = []
        for _ in range(5):
            allowed, info = rate_limiter.is_allowed(
                identifier=identifier,
                limit_key="test_tight",
            )
            results.append(allowed)

        # First 3 should be allowed, next 2 denied
        assert sum(results) == 3
        assert results == [True, True, True, False, False]

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_concurrent_requests_different_identifiers(self, rate_limiter):
        """Test that different identifiers have independent limits."""
        # Make concurrent requests from different users
        results = {}
        for user_id in range(5):
            allowed, info = rate_limiter.is_allowed(
                identifier=f"test:user:{user_id}",
                limit_key="test_tight",
            )
            results[user_id] = allowed

        # All should be allowed (separate limits)
        assert all(results.values())

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_threaded_concurrent_requests(self, rate_limiter):
        """Test thread safety with ThreadPoolExecutor."""
        identifier = "test:thread_user"
        results = []

        def make_request():
            allowed, _ = rate_limiter.is_allowed(
                identifier=identifier,
                limit_key="test_burst",
            )
            return allowed

        # Make 20 concurrent requests (capacity is 10)
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            for future in as_completed(futures):
                results.append(future.result())

        # Should have exactly 10 allowed
        assert sum(results) == 10


class TestRedisFailureMode:
    """Test behavior when Redis is unavailable."""

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG={**TEST_RATE_LIMITER_CONFIG, "failure_mode": "open"},
    )
    def test_failure_open_allows_request(self, rate_limiter):
        """Test that fail-open mode allows request on Redis error."""
        identifier = "test:failopen_user"

        # Mock Redis to raise error
        with patch.object(rate_limiter.redis, "evalsha", side_effect=Exception("Redis down")):
            allowed, info = rate_limiter.is_allowed(
                identifier=identifier,
                limit_key="test_tight",
            )
            # Should allow request
            assert allowed is True

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG={**TEST_RATE_LIMITER_CONFIG, "failure_mode": "closed"},
    )
    def test_failure_closed_denies_request(self, rate_limiter):
        """Test that fail-closed mode raises exception on Redis error."""
        identifier = "test:failclosed_user"

        # Mock Redis to raise error
        with patch.object(rate_limiter.redis, "evalsha", side_effect=Exception("Redis down")):
            with pytest.raises(RedisConnectionError):
                rate_limiter.is_allowed(
                    identifier=identifier,
                    limit_key="test_tight",
                )


class TestRateLimiterReset:
    """Test rate limit reset functionality."""

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_reset_single_limit(self, rate_limiter):
        """Test resetting a single rate limit."""
        identifier = "test:reset_user"

        # Use up tokens
        for _ in range(3):
            rate_limiter.check(identifier=identifier, limit_key="test_tight")

        # Should be denied
        allowed, _ = rate_limiter.is_allowed(
            identifier=identifier,
            limit_key="test_tight",
        )
        assert allowed is False

        # Reset
        rate_limiter.reset(identifier, limit_key="test_tight")

        # Should be allowed again
        allowed, _ = rate_limiter.is_allowed(
            identifier=identifier,
            limit_key="test_tight",
        )
        assert allowed is True


class TestRateLimiterStats:
    """Test rate limiter statistics and info."""

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_get_remaining_tokens(self, rate_limiter):
        """Test getting remaining tokens."""
        identifier = "test:stats_user"

        tokens = rate_limiter.get_remaining_tokens(identifier, "test_tight")
        assert tokens == 3  # Full capacity

        # Consume 1
        rate_limiter.check(identifier=identifier, limit_key="test_tight")

        tokens = rate_limiter.get_remaining_tokens(identifier, "test_tight")
        assert tokens == 2

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_get_stats(self, rate_limiter):
        """Test getting detailed stats."""
        identifier = "test:stats_detailed_user"

        stats = rate_limiter.get_stats(identifier, "test_tight")
        assert stats["capacity"] == 3
        assert stats["refill_rate"] == 0.1
        assert stats["remaining_tokens"] == 3


class TestTokenBucketThrottle(APITestCase):
    """Test DRF TokenBucketThrottle integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="testpass",
            first_name="Test",
        )

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_throttle_get_identifier_authenticated(self):
        """Test that authenticated users are identified by user ID."""
        throttle = TokenBucketThrottle()
        request = self.factory.get("/")
        request.user = self.user

        identifier = throttle.get_identifier(request)
        assert identifier == f"user:{self.user.id}"

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_throttle_get_identifier_anonymous(self):
        """Test that anonymous users are identified by IP."""
        throttle = TokenBucketThrottle()
        request = self.factory.get("/")
        request.user = Mock(is_authenticated=False)

        identifier = throttle.get_identifier(request)
        assert identifier.startswith("ip:")

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_throttle_get_limit_key_from_view_attribute(self):
        """Test that throttle_limit_key is read from view."""
        throttle = TokenBucketThrottle()
        request = self.factory.get("/")
        request.user = Mock(is_authenticated=True)

        view = Mock()
        view.throttle_limit_key = "test_tight"

        limit_key = throttle.get_limit_key(request, view)
        assert limit_key == "test_tight"

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_throttle_get_limit_key_default_authenticated(self):
        """Test default limit key for authenticated users."""
        throttle = TokenBucketThrottle()
        request = self.factory.get("/")
        request.user = self.user

        view = Mock(spec=APIView)

        limit_key = throttle.get_limit_key(request, view)
        assert limit_key == "default_authenticated"

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_throttle_get_limit_key_default_anonymous(self):
        """Test default limit key for anonymous users."""
        throttle = TokenBucketThrottle()
        request = self.factory.get("/")
        request.user = Mock(is_authenticated=False)

        view = Mock(spec=APIView)

        limit_key = throttle.get_limit_key(request, view)
        assert limit_key == "default_anonymous"

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_throttle_allow_request_succeeds(self):
        """Test that allow_request returns True when under limit."""
        throttle = TokenBucketThrottle()
        request = self.factory.get("/")
        request.user = Mock(is_authenticated=False)

        view = Mock(spec=APIView)
        view.throttle_limit_key = "test_loose"

        allowed = throttle.allow_request(request, view)
        assert allowed is True
        assert hasattr(request, "rate_limit_info")

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_throttle_allow_request_fails(self):
        """Test that allow_request returns False when over limit."""
        throttle = TokenBucketThrottle()
        request = self.factory.get("/")
        request.user = Mock(is_authenticated=False)

        view = Mock(spec=APIView)
        view.throttle_limit_key = "test_tight"

        # Use up tokens
        for _ in range(3):
            throttle.allow_request(request, view)

        # Next should fail
        allowed = throttle.allow_request(request, view)
        assert allowed is False


class TestDistributedCorrectness:
    """Test distributed correctness across multiple limiter instances."""

    @override_settings(
        RATE_LIMITS=TEST_RATE_LIMITS,
        RATE_LIMITER_CONFIG=TEST_RATE_LIMITER_CONFIG,
    )
    def test_multiple_limiter_instances_share_state(self):
        """Test that multiple RateLimiter instances share state via Redis."""
        limiter1 = RateLimiter()
        limiter2 = RateLimiter()

        identifier = "test:distributed_user"

        # Use tokens with first limiter
        limiter1.check(identifier=identifier, limit_key="test_tight")
        limiter1.check(identifier=identifier, limit_key="test_tight")

        # Check with second limiter (should see shared state)
        tokens = limiter2.get_remaining_tokens(identifier, "test_tight")
        assert tokens == 1

        # Use remaining token with second limiter
        limiter2.check(identifier=identifier, limit_key="test_tight")

        # Both should see exhausted limit
        allowed1, _ = limiter1.is_allowed(identifier=identifier, limit_key="test_tight")
        allowed2, _ = limiter2.is_allowed(identifier=identifier, limit_key="test_tight")

        assert allowed1 is False
        assert allowed2 is False
