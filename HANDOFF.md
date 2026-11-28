# Green Spark — where this stands, 28 November 2026

A pasteable brief for picking this up: what is live, how to deploy, what is
broken, and what to do next. `CMS-PLAN.md` is the phase plan; `AI-HANDOFF.md`
is the original project brief (site conventions, traps, the design build).
This file is the operational state on top of them.

## The repository

    github.com/Rabbi-2529/greenspark        PUBLIC -- check before committing anything
    branch: claude/loving-hopper-gc5fhq     the Django site; HEAD 07c58b6
    branch: main                            the frozen static design build only

`green-spark-website/` is that frozen build and is never edited. `gssl_site/`
is the Django project. Pushes go to the `rabbi` remote, not `origin`: the
stored credential is `Rabbi-2529`, which has no write access to the original
`Deep-RB/Green-Spark-Solutions-LTD-Main-site`.

## Setting up on a new machine

Python 3.12 or newer. Nothing else is needed: development settings have
working defaults, there is no .env to create, and `migrate` builds the
database complete with every page, programme, project and the home page
content, because the seed data lives in the migrations.

    git clone https://github.com/Rabbi-2529/greenspark.git
    cd greenspark
    git checkout claude/loving-hopper-gc5fhq
    cd gssl_site
    python -m venv .venv

Then, on Windows:

    .venv\Scripts\pip install -r requirements.txt
    .venv\Scripts\python manage.py migrate
    .venv\Scripts\python manage.py runserver

or on macOS and Linux:

    .venv/bin/pip install -r requirements.txt
    .venv/bin/python manage.py migrate
    .venv/bin/python manage.py runserver

`manage.py` defaults to `config.settings.dev`, so no environment variable
is needed. The site is then on http://localhost:8000 and the console on
http://localhost:8000/office/ — `manage.py createsuperuser` gives you an
account, which ranks as an administrator there.

Install the requirements file rather than `pip install Django`: Django is
pinned to `>=5.2,<6.0` and a bare install picks up 6.x, which this is not
tested against.

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

    python manage.py test                       # 360 tests
    python manage.py snapshot_pages --check     # 26 pages, byte for byte
    python tools/check_static_refs.py           # 263 static references
    python manage.py makemigrations --check --dry-run

**The golden-HTML harness is the thing that makes this safe.** It records every
published page to `apps/website/golden/` and compares later renders byte for
byte. It has caught four silent regressions that would have changed the live
site: a grid card with a shorter summary than its project, a card pointing at
a 1600px photo that does not exist, `data-programme` rendering a label where
the CSS expected a key, and a privacy-policy date whose field default was the
string `"2026-11-25"` rather than a `date`, which rendered
`<time datetime=""></time>` on a page nobody would have reread. Re-record it
(`snapshot_pages`, no `--check`) **only** when you have deliberately changed
the markup, and say in the commit what the diff was and how you confirmed
nothing else moved.

Also confirm the migrations replay from nothing, because the seed data lives in
them and a migration that only works against the current database is a broken
install waiting to happen:

    DJANGO_DB_PATH=/tmp/replay.sqlite3 python manage.py migrate
    DJANGO_DB_PATH=/tmp/replay.sqlite3 python manage.py snapshot_pages --check

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
| 2 Site map, hideable sections, settings | mostly built. `SiteSettings` / `ContactDetails` / `SocialLinks` / `NoticeBar` exist but only `show_topbar` is wired into a template; the rest of the chrome still reads literals. **`Page.title` and `Page.meta_description` are editable in the console and no template reads them** — see below |
| 3 Programmes and Projects | built |
| 4 Home page and impact data | done |
| 5 About, Why GSSL, Team, FAQ, Careers, Privacy | **done** |
| 6–10 | not started — **Phase 6 (Events and Gallery) is where to pick up** |

### Phase 4, precisely where it stops

Built: `ApproachItem`, `Counter`, `District`; both approach bands on the home
page read from the database; console modules for all three; impact figures
carry an "as of" date and an approval flag and are seeded **unapproved**,
because the design build's README lists every one as sample data awaiting
Green Spark's sign-off.

The impact figures and the district list are now database-driven too, on both
the home page and the cookstove page, which share them through
`ImpactBandMixin`. Only approved figures are listed, so the band ships
showing none. Proving that was awkward, because both bands are hidden and the
golden harness therefore cannot see them: the band was switched on and every
figure approved in a scratch database, both pages recorded, the templates
rewired, and the pages re-rendered under the same conditions — byte for byte
identical — then the database put back as it ships. Do the same for anything
else that lives inside a hidden section.

The hero is a `HomePage` singleton: headline, welcome line, lead, button and
scroll labels, the hidden `<h1>`, and the video. One `video_name` drives all
six files and the two preload hints in `<head>`. The hero band is visible, so
the golden harness proves it directly.

The home page project carousel is `CarouselSlide`, with its badges and its three
facts as inline rows. It is not the Projects grid filtered: five of the seven
projects, in a chosen order, with shorter copy, facts picked per card, and one
card pointing at a programme. The slide number, the active flag and the Gold
Standard registry link are all derived, and a card saved before its target is
chosen renders without a link rather than taking the home page down with a
`NoReverseMatch`.

Not built:

- The Bangladesh map SVG hard-codes its ten active districts as
  `class="bd-map__district is-active"`. The list is dynamic now; the map is
  not, so a district added in the console will not light up on it.

### Phase 5, precisely where it stops

Built: the About, Why GSSL, Team, FAQ, Careers and Privacy pages all read from
the database, sixteen new models, sixteen console modules, and the cookstove
programme page's FAQ band as well. All 26 pages are still byte-identical and
nothing was re-recorded.

Two pieces of shared machinery came first, because they did not exist:

- **`apps/content/icons.py`** — the site's 35 icons as named pairs of SVG paths
  (a stroke and its "echo"), keyed by the design build's own names. A content
  row stores the name; the template asks it for `icon_path` / `icon_echo`. An
  unknown name draws nothing rather than an empty `<svg>`. A test walks every
  template and fails if it finds an icon the library cannot draw, so adding a
  new icon to a template means adding it here too.
- **`apps/content/richtext.py`** — the ten tags an editor may type, checked when
  the record is saved. This is the question Phase 4 deferred, answered as
  narrowly as the privacy policy and the FAQ answers allowed. Internal links
  are stored as `href="route:enquire"` and resolved through `reverse()` at
  render time, so routes stay in code and a link to a page that has moved
  degrades to its own words rather than raising `NoReverseMatch`. It also
  unblocks the home page's intro `<mark>`, which Phase 4 left open — not done,
  because the home page is Phase 4's.

Read `CMS-PLAN.md` §6 Phase 5 before changing any of it. The short version of
what is **derived and must stay derived**: the FAQ accordion's `faq-0`…`faq-19`
ids run across all five topics, not within each one, and the aria wiring breaks
silently for screen-reader users if they stop agreeing; the FAQ topic nav and
the privacy policy's table of contents are rendered from the same rows as the
headings; Why GSSL's six cards stagger per row of three (`{% cycle %}`, not
`forloop.counter0`) while the single-column bands count up the list;
`process--4` is the step count driving a CSS grid; a team leader's initials come
from the name.

Not built:

- **A page's browser title and search description do nothing.** `Page.title`,
  `Page.meta_description` and `Page.og_image` are seeded and editable under
  Pages in the console, and no site template reads them — all 25 pages pass
  literals to `partials/page_meta.html`. This is the most misleading thing in
  the console today and it is Phase 2's remaining work; it touches all 25
  templates at once, which is why it was not done mid-phase.
- **The cookstove page's `benefits` loop**, which Phase 5's scope listed. It
  sits beside `programme-attributes` and `process-steps`, both still literal
  because no programme template reads the Phase 3 models yet. That page wants
  one pass, not a sliver.
- **Photographs are still template literals.** A photo-name field would be one
  typo away from a 500 under hashed static files, which is a latent risk
  `HomePage.video_name` already carries. Photographs need the plan's
  `MediaImage` model.
- **An editor who may see a list but not edit it gets a 403 on clicking a row**
  rather than a read-only view — true since Phase 1 for the impact figures and
  the settings records, and now for the privacy policy too. Two tests document
  it; Phase 9 owns the fix.

## Conventions worth knowing before you touch anything

- **Routes stay in code.** `apps/website/pages.py` is the route map; only
  content moved to the database. A URLconf is built once at startup, so
  DB-driven routes break a fresh install before `migrate` and need a restart
  after every edit. This is a deliberate deviation from the plan.
- **An unknown section key means visible.** `SectionVisibility.__missing__`
  returns `True`. Wiping the table shows too much, which is recoverable;
  showing nothing is not. There is a test documenting the trade-off.
- **Strict CSP.** No inline styles, no inline scripts, no `on*=` handlers, no
  third-party loads — in the console as well as the site. Tests enforce it. A
  content field is not a way round it: the rich-text whitelist refuses `style=`
  and every `on*` attribute, and there are tests that a policy section and an
  FAQ answer cannot put either on a page.
- **Anything derivable from row order is derived in the template, never
  stored** — card numbers, "first one open" flags, reveal delays, "3 of 5"
  labels, accordion ids, step counts, a contents list. Reordering in the
  console cannot then put two things out of step. Phases 4 and 5 both lean on
  this; `CMS-PLAN.md` lists each case.
- **A view reads a singleton with `Model.objects.filter(pk=1).first() or
  Model()`**, never `load()`, so rendering a page cannot write a row. The
  field defaults carry the wording the template had, which is why most page
  singletons are not seeded at all.
- **Seed data lives in migrations, never in fixtures.** Phase 5's seed
  migrations were written by generators that read the templates and refuse to
  write a file unless reassembling the content gives back the markup byte for
  byte. That is how the curly apostrophe in “the community’s needs” and the
  `&amp;` inside a Gold Standard registry URL survived intact. Worth copying
  for any phase with more than a paragraph or two to move.
- **Invented content is never LIVE.** The news pages, the two event detail
  pages and the feedback page still carry the design build's sample content.
  `event_detail` and `event_feedback_round` are UNLISTED: reachable for review,
  linked from nothing, not indexed. A test asserts none of them is LIVE.
- **Pages have three states**, in `pages.py`: LIVE, UNLISTED (routed, noindex,
  out of the sitemap), OFFLINE (404, template kept).
