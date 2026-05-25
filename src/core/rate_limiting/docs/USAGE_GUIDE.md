# Usage Guide

## Installation & Setup

### 1. Ensure Redis is Configured

In `settings.py`:

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### 2. Configure Rate Limits

Add to `settings.py`:

```python
RATE_LIMITS = {
    "login": {
        "capacity": 5,
        "refill_rate": 0.1,
        "description": "Login attempts",
    },
    "password_reset": {
        "capacity": 3,
        "refill_rate": 0.05,
        "description": "Password reset requests",
    },
    "default_authenticated": {
        "capacity": 1000,
        "refill_rate": 10,
        "description": "Default authenticated user limit",
    },
    "default_anonymous": {
        "capacity": 100,
        "refill_rate": 1,
        "description": "Default anonymous user limit",
    },
}

RATE_LIMITER_CONFIG = {
    "redis_connection": "default",
    "enable_metrics": True,
    "enable_logging": True,
    "failure_mode": "open",  # "open" or "closed"
}
```

### 3. Add to DRF Settings

Option A: Global (all views):

```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'src.core.rate_limiting.throttle.TokenBucketThrottle',
    ],
    'EXCEPTION_HANDLER': 'src.core.rate_limiting.throttle.custom_exception_handler',
}
```

Option B: Per-view (specific views):

```python
from src.core.rate_limiting.throttle import TokenBucketThrottle

class MyView(APIView):
    throttle_classes = [TokenBucketThrottle]
```

## Basic Usage

### Option 1: Use with DRF Views (Recommended)

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from src.core.rate_limiting.throttle import TokenBucketThrottle

class LoginView(APIView):
    throttle_classes = [TokenBucketThrottle]
    throttle_limit_key = "login"  # Optional: specify which rate limit to use
    
    def post(self, request):
        # Rate limiting is automatic via DRF throttle
        # If exceeded, returns HTTP 429 automatically
        return Response({"message": "Login successful"})
```

### Option 2: Direct Service Usage

```python
from src.core.rate_limiting.service import RateLimiter
from src.core.rate_limiting.exceptions import RateLimitExceeded

limiter = RateLimiter()

# Get identifier (usually from request)
identifier = f"user:{request.user.id}"

try:
    # Check if request is allowed
    info = limiter.check(
        identifier=identifier,
        limit_key="default_authenticated",
        token_cost=1
    )
    # Request allowed
    print(f"Remaining tokens: {info['tokens_remaining']}")
    
except RateLimitExceeded as e:
    # Request denied
    print(f"Rate limited. Retry after {e.retry_after} seconds")
    return Response(
        {"error": "Rate limit exceeded"},
        status=429,
        headers={"Retry-After": str(int(e.retry_after + 1))}
    )
```

## Advanced Usage

### Custom Limit Key per View

```python
class UserProfileView(APIView):
    throttle_classes = [TokenBucketThrottle]
    throttle_limit_key = "profile"  # Custom key
```

The throttle will use the "profile" rate limit from your RATE_LIMITS config.

### Variable Token Cost

Some requests are more expensive than others:

```python
limiter = RateLimiter()

# Normal request: 1 token
limiter.check(identifier="user:123", limit_key="api", token_cost=1)

# Expensive operation: 5 tokens
limiter.check(identifier="user:123", limit_key="api", token_cost=5)

# Light operation: 0.1 tokens (10 per token's worth)
limiter.check(identifier="user:123", limit_key="api", token_cost=0.1)
```

### Checking Without Raising

```python
limiter = RateLimiter()

# is_allowed returns (allowed: bool, info: dict)
allowed, info = limiter.is_allowed(
    identifier="user:123",
    limit_key="default_authenticated"
)

if not allowed:
    print(f"Denied. Retry after {info['retry_after']} seconds")
else:
    print(f"Allowed. {info['tokens_remaining']} tokens remaining")
```

### Getting Statistics

```python
# Get current remaining tokens
tokens = limiter.get_remaining_tokens("user:123", "default_authenticated")
print(f"Remaining: {tokens}")

# Get detailed stats
stats = limiter.get_stats("user:123", "default_authenticated")
print(f"""
Capacity: {stats['capacity']}
Refill Rate: {stats['refill_rate']} tokens/second
Remaining Tokens: {stats['remaining_tokens']}
Next Refill In: {stats['next_refill_in']} seconds
""")
```

### Resetting Rate Limits (Admin)

```python
limiter = RateLimiter()

# Reset specific limit for a user
limiter.reset("user:123", limit_key="login")

# Reset all limits for a user
limiter.reset("user:123")
```

## Common Patterns

### Pattern 1: Login Rate Limiting

```python
# settings.py
RATE_LIMITS = {
    "login": {
        "capacity": 5,           # 5 attempts
        "refill_rate": 0.1,      # ~1 every 10 seconds
    }
}

# views.py
class LoginView(APIView):
    throttle_classes = [TokenBucketThrottle]
    throttle_limit_key = "login"
    
    def post(self, request):
        # Auto rate limited by DRF
        # After 5 failed attempts, next attempt rejected
        return Response({"message": "Login successful"})
```

### Pattern 2: File Upload Limiting

```python
# settings.py
RATE_LIMITS = {
    "upload": {
        "capacity": 10,          # 10 MB burst
        "refill_rate": 1,        # 1 MB per second sustained
    }
}

# views.py
from src.core.rate_limiting.service import RateLimiter

limiter = RateLimiter()

class UploadView(APIView):
    def post(self, request):
        file = request.FILES['file']
        file_size_mb = file.size / (1024 * 1024)
        
        identifier = f"user:{request.user.id}"
        
        try:
            limiter.check(
                identifier=identifier,
                limit_key="upload",
                token_cost=file_size_mb  # Cost = file size
            )
            # Process upload
            return Response({"message": "Upload successful"})
        except RateLimitExceeded as e:
            return Response(
                {"error": f"Rate limited. Try again in {e.retry_after:.0f}s"},
                status=429,
                headers={"Retry-After": str(int(e.retry_after + 1))}
            )
```

### Pattern 3: Tiered Limits (Different for Different Users)

```python
# settings.py
RATE_LIMITS = {
    "api": {
        "capacity": 1000,
        "refill_rate": 10,
    },
    "api_premium": {
        "capacity": 10000,
        "refill_rate": 100,
    }
}

# views.py
class CustomThrottle(TokenBucketThrottle):
    def get_limit_key(self, request, view):
        # Authenticated users get premium limits
        if request.user.is_authenticated:
            if request.user.is_premium:  # Custom attribute
                return "api_premium"
            return "api"
        return "default_anonymous"

class APIView(APIView):
    throttle_classes = [CustomThrottle]
```

### Pattern 4: Request-based Token Cost

```python
from src.core.rate_limiting.service import RateLimiter

limiter = RateLimiter()

class SearchView(APIView):
    def get(self, request):
        # Estimate token cost based on query complexity
        query = request.GET.get('q', '')
        filters = request.GET.getlist('filters')
        
        # Complex query = more tokens
        token_cost = 1 + (len(filters) * 0.5)
        
        identifier = f"user:{request.user.id}"
        
        try:
            limiter.check(
                identifier=identifier,
                limit_key="search",
                token_cost=token_cost
            )
            # Perform search
        except RateLimitExceeded:
            return Response(
                {"error": "Rate limit exceeded"},
                status=429
            )
```

### Pattern 5: IP-Based Limiting for Anonymous Users

```python
from src.core.rate_limiting.throttle import TokenBucketThrottle

class IPBasedThrottle(TokenBucketThrottle):
    def get_identifier(self, request):
        if request.user.is_authenticated:
            return f"user:{request.user.id}"
        # Always use IP for anonymous (default behavior)
        return super().get_identifier(request)
```

## Error Handling

### HTTP 429 Response

When rate limit is exceeded, the response is:

```
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
Retry-After: 7

{"detail":"Request was throttled. Expected available in 7 seconds."}
```

### Custom Exception Handler

To customize the response:

```python
from rest_framework.response import Response
from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    
    if isinstance(exc, Throttled):
        response.data = {
            'error': 'Too many requests',
            'retry_after': int(exc.wait())
        }
    
    return response

# settings.py
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'myapp.handlers.custom_exception_handler',
}
```

### Handling Redis Errors

By default, Redis errors are handled gracefully:

- **Fail-Open (default)**: Allows request if Redis is down
- **Fail-Closed**: Blocks request if Redis is down

```python
# settings.py - Fail closed (strict)
RATE_LIMITER_CONFIG = {
    "failure_mode": "closed",  # Block on Redis error
}

# In code
try:
    limiter.check(identifier, limit_key)
except RedisConnectionError:
    # Handle Redis down scenario
    logger.error("Redis down, rate limiter unavailable")
    return Response({"error": "Service temporarily unavailable"}, status=503)
```

## Monitoring & Observability

### Prometheus Metrics

If enabled, these metrics are available:

```
# Counters
rate_limit_requests_allowed_total{limit_key="...",user_type="..."}
rate_limit_requests_blocked_total{limit_key="...",user_type="..."}

# Gauges
rate_limit_tokens_remaining{limit_key="...",user_type="..."}
rate_limit_failure_mode_active

# Histograms
rate_limit_redis_latency_seconds{operation="evalsha"}

# Errors
rate_limit_redis_errors_total{operation="...",error_type="..."}
```

### Logging

Logs are emitted at WARNING level when requests are blocked:

```
WARNING Rate limit exceeded: default_authenticated=user:123 
        (remaining=0.00, retry_after=7.23s)
```

### Example Prometheus Queries

```promql
# Requests blocked per limit key
rate(rate_limit_requests_blocked_total[5m]) by (limit_key)

# Block ratio
rate(rate_limit_requests_blocked_total[5m]) / 
(rate(rate_limit_requests_allowed_total[5m]) + rate(rate_limit_requests_blocked_total[5m]))

# Redis latency p95
histogram_quantile(0.95, rate_limit_redis_latency_seconds)
```

## Testing

### Unit Test Example

```python
from django.test import TestCase, override_settings
from src.core.rate_limiting.service import RateLimiter
from src.core.rate_limiting.exceptions import RateLimitExceeded

@override_settings(
    RATE_LIMITS={
        "test": {
            "capacity": 3,
            "refill_rate": 0.1,
        }
    }
)
class RateLimitTestCase(TestCase):
    def test_burst_limit(self):
        limiter = RateLimiter()
        
        # Should allow 3
        for i in range(3):
            limiter.check("user:1", "test")
        
        # 4th should fail
        with self.assertRaises(RateLimitExceeded):
            limiter.check("user:1", "test")
```

### Load Testing Example

```bash
# Using Apache Bench
ab -n 100 -c 10 http://localhost:8000/api/endpoint/

# Using wrk
wrk -t4 -c100 -d30s http://localhost:8000/api/endpoint/
```

## Performance Tuning

### Redis Connection Pool

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,  # Connection pool size
            }
        }
    }
}
```

### Lua Script Optimization

The Lua script is already optimized, but you can tune:

```python
# settings.py
RATE_LIMITER_CONFIG = {
    "use_script_with_reset": True,  # Use variant with large time gap reset
    "max_time_gap": 3600,            # Reset if gap > 1 hour
}
```

## Troubleshooting

### Issue: "Rate limit configuration error"

**Cause**: Missing or invalid RATE_LIMITS configuration

**Solution**: Ensure RATE_LIMITS exists in settings.py with proper structure

### Issue: "Redis unavailable" but requests still allowed

**Cause**: Fail-open mode is active (default)

**Solution**: This is intentional to prevent service outage. Check Redis connection.

### Issue: High Redis latency

**Cause**: Connection pool too small or Redis overloaded

**Solution**: 
- Increase connection pool size
- Add Redis replicas
- Use Redis Cluster

### Issue: Tests failing with "Rate limit exceeded"

**Cause**: Redis keys from previous tests not cleaned up

**Solution**: Reset rate limiter in test teardown
```python
def tearDown(self):
    limiter = RateLimiter()
    limiter.reset("user:1")
```

## Best Practices

1. **Use authenticated user ID when possible** (not just IP)
   - More reliable and harder to spoof
   - Better for user experience

2. **Monitor rate limit metrics**
   - Alert on high block rate
   - Indicates attack or misconfiguration

3. **Set conservative defaults**
   - Start with lower limits
   - Adjust based on metrics

4. **Test before production**
   - Load test with realistic traffic
   - Test Redis failure scenarios

5. **Document custom limits**
   - Document what each limit_key is for
   - Include rationale for capacity and refill_rate

6. **Use appropriate failure mode**
   - Development: fail-open
   - Production: fail-open (better UX)
   - High-security: fail-closed

## See Also

- [Architecture Overview](ARCHITECTURE.md)
- [Race Condition Prevention](RACE_CONDITION_PREVENTION.md)
- [Token Refill Math](TOKEN_REFILL_MATH.md)
