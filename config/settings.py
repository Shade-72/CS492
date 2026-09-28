"""
Django settings for the School Management System.

Consolidates the whole team's Sprint 1 + Sprint 2 work (originally split
across Flask blueprints, a couple of FastAPI services, raw sqlite3 scripts,
and two tkinter desktop scripts) into one Django project. See README.md for
a file-by-file map of "who wrote what, and where it lives now".
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Core ------------------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.environ.get("DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [h for h in os.environ.get("ALLOWED_HOSTS", "*").split(",") if h]

# --- Render ------------------------------------------------------------------
# Render sets RENDER_EXTERNAL_HOSTNAME automatically for every web service
# (e.g. "school-management-django.onrender.com") -- add it to ALLOWED_HOSTS
# and CSRF_TRUSTED_ORIGINS without needing a manual env var for it. Setting
# ALLOWED_HOSTS explicitly yourself (above) still overrides the "*" default.
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME and ALLOWED_HOSTS == ["*"]:
    ALLOWED_HOSTS = [RENDER_EXTERNAL_HOSTNAME]

CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o]
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "academics",
    "family_portal",
    "notices",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serves static files on Render (no separate web server)
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

WSGI_APPLICATION = "config.wsgi.application"

# --- Database ----------------------------------------------------------------
# Render's Postgres add-on (or any other host's Postgres/MySQL) is picked up
# automatically via a DATABASE_URL environment variable, which Render sets
# for you when a database is attached to the web service. Without one (local
# development, or this project's own test runner), it falls back to sqlite.
import dj_database_url  # noqa: E402

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

# --- Custom user model (UMA-001 / UMA-002) ----------------------------------
AUTH_USER_MODEL = "accounts.User"

# --- Password policy (UMA-002: "Implement password complexity validation") -
# Django's own validators plus our complexity rules (accounts/validators.py),
# ported from the Sprint 1 password checker.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "accounts.validators.ComplexityValidator", "OPTIONS": {"min_length": 10}},
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

# --- Login security (UMA-002: lockout + HTTPS) ------------------------------
MAX_FAILED_ATTEMPTS = int(os.environ.get("MAX_FAILED_ATTEMPTS", 5))
LOCKOUT_WINDOW_MINUTES = int(os.environ.get("LOCKOUT_WINDOW_MINUTES", 15))

# "Enforce HTTPS for all login traffic": set FORCE_HTTPS=true in production,
# behind a reverse proxy that terminates TLS and sets X-Forwarded-Proto.
FORCE_HTTPS = os.environ.get("FORCE_HTTPS", "false").lower() == "true"
SECURE_SSL_REDIRECT = FORCE_HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if FORCE_HTTPS else None
SESSION_COOKIE_SECURE = FORCE_HTTPS
CSRF_COOKIE_SECURE = FORCE_HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# --- Field-level encryption (UMA-003: "Encrypt Data Storage") --------------
# Used by accounts/fields.py (EncryptedTextField / EncryptedCharField) for
# student SSNs, home addresses, medical notes, contact info, and message
# bodies (CNS-011). Generate one with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Without one set, an ephemeral key is generated each process start, so
# encrypted values become unreadable after a restart -- fine for local
# development only, never for anything you intend to keep.
from cryptography.fernet import Fernet  # noqa: E402

FIELD_ENCRYPTION_KEY = os.environ.get("FIELD_ENCRYPTION_KEY") or Fernet.generate_key().decode()

# --- Password hashing --------------------------------------------------------
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_VALIDATORS_MIN_LENGTH = 10  # read by accounts.validators.ComplexityValidator default

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Render (and most PaaS hosts) don't run a separate static file server, so
# WhiteNoise serves collected static files directly from the Django process,
# with hashed filenames + far-future cache headers.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Logging (UMA-002: "Log failed login attempts", SIEM-006/AMG-009/CNS-012:
# "Access logged") -----------------------------------------------------------
# Both handlers below stay active on Render: the console handler is what
# shows up in Render's own log stream (Dashboard > your service > Logs); the
# file handler still writes to LOG_FILE for local debugging, but Render's
# disk is ephemeral by default, so that file does not survive a redeploy or
# restart there -- use the console logs (or Render's log drains) as the
# durable copy in production.
LOG_DIR = BASE_DIR / "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "auth": {"format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s"},
    },
    "handlers": {
        "auth_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.environ.get("LOG_FILE", str(LOG_DIR / "auth.log")),
            "maxBytes": 1_000_000,
            "backupCount": 5,
            "formatter": "auth",
        },
        "console": {"class": "logging.StreamHandler", "formatter": "auth"},
    },
    "loggers": {
        "accounts.auth": {"handlers": ["auth_file", "console"], "level": "INFO", "propagate": False},
        "accounts.access": {"handlers": ["auth_file", "console"], "level": "INFO", "propagate": False},
    },
}
