import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("DEBUG", "0") in {"1", "true", "True"}

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get(
        "ALLOWED_HOSTS",
        "hub.nynusoft.com,127.0.0.1,localhost",
    ).split(",")
    if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CSRF_TRUSTED_ORIGINS",
        "https://hub.nynusoft.com,http://127.0.0.1:8000,http://localhost:8000,"
        "http://127.0.0.1:5173,http://localhost:5173",
    ).split(",")
    if o.strip()
]

INSTALLED_APPS = [
    "daphne",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "rest_framework",
    "hub",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

_default_db = "sqlite:///" + str(BASE_DIR / "db.sqlite3")
# Daphne/ASGI: conn_max_age>0 filtra conexiones por hilo y satura PostgreSQL.
DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL", _default_db),
        conn_max_age=int(os.environ.get("CONN_MAX_AGE", "0")),
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "EXCEPTION_HANDLER": "hub.exceptions.api_exception_handler",
}

EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.hostinger.com").strip()
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "465"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "info@nynusoft.com").strip()
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "").strip()
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "true").lower() in {"1", "true", "yes"}
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "false").lower() in {"1", "true", "yes"}
IMAP_HOST = os.environ.get("IMAP_HOST", "imap.hostinger.com").strip()
IMAP_PORT = int(os.environ.get("IMAP_PORT", "993"))
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    "BeatLab Hub <info@nynusoft.com>",
)
PUBLIC_SITE_URL = os.environ.get("PUBLIC_SITE_URL", "https://hub.nynusoft.com").rstrip(
    "/"
)
# PNG del wordmark + corazón (Gmail/Outlook no pintan SVG ni el heartbeat CSS).
# /static/ tras collectstatic; /brand/ tras el build del frontend.
EMAIL_LOGO_URL = os.environ.get(
    "EMAIL_LOGO_URL",
    f"{PUBLIC_SITE_URL}/static/hub/email-logo.png",
)
SERVER_EMAIL = os.environ.get("SERVER_EMAIL", EMAIL_HOST_USER or "info@nynusoft.com")
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "20"))
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST
    else "django.core.mail.backends.console.EmailBackend",
)
REGISTER_OTP_TTL_SECONDS = int(os.environ.get("REGISTER_OTP_TTL_SECONDS", "600"))
REGISTER_OTP_MAX_ATTEMPTS = int(os.environ.get("REGISTER_OTP_MAX_ATTEMPTS", "5"))
