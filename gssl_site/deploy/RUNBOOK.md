# Deploying this site to greensparksolutions.com

For the `green-ics` droplet (Ubuntu 24.04, `170.64.218.194`), over PuTTY as
`root`. Every block below is meant to be pasted as-is.

## What this does, and how to undo it

`greensparksolutions.com` is currently served by a Node app on `localhost:3000`
through nginx. This replaces that with the Django site. **The Node app is left
running on port 3000 and untouched**, so the cutover is one nginx symlink and
the rollback is the same symlink back — about ten seconds, no rebuild.

Two things break the moment the apex switches, and neither is fixable by this
deploy:

- **The Gold Standard consultation notices.** The live site serves public
  consultation records under `greensparksolutions.com/events/…`. This site has
  no such pages, so those URLs will 404. They are public compliance records,
  so decide before you switch: keep the Node app on a subdomain and repoint
  the links, or have the notices rebuilt here at the same paths.
- **Any other URL the old site had.** Step 0 captures the list, so you know
  what you are breaking rather than finding out from a 404 log.

## 0. Pre-flight — read the answers before continuing

    df -h /                                   # was 88.8% full; needs ~300MB free
    ss -ltn | grep -E ':8000|:3000'           # 8000 must be free, 3000 is the old site
    ls /etc/letsencrypt/live/                 # the exact certificate directory name
    grep -rl greensparksolutions.com /etc/nginx/sites-enabled/
    curl -s localhost:3000/sitemap.xml | grep -o "<loc>[^<]*" | head -40

If disk is tight:

    apt clean && journalctl --vacuum-time=7d && df -h /

## 1. Packages

    apt update && apt install -y python3-venv python3-pip sqlite3

## 2. Service account and layout

The systemd unit assumes these paths exactly.

    adduser --system --group --home /srv/gssl gssl
    mkdir -p /srv/gssl/{app,data,static} /etc/gssl
    chown -R gssl:gssl /srv/gssl

## 3. The code

Public repository, so no credentials needed. `main` holds only the frozen
static design build; the site is on the branch below.

    sudo -u gssl git clone https://github.com/Rabbi-2529/greenspark.git /srv/gssl/app
    sudo -u gssl git -C /srv/gssl/app checkout claude/loving-hopper-gc5fhq

## 4. Virtualenv

    sudo -u gssl python3 -m venv /srv/gssl/venv
    sudo -u gssl /srv/gssl/venv/bin/pip install -U pip

## 5. The environment file

Generate a secret key and keep the output:

    /srv/gssl/venv/bin/python -c "import secrets; print(secrets.token_urlsafe(64))"

Then:

    cp /srv/gssl/app/gssl_site/.env.example /etc/gssl/gssl.env
    nano /etc/gssl/gssl.env

Set these. The first three are refused outright if missing or wrong:

    DJANGO_SECRET_KEY=<the string you just generated>
    DJANGO_ALLOWED_HOSTS=greensparksolutions.com,www.greensparksolutions.com
    DJANGO_SITE_URL=https://greensparksolutions.com
    DJANGO_DB_PATH=/srv/gssl/data/db.sqlite3
    DJANGO_STATIC_ROOT=/srv/gssl/static
    DJANGO_ADMIN_URL=admin/
    DJANGO_CONSOLE_URL=office/
    DJANGO_BEHIND_PROXY=1
    DJANGO_SECURE_SSL_REDIRECT=1
    DJANGO_HSTS_SECONDS=300
    DJANGO_HSTS_INCLUDE_SUBDOMAINS=0
    DJANGO_HSTS_PRELOAD=0

Those last three are deliberately timid for a first deploy: HSTS cannot be
withdrawn early, so a browser told "HTTPS only for a year" means it. Start at
300 seconds and raise it in step 11 once the site is confirmed good. `admin.`
and `ics.` both serve HTTPS today, so includeSubDomains can go to 1 later —
but not on day one.

Leave `DJANGO_EMAIL_HOST` empty for now. Enquiries are still saved and listed
in the console; they are simply not emailed until it is filled in.

The file holds the secret key:

    chown root:gssl /etc/gssl/gssl.env && chmod 640 /etc/gssl/gssl.env

## 6. Install, check, migrate, collect static

    sudo -u gssl /srv/gssl/app/gssl_site/deploy/release.sh

It installs requirements, runs `check --deploy` refusing on any warning,
migrates — which seeds the site map, six programmes, seven projects and the
home page content — and writes the static files. It stops at the first
failure, so a broken release never reaches the reload.

## 7. The first console account

    cd /srv/gssl/app/gssl_site
    sudo -u gssl DJANGO_ENV_FILE=/etc/gssl/gssl.env \
      DJANGO_SETTINGS_MODULE=config.settings.prod \
      /srv/gssl/venv/bin/python manage.py createsuperuser

A superuser ranks as an administrator in the console. Accounts made later
start read-only until given a group, so adding staff never hands out write
access by accident.

## 8. Start it — still not serving the public

    cp /srv/gssl/app/gssl_site/deploy/gssl.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable --now gssl
    systemctl status gssl --no-pager

Check it directly, before nginx points at it:

    curl -sI -H 'Host: greensparksolutions.com' http://127.0.0.1:8000/ | head -3

A 301 to https is correct here — that is `SECURE_SSL_REDIRECT` doing its job.

## 9. The cutover

Install the shipped nginx site. It is already written for this domain, so the
only thing to check is the certificate path against what step 0 showed:

    cp /srv/gssl/app/gssl_site/deploy/nginx.conf /etc/nginx/sites-available/gssl
    grep ssl_certificate /etc/nginx/sites-available/gssl

If `/etc/letsencrypt/live/` holds a different directory name (certbot
sometimes appends `-0001`), fix it now:

    nano /etc/nginx/sites-available/gssl

Now swap. Replace `OLDSITE` with the filename step 0 printed:

    rm /etc/nginx/sites-enabled/OLDSITE
    ln -s /etc/nginx/sites-available/gssl /etc/nginx/sites-enabled/gssl
    nginx -t && systemctl reload nginx

Both files claim `server_name greensparksolutions.com`, so the old one must be
unlinked, not merely left beside it — otherwise nginx keeps the first and
quietly ignores yours.

### Rollback

If anything is wrong, this puts the old site straight back. The Node app never
stopped, so there is nothing to restart:

    rm /etc/nginx/sites-enabled/gssl
    ln -s /etc/nginx/sites-available/OLDSITE /etc/nginx/sites-enabled/OLDSITE
    nginx -t && systemctl reload nginx

## 10. Verify

    curl -sI https://greensparksolutions.com/ | head -6
    curl -sI https://www.greensparksolutions.com/ | head -3     # 301 to the bare domain
    curl -s  https://greensparksolutions.com/sitemap.xml | head -5
    curl -sI https://greensparksolutions.com/static/css/tokens.css | head -3
    curl -sI https://admin.greensparksolutions.com/ | head -3   # untouched
    curl -sI https://ics.greensparksolutions.com/ | head -3     # untouched

Then in a browser: the home page, a project page, the enquiry form, and the
console at `https://greensparksolutions.com/office/`.

## 11. Once it is confirmed good

Raise HSTS, and turn on subdomain coverage only when you are sure `admin.`
and `ics.` will always be HTTPS:

    nano /etc/gssl/gssl.env     # DJANGO_HSTS_SECONDS=31536000, INCLUDE_SUBDOMAINS=1
    systemctl restart gssl

Fill in the mail settings so enquiries are emailed as well as stored:

    nano /etc/gssl/gssl.env     # DJANGO_EMAIL_HOST and friends
    systemctl restart gssl

## Updating, from then on

    sudo -u gssl git -C /srv/gssl/app pull
    sudo -u gssl /srv/gssl/app/gssl_site/deploy/release.sh
    systemctl reload gssl

## Backups — the one thing that is not in git

`/srv/gssl/data/db.sqlite3` holds the console logins, every contact-form
enquiry and all the editable content. It is in WAL mode, so copy it with
sqlite3 rather than `cp`:

    sudo -u gssl sqlite3 /srv/gssl/data/db.sqlite3 ".backup '/srv/gssl/data/backup.sqlite3'"

Put a dated version of that in cron, and copy the result off the droplet.
