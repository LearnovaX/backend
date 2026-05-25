"""
Django REST Framework throttle class for rate limiting.

Integrates the RateLimiter service with DRF's throttling system.
Returns HTTP 429 when rate limit exceeded and includes standard headers.
"""

import logging
from typing import Optional

from rest_framework.throttling import BaseThrottle
from rest_framework.request import Request

from .exceptions import RateLimitExceeded, RateLimitConfigError, RedisConnectionError
from .service import RateLimiter
from .settings import get_rate_limiter_config, get_rate_limits_config

logger = logging.getLogger(__name__)


class TokenBucketThrottle(BaseThrottle):
    """
    DRF throttle class implementing token bucket rate limiting.

    This throttle can be applied per-view or globally in DRF settings.

    Usage in views:
        from rest_framework.views import APIView
        from src.core.rate_limiting.throttle import TokenBucketThrottle

        class LoginView(APIView):
            throttle_classes = [TokenBucketThrottle]
            # ... view logic ...

        # Or set throttle_limit_key to customize:
        class LoginView(APIView):
            throttle_classes = [TokenBucketThrottle]
            throttle_limit_key = "login"  # Use "login" rate limit config
            # ... view logic ...

    Usage in settings.py:
        REST_FRAMEWORK = {
            'DEFAULT_THROTTLE_CLASSES': [
                'src.core.rate_limiting.throttle.TokenBucketThrottle',
            ],
        }

    Rate limit key resolution:
    1. Use view.throttle_limit_key if set
    2. Use view.basename if available (DRF API view name)
    3. Use "default_authenticated" or "default_anonymous" based on auth
    """

    cache_format = "rl:%(identifier)s:%(limit_key)s"

    def __init__(self):
        super().__init__()
        self.rate_limiter = RateLimiter()
        self.config = get_rate_limiter_config()

    def get_identifier(self, request: Request) -> str:
        """
        Get unique identifier for rate limiting.

        Priority:
        1. Authenticated user ID
        2. IP address (X-Forwarded-For or REMOTE_ADDR)

        Args:
            request: DRF Request object

        Returns:
            Unique identifier string
        """
        if request.user and request.user.is_authenticated:
            return f"user:{request.user.id}"

        # Get IP address, considering proxy headers
        ip = self._get_client_ip(request)
        return f"ip:{ip}"

    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request, handling proxies.

        Checks in order:
        1. X-Forwarded-For header (first IP in list)
        2. X-Real-IP header
        3. REMOTE_ADDR

        Args:
            request: DRF Request object

        Returns:
            Client IP address
        """
        # Check X-Forwarded-For (may contain multiple IPs)
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            # Use first IP in the list
            ip = x_forwarded_for.split(",")[0].strip()
            return ip

        # Check X-Real-IP
        x_real_ip = request.META.get("HTTP_X_REAL_IP")
        if x_real_ip:
            return x_real_ip

        # Fallback to REMOTE_ADDR
        return request.META.get("REMOTE_ADDR", "unknown")

    def get_limit_key(self, request: Request, view) -> str:
        """
        Get rate limit key for this request.

        Resolution order:
        1. view.throttle_limit_key (if set)
        2. view.basename (for DRF viewsets)
        3. view class name (lowercase)
        4. default based on authentication status

        Args:
            request: DRF Request object
            view: DRF view being throttled

        Returns:
            Rate limit configuration key
        """
        # Check if view has custom throttle_limit_key
        if hasattr(view, "throttle_limit_key"):
            return view.throttle_limit_key

        # Try to use DRF basename (for viewsets) if configured
        if hasattr(view, "basename") and view.basename:
            # Clean up basename (e.g., 'api:user-list' -> 'user')
            basename = view.basename.split(":")[-1]
            basename = basename.rsplit("-", 1)[0]  # Remove -list, -detail suffix
            if basename in get_rate_limits_config():
                return basename

        # Use default based on authentication
        if request.user and request.user.is_authenticated:
            return "default_authenticated"
        return "default_anonymous"

    def throttle_success(self) -> bool:
        """
        Called after throttle check passes.
        Update response headers before returning.

        Returns:
            True (always returns True from DRF throttle)
        """
        return True

    def throttle_failure(self) -> bool:
        """
        Called after throttle check fails.
        Should not be called as we raise exception instead.

        Returns:
            False (never reached)
        """
        return False

    def allow_request(self, request: Request, view) -> bool:
        """
        Check if request is allowed under rate limit.

        Called by DRF before view execution. If rate limit exceeded,
        sets exception that DRF will handle.

        Args:
            request: DRF Request object
            view: DRF view being throttled

        Returns:
            True if allowed, False (via exception) if not

        Raises:
            Throttled exception (caught by DRF)
        """
        identifier = self.get_identifier(request)
        limit_key = self.get_limit_key(request, view)

        try:
            allowed, info = self.rate_limiter.is_allowed(
                identifier,
                limit_key=limit_key,
                token_cost=1,
            )

            # Store info for response headers
            request.rate_limit_info = info

            if not allowed:
                # Store retry_after on request for use in exception handler
                request.throttled_retry_after = info["retry_after"]
                # Return False to trigger throttled exception
                # (DRF will raise Throttled exception)
                return False

            return True

        except RateLimitConfigError as e:
            logger.error(f"Rate limit configuration error: {e}")
            # Configuration error: allow request, log error
            return True

        except RedisConnectionError as e:
            logger.error(f"Rate limit Redis error: {e}")
            # Redis error: fail based on configured mode
            # (already handled in service, re-raise if needed)
            raise

    def get_throttle_duration(self) -> Optional[float]:
        """
        Get throttle duration for Retry-After header.

        Returns:
            Duration in seconds (used by DRF Throttled exception)
        """
        # This is called by DRF's Throttled exception
        # We'll set it in the exception handler instead
        return None


class CustomThrottledResponse:
    """
    Helper to customize throttle response with rate limit headers.

    Used in custom exception handlers to include rate limit information.
    """

    @staticmethod
    def get_headers_for_response(request: Request) -> dict:
        """
        Get rate limit headers to include in response.

        Args:
            request: DRF Request object

        Returns:
            Dictionary of headers to include in response
        """
        if not hasattr(request, "rate_limit_info"):
            return {}

        info = request.rate_limit_info
        config_key = info["limit_key"]

        headers = {}

        # Include rate limit headers if enabled
        if get_rate_limiter_config()["include_headers"]:
            # Get capacity from config
            try:
                from .settings import get_rate_limit_config
                config = get_rate_limit_config(config_key)
                headers["X-RateLimit-Limit"] = str(int(config["capacity"]))
            except:
                pass

            headers["X-RateLimit-Remaining"] = str(int(info["tokens_remaining"]))

            if info["retry_after"] > 0:
                headers["Retry-After"] = str(int(info["retry_after"] + 1))

        return headers


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF that includes rate limit headers.

    Add this to your DRF settings:

        REST_FRAMEWORK = {
            'EXCEPTION_HANDLER': 'src.core.rate_limiting.throttle.custom_exception_handler',
        }

    Args:
        exc: Exception instance
        context: Context dict from DRF

    Returns:
        Response or None
    """
    from rest_framework.exceptions import Throttled
    from rest_framework.response import Response
    from rest_framework.views import exception_handler

    # Call the default DRF exception handler
    response = exception_handler(exc, context)

    # If it's a throttled exception, add rate limit headers
    if isinstance(exc, Throttled) and response is not None:
        request = context.get("request")
        if request:
            headers = CustomThrottledResponse.get_headers_for_response(request)
            for key, value in headers.items():
                response[key] = value

            # Set Retry-After if stored on request
            if hasattr(request, "throttled_retry_after"):
                response["Retry-After"] = str(int(request.throttled_retry_after + 1))

    return response
