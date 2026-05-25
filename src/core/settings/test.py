"""
Test settings - optimized for running tests.
"""

from .base import *  # noqa: F401, F403
from .base import INSTALLED_APPS, MIDDLEWARE, TEMPLATES, env

# DEBUG
# ============================================================================
DEBUG = True
ALLOWED_HOSTS = ["*"]

# PASSWORD HASHERS - Faster MD5 for tests
# ============================================================================
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# EMAIL - In-memory backend for tests
# ============================================================================
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# DATABASE - Use default or test database
# ============================================================================
# Tests will use a separate test database automatically

# TEMPLATES - Enable debug mode for templates in tests
# ============================================================================
TEMPLATES[0]["OPTIONS"]["debug"] = True

# LOGGING - Minimal logging during tests
# ============================================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "CRITICAL",
    },
}

# CACHES - Use dummy cache for tests
# ============================================================================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}
