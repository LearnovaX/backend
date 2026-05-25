# Quick Start

Get rate limiting working in 5 minutes.

## Step 1: Configure Rate Limits

Add to `settings.py`:

```python
RATE_LIMITS = {
    "default_authenticated": {
        "capacity": 1000,
        "refill_rate": 10,  # 600 requests/minute
    },
    "default_anonymous": {
        "capacity": 100,
        "refill_rate": 1,  # 60 requests/minute
    },
}

RATE_LIMITER_CONFIG = {
    "redis_connection": "default",
    "enable_logging": True,
}
```

## Step 2: Enable Rate Limiting Globally

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'src.core.rate_limiting.throttle.TokenBucketThrottle',
    ],
}
```

## Step 3: Done!

All API views are now rate-limited:

```
curl http://localhost:8000/api/endpoint/

# Response includes rate limit headers:
# X-RateLimit-Limit: 1000
# X-RateLimit-Remaining: 999
```

When limit exceeded: `HTTP 429 Too Many Requests`

## Custom Limits per View

```python
from rest_framework.views import APIView
from src.core.rate_limiting.throttle import TokenBucketThrottle

# First, add to RATE_LIMITS
RATE_LIMITS = {
    "login": {
        "capacity": 5,
        "refill_rate": 0.1,
    },
    ...
}

# Then use in view:
class LoginView(APIView):
    throttle_classes = [TokenBucketThrottle]
    throttle_limit_key = "login"
    
    def post(self, request):
        ...
```

## Direct Service Usage

```python
from src.core.rate_limiting.service import RateLimiter
from src.core.rate_limiting.exceptions import RateLimitExceeded

limiter = RateLimiter()

try:
    limiter.check("user:123", "default_authenticated")
    # Request allowed
except RateLimitExceeded as e:
    # Return 429 with Retry-After header
    return Response(
        {"error": "Rate limit exceeded"},
        status=429,
        headers={"Retry-After": str(int(e.retry_after))}
    )
```

## Test It

```bash
# This should succeed
for i in {1..5}; do curl http://localhost:8000/api/endpoint/; done

# 6th request onwards will be rate limited
# Response: HTTP 429 Too Many Requests
```

## What's Happening

1. Each request checks rate limit in Redis
2. Token bucket refills at configured rate
3. When tokens exhausted → HTTP 429
4. Retry-After header tells client when to retry

## Next Steps

- Read [USAGE_GUIDE.md](USAGE_GUIDE.md) for advanced usage
- Read [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- Run tests: `pytest src/core/rate_limiting/tests/`

## Common Issues

**"Too many requests immediately"**
- Check capacity is appropriate (default 100 for anonymous)
- Check refill_rate is not too small

**"Rate limiting not working"**
- Ensure Redis is running and configured
- Check RATE_LIMITS is in settings
- Check TokenBucketThrottle is in DEFAULT_THROTTLE_CLASSES

**"Getting Redis errors"**
- Check Redis connection string
- Ensure Redis server is accessible
- Check Django cache alias matches RATE_LIMITER_CONFIG
