import sys

from .base import *  # noqa: F403

DEBUG = False

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405

# Reverse proxy (Render, Railway, ...) terminates TLS and forwards over plain HTTP internally;
# this header tells Django the original request was HTTPS so SECURE_SSL_REDIRECT and secure
# cookies behave correctly instead of redirect-looping.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 7)  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

X_FRAME_OPTIONS = "DENY"

# Media files (uploaded CVs) live on local disk by default. On free-tier hosting (e.g. Render's
# free plan) that disk is EPHEMERAL: it is wiped on every deploy and every restart. This is fine
# for a portfolio demo, but not for real user data. To add durable storage later, set
# MEDIA_STORAGE_BACKEND to a real backend (e.g. "storages.backends.s3.S3Storage" with
# django-storages installed and its credentials configured) — no other code changes required,
# since CVDocument.file already goes through Django's storage abstraction.
MEDIA_STORAGE_BACKEND = env(  # noqa: F405
    "MEDIA_STORAGE_BACKEND", default="django.core.files.storage.FileSystemStorage"
)

STORAGES = {
    "default": {"BACKEND": MEDIA_STORAGE_BACKEND},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Logging: everything to stdout so the platform's own log aggregator captures it. Level is
# configurable per environment. Never log request bodies, headers, or settings values — those
# can carry API keys (LLM_API_KEY, FRANCE_TRAVAIL_CLIENT_SECRET, SECRET_KEY).
LOG_LEVEL = env("LOG_LEVEL", default="INFO")  # noqa: F405
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
