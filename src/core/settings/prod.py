"""
Production settings - with security and performance optimizations.
"""
import dj_database_url

from .base import *  # noqa: F401, F403
from .base import DATABASES, INSTALLED_APPS, REST_FRAMEWORK, SPECTACULAR_SETTINGS, env

# DEBUG
# ============================================================================
DEBUG = env.bool("DJANGO_DEBUG", False)
if DEBUG:
    raise RuntimeError(
        "DEBUG=True in production is not allowed. Set DJANGO_DEBUG=False in your environment."
    )

# SECURITY - SSL/HTTPS
# ============================================================================
# SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_BROWSER_XSS_FILTER = True
# SECURE_CONTENT_TYPE_NOSNIFF = True

# HSTS
# SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=31536000)
# SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
#     "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
# )
# SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
#
# # Proxy SSL header
# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
#
# # SESSION & CSRF
# # ============================================================================
# SESSION_COOKIE_HTTPONLY = True
# CSRF_COOKIE_HTTPONLY = True
# SESSION_COOKIE_NAME = "__Secure-sessionid"
# CSRF_COOKIE_NAME = "__Secure-csrftoken"

# ALLOWED HOSTS
# ============================================================================
ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS", default=["*"]
)

# CORS - Restricted in production
# ============================================================================
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        env.str("DOMAIN_URL", default="https://example.com"),
        env.str("FRONTEND_URL", default="https://example.com"),
        "http://localhost:8080",
        "http://localhost:5173",
    ],
)

CORS_ORIGIN_WHITELIST = CORS_ALLOWED_ORIGINS

CSRF_TRUSTED_ORIGINS = [
    env.str("DOMAIN_URL", default="https://example.com"),
    env.str("FRONTEND_URL", default="https://example.com"),
    "http://localhost:5173",
]
# EMAIL - Production email backend
# ============================================================================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env.str("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD")

DATABASES = {
    'default': dj_database_url.config(
        default=env.str('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# REST FRAMEWORK - JSON only in production
# ============================================================================
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
]

# SPECTACULAR - Restrict schema in production
# ============================================================================
SPECTACULAR_SETTINGS["SERVERS"] = [
    {"url": env.str("DOMAIN_URL", default="https://example.com")},
]

# LOGGING - Production logging (Console only for K8s)
# ============================================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}:{lineno} - {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

# STATIC & MEDIA FILES - Optimizations for production
# ============================================================================
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"


