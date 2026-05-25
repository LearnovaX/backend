# Rate Limiter Implementation - File Index & Quick Reference

## 📂 Project Structure

```
backend/src/core/rate_limiting/                    # Main package
├── __init__.py                                    # Package exports & documentation
├── README.md                                      # Overview & getting started
├── IMPLEMENTATION_SUMMARY.md                      # Detailed implementation summary
│
├── lua_script.py                                 # Redis Lua scripts (2 variants)
├── service.py                                    # Core RateLimiter class (350+ lines)
├── throttle.py                                   # DRF TokenBucketThrottle (350+ lines)
├── exceptions.py                                 # Custom exceptions
├── metrics.py                                    # Prometheus metrics integration
├── settings.py                                   # Configuration management
│
├── tests/
│   ├── __init__.py
│   └── test_rate_limiting.py                    # Comprehensive test suite (500+ lines)
│
└── docs/
    ├── QUICK_START.md                           # 5-minute setup guide
    ├── USAGE_GUIDE.md                           # Comprehensive usage (500+ lines)
    ├── ARCHITECTURE.md                          # Technical design (300+ lines)
    ├── RACE_CONDITION_PREVENTION.md             # Atomicity explained (300+ lines)
    ├── TOKEN_REFILL_MATH.md                    # Algorithm details (400+ lines)
    └── SETTINGS_EXAMPLE.py                      # Configuration template (200+ lines)

RATE_LIMITER_IMPLEMENTATION.md                    # This file's summary at root
```

## 🎯 What to Read First

1. **NEW to rate limiting?** → Start with [QUICK_START.md](src/core/rate_limiting/docs/QUICK_START.md) (5 min)
2. **Want to use it?** → Read [USAGE_GUIDE.md](src/core/rate_limiting/docs/USAGE_GUIDE.md) (20 min)
3. **Need to understand design?** → Read [ARCHITECTURE.md](src/core/rate_limiting/docs/ARCHITECTURE.md) (15 min)
4. **Wondering about race conditions?** → Read [RACE_CONDITION_PREVENTION.md](src/core/rate_limiting/docs/RACE_CONDITION_PREVENTION.md) (15 min)
5. **Need to tune config?** → Read [TOKEN_REFILL_MATH.md](src/core/rate_limiting/docs/TOKEN_REFILL_MATH.md) (20 min)
6. **See full implementation details?** → Read [IMPLEMENTATION_SUMMARY.md](RATE_LIMITER_IMPLEMENTATION.md)

## 🚀 Get Started in 3 Steps

### Step 1: Configure Settings
Copy this to your `settings.py`:

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

### Step 2: Run Tests
```bash
pytest src/core/rate_limiting/tests/
```

### Step 3: Use It
```bash
curl http://localhost:8000/api/endpoint/
# X-RateLimit-Limit: 1000
# X-RateLimit-Remaining: 999
```

## 📖 Core Files

### `lua_script.py` - Redis Scripts
- **Token bucket Lua script** for atomic operations
- **Variant with reset** for large time gaps
- No race conditions guaranteed

### `service.py` - Main Service Class
**Key Methods:**
- `is_allowed(identifier, limit_key, token_cost)` - Returns (bool, info)
- `check(identifier, limit_key, token_cost)` - Raises on denied
- `reset(identifier, limit_key)` - Admin reset
- `get_remaining_tokens(identifier, limit_key)` - Query state
- `get_stats(identifier, limit_key)` - Detailed info

**Example:**
```python
from src.core.rate_limiting.service import RateLimiter
limiter = RateLimiter()
try:
    limiter.check("user:123", "default_authenticated")
except RateLimitExceeded as e:
    print(f"Retry after {e.retry_after} seconds")
```

### `throttle.py` - DRF Integration
**Main Class:** `TokenBucketThrottle`

**Features:**
- Automatic HTTP 429 responses
- Rate limit headers (X-RateLimit-*)
- Identifier resolution (user ID or IP)
- Limit key resolution (from view or default)

**Example:**
```python
from rest_framework.views import APIView
from src.core.rate_limiting.throttle import TokenBucketThrottle

class LoginView(APIView):
    throttle_classes = [TokenBucketThrottle]
    throttle_limit_key = "login"
```

### `exceptions.py` - Custom Exceptions
- `RateLimitExceeded` - Main exception with retry_after
- `RateLimitConfigError` - Configuration invalid
- `RedisConnectionError` - Redis unavailable (fail-closed)

### `metrics.py` - Prometheus Integration
**Metrics:**
- `rate_limit_requests_allowed_total` - Counter
- `rate_limit_requests_blocked_total` - Counter
- `rate_limit_tokens_remaining` - Gauge
- `rate_limit_redis_latency_seconds` - Histogram
- `rate_limit_redis_errors_total` - Error counter
- `rate_limit_failure_mode_active` - Failure mode indicator

### `settings.py` - Configuration Management
**Functions:**
- `get_rate_limits_config()` - Get all rate limits
- `get_rate_limiter_config()` - Get global config
- `get_rate_limit_config(key)` - Get specific limit
- `validate_rate_limit_config(config)` - Validate config
- `validate_all_rate_limits()` - Validate all

## 🧪 Testing

### Run Tests
```bash
# All tests
pytest src/core/rate_limiting/tests/

# Specific test class
pytest src/core/rate_limiting/tests/test_rate_limiting.py::TestConcurrency

# With coverage
pytest --cov=src.core.rate_limiting src/core/rate_limiting/tests/
```

### Test Coverage (15+ test classes)
- ✅ Basic rate limiting
- ✅ Token refill behavior
- ✅ Configuration validation
- ✅ Concurrent requests (race conditions)
- ✅ Redis failure modes
- ✅ Rate limiter reset
- ✅ Statistics & info
- ✅ DRF throttle integration
- ✅ Distributed correctness

## 🔧 Configuration

### Minimum Configuration

```python
RATE_LIMITS = {
    "default_authenticated": {
        "capacity": 1000,
        "refill_rate": 10,
    },
    "default_anonymous": {
        "capacity": 100,
        "refill_rate": 1,
    },
}
```

### Full Configuration

```python
RATE_LIMITS = {
    "limit_name": {
        "capacity": 100,           # Burst size
        "refill_rate": 1,          # Tokens per second
        "description": "Optional", # Human-readable
    }
}

RATE_LIMITER_CONFIG = {
    "redis_connection": "default",    # Django cache alias
    "use_script_with_reset": False,   # Lua script variant
    "max_time_gap": 3600,             # Reset on large gap
    "failure_mode": "open",           # "open" or "closed"
    "enable_metrics": True,           # Prometheus
    "enable_logging": True,           # Logging
    "log_level": "WARNING",           # Log level
    "include_headers": True,          # Rate limit headers
}
```

### Common Patterns

| Use Case | Capacity | Rate | Behavior |
|----------|----------|------|----------|
| Login | 5 | 0.1 | 5 attempts, then 1 per 10s |
| API | 1000 | 10 | 1000 burst, then 600/min |
| Upload | 10 | 1 | 10 burst, then 60/min |
| Search | 100 | 2 | 100 burst, then 120/min |

## 💡 Key Concepts

### Token Bucket Algorithm
```
capacity = 1000          # Burst size (max tokens)
refill_rate = 10         # Tokens per second (sustained rate)

Behavior:
- First 1000 requests allowed (burst)
- After that, average 10 requests/second
- Smooth rate limiting, no reset boundaries
```

### Atomicity via Lua Script
```
Problem: GET/SET has race conditions
Solution: Lua script atomic in Redis

Redis executes entire script without interruption:
1. Read tokens
2. Calculate refill
3. Check limit
4. Update state
5. Return result

All in ONE atomic operation!
```

### Identifiers
```
Authenticated Users: "user:123"        → Per-user limit
Anonymous Users: "ip:192.168.1.1"     → Per-IP limit
```

### Limit Keys
```
Default: "default_authenticated" or "default_anonymous"
Custom: Specify via view.throttle_limit_key = "login"
```

## 📊 Monitoring

### Prometheus Queries
```promql
# Requests blocked per endpoint
rate(rate_limit_requests_blocked_total[5m]) by (limit_key)

# Block ratio
rate(rate_limit_requests_blocked_total[5m]) / 
(rate(rate_limit_requests_allowed_total[5m]) + rate(rate_limit_requests_blocked_total[5m]))

# Redis latency
histogram_quantile(0.95, rate_limit_redis_latency_seconds)
```

### Logging
```
WARNING Rate limit exceeded: api=user:123 
        (remaining=0.00, retry_after=7.23s)
```

## 🛡️ Production Checklist

- [ ] Redis is running and accessible
- [ ] RATE_LIMITS configured in settings
- [ ] TokenBucketThrottle in DRF config
- [ ] Tests passing: `pytest src/core/rate_limiting/tests/`
- [ ] Load tested with realistic traffic
- [ ] Prometheus scraping configured
- [ ] Logging level appropriate
- [ ] Failure mode set (open for public APIs)
- [ ] Redis memory monitored
- [ ] Rate limit alerts configured
- [ ] Documentation reviewed

## 🐛 Troubleshooting

### Issue: "Rate limiting not working"
**Solution:**
1. Check Redis running: `redis-cli ping`
2. Check RATE_LIMITS in settings
3. Check TokenBucketThrottle in DRF
4. Check cache backend configured

### Issue: "Getting Redis errors"
**Solution:**
1. Check Redis connection string
2. Check Redis is accessible from app
3. Check failure_mode setting
4. Increase connection pool size

### Issue: "Too many requests immediately"
**Solution:**
1. Check capacity is appropriate (>= 10)
2. Check refill_rate is not too small
3. Check identifier resolution (user vs IP)

## 📚 Documentation Map

| File | Purpose | Read Time |
|------|---------|-----------|
| README.md | Overview & features | 5 min |
| QUICK_START.md | 5-minute setup | 5 min |
| USAGE_GUIDE.md | Comprehensive guide | 20 min |
| ARCHITECTURE.md | Technical design | 15 min |
| RACE_CONDITION_PREVENTION.md | Atomicity explained | 15 min |
| TOKEN_REFILL_MATH.md | Algorithm details | 20 min |
| SETTINGS_EXAMPLE.py | Configuration | 10 min |

## ✅ Deliverables Summary

**Core Implementation:**
- 7 Python modules (1500+ lines)
- Lua scripts (2 variants)
- Comprehensive error handling

**Testing:**
- 15+ test classes
- 500+ lines of tests
- Concurrent, distributed, and failure scenarios

**Documentation:**
- 7 markdown files (2000+ lines)
- Configuration examples
- Architecture explanations
- Troubleshooting guides

**Features:**
- ✅ Atomic operations (no race conditions)
- ✅ Distributed across instances
- ✅ DRF throttle integration
- ✅ Prometheus metrics
- ✅ Detailed logging
- ✅ Configurable failure modes
- ✅ Per-endpoint customization
- ✅ Production-ready code

## 🚀 Next Steps

1. **Read** [QUICK_START.md](src/core/rate_limiting/docs/QUICK_START.md)
2. **Copy settings** from [SETTINGS_EXAMPLE.py](src/core/rate_limiting/docs/SETTINGS_EXAMPLE.py)
3. **Run tests** to verify
4. **Load test** with realistic traffic
5. **Deploy** to production
6. **Monitor** with Prometheus/logging

---

**Questions?** See documentation files in `docs/` folder.
**Issues?** Check troubleshooting in [USAGE_GUIDE.md](src/core/rate_limiting/docs/USAGE_GUIDE.md).
