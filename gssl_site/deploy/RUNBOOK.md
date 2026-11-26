# Deploying this site to greensparksolutions.com

For the `green-ics` droplet (Ubuntu 24.04, `170.64.218.194`), over PuTTY as
`root`. Every block below is meant to be pasted as-is.

## Where the live site actually is — read this first

**The live `greensparksolutions.com` is not on this droplet.** Checked on
26 November 2026:

| | |
|---|---|
| DNS | the apex, `www.` and `ics.` all resolve to Cloudflare (`104.21.91.12`, `172.67.207.75`) |
| Response headers | `Server: cloudflare`, `x-powered-by: Next.js`, `x-do-app-origin: f4aeebd9-…` |
| The droplet, asked for the apex directly | `502 Bad Gateway` — nothing is listening on port 3000 |

So the Next.js site runs on **DigitalOcean App Platform**, with **Cloudflare**
in front of it. The droplet's nginx block for the apex is dead configuration:
it proxies to a port nothing listens on, and no apex traffic reaches it anyway.
That is also why `/etc/letsencrypt/live/` has certificates for `admin.` and
`ics.` but none for the apex — this server has never served it.

Three consequences:

- **Nothing you do on this droplet changes the live site** until the apex DNS
  is repointed in Cloudflare. The cutover is a DNS change, not an nginx
  symlink.
- **That makes the cutover unusually safe.** You can bring the Django site up
  on the droplet and test it thoroughly against the real hostname before any
  visitor is affected (step 9).
- **The rollback is the App Platform app**, which stays running and untouched
  throughout. Reverting is a DNS change back.

### What still breaks at cutover

- **The Gold Standard consultation notices.** The live site serves public
  consultation records under `greensparksolutions.com/events/…`. This site has
  no such pages, so those URLs will 404. They are public compliance records —
  decide before switching: keep the App Platform app on a subdomain and
  repoint the links, or have the notices rebuilt here at the same paths.
- **Any other URL the old site had.** Capture the list first:

      curl -s https://greensparksolutions.com/sitemap.xml | grep -o "<loc>[^<]*" | head -60

## 0. Pre-flight

    df -h /                         # was 88.8% full; needs ~300MB free
    ss -ltn | grep ':8000'          # must be empty
    ls /etc/letsencrypt/live/       # no apex certificate yet; step 8 fixes that

If disk is tight:

    apt clean && journalctl --vacuum-time=7d && df -h /

In the Cloudflare dashboard, note the current apex and `www` DNS records
before you change anything, and check **SSL/TLS → Overview** for the
encryption mode. `Full` or `Full (strict)` is what `ics.` already relies on.

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

The HSTS values are deliberately timid for a first deploy: HSTS cannot be
withdrawn early, so a browser told "HTTPS only for a year" means it. Start at
300 seconds and raise it in step 12. Leave `DJANGO_EMAIL_HOST` empty for now —
enquiries are still saved and listed in the console, just not emailed.

The file holds the secret key:

    chown root:gssl /etc/gssl/gssl.env && chmod 640 /etc/gssl/gssl.env

## 6. Install, check, migrate, collect static

    sudo -u gssl /srv/gssl/app/gssl_site/deploy/release.sh

It installs requirements, runs `check --deploy` refusing on any warning,
migrates — seeding the site map, six programmes, seven projects and the home
page content — and writes the static files. It stops at the first failure, so
a broken release never reaches the reload.

## 7. The first console account

    cd /srv/gssl/app/gssl_site
    sudo -u gssl DJANGO_ENV_FILE=/etc/gssl/gssl.env \
      DJANGO_SETTINGS_MODULE=config.settings.prod \
      /srv/gssl/venv/bin/python manage.py createsuperuser

A superuser ranks as an administrator in the console. Accounts made later
start read-only until given a group, so adding staff never hands out write
access by accident.

## 8. Start it, and get a certificate

    cp /srv/gssl/app/gssl_site/deploy/gssl.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable --now gssl
    systemctl status gssl --no-pager

    cp /srv/gssl/app/gssl_site/deploy/nginx.conf /etc/nginx/sites-available/gssl
    ln -s /etc/nginx/sites-available/gssl /etc/nginx/sites-enabled/gssl

Unlink the dead apex site, or it and this one both claim
`server_name greensparksolutions.com` and nginx keeps whichever it loads
first. On this droplet it is `website` -- confirm before removing, and
leave `admin` (port 3001) and `ics` alone:

    grep -l 'localhost:3000' /etc/nginx/sites-enabled/*
    rm /etc/nginx/sites-enabled/website

The shipped nginx file expects `/etc/letsencrypt/live/greensparksolutions.com/`,
which does not exist yet, so `nginx -t` will fail until you have a
certificate. Two ways to get one, since certbot's usual HTTP challenge cannot
work while Cloudflare still sends the apex to App Platform:

**Option A — Cloudflare Origin Certificate (no DNS change, works today).**
In Cloudflare: **SSL/TLS → Origin Server → Create Certificate**, covering
`greensparksolutions.com` and `*.greensparksolutions.com`. Save the two PEMs
on the droplet and point the config at them:

    mkdir -p /etc/ssl/cloudflare && nano /etc/ssl/cloudflare/gssl.pem      # certificate
    nano /etc/ssl/cloudflare/gssl.key                                      # private key
    chmod 600 /etc/ssl/cloudflare/gssl.key
    nano /etc/nginx/sites-available/gssl     # ssl_certificate / ssl_certificate_key

Valid for 15 years, trusted by Cloudflare only — fine, because only Cloudflare
ever connects to the origin. Requires Cloudflare's mode to be Full or
Full (strict).

**Option B — Let's Encrypt via DNS-01.** Needs a Cloudflare API token:

    apt install -y python3-certbot-dns-cloudflare
    printf 'dns_cloudflare_api_token = YOUR_TOKEN\n' > /root/.cf.ini && chmod 600 /root/.cf.ini
    certbot certonly --dns-cloudflare --dns-cloudflare-credentials /root/.cf.ini \
      -d greensparksolutions.com -d www.greensparksolutions.com

Then:

    nginx -t && systemctl reload nginx

## 9. Test against the real hostname, before any visitor sees it

This is the step the setup makes possible. The apex still points at App
Platform, so the droplet can be exercised in full with nothing at risk.

From the server:

    curl -sI -H 'Host: greensparksolutions.com' http://127.0.0.1:8000/ | head -3

A 301 to https is correct — that is `SECURE_SSL_REDIRECT` working.

    curl -skI -H 'Host: greensparksolutions.com' https://170.64.218.194/ | head -6
    curl -sk  -H 'Host: greensparksolutions.com' https://170.64.218.194/sitemap.xml | head -5

From your own machine, add a hosts entry and browse the site properly — home
page, a project page, the enquiry form, and the console at `/office/`. On
Windows, as administrator, add to `C:\Windows\System32\drivers\etc\hosts`:

    170.64.218.194  greensparksolutions.com

Remove that line when you are done testing, or your machine will keep using
the droplet after the cutover regardless of DNS.

## 10. Real visitor addresses — do this before going live

The enquiry form throttles per visitor, and it reads the **last** entry of
`X-Forwarded-For`, which is correct when one trusted nginx sits in front. With
Cloudflare added, nginx appends Cloudflare's edge address, so that last entry
becomes the edge — and every visitor through one Cloudflare node shares a
single throttle bucket. Five genuine enquiries would then lock out everyone
routed through it.

Fix it in nginx, so `REMOTE_ADDR` is the real client and the app's logic stays
right:

    { curl -s https://www.cloudflare.com/ips-v4; curl -s https://www.cloudflare.com/ips-v6; } \
      | sed 's/^/set_real_ip_from /; s/$/;/' > /etc/nginx/conf.d/cloudflare-realip.conf
    printf 'real_ip_header CF-Connecting-IP;\nreal_ip_recursive on;\n' >> /etc/nginx/conf.d/cloudflare-realip.conf
    nginx -t && systemctl reload nginx

Those ranges change occasionally; re-run it once or twice a year.

## 11. The cutover — in Cloudflare, not on the droplet

In the Cloudflare dashboard, **DNS → Records**: change the apex `A` record
(and `www`) to `170.64.218.194`. Keep the orange cloud on, so Cloudflare keeps
terminating TLS and the origin certificate from step 8 is what it talks to.
Leave the App Platform app running.

Then watch it:

    curl -sI https://greensparksolutions.com/ | head -6
    curl -sI https://www.greensparksolutions.com/ | head -3     # 301 to the bare domain
    curl -sI https://admin.greensparksolutions.com/ | head -3   # untouched
    curl -sI https://ics.greensparksolutions.com/ | head -3     # untouched
    journalctl -u gssl -f

`x-powered-by: Next.js` disappearing from the apex response is how you know
the switch has taken effect.

### Rollback

Put the apex and `www` records back to what step 0 recorded. The App Platform
app never stopped, so it starts serving again as soon as DNS propagates —
seconds, with Cloudflare's proxy on. Nothing on the droplet needs touching.

## 12. Once it is confirmed good

Raise HSTS, and turn on subdomain coverage only when you are sure `admin.`
and `ics.` will always be HTTPS:

    nano /etc/gssl/gssl.env     # DJANGO_HSTS_SECONDS=31536000, INCLUDE_SUBDOMAINS=1
    systemctl restart gssl

Fill in the mail settings so enquiries are emailed as well as stored:

    nano /etc/gssl/gssl.env     # DJANGO_EMAIL_HOST and friends
    systemctl restart gssl

Then decide what happens to the App Platform app. While it runs it is your
rollback; once you are sure, retiring it saves its monthly cost — but move the
consultation notices first if they have not been rebuilt here.

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
