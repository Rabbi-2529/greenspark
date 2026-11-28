"""
Production settings for the GSSL website.

Required environment variables (the site refuses to start without them):
    DJANGO_SECRET_KEY        a long random string, unique to the server
    DJANGO_ALLOWED_HOSTS     comma-separated hostnames, e.g. greensparksolutions.com,www.greensparksolutions.com
    DJANGO_SITE_URL          canonical origin, e.g. https://greensparksolutions.com

Everything else is optional; see .env.example for the full list.
"""

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, env, env_bool, env_int, env_list

DEBUG = False

SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY or SECRET_KEY.startswith("insecure-"):
    raise RuntimeError("DJANGO_SECRET_KEY must be set in production.")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must be set in production.")

SITE_URL = env("DJANGO_SITE_URL").rstrip("/")
if not SITE_URL.startswith("https://"):
    raise RuntimeError(
        "DJANGO_SITE_URL must be set in production, as the https:// origin of the live "
        "site (canonical links, the sitemap and share cards are built from it)."
    )

CSRF_TRUSTED_ORIGINS = [f"https://{host.lstrip('.')}" for host in ALLOWED_HOSTS]

# --- HTTPS and cookies ------------------------------------------------------
# Behind a reverse proxy that terminates TLS (the normal set-up), leave
# DJANGO_BEHIND_PROXY at 1 and make sure the proxy sets X-Forwarded-Proto.

BEHIND_PROXY = env_bool("DJANGO_BEHIND_PROXY", True)
if BEHIND_PROXY:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# HSTS tells browsers to use HTTPS only, for the whole max-age, and cannot be
# taken back early. includeSubDomains covers every subdomain of the site's
# domain: if any of them (mail, cPanel, an old site) still serves plain HTTP,
# set DJANGO_HSTS_INCLUDE_SUBDOMAINS=0 before the first deploy.
SECURE_HSTS_SECONDS = env_int("DJANGO_HSTS_SECONDS", 60 * 60 * 24 * 365)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_HSTS_INCLUDE_SUBDOMAINS", True)
# "preload" lets anyone submit the domain to the browsers' built-in HSTS list,
# which takes months to undo. Opt in deliberately once HTTPS is settled.
SECURE_HSTS_PRELOAD = env_bool("DJANGO_HSTS_PRELOAD", False)

# check --deploy warns about both HSTS choices above, and release.sh refuses to
# deploy on any warning. Both are deliberate per-server decisions made through
# the environment, so the warning is silenced once the decision is recorded --
# otherwise following .env.example's own advice (turn includeSubDomains off
# when a subdomain still serves plain HTTP) would block the release.
SILENCED_SYSTEM_CHECKS = []
if not SECURE_HSTS_PRELOAD:
    SILENCED_SYSTEM_CHECKS.append("security.W021")
if not SECURE_HSTS_INCLUDE_SUBDOMAINS:
    SILENCED_SYSTEM_CHECKS.append("security.W005")

CONTENT_SECURITY_POLICY_REPORT_ONLY = False

# --- Email ------------------------------------------------------------------

if not ENQUIRY_EMAIL_ENABLED:  # noqa: F405
    # Enquiries are kept in the admin; nothing tries to reach a mail server.
    EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"

# --- Static files -----------------------------------------------------------
# WhiteNoise marks hashed files (everything {% static %} links to) immutable
# for a year by itself. This is the lifetime of the few un-hashed URLs, such
# as a favicon requested by its plain name.
WHITENOISE_MAX_AGE = 60 * 60

# --- Caching ----------------------------------------------------------------
# Per-process memory cache: holds the contact-form throttle counters.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "gssl",
    }
}

# Make sure the database directory exists before Django opens the file.
DATABASES["default"]["NAME"].parent.mkdir(parents=True, exist_ok=True)  # noqa: F405
# And the upload directory, before anyone saves a photo into it. nginx serves
# this path directly; see deploy/nginx.conf.
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)  # noqa: F405
