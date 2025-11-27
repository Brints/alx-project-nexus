import os
from datetime import timedelta
from pathlib import Path
import dj_database_url

import cloudinary
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Load Environment Variables ---
# Load .env file
load_dotenv(BASE_DIR / ".env")

# --- Core Secrets & Config ---
SECRET_KEY = os.environ.get("SECRET_KEY")
DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", ".herokuapp.com"] + os.environ.get(
    "ALLOWED_HOSTS", ""
).split(",")

CSRF_TRUSTED_ORIGINS = [
    "https://af64ab7848ce.ngrok-free.app",
    "https://*.ngrok-free.app",
]

# --- Installed Apps ---
# Application definition
INSTALLED_APPS = [
    # Daphne for Channels
    "daphne",
    # Django contrib
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third-party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework.authtoken",
    "corsheaders",
    "drf_spectacular",
    "anymail",
    "channels",
    # Storage
    "storages",
    "cloudinary",
    # modular apps
    "core",
    "users",
    "authentication",
    "polls",
    "payments",
    "notifications",
    "organizations",
]

STATIC_ROOT = BASE_DIR / "staticfiles"
# Enable compression and caching
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# --- Middleware ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# --- Core Routing & Servers ---
ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"  # Django Channels


# --- Templates & Static ---
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

STATIC_URL = "static/"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"


# --- Database (PostgreSQL) ---
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=True,
        )
    }
else:
    # Fallback for local development
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "agora_db"),
            "USER": os.environ.get("DB_USER", "postgres"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }


# --- Cache & Channels (Redis) ---
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

if REDIS_URL.startswith("rediss://"):
    redis_config = {
        "hosts": [
            {
                "address": REDIS_URL,
                "ssl_cert_reqs": None,
            }
        ],
    }
else:
    # Standard Redis connection
    redis_config = {"hosts": [REDIS_URL]}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": redis_config,
    },
}

# Django-Redis cache also needs SSL handling
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# Add SSL options for django-redis if needed
if REDIS_URL.startswith("rediss://"):
    CACHES["default"]["OPTIONS"]["CONNECTION_POOL_KWARGS"] = {"ssl_cert_reqs": None}


# --- Authentication ---
AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- API, JWT & CORS (DRF) ---
SITE_ID = 1

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "core.custom_renderer.CustomJSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "EXCEPTION_HANDLER": "core.custom_exception_handler.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "USER_ID_FIELD": "user_id",
    "USER_ID_CLAIM": "user_id",
}

if DEBUG:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
else:
    CORS_ALLOWED_ORIGINS = os.environ.get(
        "CORS_ALLOWED_ORIGINS", "https://yourfrontend.com"
    ).split(",")

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_BROWSER_XSS_FILTER = True


# --- Email (Mailgun) ---
ANYMAIL = {
    "MAILGUN_API_KEY": os.environ.get("MAILGUN_API_KEY"),
    "MAILGUN_SENDER_DOMAIN": os.environ.get("MAILGUN_SENDER_DOMAIN"),
    "MAILGUN_API_URL": "https://api.mailgun.net/v3",
}

EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@example.com")
EMAIL_TIMEOUT = 10
EMAIL_FAIL_SILENTLY = False


# --- Payments (Chapa) ---
CHAPA_SECRET_KEY = os.environ.get("CHAPA_SECRET_KEY")
CHAPA_WEBHOOK_SECRET = os.environ.get(
    "CHAPA_WEBHOOK_SECRET", os.environ.get("CHAPA_SECRET_KEY")
)
FRONTEND_VERIFICATION_URL = os.environ.get(
    "FRONTEND_VERIFICATION_URL", "http://localhost:8000"
)


# --- API Docs (Spectacular) ---
SPECTACULAR_SETTINGS = {
    "TITLE": "The Agora Poll API",
    "DESCRIPTION": "API documentation for The Agora Poll application. A Real-time Online Poll System.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}


# --- Internationalization ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Media Storage (Cloudinary / S3) ---
# -- Cloudinary Configuration (Current) ---
cloudinary.config(url=os.environ.get("CLOUDINARY_URL"))
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"


# --- AWS S3 Configuration (Provisioned for later) ---
# DEFAULT_FILE_STORAGE = 'storages.backends.s3.S3Storage'
# AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
# AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
# AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
# AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME')
# AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
# AWS_S3_FILE_OVERWRITE = False

SITE_URL = os.environ.get("SITE_URL", "http://localhost:8000/api/")
WS_URL = os.environ.get("WS_URL", "ws://localhost:8000/")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

if REDIS_URL.startswith("rediss://"):
    CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": None}
    CELERY_REDIS_BACKEND_USE_SSL = {"ssl_cert_reqs": None}


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "debug.log",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "authentication": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "notifications": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "users": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "organizations": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "payments": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


# --- GeoIP Configuration ---
GEOIP_PATH = BASE_DIR / "geoip"
GEOIP_COUNTRY = "GeoLite2-Country.csv"
