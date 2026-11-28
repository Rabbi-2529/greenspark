#!/usr/bin/env bash
# Release the current checkout: install, check, migrate, collect static.
#
# Run as the gssl user, after `git pull`:
#   sudo -u gssl /srv/gssl/app/gssl_site/deploy/release.sh
# then reload the site:
#   sudo systemctl reload gssl
#
# Stops at the first failure, so a broken release never reaches the reload.
set -euo pipefail

VENV="${VENV:-/srv/gssl/venv}"
export DJANGO_ENV_FILE="${DJANGO_ENV_FILE:-/etc/gssl/gssl.env}"
export DJANGO_SETTINGS_MODULE=config.settings.prod

cd "$(dirname "$0")/.."

"$VENV/bin/pip" install --quiet -r requirements.txt
"$VENV/bin/python" manage.py check --deploy --fail-level WARNING
"$VENV/bin/python" manage.py migrate --noinput
"$VENV/bin/python" manage.py collectstatic --noinput --verbosity 0

# Uploaded photographs. Unlike static, nothing recreates these -- the release
# only has to make sure the directory is there and ours, because nginx serves
# it directly and the first upload would otherwise fail on a fresh server.
# config.settings.prod creates it too; this prints it, so a release makes the
# path visible rather than leaving it to be discovered when a photo 404s.
MEDIA_ROOT="$("$VENV/bin/python" -c 'import django; django.setup(); from django.conf import settings; print(settings.MEDIA_ROOT)')"
mkdir -p "$MEDIA_ROOT"
echo "Uploads: $MEDIA_ROOT  (nginx must serve /media/ from here; back it up)"

echo "Ready: $(git rev-parse --short HEAD). Now run: sudo systemctl reload gssl"
