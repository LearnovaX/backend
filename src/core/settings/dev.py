"""
Development settings.
"""

from .base import *  # noqa: F401, F403
from .base import INSTALLED_APPS, MIDDLEWARE, REST_FRAMEWORK, env

# DEBUG
# ============================================================================
DEBUG = True
ALLOWED_HOSTS = ["*"]

# CORS - Allow all origins in development
# ============================================================================
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8080",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    env.str("DOMAIN_URL", default="http://localhost:8000"),
    env.str("FRONTEND_URL", default="http://localhost:5173"),
]


CORS_ORIGIN_WHITELIST = [
    "http://localhost:8080",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    env.str("DOMAIN_URL", default="http://localhost:8000"),
    env.str("FRONTEND_URL", default="http://localhost:5173"),
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8080",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    env.str("DOMAIN_URL", default="http://localhost:8000"),
    env.str("FRONTEND_URL", default="http://localhost:5173"),
]

# EMAIL - Console backend for development
# ============================================================================
EMAIL_BACKEND = env.str(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)

# REST FRAMEWORK - Add browsable API renderer for development
# ============================================================================
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

# INSTALLED APPS - Add development tools
# ============================================================================
INSTALLED_APPS += [
    app for app in ["django_extensions"] if app not in INSTALLED_APPS
]

# LOGGING - Minimal logging in development, only Django request logs
# ============================================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
