"""
The site map, in one place.

Every page of the design build is one row here: the URL route, the template
that renders it, which top-level nav item should show as current, and whether
the page is on the live site.

The site is deliberately static for now — each row is a plain template with no
database behind it. When the admin panel lands, the rows that represent real
content (programmes, projects, events, posts, albums) become model-backed
detail views. Nothing else about the templates has to change.

Status
------
LIVE      routed, linked from the site, listed in sitemap.xml.
UNLISTED  routed, but no menu links to it: kept out of sitemap.xml and
          marked noindex. Used for pages GSSL has hidden from the menus.
OFFLINE   answers 404. The template is kept so the page can come back by
          changing this one word. Used for pages whose only content is the
          design build's sample data (invented posts, events and albums),
          which must not be published as fact.
"""

from dataclasses import dataclass

LIVE = "live"
UNLISTED = "unlisted"
OFFLINE = "offline"


@dataclass(frozen=True)
class Page:
    name: str          # URL name, reachable as {% url 'website:<name>' %}
    route: str         # Django route, relative to the site root
    template: str      # template under templates/pages/
    nav: str = ""      # top-level nav key to mark current (see partials/site_header.html)
    status: str = LIVE

    @property
    def is_published(self) -> bool:
        return self.status != OFFLINE

    @property
    def in_sitemap(self) -> bool:
        return self.status == LIVE


PAGES: tuple[Page, ...] = (
    Page("home", "", "home.html"),

    # What We Do — one page per programme. These six collapse into a single
    # slug-driven view once the Programme model exists.
    Page("programme_improved_cookstove", "what-we-do/improved-cookstove/",
         "programme_improved_cookstove.html", nav="what-we-do"),
    Page("programme_rooftop_solar", "what-we-do/rooftop-solar/",
         "programme_rooftop_solar.html", nav="what-we-do"),
    Page("programme_safe_drinking_water", "what-we-do/safe-drinking-water/",
         "programme_safe_drinking_water.html", nav="what-we-do"),
    Page("programme_solar_irrigation", "what-we-do/solar-irrigation/",
         "programme_solar_irrigation.html", nav="what-we-do"),
    Page("programme_rural_productive_use_solar", "what-we-do/rural-productive-use-solar/",
         "programme_rural_productive_use_solar.html", nav="what-we-do"),
    Page("programme_low_emission_rice", "what-we-do/low-emission-rice/",
         "programme_low_emission_rice.html", nav="what-we-do"),

    # Projects
    Page("projects", "projects/", "projects.html", nav="projects"),
    # project_detail is slug-driven; see urls.py and content.py.
    Page("gallery", "gallery/", "gallery.html", nav="about"),
    Page("gallery_album", "gallery/green-ics-in-the-field/",
         "gallery_album.html", nav="about"),

    # Why GSSL — hidden from the menus by GSSL; its content leads What We Do.
    Page("why_gssl", "why-gssl/", "why_gssl.html", nav="why-gssl", status=UNLISTED),

    # News & Insights — GSSL asked for this section to be removed. Every post
    # in it is a design-build sample.
    Page("news", "news-insights/", "news.html", nav="news", status=OFFLINE),
    Page("news_article", "news-insights/how-mrv-works-for-rooftop-solar/",
         "news_article.html", nav="news", status=OFFLINE),

    # Events. The listing carries the three real consultation notices. The two
    # detail templates still hold the design build's invented events (a 2027
    # Manikganj LSC and a feedback round to January 2027), so they are
    # UNLISTED, not LIVE: the design is reachable for review and nothing
    # indexes a consultation notice that never happened. Make them LIVE from
    # the console once the wording is Green Spark's own.
    Page("events", "events/", "events.html", nav="events"),
    Page("event_detail", "events/lsc-manikganj-2027/", "event_detail.html",
         nav="events", status=UNLISTED),
    Page("event_feedback_round", "events/feedback-round-ics-2026/",
         "event_feedback_round.html", nav="events", status=UNLISTED),
    # Feedback — GSSL asked for no feedback page. Its form was never wired to
    # a server; wire it (see EnquireView) before bringing it back.
    Page("feedback", "feedback/", "feedback.html", nav="events", status=OFFLINE),

    # About Us
    Page("about", "about-us/", "about.html", nav="about"),
    Page("team", "about-us/team/", "team.html", nav="about"),
    Page("faq", "faq/", "faq.html", nav="about", status=UNLISTED),

    # Utility
    Page("enquire", "contact-us/", "enquire.html", nav="enquire"),
    Page("privacy", "privacy/", "privacy.html"),
)

PAGES_BY_NAME = {page.name: page for page in PAGES}
