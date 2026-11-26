# Green Spark — where this stands, 26 November 2026

A pasteable brief for picking this up: what is live, how to deploy, what is
broken, and what to do next. `CMS-PLAN.md` is the phase plan; `AI-HANDOFF.md`
is the original project brief (site conventions, traps, the design build).
This file is the operational state on top of them.

## The repository

    github.com/Rabbi-2529/greenspark        PUBLIC -- check before committing anything
    branch: claude/loving-hopper-gc5fhq     the Django site; HEAD 40f0fe2
    branch: main                            the frozen static design build only

`green-spark-website/` is that frozen build and is never edited. `gssl_site/`
is the Django project. Pushes go to the `rabbi` remote, not `origin`: the
stored credential is `Rabbi-2529`, which has no write access to the original
`Deep-RB/Green-Spark-Solutions-LTD-Main-site`.

## The server

One DigitalOcean droplet, `170.64.218.194`, hostname `green-ics`, Ubuntu
24.04, root login over SSH. It serves three things:

| Host | What | Where |
|---|---|---|
| `greensparksolutions.com`, `www.` | **this Django site** | `/srv/gssl/app`, gunicorn on `127.0.0.1:8000` |
| `admin.greensparksolutions.com` | a Next.js app on `:3001` | `/var/www/admin`, pm2 under user `am` |
| `ics.greensparksolutions.com` | another Django app | `/home/am/code`, gunicorn over a unix socket |

`/var/www/website` holds the **old** main site's source (the Next.js app that
used to serve the apex from DigitalOcean App Platform). Disk was 86% full
after a journal vacuum; keep an eye on it.

### Layout this site expects

    /srv/gssl/app           the checkout
    /srv/gssl/venv          the virtualenv
    /srv/gssl/data          db.sqlite3 -- the only thing not in git
    /srv/gssl/static        collectstatic output, served by nginx
    /etc/gssl/gssl.env      the environment file, root:gssl, mode 640
    /etc/systemd/system/gssl.service
    /etc/nginx/sites-available/gssl

`deploy/RUNBOOK.md` is the full first-time setup. `deploy/DNS-INVENTORY.md`
records the DNS zone as it was before it moved.

## Deploying a change

Three commands, every time:

    sudo -u gssl git -C /srv/gssl/app pull
    sudo -u gssl /srv/gssl/app/gssl_site/deploy/release.sh
    systemctl reload gssl

`release.sh` installs requirements, runs `check --deploy` refusing on any
warning, migrates, and runs collectstatic. It stops at the first failure, so a
broken release never reaches the reload. **A CSS or template change still needs
`release.sh`**, not just the reload: static files are hashed and have to be
re-collected.

Rolling back is `git -C /srv/gssl/app checkout <sha>` then the same two
commands. Migrations are not reversed by that, so check whether the commit
added one.

## Verifying before you push

Run all four from `gssl_site/` with the venv's python. They are the contract:

    python manage.py test                       # 200 tests
    python manage.py snapshot_pages --check     # 26 pages, byte for byte
    python tools/check_static_refs.py           # 263 static references
    python manage.py makemigrations --check --dry-run

**The golden-HTML harness is the thing that makes this safe.** It records every
published page to `apps/website/golden/` and compares later renders byte for
byte. It has caught three silent regressions that would have changed the live
site: a grid card with a shorter summary than its project, a card pointing at
a 1600px photo that does not exist, and `data-programme` rendering a label
where the CSS expected a key. Re-record it (`snapshot_pages`, no `--check`)
**only** when you have deliberately changed the markup, and say in the commit
what the diff was and how you confirmed nothing else moved.

## Broken right now, in priority order

1. **Email is down.** The zone moved from Cloudflare to Namecheap BasicDNS on
   26 November and the Google Workspace MX records were never recreated.
   Nothing is bouncing yet -- senders defer and retry for days -- but
   `info@greensparksolutions.com` is not receiving. Fix: Namecheap → Advanced
   DNS → **MAIL SETTINGS** (a separate section below HOST RECORDS) → **Gmail**.
   Then the three apex TXT records from `deploy/DNS-INVENTORY.md`: the SPF line
   and both `google-*-verification` values.
2. **The site serves a self-signed certificate.** Every visitor sees a security
   warning. certbot has never run. The nginx config now serves
   `/.well-known/acme-challenge/` from `/var/www/certbot` ahead of the HTTPS
   redirect, so:

       certbot certonly --webroot -w /var/www/certbot \
         -d greensparksolutions.com -d www.greensparksolutions.com

   then point `/etc/nginx/sites-available/gssl` at
   `/etc/letsencrypt/live/greensparksolutions.com/` and reload nginx. Raise
   `DJANGO_HSTS_SECONDS` from 300 to 31536000 in `/etc/gssl/gssl.env` once it
   holds.
3. **`admin.` is down and has been for a long time.** `/var/www/admin/.next`
   does not exist, so `next start` exits immediately and pm2 has restarted it
   500+ times; nginx answers 502. Fix: `cd /var/www/admin && sudo -u am npm
   install && sudo -u am npm run build && sudo -u am pm2 restart admin`. Check
   for a missing `.env` if the build fails. Nothing to do with this site.
4. **Three Gold Standard consultation notices 404.** The events page links to
   `/events/green-ics-bangladesh`, `-part-two` and `-part-three`. They were on
   the old site; the apex now points here and we do not have their text. Each
   path currently 302s to the events listing so they are not dead ends. They
   are public compliance records, so they need the **real** wording, which is
   most likely in `/var/www/website` on the droplet, or on the App Platform app
   (still running, reachable by its own `*.ondigitalocean.app` hostname from
   the DigitalOcean panel). Do not write replacements.

## Where the CMS phases stand

Phases are in `CMS-PLAN.md`, which carries the detail and the decisions taken
against the plan.

| Phase | State |
|---|---|
| 0 Foundations | done |
| 1 The console shell | built, except the vendored widgets (Select2, DataTables, FullCalendar, SortableJS, a rich-text editor still need downloading into `static/console/vendor/`) |
| 2 Site map, hideable sections, settings | mostly built. `SiteSettings` / `ContactDetails` / `SocialLinks` / `NoticeBar` exist but only `show_topbar` is wired into a template; the rest of the chrome still reads literals |
| 3 Programmes and Projects | built |
| 4 Home page and impact data | **started — this is where to pick up** |
| 5–10 | not started |

### Phase 4, precisely where it stops

Built: `ApproachItem`, `Counter`, `District`; both approach bands on the home
page read from the database; console modules for all three; impact figures
carry an "as of" date and an approval flag and are seeded **unapproved**,
because the design build's README lists every one as sample data awaiting
Green Spark's sign-off.

Not built:

- The `impact-counters` and `areas` loops in `home.html` and
  `programme_improved_cookstove.html` are still hand-written markup. The models
  and the view context exist; the templates were never switched over, so
  editing a counter in the console changes nothing. Both bands sit inside
  hidden sections, so nothing on the live site is stale.
- A gotcha found while starting this: the Bangladesh map SVG hard-codes its ten
  active districts as `class="bd-map__district is-active"`. Making the district
  list dynamic will not light up the map without more work.
- `HeroSlide` and the `HomePage` singleton — hero wording, the video, section
  headings. The hero copy and its CSS have been hand-edited twice at Green
  Spark's request this week, which is the argument for building this next.
- The home page project carousel, carried over from Phase 3. It is a different
  component from the Projects grid: `fcard` markup, five of the seven projects,
  slide indices in `aria-label="1 of 5"`.

## Conventions worth knowing before you touch anything

- **Routes stay in code.** `apps/website/pages.py` is the route map; only
  content moved to the database. A URLconf is built once at startup, so
  DB-driven routes break a fresh install before `migrate` and need a restart
  after every edit. This is a deliberate deviation from the plan.
- **An unknown section key means visible.** `SectionVisibility.__missing__`
  returns `True`. Wiping the table shows too much, which is recoverable;
  showing nothing is not. There is a test documenting the trade-off.
- **Strict CSP.** No inline styles, no inline scripts, no `on*=` handlers, no
  third-party loads — in the console as well as the site. Tests enforce it.
- **Invented content is never LIVE.** The news pages, the two event detail
  pages and the feedback page still carry the design build's sample content.
  `event_detail` and `event_feedback_round` are UNLISTED: reachable for review,
  linked from nothing, not indexed. A test asserts none of them is LIVE.
- **Pages have three states**, in `pages.py`: LIVE, UNLISTED (routed, noindex,
  out of the sitemap), OFFLINE (404, template kept).
