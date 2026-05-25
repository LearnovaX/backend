# Distributed Token Bucket Rate Limiter
distributed
A production-grade, thread-safe,  rate limiter for Django + Django REST Framework using Redis and the token bucket algorithm.

## Features

✅ **Token Bucket Algorithm**
- Configurable capacity (burst) and refill rate
- Smooth, fair rate limiting
- Supports burst traffic while maintaining sustained rate

✅ **Distributed & Thread-Safe**
- Redis-backed centralized state
- Atomic Lua script operations
- Zero race conditions
- Works across multiple application instances

✅ **DRF Integration**
- Drop-in throttle class
- Automatic HTTP 429 responses
- Standard rate limit headers (X-RateLimit-*, Retry-After)
- Configurable per-view or globally

✅ **Flexible Identification**
- Per-authenticated-user limiting
- Per-IP limiting for anonymous users
- Custom identifier support

✅ **Observable**
- Prometheus metrics
- Detailed logging
- Request/block counters
- Redis latency tracking

✅ **Configurable Failure Modes**
- Fail-open: Allows requests if Redis is down
- Fail-closed: Blocks requests if Redis is down

✅ **Admin & Debugging**
- Reset rate limits for users
- Query current token state
- Get detailed statistics

## Quick Start

### 1. Install

```bash
pip install django django-rest-framework django-redis
```

### 2. Configure

Add to `settings.py`:

```python
RATE_LIMITS = {
    "default_authenticated": {"capacity": 1000, "refill_rate": 10},
    "default_anonymous": {"capacity": 100, "refill_rate": 1},
}

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'src.core.rate_limiting.throttle.TokenBucketThrottle',
    ],
}
```

### 3. Use

```bash
curl http://localhost:8000/api/endpoint/
# X-RateLimit-Limit: 1000
# X-RateLimit-Remaining: 999
```

When limit exceeded:
```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Remaining: 0
Retry-After: 7
```

## Documentation

- **[QUICK_START.md](docs/QUICK_START.md)** - Get started in 5 minutes
- **[USAGE_GUIDE.md](docs/USAGE_GUIDE.md)** - Comprehensive usage guide
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture & design
- **[RACE_CONDITION_PREVENTION.md](docs/RACE_CONDITION_PREVENTION.md)** - How atomicity is achieved
- **[TOKEN_REFILL_MATH.md](docs/TOKEN_REFILL_MATH.md)** - Algorithm explanation
- **[SETTINGS_EXAMPLE.py](docs/SETTINGS_EXAMPLE.py)** - Configuration examples

## Architecture

```
Request → DRF Throttle → RateLimiter → Redis (Lua Script) → Allow/Deny
                                            ↓
                                      Atomically:
                                      1. Read state
                                      2. Calculate refill
                                      3. Check capacity
                                      4. Update state
```

**Key Properties:**
- **Atomic**: Lua script ensures no race conditions
- **Distributed**: Redis is centralized state store
- **Scalable**: Works across multiple instances
- **Observable**: Metrics and logging included

## Token Bucket Algorithm

The token bucket is a classic algorithm allowing both rate limiting AND burst handling:

```
Parameters:
  - capacity = 1000 (max burst)
  - refill_rate = 10 tokens/second (600/min sustained)

Behavior:
  - First 1000 requests allowed immediately (burst)
  - After burst, sustained rate of 10 requests/second
  - Very smooth rate limiting
```

## Configuration

### Per-Endpoint Rate Limits

```python
RATE_LIMITS = {
    "login": {
        "capacity": 5,           # 5 attempts
        "refill_rate": 0.1,      # ~1 every 10 seconds
    },
    "api": {
        "capacity": 1000,        # 1000 token burst
        "refill_rate": 10,       # 600 requests/minute sustained
    },
    "upload": {
        "capacity": 10,          # 10 MB burst
        "refill_rate": 1,        # 1 MB/second
    },
}
```

### Global Configuration

```python
RATE_LIMITER_CONFIG = {
    "redis_connection": "default",  # Django cache alias
    "failure_mode": "open",         # "open" or "closed" on Redis error
    "enable_metrics": True,         # Prometheus metrics
    "enable_logging": True,         # Detailed logging
}
```

## Usage Examples

### Basic (Global Rate Limiting)

```python
# All views are automatically rate limited
# No code changes needed!

curl -H "Authorization: Bearer token" http://localhost:8000/api/endpoint/
# Returns X-RateLimit-* headers and HTTP 429 when exceeded
```

### Custom Limit per View

```python
from rest_framework.views import APIView
from src.core.rate_limiting.throttle import TokenBucketThrottle

class LoginView(APIView):
    throttle_classes = [TokenBucketThrottle]
    throttle_limit_key = "login"  # Use "login" rate limit
```

### Direct Service Usage

```python
from src.core.rate_limiting.service import RateLimiter
from src.core.rate_limiting.exceptions import RateLimitExceeded

limiter = RateLimiter()

try:
    limiter.check("user:123", "api", token_cost=1)
except RateLimitExceeded as e:
    return Response({"error": "Rate limited"}, status=429)
```

## Distributed Correctness

Multiple application instances share Redis state:

```
Instance 1                    Instance 2
  Request A                     Request B
    ↓                             ↓
  RateLimiter               RateLimiter
    ↓                             ↓
  Redis.evalsha             Redis.evalsha
    ↓       (serialized)         ↓
  Tokens: 10 → 9           Tokens: 9 → 8
    ↓                             ↓
  Allow                         Allow

Result: Correct distributed rate limiting!
```

The key is **Lua script atomicity**: All operations happen in a single atomic transaction on the Redis server, preventing race conditions.

## Performance

- **Latency**: ~1-5ms per check (Redis round-trip)
- **Throughput**: Limited only by Redis (100k+ ops/sec typical)
- **Memory**: ~100 bytes per identifier

## Security

⚠️ **Security Considerations**

1. **IP Spoofing**: IP-based limits can be spoofed. Use authenticated user ID when possible.

2. **Distributed Attacks**: A single rate limiter protects one resource. For DDoS protection, add:
   - CDN-level rate limiting (CloudFlare, Akamai)
   - Network-level DDoS protection
   - Multiple instances behind load balancer

3. **Redis Security**:
   - Don't expose Redis to internet
   - Use password authentication
   - Use same VPC/private network
   - Enable persistence (RDB/AOF)

## Failure Modes

### Fail-Open (Default)

```
Redis Down → Allow Request
```

**Pro**: Better user experience, system doesn't go down
**Con**: Rate limiting disabled during Redis outage

**Use Case**: Production with high availability requirement

### Fail-Closed

```
Redis Down → Block Request (HTTP 500)
```

**Pro**: Strict rate limiting even if Redis is down
**Con**: Service degradation

**Use Case**: High-security systems, or systems that rarely lose Redis

## Monitoring

### Prometheus Metrics

```
rate_limit_requests_allowed_total{limit_key="api",user_type="authenticated"}
rate_limit_requests_blocked_total{limit_key="api",user_type="authenticated"}
rate_limit_tokens_remaining{limit_key="api",user_type="authenticated"}
rate_limit_redis_latency_seconds{operation="evalsha"}
```

### Logging

```
WARNING Rate limit exceeded: api=user:123 (remaining=0.00, retry_after=7.23s)
```

## Testing

```bash
# Run tests
pytest src/core/rate_limiting/tests/

# Test with load tool
ab -n 100 -c 10 http://localhost:8000/api/endpoint/
```

## Common Issues

**Q: Rate limiting doesn't seem to work**
- A: Check Redis is running: `redis-cli ping` should return PONG
- A: Check RATE_LIMITS is in settings.py
- A: Check TokenBucketThrottle is in DEFAULT_THROTTLE_CLASSES

**Q: Getting "Rate limit exceeded" immediately**
- A: Check capacity is reasonable (default 100 for anonymous)
- A: Check refill_rate is positive

**Q: High Redis latency/errors**
- A: Check Redis connection and memory
- A: Increase connection pool size
- A: Consider Redis Cluster for scaling

## Implementation Details

### Lua Script

All rate limiting operations happen atomically in Redis via Lua script:

```lua
-- Get current state
local tokens = redis.call('HMGET', key, 'tokens', 'last_refill')
-- Calculate refill
local new_tokens = math.min(capacity, current + elapsed * rate)
-- Check and update atomically
if new_tokens >= cost then
    redis.call('HMSET', key, 'tokens', new_tokens - cost)
    return 1  -- allowed
else
    return 0  -- denied
end
```

**Why Lua?** No race conditions. All operations happen in one atomic transaction.

### Identifier Resolution

1. **Authenticated**: `user:{user_id}` - per user limit
2. **Anonymous**: `ip:{ip_address}` - per IP limit
3. **Custom**: Can override in code

### Limit Key Resolution

1. **Explicit**: `view.throttle_limit_key = "custom"`
2. **DRF Basename**: `view.basename` (for viewsets)
3. **Default**: "default_authenticated" or "default_anonymous"

## Production Checklist

- [ ] Redis configured and running
- [ ] RATE_LIMITS configured in settings.py
- [ ] TokenBucketThrottle in DRF config
- [ ] Load tested with realistic traffic
- [ ] Prometheus scraping configured (if using metrics)
- [ ] Logging level appropriate
- [ ] Failure mode set appropriately
- [ ] Redis memory monitored
- [ ] Rate limit alerts configured

## See Also

- [Token Bucket Algorithm](https://en.wikipedia.org/wiki/Token_bucket)
- [Redis Lua Scripting](https://redis.io/commands/eval)
- [DRF Throttling](https://www.django-rest-framework.org/api-guide/throttling/)

## License

Part of LMS Full application

## Contributing

See CONTRIBUTING.md for guidelines

## Support

For issues or questions:
1. Check the documentation in `docs/`
2. Run the test suite: `pytest src/core/rate_limiting/tests/`
3. Check Redis is running: `redis-cli ping`
