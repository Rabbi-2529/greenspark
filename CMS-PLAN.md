# Green Spark website — plan to make it fully dynamic

**Goal.** Every word, number, photo and video on the public site becomes editable
by Green Spark staff through an admin panel of our own, built in the site's own
theme. The public site must not change: same markup, same CSS, same JS, same
rendered HTML.

**Stack.** Python + Django 5.2 LTS + SQLite3 (already in place), Pillow for image
renditions. No new runtime services. No CDN.

---

## 1. What "without changing the frontend" means here

Making content dynamic means editing templates — there is no way around that.
What must not change is the **output**. So the rule for every phase is:

> Literal text and literal markup in a template may be replaced by a variable
> or a `{% for %}` over the same shape. Nothing else may change: no new
> classes, no restructured elements, no reordered attributes, no new wrappers.

This is enforced mechanically, not by eye — see Phase 0's parity harness. If a
phase changes one byte of rendered HTML that was not meant to change, CI fails.

The design build in `green-spark-website/` stays **frozen**. It is the reference
for what the output must look like.

---

## 2. What is hardcoded today

| Where | Size | What is in it |
|---|---|---|
| `apps/website/pages.py` | 104 lines | The site map: 22 pages, route, template, nav key, LIVE/UNLISTED/OFFLINE |
| `apps/website/content.py` | 239 lines | 7 projects as frozen dataclasses, 2 programmes, badge classes |
| `templates/` | 41 files, 703 KB | All page copy, headings, stats, FAQ, team, events, gallery, footer, contact details |
| `static/img/photos/` | 133 files | Every photo, pre-rendered at 480/600/960/1600 in jpg + webp |
| `static/video/` | 31 files | Hero videos (wide + tall, WebM + MP4) and section clips |
| `apps/website/models.py` | 54 lines | `Enquiry` only — the single existing model |
| `apps/website/admin.py` | 33 lines | One `django.contrib.admin` ModelAdmin for enquiries |

The design build already did the hard part of the analysis for us: every
repeatable block in the templates is wrapped in `<!-- loop:start NAME -->` /
`<!-- loop:end NAME -->`, and `green-spark-website/README.md` §7–§8 is a CMS
field map naming the fields each one needs. There are **35 distinct loops**
across 20 templates. That inventory is the content model, and it is reproduced
in §4 below.

---

## 3. Architecture

Three apps instead of one, so the public site stays thin and the panel stays
generic:

```
apps/website/     The public site. Views, URLs, templates, the Enquiry model.
                  Loses pages.py and content.py; gains nothing else.
apps/content/     The CMS. All content models, split into modules:
                    models/site.py       settings, contact, social, notice bar, pages
                    models/programmes.py programmes and their attributes/steps
                    models/projects.py   projects, paragraphs, attributes, gallery
                    models/home.py       hero slides, highlights, counters, districts
                    models/editorial.py  posts, events, albums, FAQ, team, careers
                    models/media.py      MediaImage / MediaVideo + renditions
                    models/audit.py      revisions, audit log
apps/console/     The custom admin panel. Own URLs, own auth views, own
                  templates and CSS, own CRUD framework. Mounted at /office/.
```

`django.contrib.admin` stays available as a safety net until the panel reaches
parity, then comes out of `INSTALLED_APPS` in Phase 10.

**Panel URL.** `CONSOLE_URL` env var, default `office/`, same pattern as the
existing `DJANGO_ADMIN_URL`. The CSP middleware must learn this prefix.

---

## 4. Content model inventory

Every loop marker in the templates, mapped to the model that will feed it.
Singletons are one-row models edited as a single form, not a list.

### Singletons

| Model | Feeds | Fields |
|---|---|---|
| `SiteSettings` | base, meta | site name, default OG image, Meet GSSL video + poster, ABN |
| `ContactDetails` | topbar, footer, enquire | AU address + map link, BD address + map link, WhatsApp/phone, email, hours per office with time zone |
| `SocialLinks` | topbar, footer | facebook, youtube, linkedin, whatsapp, x — empty value hides the icon |
| `NoticeBar` | notice bar | text, link, window start/end, active |
| `HomePage` | `home.html` | hero title/subtitle/buttons, hero video (wide + tall, WebM + MP4), intro eyebrow/heading/body, every section heading and eyebrow |
| `AboutPage` | `about.html` | vision block, approach block, careers intro and empty-state text |
| `WhyGsslPage` | `why_gssl.html` | intro, lead copy |
| `EnquirePage` | `enquire.html` | intro copy, thank-you copy, enquiry type and subject choices |
| `PrivacyPage` | `privacy.html` | rich text body, retention periods, last-updated date |

### Collections

| Loop marker(s) | Model | Key fields |
|---|---|---|
| `programmes`, `other-programmes` | `Programme` | title, slug, stage, stage_step (Concept/Feasibility/Pilot/Active), summary, body, icon, image, priority, sort_order, show_on_website, animation strip + card |
| `programme-attributes` | `ProgrammeAttribute` | programme FK, icon, title, text, sort_order |
| `process-steps` | `ProgrammeStep` | programme FK, title, text, sort_order |
| `projects`, `related-projects` | `Project` | slug, title, summary, location, stage, programme FK, gs_id, standard, proponent, status_label, status_note, card_badge, stove_detail, hero image, sort_order |
| `project-description` | `ProjectParagraph` | project FK, body, sort_order |
| `project-attributes` | `ProjectAttribute` | project FK, icon, title, details |
| `project-gallery` | `ProjectImage` | project FK, image, alt, caption, sort_order |
| — (filter chips) | `ProjectTag` | slug, label, badge class |
| `impact-counters` | `Counter` | label, value, suffix, as_of date, note, published, sort_order |
| `areas` | `District` | division, name, highlighted, is_base, sort_order |
| `approach-highlights`, `approach-attributes` | `ApproachItem` | kind (highlight/attribute), icon, title, text, sort_order |
| `vision-attributes` | `VisionAttribute` | icon, title, text, sort_order |
| `audiences`, `why-audiences` | `Audience` | scope, icon, title, text, sort_order |
| `benefits` | `Benefit` | programme FK, icon, title, text, sort_order |
| `why-reasons`, `why-steps` | `WhyItem` | kind, icon, title, text, sort_order |
| `faq`, `faq-groups` | `FaqGroup` + `FaqItem` | group title, question, answer, programme FK (nullable), sort_order |
| `team-leaders`, `team-groups` | `TeamLeader`, `TeamGroup` + `TeamMember` | name, role, photo, bio, group, sort_order |
| `career-areas`, `job-openings` | `CareerArea`, `JobOpening` | title, location, type, summary, closing date, apply link/email, published |
| `events`, `related-events` | `Event` | type, title, slug, start/end, venue, district, language, organiser, feedback window, summary, body, documents, status |
| `agenda` | `EventAgendaItem` | event FK, time, title, text, sort_order |
| `participation`, `feedback-steps` | `EventStep` | event FK, kind, title, text, sort_order |
| `albums` | `Album` | title, slug, summary, cover image, published, sort_order |
| `gallery-images` | `AlbumImage` | album FK, image, alt, caption, sort_order |
| `posts`, `latest-posts`, `related-posts` | `Post` + `PostCategory` | title, slug, category, excerpt, cover, body, author, published_at, reading time, featured, published |
| hero | `HeroSlide` | image, video (wide + tall), headline, text, button label + link, alt, active, sort_order |

### Infrastructure models

| Model | Purpose |
|---|---|
| `Page` | Replaces `pages.py`. name, route, template, nav key, status (LIVE/UNLISTED/OFFLINE), `<title>`, meta description, canonical override. URLs and `sitemap.xml` build from this. |
| `MediaImage` | One upload, many renditions. Stores the original and the generated 480/600/960/1600 jpg + webp set, with alt text and credit. |
| `MediaVideo` | MP4 + WebM pair with a poster frame. |
| `Revision` | A JSON snapshot per save, per object, with author and timestamp. Restorable. |
| `AuditEntry` | Who changed what, when, and the field-level diff. |
| `Feedback` | The feedback form the design build never wired up: event FK, stakeholder type, name, organisation, contact, message, attachment, consent, reference, status, reply. |
| `Enquiry` | Already exists. Moves from `django.contrib.admin` into the panel. |

Roughly **38 models**. Most are small ordered lists of `icon / title / text`,
which is why the panel needs one good generic inline editor rather than 38
bespoke screens.

---

## 5. The parity harness (the thing that makes this safe)

Before any model exists:

1. `manage.py snapshot_pages` renders every published page plus all 7 project
   pages and writes them to `apps/website/tests/golden/<name>.html`.
2. A new test renders the same pages and asserts byte-equality with the golden
   file, after masking the CSRF token and any nonce.
3. The goldens are committed. They are the contract.

From then on, every phase follows the same loop: move content into the database,
seed it from the values that were in the template, re-run the tests. A diff in
the golden comparison means the migration was lossy — fix it, do not update the
golden. The golden file changes only when Green Spark asks for a content change,
and then the diff in the pull request shows exactly what visitors will see
differently.

This also protects the 58 tests already in `apps/website/tests.py`, which check
nav state, CSP safety, unique titles, sitemap membership, offline pages and the
Gold Standard claims. They keep running unchanged.

---

## 6. Phases

Each phase ends with: migrations applied, content seeded, 58 + N tests green,
golden HTML unchanged, `check_static_refs.py` clean.

### Phase 0 — Foundations

- Create the venv, install requirements, run the existing 58 tests, confirm green.
- Add Pillow to `requirements.txt`.
- Build the parity harness above.
- Create `apps/content` and `apps/console` skeletons; wire `INSTALLED_APPS`,
  `CONSOLE_URL`, and teach `SecurityHeadersMiddleware` the panel prefix.
- Serve `MEDIA_URL` in dev; add the `location /media/` block to `deploy/nginx.conf`
  with the same cache headers static gets.
- Image pipeline: `MediaImage` + a Pillow renditions service that turns one
  upload into the exact `-480/-600/-960/-1600` x `jpg`/`webp` set the templates
  expect, plus a `manage.py import_static_photos` that ingests the 133 existing
  photos so nothing is orphaned when templates switch over.
- Extend `check_static_refs.py` to also prove every media reference resolves.

### Phase 1 — The admin panel shell — **built, except the vendored widgets**

Done and tested (79 console tests; `apps/console/`, `templates/console/`,
`static/console/`). The one piece still open is the vendored UI libraries,
marked below.

The panel, with no content models behind it yet:

- Own auth: login, logout, password change, idle timeout, staff-only access,
  three roles (Editor, Publisher, Administrator). Login is rate-limited and
  never reveals whether an address exists.
- Layout in the site's own theme: sidebar, topbar, breadcrumbs, dashboard.
  Built on `static/css/tokens.css` — the same `--gs-*` palette, Open Sauce Sans,
  leaf green and spark lime — in a new `static/console/css/console.css`. The
  panel looks like the site, not like Django.
- **Still open.** Vendored UI libraries, self-hosted under
  `static/console/vendor/<name>-<version>/` because the CSP is `'self'` only and
  the design build forbids third-party loads: **Select2** for every relation and
  multi-select, **DataTables** in server-side mode for every list, **FullCalendar**
  for the events calendar, **SortableJS** for drag ordering, and one small
  rich-text editor for the few long-form fields.

  This needs the files downloaded and committed, so it waits for a go-ahead.
  Nothing depends on it: every list is already searched, filtered, sorted and
  paginated **on the server**, every select is a real `<select>`, and ordering
  already works by dragging. The libraries are an upgrade on top of screens that
  work without them — which is also why the console still works with JavaScript
  off. `console:data` already answers DataTables' own parameters
  (`draw`, `start`, `length`, `search[value]`, `order[0][column]`), so turning
  the table on is a JavaScript change with no Python behind it.
- A generic CRUD framework: register a model, get a server-side DataTables list
  with search and filters, a themed form, inline formsets with drag ordering, a
  media picker, publish/unpublish, delete with a real confirmation, and an audit
  entry on every write.
- Dashboard: unread enquiries, unpublished drafts, counters past their "as of"
  date, recent changes.

### Phase 2 — Site map, hideable sections and settings — **mostly built**

Done: the parity harness, the `Page` and `Section` models, all 84 section
switches, and the console screens. Still open: the four settings records are
modelled and editable but do not yet feed the templates — see the end of this
section.

- **The parity harness** (Phase 0's, built here because this is the first phase
  that touches a template). 24 golden files under `apps/website/golden/`,
  compared byte for byte by `GoldenHtmlTests`. Verified to have teeth: a
  one-character change fails it and names the page, line and column.
- **`Page`** — title, search description, share image and status, read per
  request. **Routes stay in `apps/website/pages.py`**: a URLconf is built once
  at startup, so reading routes from the database would break a fresh install
  before `migrate` and would not pick up a change without a restart. Routes are
  structure; the wording and the status are content. A page with no row falls
  back to the code map, so the site serves even with an empty table.
- **`Section`** — one row per band of each page, 84 of them, each with the
  wording it carries so staff can tell which is which. Templates wrap each
  `<section>` in `{% if sections.<key> %}`, hard against the markup so a shown
  section renders byte for byte what it did before. **An unknown key means
  shown**, so a typo or a missing row can never silently delete a band.
- **Four bands that were hidden in code** (`{% comment %}` on the home page's
  district map, news and events, and the cookstove page's district map) are now
  switches, off by default, each carrying the reason it is off. Hiding them no
  longer needs a deploy.
- Console screens: Pages, Page sections, Site settings, Contact details, Social
  links, Notice bar. Singleton records open their form directly instead of a
  list with one row in it.

**Still open — the settings records do not feed the site yet.** `SiteSettings`,
`ContactDetails`, `SocialLinks` and `NoticeBar` exist, are seeded with the
values the templates already carry, and can be edited in the console, but the
chrome still reads its own hard-coded copies. Editing them changes nothing on
the site until these are switched over:

- `site_topbar.html` — phone, email, hours
- `social_links.html` — the icon list, driven by which addresses are filled in.
  Note this one legitimately changes the golden files: the partial carries an
  HTML comment (`<!-- twitter: URL empty … -->`) that a dynamic version drops.
- `contact_details.html` and `site_footer.html` — the two office addresses
- `page_meta.html` — title, description and share image from the `Page` row
  (the rows already hold the right values)
- the notice bar, which has no markup on the site yet

### Phase 3 — Programmes and Projects — **built**

- Models: `Programme`, `ProgrammeAttribute`, `ProgrammeStep`, `Project`,
  `ProjectParagraph`, `ProjectAttribute`, `ProjectImage`. The model mirrors the
  frozen dataclass property for property (`filters`, `badge_class`,
  `is_registered`, `programme_label`, `programme_url_name`, `description`), so
  the card and the detail page read the same names and barely moved.
- All 7 rows of `content.py` copied in by migration, paragraphs included, and
  `content.py` deleted. Its data is frozen in `apps/content/seed_projects.py`
  so the migration still replays on an empty database (verified).
- `projects.html`'s hand-written grid is now a loop; `project_detail.html` and
  the related-projects list are database-driven. All 24 pages byte-identical.
- Gold Standard claims stay guarded: `is_registered` is derived from `gs_id`,
  and the model refuses an ID that is not a Gold Standard one.
- Console: Projects (with inline paragraphs, key details and photos) and
  Programmes (with a "show on the site" switch).

**Three things the parity test caught**, each of which would have quietly
changed the live site:

- The rooftop card on the Projects page carried a **shorter summary** than the
  project's own. Stored as `card_summary` and used on the grid only, so the
  card still says what it said.
- `stove-manufacturing` has **no 1600px photo**. The hand-written card knew;
  a shared partial did not, and would have pointed at a missing file.
  `photo_has_large` is set from what is actually on disk.
- `data-programme` is the programme **key**, not its name — the colour hook
  would have broken on every project page.

**Not done:** the six programme templates were *not* collapsed into one
slug-driven view. They differ in structure (rooftop has a platform video and a
steps band, water has steps, the other three have neither), so one template
would be a pile of conditionals for no gain to Green Spark. They stay as six.

**Not done:** the home page's project carousel is still hand-written. It is a
different component from the grid — `fcard` markup, only 5 of the 7 projects,
and slide indices in `aria-label="1 of 5"` — so it needs its own pass.

### Phase 4 — Home page and impact data — **built**

Done:

- Models `ApproachItem`, `Counter` and `District`, seeded from the page's own
  wording, with console screens for each.
- **Both approach bands on the home page are database-driven** and byte-identical:
  the expanding “Why Green Spark” cards and the “A holistic approach” points
  (the band in the screenshot that started this). Neither stores a card number,
  an open/closed flag or a reveal delay — those follow from the order the rows
  are in, so reordering in the console cannot put them out of step. There is a
  test that reorders the cards and checks the open one moves with them.
- Counters carry an “as of” date and an **approval** flag, and all six are
  seeded unapproved, because README §11 lists every one as sample data awaiting
  Green Spark's sign-off. Approving a figure needs the publisher role, not the
  editor role: a number on that page is a claim about impact.

- **The impact figures and the district map are database-driven** on both the
  home page and the cookstove programme page, which share the band through
  `ImpactBandMixin`. Only approved figures are listed, so as shipped the band
  renders no numbers at all — that is the point of the approval flag.
  A figure with no number yet (`is_pending`) is badged “Published once
  measured” rather than animating to zero.

  Both bands are hidden, so the golden harness could not see them and could
  not prove the loops were faithful. Instead the band was switched on and
  every figure approved in a scratch database, both pages recorded, the
  templates rewired, and the pages re-rendered under the same conditions:
  **byte for byte identical**, 213,998 and 214,072 bytes. The database was
  then put back as it ships.

- **The hero is a `HomePage` singleton**: the headline, the welcome line, the
  lead, the button and scroll labels, the hidden `<h1>` and the video. One
  `video_name` drives all six files — `<name>-poster.jpg/.webp`,
  `<name>.webm/.mp4` and the `-mobile` pair — including the two preload hints
  in `<head>`, which would otherwise keep pointing at the old poster and
  fetch a file that is no longer used. The hero band is visible, so the
  golden harness proved this one directly: all 26 pages still match.

  No `HeroSlide`. The plan assumed a slideshow; there is one hero with a
  background video, and a model for slides that never have more than one row
  is a worse thing to hand Green Spark than a form with nine fields on it.

- **The project carousel** is `CarouselSlide`, with its badges and its three
  facts as inline rows. It is not the Projects grid filtered: it shows five of
  the seven, in a chosen order, with shorter copy, facts picked per card
  (“Stoves: 20,000+ installed”, “Visits: Every year”) and one card pointing at
  a programme rather than a project. The slide number, the active flag and the
  Gold Standard registry link are all derived — from row order and from the
  project's own `gs_id` — so reordering cannot put them out of step. A card
  saved before its target is chosen renders without a link rather than taking
  the home page down with a `NoReverseMatch`; there is a test for that.

Still open:
- The intro band below the hero. Its reveal paragraph contains a `<mark>`
  element, so making it editable means first deciding how much HTML an editor
  may type — which is Phase 9's question, not this one's.
- The Bangladesh map SVG hard-codes its ten active districts as
  `class="bd-map__district is-active"`. The district *list* is now dynamic;
  the map's highlighting is not, so a district added in the console appears
  in the list but does not light up on the map.

### Phase 5 — About, Why GSSL, Team, FAQ, Careers, Privacy — **built**

All six pages read from the database, and all 26 pages are still byte-identical
to the golden HTML. Nothing was re-recorded at any point in this phase.

**Two pieces of shared machinery had to come first**, because Phases 3 and 4
never needed them:

- **An icon library** (`apps/content/icons.py`). Four of this phase's loops
  carry an inline SVG icon; the loops Phase 4 wired had none. Every icon on the
  site is one drawing twice — a stroke path and a second, slightly offset
  "echo" path the CSS fades behind it — so an icon is a *pair* of paths. All 35
  used across the site are keyed by the design build's own names (`users`,
  `handshake`, `flask`, …), matched one for one against
  `green-spark-website/assets/img/icons`; the echo paths are not in those files
  and were read off the templates. A content row stores the name and the
  template asks it for `icon_path` / `icon_echo`. An empty or unknown name
  yields empty strings and the icon wrapper drops out, rather than an empty
  `<svg>`. One test walks every template and fails if it finds an icon the
  library cannot draw.

  Not an upload and not a markup field: an icon is part of the design, not part
  of the words, and the same handful recurs across the site — the people icon
  five times, the spanner three — so paths on each row would mean many copies
  of one drawing and a correction that only landed on one of them.

- **A limited-HTML field** (`apps/content/richtext.py`), which answers the
  question Phase 4 deferred. Phase 4 left the home page's intro paragraph in
  the template because it contains a `<mark>`, and called "how much HTML may an
  editor type" a Phase 9 question. Phase 5 could not: a privacy policy is prose
  with emphasis and lists, and six of the twenty FAQ answers contain a link.

  Answered narrowly. A whitelist of ten tags (`a br em li mark ol p span strong
  ul`), checked when the record is saved, so the console names the tag or
  attribute it refused. `span` may carry only `class="visually-hidden"`.
  Rendering re-emits rather than passing through, so content written straight
  into the database still cannot carry a script, a style or an event handler.
  And internal links are route names — `href="route:enquire"` resolves through
  `reverse()` at render time — because routes stay in code here, so an answer
  cannot be left pointing at a page that has moved; a link to a route that has
  gone renders as its own words rather than raising `NoReverseMatch`.

  This also unblocks the home page's intro band, which Phase 4 left open. It
  was not done here, because the home page is Phase 4's and this phase had six
  of its own.

**Models built**: `AboutPage`, `AboutStat`, `VisionAttribute`, `Audience`,
`CareerArea`, `JobOpening`, `WhyGsslPage`, `WhyItem`, `TeamPage`, `TeamLeader`,
`TeamGroup`, `FaqPage`, `FaqGroup`, `FaqItem`, `PrivacyPage`, `PolicySection`.
`ApproachItem` gained an `icon` and a third kind. Sixteen console modules, taking the console to 32.

**What is derived rather than stored.** This is the part worth reading before
changing any of it:

- **The FAQ accordion ids.** Each item carries an `aria-expanded`, an
  `aria-controls`, an `id` and an `aria-labelledby` that must agree, and on the
  FAQ page they run `faq-0` to `faq-19` **across all five topics**, not from
  zero within each one. `number_questions` works the number out from the row's
  position when the page renders, so reordering a topic, reordering a question
  or moving a question between topics renumbers everything after it and the
  aria wiring follows. Stored, that would be an editor's problem and a silent
  one: a mismatched `aria-controls` breaks the accordion only for someone using
  a screen reader. A Django template cannot count across nested loops, so
  `FaqGroup.with_questions()` does it in two queries. Which panel starts open
  is derived the same way — exactly one per page, the first.
- **Both pages' in-page contents lists.** The FAQ topic nav and the privacy
  policy's thirteen-entry table of contents are rendered from the same rows as
  the headings below them, so renaming a section renames its own link. The way
  a policy page actually goes wrong is a heading edited and the link to it left
  behind.
- **Why GSSL's six reason cards stagger per row of three**, not up the whole
  list: the grid is `attr-grid--3`, so the markup is `""`, `d1`, `d2`, `""`,
  `d1`, `d2`. That is a `{% cycle %}`, not `forloop.counter0`, and a test pins
  all six classes. The single-column `attr-list` bands (vision points, areas of
  work, what each partner can expect) do count up the list, which is why they
  use `forloop.counter0` — the two look the same at three rows and diverge at
  four.
- **`process--4`** is not decoration: `flow.css` maps it to `--steps: 4`, the
  number of columns the steps are laid out in. It follows the number of steps
  now. Outside 3–6 the class is undefined and the grid falls back to
  `var(--steps, 6)` — a layout wobble, not a broken page.
- **A team leader's initials.** The circle held `PR` as a literal; it holds the
  initials worked out from `Pankaj Rajbangshi`, so correcting a spelling
  corrects the circle. There is an override field, empty as shipped, for the
  names the rule gets wrong: an honorific first, a mononym, a name that reads
  better with three letters.
- **A role's "Manikganj, Bangladesh · Full time" line**, composed from two
  optional fields and absent when both are empty. The privacy policy's date is
  one field rendered twice, as `datetime="2026-11-25"` and "25 November 2026".

**Deviations from this plan, and why:**

- **No `TeamMember`.** The plan asked for `TeamGroup` + `TeamMember`. There is
  nowhere on the page for a member to go: the teams band is five headed
  paragraphs about how the work is divided, and the design build's markup has
  no list of people under a team anywhere in it. A model for rows nothing
  renders is a worse thing to hand Green Spark than no model. If named staff
  under each team are wanted later, that is a markup decision first.
- **No shared `Audience` scope across two pages.** The plan put About's partner
  grid and Why GSSL's "what each partner can expect" on one model with a
  `scope` field. They share no markup — About's cards carry an icon and a
  different card entirely — so a scope field would have produced one console
  list in which half the rows could not be used on either page. Why GSSL's
  three are a third kind of `WhyItem`; About's six are `Audience`.
- **About's "Our approach" is a third kind of `ApproachItem`**, which *is* what
  the plan asked for and was right: they are the home page's cards said again,
  and the only difference is the icon.
- **The privacy policy is sections, not one body.** The plan asked for one
  rich-text body plus retention fields. Thirteen rows is what makes the
  contents list derivable (above). There is no retention field either: "how
  long we keep it" is one of the thirteen, written as prose, and splitting that
  sentence into a number and a unit would not survive its first reading by a
  lawyer.
- **`AboutStat` is not `Counter`.** The three figures beside "Who we are" — 2
  offices, 3 countries, 2 registered phases — are facts about the company. A
  `Counter` is a claim about impact that a publisher approves and that animates
  up to a number, and it renders in the impact band. Mixing them would have put
  "2 offices" among the impact figures.
- **`Module.fieldsets` now works.** It had been declared and documented in the
  registry since Phase 1 and never read: the only way to group a form's fields
  was a form subclass carrying nothing else. `AboutPage` has twenty fields
  across six bands and five more page singletons arrived in this phase, so the
  registry derives a module's field list from its fieldsets and hands them to
  the generated form. That is what "one good generic editor rather than 38
  bespoke screens" was supposed to mean.

**Careers keeps its empty state, and that is what ships.** `JobOpening` is
seeded empty, so the band shows its "no open roles right now" paragraph and the
two buttons exactly as before — which is the case the golden harness proves.
The design build never drew a role (its `job-openings` loop is empty in the
frozen build too), so the markup for one is new and uses only classes the site
already has; tests cover the populated case, including a role with no location,
no closing date and no way to apply yet, each rendering without an empty
element rather than with one.

**The cookstove page's FAQ came too.** Its six questions are `FaqItem` rows
against the programme — the plan's nullable `programme` FK — found by the route
the programme points at, so the other five programme pages pick theirs up the
same way. They are not a filtered view of the FAQ page's twenty: it asks
several of the same things in shorter words and one thing the FAQ page does not
ask at all. A question may belong to a topic, to a programme or to both; one
with neither is listed in the console as "Not shown anywhere yet" rather than
hidden. The accordion item markup is one partial, included by both pages:
nineteen attributes of interlocking aria wiring, which in two places would
eventually have come apart.

**Still open, in priority order:**

1. **The console can edit a page's browser title and search description, and
   nothing happens.** `Page.title`, `Page.meta_description` and `Page.og_image`
   are seeded, listed and editable under Pages — and no site template reads
   them. All 25 pages pass literals to `partials/page_meta.html`. This is
   Phase 2's remaining work rather than Phase 5's, and it is the most
   misleading thing in the console today: a field that looks editable and is
   not. Fixing it touches all 25 templates at once, which is why it was not
   done in the middle of this phase.
2. **The cookstove page's `benefits` loop**, which this phase's scope listed.
   It sits beside `programme-attributes` and `process-steps`, both still
   literal because no programme template reads the Phase 3 models yet. That
   page wants one coherent pass, not a sliver of one.
3. **Photographs stay in the templates.** Phase 4 made the hero's video a name
   field; under hashed static files a name with no matching file raises rather
   than rendering a broken image, so a photograph field would be one typo away
   from a 500 on that page. Photographs need the `MediaImage` model from §4,
   which is not built. The same latent risk already exists on `HomePage.
   video_name`.
4. **`ContactDetails` is still not wired**, so the WhatsApp number, the email
   address and the postal addresses remain literals — in Why GSSL's hero
   button, in an FAQ answer and in the policy's contact section as well as in
   the chrome. Phase 2's remaining work; doing it on one page only would make
   it worse.
5. **An editor who may see a list but not edit it gets a 403 on clicking a
   row**, rather than a read-only view. True since Phase 1 for the impact
   figures and all four settings records, and now for the privacy policy too.
   Phase 9 owns editorial safety and should fix it there. Two tests document
   the behaviour so the fix is a visible change rather than a surprise.
6. **Two counts are prose an editor has to keep in step**, and their help text
   says so: "Five teams share one way of working" and "Six reasons partners
   work with Green Spark". A number spelled out in a sentence is not derivable
   from a row count without rewriting the sentence.
7. **`about.html`'s "Our approach" section has `aria-labelledby="approach-title"`
   pointing at an id that is not on the page** — its `<h2>` carries no `id`.
   A pre-existing design-build bug, left alone because fixing it changes the
   markup; it belongs in an accessibility pass with the golden files
   re-recorded deliberately.

### Phase 6 — Events and Gallery

- Models: `Event`, `EventAgendaItem`, `EventStep`, `Album`, `AlbumImage`.
- Panel gets the FullCalendar month view for events, with the feedback window
  shown as a band.
- The notice bar becomes automatic: it renders only while an event's feedback
  window is open, as the design build specifies.
- The two event detail pages and the feedback page are OFFLINE today because
  their content is invented. They come back the moment real events are entered —
  status is now a field, not a code change.
- Album photo counts stay honest; the existing test that compares the count to
  the number of photos keeps passing.

### Phase 7 — News & Insights

- Models: `Post`, `PostCategory`.
- The whole section is OFFLINE today (every post is a design-build sample). It
  returns only when a real post is published, and the `Page` status controls it.
- Filter chips become category filters; `latest-posts` on the home page and
  `related-posts` on the article page follow.

### Phase 8 — Enquiries and feedback

- `Enquiry` moves out of `django.contrib.admin` into the panel: server-side
  DataTables list, filters by subject/type/handled, detail view, mark handled,
  internal notes, CSV export, and the delivery status the model already records.
- `Feedback` model and the `/feedback` page back online with a working server
  handler, the same honeypot and throttle the enquiry form uses, a reference
  number, and a reply field.
- Email recipients and the from-address become editable in the panel instead of
  environment variables, with the environment still winning if set.

### Phase 9 — Editorial safety

- Draft and preview: an unpublished object is viewable on the real page through
  a signed preview URL, so copy can be checked in place before going live.
- Scheduled publishing for posts and events.
- `Revision` history with a diff view and one-click restore; `AuditEntry` log.
- Soft delete with a trash that can be emptied deliberately.
- Role permissions enforced per module (Editor drafts, Publisher publishes).
- Unsaved-changes guard and themed server-side validation messages.

### Phase 10 — Cut over and harden

- Remove `django.contrib.admin` from `INSTALLED_APPS` and `config/urls.py`;
  rewrite the one test that asserts enquiries are listed in the Django admin to
  assert it against the panel instead.
- Tighten the panel CSP: with every widget self-hosted, drop `'unsafe-inline'`
  from `style-src` once the vendored bundles are checked for inline style
  attributes.
- Backups: `deploy/release.sh` and the backup job must now cover `MEDIA_ROOT`
  as well as the SQLite file. A content database with no media backup is a
  broken site.
- `manage.py seed_content` for a fresh install and for demos.
- Update `gssl_site/README.md`, `AI-HANDOFF.md` and the go-live checklist.
- Performance pass: cache the site map and the heavy fragments, and confirm the
  page weight has not moved.

---

## 7. Constraints to hold throughout

- **`green-spark-website/` is frozen.** Never edit it. It is the reference build.
- **No third-party requests.** CSP is `default-src 'self'`. Every library the
  panel uses is vendored into `static/console/vendor/` with its licence, the
  way `bootstrap-grid` already is.
- **SQLite stays.** WAL and `IMMEDIATE` transactions are already configured for
  multiple gunicorn workers. Content editing is low-concurrency; this is fine.
  The one thing to add is media backup.
- **Sample data must not be published as fact.** README §11 lists every invented
  figure, event, album and ID. Seeded content starts unpublished, and counters
  need an "as of" date before they render.
- **Programme confidentiality.** README §13 governs which programmes in
  development may be shown; `show_on_website` is the switch and it defaults off.
- **Migrations are checked in CI** (`makemigrations --check`), so every model
  change ships with its migration.

---

## 8. Sizing

| Phase | Scope | Rough size |
|---|---|---|
| 0 | Foundations, parity harness, image pipeline | Medium |
| 1 | Panel shell, auth, CRUD framework, theme | Large |
| 2 | Chrome, settings, Page model | Medium |
| 3 | Programmes and Projects | Large |
| 4 | Home page and impact data | Large |
| 5 | About, Why, Team, FAQ, Careers, Privacy | Medium — **built** |
| 6 | Events and Gallery | Medium |
| 7 | News & Insights | Small |
| 8 | Enquiries and feedback | Medium |
| 9 | Drafts, revisions, roles | Medium |
| 10 | Cut over, harden, document | Small |

Phases 0 and 1 are the investment; everything after them is the same pattern
repeated, which is why the generic CRUD framework in Phase 1 is worth building
properly rather than hand-writing 38 screens.

---

## 9. Suggested order of work

Phase 0 first, alone — the harness is what makes every later phase provable.
Then Phase 1, because nothing can be edited without it. Then Phase 2, which is
small enough to shake out the pattern across every page at once. After that,
Phases 3 to 8 can be done in any order Green Spark prefers, since each one owns
its own templates and models. Phases 9 and 10 close it out.
