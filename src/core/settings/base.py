"""
Base Django settings shared across all environments.
"""

import os
from datetime import timedelta
from pathlib import Path

import environ

env = environ.Env()

# Environment detection
IN_K8S = "KUBERNETES_SERVICE_HOST" in os.environ
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

if not IN_K8S:
    # Try multiple common .env file names for local development
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        environ.Env.read_env(str(env_file))
    elif (BASE_DIR / ".env.example").exists():
        environ.Env.read_env(str(BASE_DIR / ".env.example"))

# GENERAL SETTINGS
# ============================================================================
SECRET_KEY = env.str("SECRET_KEY", default="secret")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])
DEBUG = env.bool("DEBUG", default=env.bool("DJANGO_DEBUG", default=False))
TESTING = env.bool("TESTING", default=False)

# Build paths
ROOT_URLCONF = "src.core.urls"
ASGI_APPLICATION = "src.core.asgi.application"

# Application definition
DJANGO_APPS = [
    "daphne",
    "unfold",
    "unfold.contrib.filters",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

LOCAL_APPS = [
    "src.apps.users",
    "src.apps.assignments",
    "src.apps.courses",
    "src.apps.submissions",
    "src.apps.plagiarism",
    "src.apps.notifications",
    "src.apps.chat",
    "src.apps.grades",
    "src.apps.logs",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_celery_beat",
    "drf_spectacular",
    "django_extensions",
    "channels",
    "django_filters",
    "ckeditor",
    "ckeditor_uploader",
    "django_cleanup.apps.CleanupConfig",
    "silk",
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS + THIRD_PARTY_APPS

# MIDDLEWARE
# ============================================================================
MIDDLEWARE = [
    'src.core.middleware.HealthCheckMiddleware',
    "django.middleware.security.SecurityMiddleware",
    "src.core.observability.metrics.PrometheusRequestMiddleware",
    "silk.middleware.SilkyMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# TEMPLATES
# ============================================================================
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# DATABASE
# ============================================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env.str("POSTGRES_DB", default="postgres"),
        "USER": env.str("POSTGRES_USER", default="postgres"),
        "PASSWORD": env.str("POSTGRES_PASSWORD", default="postgres"),
        "HOST": env.str("POSTGRES_HOST", default="localhost"),
        "PORT": env.int("POSTGRES_PORT", default=5432),
    }
}

# PASSWORD VALIDATION
# ============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# AUTHENTICATION
# ============================================================================
AUTH_USER_MODEL = "users.User"

# INTERNATIONALIZATION
# ============================================================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_L10N = True
USE_TZ = True

LANGUAGES = [
    ("en", "English"),
    ("uz", "Uzbek"),
    ("ru", "Russian"),
]

# STATIC & MEDIA FILES
# ============================================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Storage configuration
USE_S3 = env.bool("USE_S3", False)

STORAGES: dict[str, dict[str, object]] = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

if USE_S3:
    INSTALLED_APPS += ["storages"]

    S3_ACCESS_KEY_ID = env("S3_ACCESS_KEY_ID")
    S3_SECRET_ACCESS_KEY = env("S3_SECRET_ACCESS_KEY")

    S3_BUCKET_NAME = env("S3_BUCKET_NAME")

    S3_REGION = env("S3_REGION")

    S3_ENDPOINT_URL = env("S3_ENDPOINT_URL", default=None)

    S3_PUBLIC_URL = env("S3_PUBLIC_URL", default=None)

    S3_ADDRESSING_STYLE = env(
        "S3_ADDRESSING_STYLE",
        default="path",
    )

    S3_QUERYSTRING_AUTH = env.bool(
        "S3_QUERYSTRING_AUTH",
        False,
    )

    if not S3_PUBLIC_URL:
        if S3_ENDPOINT_URL:
            S3_PUBLIC_URL = S3_ENDPOINT_URL

    S3_OPTIONS = {
        "access_key": S3_ACCESS_KEY_ID,
        "secret_key": S3_SECRET_ACCESS_KEY,
        "bucket_name": S3_BUCKET_NAME,
        "region_name": S3_REGION,
        "endpoint_url": S3_ENDPOINT_URL,
        "addressing_style": S3_ADDRESSING_STYLE,
        "default_acl": None,
        "querystring_auth": S3_QUERYSTRING_AUTH,
        "file_overwrite": False,
    }

    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            **S3_OPTIONS,
            "location": "media",
        },
    }

    USE_S3_FOR_STATIC = env.bool("USE_S3_FOR_STATIC", False, )

    if USE_S3_FOR_STATIC:
        STORAGES["staticfiles"] = {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                **S3_OPTIONS,
                "location": "static",
            },
        }

        STATIC_URL = (
            f"{S3_PUBLIC_URL}/{S3_BUCKET_NAME}/static/"
        )

    MEDIA_URL = (
        f"{S3_PUBLIC_URL}/{S3_BUCKET_NAME}/media/"
    )

# DEFAULT AUTO FIELD
# ============================================================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REDIS
# ============================================================================
REDIS_HOST = env.str("REDIS_HOST", default="127.0.0.1")
REDIS_PORT = env.int("REDIS_PORT", default=6379)

# CORS
# ============================================================================
CORS_ALLOW_CREDENTIALS = True

# EMAIL
# ============================================================================
EMAIL_BACKEND = env.str(
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = env.str("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER", default="email@example.com")
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD", default="password")

# REST FRAMEWORK
# ============================================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    'DEFAULT_THROTTLE_CLASSES': [
        'src.core.rate_limiting.throttle.TokenBucketThrottle',
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# SIMPLE JWT
# ============================================================================
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=60),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "JWK_URL": None,
    "LEEWAY": 0,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": (
        "rest_framework_simplejwt.authentication.default_user_authentication_rule"
    ),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
}

# CELERY
# ============================================================================
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/2"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/2"

# Task serialization
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]

# Timezone
CELERY_TIMEZONE = "Asia/Tashkent"
CELERY_ENABLE_UTC = False

# Task execution settings
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 1800
CELERY_TASK_SOFT_TIME_LIMIT = 1200

CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Queue configuration
CELERY_TASK_DEFAULT_QUEUE = "celery"
CELERY_TASK_CREATE_MISSING_QUEUES = True

CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers.DatabaseScheduler"

# CELERY_BEAT_SCHEDULE = {
#     "generate-daily-stats": {
#         "task": "users.generate_daily_stats",
#         "schedule": crontab(hour=23, minute=59),
#     },
#     "delete-deactivated-users": {
#         "task": "users.delete_deactivated_users",
#         "schedule": crontab(hour=0, minute=1),
#     },
#     "run-nightly-plagiarism-batch": {
#         "task": "plagiarism.run_nightly_batch",
#         "schedule": crontab(hour=2, minute=0),
#         "options": {"queue": "celery"},
#     },
# }

CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_WORKER_LOG_COLOR = True

# CACHING
# ============================================================================
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/2",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# RATE LIMITING
# ============================================================================
RATE_LIMITS = {
    "default_authenticated": {"capacity": 300, "refill_rate": 10},
    "default_anonymous": {"capacity": 60, "refill_rate": 1},
}

# DJANGO UNFOLD
# ============================================================================
UNFOLD = {
    "SITE_TITLE": "LearnovaX Admin",
    "SITE_HEADER": "LearnovaX Administration",
    "SITE_URL": "/",
    "SITE_ICON": None,
    "SITE_LOGO": None,
    "SITE_SYMBOL": "settings",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "ENVIRONMENT": "src.core.admin.environment_callback",
    "DASHBOARD_CALLBACK": "src.core.admin.dashboard_callback",
    "LOGIN": {
        "image": None,
        "redirect_after": None,
    },
    "STYLES": [],
    "SCRIPTS": [],
    "COLORS": {
        "primary": {
            "50": "250 245 255",
            "100": "243 232 255",
            "200": "233 213 255",
            "300": "216 180 254",
            "400": "192 132 252",
            "500": "168 85 247",
            "600": "147 51 234",
            "700": "126 34 206",
            "800": "107 33 168",
            "900": "88 28 135",
            "950": "59 7 100",
        },
    },
    "EXTENSIONS": {
        "modeltranslation": {
            "flags": {
                "en": "🇬🇧",
                "fr": "🇫🇷",
                "nl": "🇳🇱",
                "de": "🇩🇪",
            },
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
    },
}

# DRF SPECTACULAR (OpenAPI/Swagger)
# ============================================================================
SPECTACULAR_SETTINGS = {
    "TITLE": "LearnovaX API",
    "DESCRIPTION": "LearnovaX API",
    "VERSION": "1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
    },
    "SECURITY": [{"BearerAuth": []}],
    "COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
}

# CHANNELS (WebSockets)
# ============================================================================
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
        },
    },
}

# CKEDITOR
# ============================================================================
CKEDITOR_UPLOAD_PATH = "ckeditor_uploads/"
CKEDITOR_ALLOW_NONIMAGE_FILES = True
CKEDITOR_CONFIGS = {
    "default": {
        "toolbar": "full",
        "height": 300,
        "width": "100%",
        "extraAllowedContent": "iframe[*];span[*];p[*];div[*];img[*]",
    }
}
SILENCED_SYSTEM_CHECKS = ["ckeditor.W001"]

LOGS_DIR = BASE_DIR / "logs"
FILE_LOGGING_ENABLED = env.bool("FILE_LOGGING_ENABLED", default=False)

if FILE_LOGGING_ENABLED:
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        FILE_LOGGING_ENABLED = False
    else:
        FILE_LOGGING_ENABLED = os.access(LOGS_DIR, os.W_OK)

# LOGGING
# ============================================================================
# In-memory logging configuration for high-scale applications
IN_MEMORY_LOG_BUFFER_SIZE = env.int("IN_MEMORY_LOG_BUFFER_SIZE", default=10000)
IN_MEMORY_LOG_OVERFLOW = env.str(
    "IN_MEMORY_LOG_OVERFLOW", default="drop_oldest"
)  # drop_oldest, drop_newest, error
IN_MEMORY_LOG_QUEUE_SIZE = env.int("IN_MEMORY_LOG_QUEUE_SIZE", default=5000)
IN_MEMORY_LOG_FLUSH_INTERVAL = env.float("IN_MEMORY_LOG_FLUSH_INTERVAL", default=5.0)
IN_MEMORY_LOG_BATCH_SIZE = env.int("IN_MEMORY_LOG_BATCH_SIZE", default=100)

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
        # "db": {
        #     "level": "INFO",
        #     "class": "src.apps.logs.handlers.DatabaseHandler",
        #     "formatter": "verbose",
        # },
    },
    "root": {
        "handlers": ["console", "db"],
        "level": "INFO",
    },
}

ENROL_LINK_URL = env.str("ENROL_LINK_URL", default="http://localhost:5173/enroll/")
import platform

if platform.system() == "Windows":
    TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
else:
    TESSERACT_CMD = "tesseract"

ENVIRONMENT = env.str("DJANGO_ENV", default="development")
FRONTEND_URL = env.str("FRONTEND_URL", default="http://localhost:5173/")

# OBSERVABILITY
# ============================================================================
PROMETHEUS_ENABLED = env.bool("PROMETHEUS_ENABLED", default=True)
OTEL_ENABLED = env.bool("OTEL_ENABLED", default=False)
OTEL_SERVICE_NAME = env.str("OTEL_SERVICE_NAME", default="backend")
OTEL_EXPORTER_OTLP_ENDPOINT = env.str(
    "OTEL_EXPORTER_OTLP_ENDPOINT", default="http://localhost:4318"
)
OTEL_EXPORTER_OTLP_PROTOCOL = env.str(
    "OTEL_EXPORTER_OTLP_PROTOCOL", default="http/protobuf"
)
