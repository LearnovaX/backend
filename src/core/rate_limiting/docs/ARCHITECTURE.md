# Token Bucket Rate Limiter - Architecture

## Overview

This is a production-grade distributed token bucket rate limiter for Django + Django REST Framework applications using Redis as the centralized state store.

## Key Design Principles

1. **Atomic Operations**: All state mutations happen atomically in Redis using Lua scripts
2. **Distributed Correctness**: Works across multiple application instances
3. **Race Condition Free**: No GET/SET patterns, preventing race conditions
4. **Fail-Safe Defaults**: Configurable failure modes (open or closed)
5. **Observable**: Prometheus metrics and detailed logging
6. **Configurable**: Different limits for different endpoints/users
7. **Composable**: Clean separation of concerns

## Architecture Components

### 1. Lua Script (`lua_script.py`)

The core of the system - a single Redis Lua script that performs all token bucket operations atomically:

```
Token Bucket State:
├── HMSET key
│   ├── tokens: current token count
│   └── last_refill: timestamp of last refill
└── EXPIRE key: 2 hours (auto-cleanup)
```

**Advantages of Lua script**:
- Single network round-trip to Redis
- All operations (read, calculate, write) happen atomically
- No possibility of race conditions
- Prevents TOCTOU (Time-Of-Check, Time-Of-Use) bugs

### 2. Rate Limiter Service (`service.py`)

The `RateLimiter` class:

**Responsibilities**:
- Load Lua script on initialization
- Convert configuration to Redis calls
- Call Lua script with appropriate parameters
- Perform error handling and logging
- Record metrics

**Key Methods**:
```python
is_allowed(identifier, limit_key, token_cost)  # Returns (bool, info_dict)
check(identifier, limit_key, token_cost)       # Raises on denied
reset(identifier, limit_key)                   # Admin reset
get_remaining_tokens(identifier, limit_key)    # Read current state
get_stats(identifier, limit_key)               # Detailed info
```

### 3. DRF Integration (`throttle.py`)

The `TokenBucketThrottle` class integrates with Django REST Framework's throttling system:

**Benefits**:
- Works with DRF's exception handling
- Automatic 429 response on throttle
- Automatic rate limit headers (X-RateLimit-*)
- Automatic Retry-After header

**Identifier Resolution**:
1. Authenticated user → `user:123`
2. Anonymous user → `ip:192.168.1.1`

**Limit Key Resolution**:
1. `view.throttle_limit_key` if set
2. `view.basename` (DRF viewset name)
3. View class name
4. Default based on auth status

### 4. Metrics (`metrics.py`)

Prometheus metrics for observability:

- `rate_limit_requests_allowed_total` - Counter
- `rate_limit_requests_blocked_total` - Counter
- `rate_limit_tokens_remaining` - Gauge
- `rate_limit_redis_latency_seconds` - Histogram
- `rate_limit_redis_errors_total` - Counter
- `rate_limit_failure_mode_active` - Gauge

### 5. Configuration (`settings.py`)

Two-tier configuration system:

**Rate Limits** (per-limit configuration):
```python
RATE_LIMITS = {
    "login": {
        "capacity": 5,           # Max burst tokens
        "refill_rate": 0.1,      # Tokens per second
        "description": "..."     # Optional
    }
}
```

**Rate Limiter Config** (global configuration):
```python
RATE_LIMITER_CONFIG = {
    "redis_connection": "default",      # Django cache alias
    "use_script_with_reset": False,     # Lua script variant
    "max_time_gap": 3600,               # Reset if gap > N seconds
    "failure_mode": "open",             # "open" or "closed"
    "enable_metrics": True,
    "enable_logging": True,
    "log_level": "WARNING",
    "include_headers": True,
}
```

## Data Flow

### Request Processing Flow

```
User Request
    ↓
DRF Throttle.allow_request()
    ↓
TokenBucketThrottle.get_identifier()  → "user:123" or "ip:X.X.X.X"
    ↓
TokenBucketThrottle.get_limit_key()   → "login", "default_authenticated", etc.
    ↓
RateLimiter.is_allowed()
    ↓
Redis.evalsha(LUA_SCRIPT)
    ├─ Get current state: tokens, last_refill
    ├─ Calculate: elapsed = now - last_refill
    ├─ Calculate: new_tokens = min(capacity, current + elapsed * refill_rate)
    ├─ Calculate: allowed = (new_tokens >= token_cost)
    ├─ Update state in Redis
    └─ Return: (allowed, tokens_remaining, retry_after)
    ↓
Record Metrics
    ↓
Log Event
    ↓
Return to Throttle
    ↓
Either:
  ✓ Return True → Request allowed, continue to view
  ✗ Return False → Raise Throttled exception → HTTP 429
```

### Concurrent Request Handling

```
Request 1 (from User A)          Request 2 (from User A)
    ↓                                 ↓
  evalsha                           evalsha
    ↓                                 ↓
Redis executes LUA atomically ←→ Serialized by Redis
    ↓                                 ↓
  Result: allowed                 Result: denied (no tokens left)
```

## Failure Modes

### Fail-Open (Default)

```
Redis Unavailable → Log Error → Allow Request
```

**Use Case**: Better UX, allows legitimate requests through despite monitoring failure

### Fail-Closed

```
Redis Unavailable → Raise RedisConnectionError → Return HTTP 500
```

**Use Case**: Stricter security, prevent abuse if rate limiter is down

## Distributed Correctness

### Multi-Instance Scenario

```
Instance 1                   Instance 2
    ↓                            ↓
Request from User A         Request from User A
    ↓                            ↓
RateLimiter.is_allowed()    RateLimiter.is_allowed()
    ↓                            ↓
Both call Redis evalsha
    ↓
Redis serializes LUA executions:
  1. Instance 1 executes: tokens 10 → 9 ✓
  2. Instance 2 executes: tokens 9 → 8 ✓
    ↓
Distributed correctness maintained!
```

The key is that Redis Lua script execution is atomic and serialized. All concurrent evalsha calls are executed one-at-a-time on the server, preventing race conditions.

## Configuration Examples

### Example 1: Login Rate Limiting

```python
RATE_LIMITS = {
    "login": {
        "capacity": 5,           # Allow 5 attempts in a burst
        "refill_rate": 0.1,      # Then 1 every 10 seconds (6/min)
    }
}

# Usage in view:
class LoginView(APIView):
    throttle_classes = [TokenBucketThrottle]
    throttle_limit_key = "login"
```

This allows a burst of 5 failed login attempts, then 1 attempt every 10 seconds after that.

### Example 2: API Rate Limiting (Per User)

```python
RATE_LIMITS = {
    "default_authenticated": {
        "capacity": 1000,        # Burst 1000 requests
        "refill_rate": 10,       # Then 10 per second (600/min)
    },
    "default_anonymous": {
        "capacity": 100,         # Burst 100 requests
        "refill_rate": 1,        # Then 1 per second (60/min)
    }
}

# Applied globally to all views:
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'src.core.rate_limiting.throttle.TokenBucketThrottle',
    ],
}
```

### Example 3: Multiple Endpoints

```python
RATE_LIMITS = {
    "api": {
        "capacity": 1000,
        "refill_rate": 10,
    },
    "upload": {
        "capacity": 10,
        "refill_rate": 0.2,  # 1 upload per 5 seconds
    },
    "search": {
        "capacity": 100,
        "refill_rate": 2,
    }
}

# Per-view configuration:
class UploadView(APIView):
    throttle_classes = [TokenBucketThrottle]
    throttle_limit_key = "upload"

class SearchView(APIView):
    throttle_classes = [TokenBucketThrottle]
    throttle_limit_key = "search"
```

## Performance Characteristics

- **Request Latency**: ~1-5ms per rate limit check (Redis network round-trip)
- **Memory per Identifier**: ~100 bytes (2 hash fields)
- **Token Consumption**: 1 token per request
- **Scalability**: Limited only by Redis throughput (100k+ ops/sec typical)

## Security Considerations

1. **IP Spoofing**: Identifiers based on IP are vulnerable to spoofing. Use authenticated user ID when possible.

2. **Distributed Attacks**: A rate limiter protects a single resource from overload, but coordinated attacks from many clients will still hit your service. Consider:
   - CDN-level rate limiting (CloudFlare, Akamai)
   - Network-level DDoS protection
   - Load balancing across multiple instances

3. **Redis Security**: Ensure Redis is:
   - Not exposed to internet
   - Password protected
   - In same VPC/private network as application
   - Backed by persistence (RDB/AOF)

## Deployment Checklist

- [ ] Configure Redis connection in Django settings
- [ ] Add RATE_LIMITS to settings
- [ ] Add RATE_LIMITER_CONFIG to settings (optional, uses defaults)
- [ ] Add TokenBucketThrottle to DRF global config or per-view
- [ ] Optionally add custom_exception_handler to DRF config
- [ ] Configure Prometheus scraping (if metrics enabled)
- [ ] Test with load testing tool (e.g., Apache Bench, wrk)
- [ ] Monitor Redis memory and connections
- [ ] Alert on rate limit blocks or Redis errors

## Troubleshooting

See `TROUBLESHOOTING.md` for common issues and solutions.
