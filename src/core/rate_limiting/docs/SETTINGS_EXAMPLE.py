# Rate Limiting Settings Example
#
# Copy these settings to your Django settings.py and customize as needed

# ============================================================================
# RATE LIMITS CONFIGURATION
# ============================================================================
#
# Defines rate limit rules for different endpoints/operations.
# Each entry specifies:
#   - capacity: Maximum tokens (burst size)
#   - refill_rate: Tokens per second
#   - description: Human-readable description

RATE_LIMITS = {
    # Authentication endpoints
    "login": {
        "capacity": 5,           # 5 login attempts
        "refill_rate": 0.1,      # ~1 every 10 seconds (6/min)
        "description": "Login attempts - prevents password brute forcing",
    },
    
    "password_reset": {
        "capacity": 3,           # 3 password reset attempts
        "refill_rate": 0.05,     # ~1 every 20 seconds (3/10min)
        "description": "Password reset requests",
    },
    
    "register": {
        "capacity": 10,          # 10 registration attempts
        "refill_rate": 0.2,      # ~1 every 5 seconds (12/min)
        "description": "User registration",
    },
    
    # API endpoints for authenticated users
    "default_authenticated": {
        "capacity": 1000,        # 1000 token burst
        "refill_rate": 10,       # 10 tokens/second (600/min sustained)
        "description": "Default rate limit for authenticated users",
    },
    
    # API endpoints for unauthenticated/anonymous users
    "default_anonymous": {
        "capacity": 100,         # 100 token burst
        "refill_rate": 1,        # 1 token/second (60/min sustained)
        "description": "Default rate limit for anonymous users",
    },
    
    # Specific endpoints (if used)
    "search": {
        "capacity": 50,          # Smaller burst for search
        "refill_rate": 2,        # 2/second (120/min)
        "description": "Search API - can be expensive",
    },
    
    "upload": {
        "capacity": 10,          # Small burst
        "refill_rate": 0.5,      # 1 upload per 2 seconds
        "description": "File uploads - limit to prevent storage abuse",
    },
    
    "download": {
        "capacity": 20,
        "refill_rate": 1,        # 60 downloads/min
        "description": "File downloads",
    },
}

# ============================================================================
# RATE LIMITER GLOBAL CONFIGURATION
# ============================================================================

RATE_LIMITER_CONFIG = {
    # Redis connection to use (Django cache alias)
    "redis_connection": "default",
    
    # Use Lua script variant with large time gap reset
    # Useful if Redis connections are frequently dropped
    "use_script_with_reset": False,
    
    # Maximum allowed time gap before bucket reset (seconds)
    # Only used if use_script_with_reset=True
    # If more than this time passes, bucket is reset to full capacity
    "max_time_gap": 3600,  # 1 hour
    
    # Failure mode when Redis is unavailable
    # "open": Allow all requests (fail-safe for user experience)
    # "closed": Block all requests (fail-safe for security)
    "failure_mode": "open",
    
    # Enable Prometheus metrics collection
    "enable_metrics": True,
    
    # Enable detailed logging of rate limit events
    "enable_logging": True,
    
    # Log level for rate limit events (when exceeded)
    # Options: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    "log_level": "WARNING",
    
    # Include rate limit headers in HTTP responses
    # Headers: X-RateLimit-Limit, X-RateLimit-Remaining, Retry-After
    "include_headers": True,
}

# ============================================================================
# DJANGO REST FRAMEWORK CONFIGURATION
# ============================================================================
#
# Integrate rate limiting with DRF

REST_FRAMEWORK = {
    # Apply rate limiting to all views by default
    'DEFAULT_THROTTLE_CLASSES': [
        'src.core.rate_limiting.throttle.TokenBucketThrottle',
    ],
    
    # Use custom exception handler to include rate limit headers
    'EXCEPTION_HANDLER': 'src.core.rate_limiting.throttle.custom_exception_handler',
}

# ============================================================================
# REDIS CACHE CONFIGURATION (if not already configured)
# ============================================================================
#
# Make sure Redis is properly configured for Django cache

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',  # Adjust host/port as needed
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            # Connection pool settings
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,  # Connection pool size
                'retry_on_timeout': True,
            },
            # Socket connection settings
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'IGNORE_EXCEPTIONS': False,  # Raise exceptions (don't silently fail)
        }
    }
}

# ============================================================================
# LOGGING CONFIGURATION (Optional)
# ============================================================================
#
# Configure logging to see rate limit events

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'src.core.rate_limiting': {
            'handlers': ['console'],
            'level': 'WARNING',  # Increase to 'DEBUG' for verbose output
            'propagate': False,
        },
    },
}

# ============================================================================
# PROMETHEUS CONFIGURATION (Optional, if using prometheus_client)
# ============================================================================
#
# The rate limiter will automatically expose metrics to Prometheus

# Add to INSTALLED_APPS if using django-prometheus
INSTALLED_APPS = [
    # ...
    # 'django_prometheus',
]

# ============================================================================
# NOTES ON TUNING
# ============================================================================
#
# Refill Rate Calculation:
#   refill_rate = desired_requests_per_minute / 60
#   Examples:
#   - 60 requests/min → refill_rate = 1
#   - 600 requests/min → refill_rate = 10
#   - 10 requests/min → refill_rate = 0.167
#
# Capacity Calculation:
#   capacity = burst_size
#   Examples:
#   - Allow 10 requests in a burst: capacity = 10
#   - Allow 100 requests in a burst: capacity = 100
#   - Burst duration = capacity / refill_rate
#
# Examples:
#   - Capacity=100, Refill=10 → 10 second burst at max capacity, then 10/sec sustained
#   - Capacity=5, Refill=0.1 → 50 second burst, then 1 request per 10 seconds
