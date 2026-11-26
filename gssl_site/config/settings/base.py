"""
Shared Django settings for the Green Spark Solutions Australia website.

Environment-specific values live in dev.py / prod.py. Nothing secret is
stored here; secrets come from the environment (see .env.example).
"""

from email.utils import getaddresses
from pathlib import Path
import os

# gssl_site/config/settings/base.py -> gssl_site/
BASE_DIR = Path(__file__).resolve().parents[2]

# Load an env file if there is one: gssl_site/.env in development, or the file
# DJANGO_ENV_FILE names (e.g. /etc/gssl/gssl.env, for manage.py commands run on
# the server). Real environment variables always win, so under systemd the
# unit's EnvironmentFile is what counts.
try:
    from dotenv import load_dotenv
except ImportError:  # dotenv is optional
    pass
else:
    load_dotenv(os.environ.get("DJANGO_ENV_FILE") or BASE_DIR / ".env", override=False)


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw else default


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


# --- Core -------------------------------------------------------------------

SECRET_KEY = env("DJANGO_SECRET_KEY", "insecure-key-for-local-development-only")
DEBUG = False
ALLOWED_HOSTS: list[str] = env_list("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.content",
    "apps.website",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "apps.website.middleware.SecurityHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

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
                "apps.website.context_processors.site",
            ],
        },
    },
]

# The admin lives at /admin/ unless DJANGO_ADMIN_URL moves it somewhere less
# guessable, e.g. "gssl-office/". Always ends with a slash.
ADMIN_URL = env("DJANGO_ADMIN_URL", "admin/").strip("/") + "/"

# --- Database ---------------------------------------------------------------
# Page content is static. The database holds the admin login, sessions and the
# enquiries sent through the contact form, so it must be backed up and must
# live somewhere a deploy does not overwrite: set DJANGO_DB_PATH in production.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(env("DJANGO_DB_PATH", str(BASE_DIR / "db.sqlite3"))),
        "OPTIONS": {
            # Several gunicorn workers share one file: wait for a lock rather
            # than fail, take the write lock up front, and let reads run
            # alongside writes.
            "timeout": 20,
            "transaction_mode": "IMMEDIATE",
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL",
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internationalisation ---------------------------------------------------
# Bangla is planned (see README §4, --gs-font-bn); English only for now.

LANGUAGE_CODE = "en-au"
TIME_ZONE = "Australia/Sydney"
USE_I18N = True
USE_TZ = True

# --- Static files -----------------------------------------------------------

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = Path(env("DJANGO_STATIC_ROOT", str(BASE_DIR / "staticfiles")))

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# --- Site identity ----------------------------------------------------------
# Canonical, Open Graph, sitemap and share URLs are built from SITE_URL. The
# templates never hard-code a domain. Production refuses to start without it.

SITE_URL = env("DJANGO_SITE_URL", "http://localhost:8000").rstrip("/")
SITE_NAME = "Green Spark Solutions Australia"

# True when a reverse proxy (nginx, Apache, a load balancer) sits in front of
# Django and terminates TLS. Decides whether X-Forwarded-* headers are trusted.
BEHIND_PROXY = env_bool("DJANGO_BEHIND_PROXY", False)

# --- Email and the contact form ---------------------------------------------
# Every enquiry is saved to the database first and shown in the admin. It is
# also emailed to ENQUIRY_RECIPIENTS once DJANGO_EMAIL_HOST is set; until
# then nothing is lost, it simply waits in the admin.

EMAIL_HOST = env("DJANGO_EMAIL_HOST")
EMAIL_PORT = env_int("DJANGO_EMAIL_PORT", 587)
EMAIL_HOST_USER = env("DJANGO_EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("DJANGO_EMAIL_HOST_PASSWORD")
EMAIL_USE_SSL = env_bool("DJANGO_EMAIL_USE_SSL", False)
EMAIL_USE_TLS = env_bool("DJANGO_EMAIL_USE_TLS", not EMAIL_USE_SSL)
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = env("DJANGO_DEFAULT_FROM_EMAIL", "Green Spark website <info@greensparksolutions.com>")
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", DEFAULT_FROM_EMAIL)

ENQUIRY_RECIPIENTS = env_list("DJANGO_ENQUIRY_RECIPIENTS", "info@greensparksolutions.com")
ENQUIRY_EMAIL_ENABLED = bool(EMAIL_HOST)
# At most this many enquiries per visitor per window; more get a polite 429.
ENQUIRY_THROTTLE_COUNT = env_int("DJANGO_ENQUIRY_THROTTLE_COUNT", 5)
ENQUIRY_THROTTLE_SECONDS = env_int("DJANGO_ENQUIRY_THROTTLE_SECONDS", 10 * 60)

# Server errors are emailed here when email is configured, e.g.
# DJANGO_ADMINS="Web team <web@example.com>, Someone <someone@example.com>"
ADMINS = [(name or addr, addr) for name, addr in getaddresses([env("DJANGO_ADMINS")]) if addr]

# --- Security headers -------------------------------------------------------
# The templates have no inline <script>, no on*= handlers and no style=""
# attributes (tests enforce it), so the site runs under a strict policy.
# JSON-LD data blocks are not executed and need no allowance.

CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' data:",
    "font-src 'self'",
    "media-src 'self'",
    "connect-src 'self'",
    "manifest-src 'self'",
    "frame-src 'none'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'",
    "base-uri 'self'",
])
# The Django admin uses a few inline style attributes.
CONTENT_SECURITY_POLICY_ADMIN = CONTENT_SECURITY_POLICY.replace(
    "style-src 'self'", "style-src 'self' 'unsafe-inline'"
)
CONTENT_SECURITY_POLICY_REPORT_ONLY = False

PERMISSIONS_POLICY = (
    "accelerometer=(), browsing-topics=(), camera=(), geolocation=(), gyroscope=(), "
    "magnetometer=(), microphone=(), payment=(), usb=()"
)

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# --- Logging ----------------------------------------------------------------
# Everything goes to stderr, where gunicorn / systemd / the host collects it.
# Server errors are also emailed to ADMINS when email is configured.

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {name} {message}", "style": "{"},
    },
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
        "mail_admins": {
            "class": "django.utils.log.AdminEmailHandler",
            "level": "ERROR",
            "filters": ["require_debug_false"],
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console", "mail_admins"], "level": "ERROR", "propagate": False},
        "django.security": {"handlers": ["console", "mail_admins"], "level": "ERROR", "propagate": False},
        "apps.website": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
