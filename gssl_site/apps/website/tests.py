"""
Tests for the website.

Most of these pin down a bug that was once live and invisible: a sample
banner, a form that faked success, a project page headed with another
project's name. Read the docstring before deleting one.
"""

import codecs
import os
import re
import subprocess
import sys
from unittest import mock

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.management.utils import get_random_secret_key
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.content.models import Project

from . import parity
from .models import Enquiry
from .pages import LIVE, OFFLINE, PAGES, UNLISTED
from .views import server_error

PUBLISHED = [p for p in PAGES if p.is_published]
OFFLINE_PAGES = [p for p in PAGES if p.status == OFFLINE]


def all_projects() -> list:
    """The projects, from the database. Not a module constant: there is no
    database yet when this module is imported."""
    return list(Project.objects.select_related("programme"))


def published_urls() -> list[str]:
    return ([reverse(f"website:{p.name}") for p in PUBLISHED]
            + [reverse("website:project_detail", args=[pr.slug]) for pr in all_projects()])


class RenderedPages:
    """Render every published page once per test class."""

    _cache: dict[str, str] = {}

    def body(self, url: str) -> str:
        if url not in self._cache:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self._cache[url] = response.content.decode()
        return self._cache[url]


class PageRenderTests(RenderedPages, TestCase):
    """Every published page renders with the shared chrome and nothing leaks."""

    def test_every_published_page_returns_200(self):
        for url in published_urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_pages_carry_the_shared_chrome(self):
        for url in published_urls():
            with self.subTest(url=url):
                body = self.body(url)
                self.assertIn('<header class="site-header"', body)
                self.assertIn('<footer class="site-footer', body)
                self.assertIn('id="gs-mark"', body)          # svg sprite
                self.assertIn('<main id="main"', body)

    def test_no_unrendered_template_tags(self):
        # {# #} included: Django only treats it as a comment on ONE line, so a
        # multi-line one renders as visible text.
        leak = re.compile(r"\{%|\{\{|\{#")
        for url in published_urls():
            with self.subTest(url=url):
                self.assertIsNone(leak.search(self.body(url)), "unrendered template syntax in output")

    def test_no_design_build_asset_paths_remain(self):
        for url in published_urls():
            with self.subTest(url=url):
                body = self.body(url)
                self.assertNotIn("../assets/", body)
                self.assertIn(settings.STATIC_URL, body)

    def test_no_links_to_raw_html_files(self):
        """Internal links must go through {% url %}, not foo.html."""
        for url in published_urls():
            with self.subTest(url=url):
                stray = re.findall(r'href="(?!https?:)[^"]*?[a-z0-9-]+\.html[^"]*"', self.body(url))
                self.assertEqual(stray, [], f"{url} still links to .html files")


class SampleContentTests(RenderedPages, TestCase):
    """
    The design build carried a "Design preview · sample data" ribbon, "Sample
    data" badges, invented posts and events, and build notes in visible copy.
    None of it may reach the live site.
    """

    VISIBLE_LEAKS = re.compile(
        r"design preview|sample data|sample post|\bsample\b|placeholder|lorem ipsum|"
        r"to be confirmed\.|districts to confirm|venue to confirm|new field|"
        r"field photo ·|GS-FB-\d+|\bdraft\b|legal review|before the site goes|time zone to",
        re.I,
    )

    def visible_text(self, body: str) -> str:
        body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", body, flags=re.S)
        body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
        attrs = " ".join(re.findall(r'(?:alt|title|aria-label|placeholder)="([^"]*)"', body))
        return re.sub(r"<[^>]+>", " ", body) + " " + attrs

    def test_no_preview_ribbon_or_sample_badge(self):
        for url in published_urls():
            with self.subTest(url=url):
                body = self.body(url)
                self.assertNotIn("preview-ribbon", body)
                self.assertNotIn("is-preview", body)
                self.assertNotIn("badge--sample", body)

    def test_no_sample_or_build_wording_in_visible_text(self):
        for url in published_urls():
            with self.subTest(url=url):
                found = self.VISIBLE_LEAKS.findall(self.visible_text(self.body(url)))
                self.assertEqual(found, [], f"{url} shows {found}")

    def test_no_photo_or_script_loads_from_another_server(self):
        """Stock photos used to hot-link Pexels and Unsplash, with a grey
        'Field photo' placeholder as the fallback."""
        remote = re.compile(r'(?:src|srcset|poster|data-fallback)="(https?://[^"]*)"')
        for url in published_urls():
            with self.subTest(url=url):
                self.assertEqual(remote.findall(self.body(url)), [])

    def test_social_icons_never_point_at_a_bare_platform_home_page(self):
        bare = re.compile(r'href="https://(?:www\.)?(?:facebook|youtube|linkedin|twitter|x|instagram)\.com/?"')
        for url in published_urls():
            with self.subTest(url=url):
                self.assertIsNone(bare.search(self.body(url)))

    def test_no_fake_pagination(self):
        """Every page number used to link back to the same page."""
        for url in (reverse("website:events"), reverse("website:gallery")):
            with self.subTest(url=url):
                self.assertNotIn('class="pagination"', self.body(url))

    def test_gallery_album_count_matches_its_photos(self):
        body = self.body(reverse("website:gallery_album"))
        photos = body.count('data-lightbox="album"')
        self.assertIn(f"{photos} photos", body)
        gallery = self.body(reverse("website:gallery"))
        self.assertEqual(gallery.count('class="album-card"'), 1)
        self.assertIn(f"{photos} photos", gallery)


class PublishingTests(RenderedPages, TestCase):
    def test_offline_pages_answer_404(self):
        self.assertTrue(OFFLINE_PAGES)
        for page in OFFLINE_PAGES:
            with self.subTest(page=page.name):
                self.assertEqual(self.client.get(reverse(f"website:{page.name}")).status_code, 404)

    def test_sample_only_pages_are_never_live(self):
        """
        These still carry the design build's invented content. OFFLINE or
        UNLISTED are both acceptable -- unlisted keeps a page reachable for
        review while no menu links to it and nothing indexes it -- but LIVE
        would put invented posts and consultation notices on the site as fact.
        """
        for name in ("news", "news_article", "event_detail", "event_feedback_round", "feedback"):
            with self.subTest(page=name):
                self.assertNotEqual(next(p for p in PAGES if p.name == name).status, LIVE)

    def test_no_published_page_links_to_a_missing_page(self):
        """Every in-site link on every published page answers 200."""
        targets: dict[str, str] = {}
        for url in published_urls():
            for href in re.findall(r'href="(/[^"]*)"', self.body(url)):
                path = href.split("#")[0].split("?")[0]
                if path and not path.startswith(settings.STATIC_URL):
                    targets.setdefault(path, url)
        for path, source in sorted(targets.items()):
            with self.subTest(href=path, on=source):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_unlisted_pages_are_noindex_and_live_pages_are_not(self):
        for page in PUBLISHED:
            with self.subTest(page=page.name):
                body = self.body(reverse(f"website:{page.name}"))
                has_noindex = '<meta name="robots" content="noindex">' in body
                self.assertEqual(has_noindex, page.status == UNLISTED)

    def test_sitemap_lists_live_pages_and_projects_only(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml; charset=utf-8")
        body = response.content.decode()
        for page in PAGES:
            loc = f"<loc>{settings.SITE_URL}{reverse(f'website:{page.name}')}</loc>"
            with self.subTest(page=page.name):
                self.assertEqual(loc in body, page.status == LIVE)
        for project in all_projects():
            self.assertIn(reverse("website:project_detail", args=[project.slug]), body)

    def test_robots_txt_points_at_the_sitemap(self):
        body = self.client.get("/robots.txt").content.decode()
        self.assertIn("User-agent: *", body)
        self.assertIn(f"Sitemap: {settings.SITE_URL}/sitemap.xml", body)


class MetadataTests(RenderedPages, TestCase):
    def test_each_page_has_a_unique_title_and_description(self):
        titles, descriptions = {}, {}
        for url in published_urls():
            body = self.body(url)
            title = re.search(r"<title>(.*?)</title>", body, re.S).group(1).strip()
            desc = re.search(r'<meta name="description" content="(.*?)">', body, re.S).group(1)
            self.assertTrue(title, f"{url} has an empty title")
            self.assertTrue(desc, f"{url} has an empty description")
            titles.setdefault(title, []).append(url)
            descriptions.setdefault(desc, []).append(url)
        dupes = {t: p for t, p in titles.items() if len(p) > 1}
        self.assertEqual(dupes, {}, f"duplicate <title>: {dupes}")
        dupes = {d: p for d, p in descriptions.items() if len(p) > 1}
        self.assertEqual(dupes, {}, f"duplicate meta description: {dupes}")

    def test_canonical_matches_the_page_url(self):
        for url in published_urls():
            with self.subTest(url=url):
                self.assertIn(f'<link rel="canonical" href="{settings.SITE_URL}{url}">', self.body(url))

    def test_canonical_has_no_hard_coded_domain(self):
        """The domain comes from SITE_URL, so overriding it moves every link."""
        with override_settings(SITE_URL="https://example.test"):
            body = self.client.get(reverse("website:home")).content.decode()
        self.assertIn('href="https://example.test/"', body)
        self.assertNotIn("gssl.thingbd.com", body)


class NavigationTests(RenderedPages, TestCase):
    def test_nav_marks_the_current_section(self):
        for name in ("projects", "events", "about", "programme_rooftop_solar", "gallery"):
            with self.subTest(page=name):
                body = self.body(reverse(f"website:{name}"))
                self.assertTrue("is-current" in body or 'aria-current="page"' in body)

    def test_home_marks_nothing_as_current(self):
        self.assertNotIn("is-current", self.body(reverse("website:home")))

    def test_menus_offer_events_but_not_news_or_feedback(self):
        """GSSL asked for News & insights and Give feedback to be removed,
        keeping events and consultation rounds."""
        events = reverse("website:events")
        for url in published_urls():
            with self.subTest(url=url):
                body = self.body(url)
                header = body[body.index("<header"):body.index("</header>")]
                self.assertIn(f'href="{events}"', header)
                self.assertNotIn("News &amp; Insights", header)
                self.assertNotIn(f'href="{reverse("website:news")}"', body)
                self.assertNotIn(f'href="{reverse("website:feedback")}"', body)


class ScriptOrderTests(RenderedPages, TestCase):
    """
    website.js calls GS.boot(), which runs every module registered up to that
    point. A component script loaded after it registers too late and never
    boots — which silently cost the home page its hero video once already.
    """

    def test_component_scripts_load_before_the_bootstrap(self):
        for url in published_urls():
            with self.subTest(url=url):
                body = self.body(url)
                boot = body.find("js/website.js")
                self.assertNotEqual(boot, -1, "website.js is missing")
                after = [
                    src for src in re.findall(r'<script src="([^"]*js/components/[^"]*)"', body)
                    if body.find(src) > boot
                ]
                self.assertEqual(after, [], "component script loaded after website.js")

    def test_home_loads_the_video_hero_module(self):
        body = self.body(reverse("website:home"))
        self.assertIn("js/components/video-hero.js", body)
        self.assertIn("data-vhero", body)
        for attr in ("data-wide-webm", "data-wide-mp4", "data-tall-webm", "data-tall-mp4"):
            self.assertIn(attr, body, f"hero video is missing {attr}")


class SecurityTests(RenderedPages, TestCase):
    def test_pages_are_csp_safe(self):
        """No inline script, no on*= handlers, no style attributes: the
        Content-Security-Policy forbids all three."""
        for url in published_urls():
            with self.subTest(url=url):
                body = self.body(url)
                inline = [m for m in re.findall(r"<script(?![^>]*\bsrc=)([^>]*)>", body)
                          if "application/ld+json" not in m]
                self.assertEqual(inline, [], "inline <script>")
                self.assertIsNone(re.search(r"\son[a-z]+=", body), "on*= handler")
                self.assertIsNone(re.search(r'\sstyle="', body), "style attribute")

    def test_csp_and_permissions_policy_headers(self):
        response = self.client.get(reverse("website:home"))
        csp = response.get("Content-Security-Policy") or response.get("Content-Security-Policy-Report-Only")
        self.assertIn("default-src 'self'", csp)
        self.assertIn("script-src 'self'", csp)
        self.assertNotIn("unsafe-inline", csp)
        self.assertIn("camera=()", response["Permissions-Policy"])

    @override_settings(CONTENT_SECURITY_POLICY_REPORT_ONLY=False)
    def test_csp_is_enforced_when_not_report_only(self):
        response = self.client.get(reverse("website:home"))
        self.assertIn("Content-Security-Policy", response)


class ErrorPageTests(TestCase):
    def test_unknown_url_renders_the_404_page(self):
        response = self.client.get("/no-such-page/")
        self.assertEqual(response.status_code, 404)
        self.assertIn("Page not found", response.content.decode())

    def test_500_page_renders(self):
        request = RequestFactory().get("/")
        response = server_error(request)
        self.assertEqual(response.status_code, 500)
        self.assertIn("<html", response.content.decode())


class SiteChromeTests(RenderedPages, TestCase):
    """
    Markup that lives between partials in the design build, so the partial
    extractor never saw it. All of this went missing in the first conversion.
    """

    def test_every_page_has_the_skip_link(self):
        for url in published_urls():
            with self.subTest(url=url):
                self.assertIn('<a class="skip-link" href="#main">Skip to content</a>', self.body(url))

    def test_every_page_wraps_the_header_in_site_chrome(self):
        """nav.js queries [data-site-chrome]; the CSS makes it position:fixed."""
        for url in published_urls():
            with self.subTest(url=url):
                body = self.body(url)
                self.assertIn('<div class="site-chrome" data-site-chrome>', body)
                self.assertIn('<div class="site-chrome__spacer" aria-hidden="true"></div>', body)
                # The top bar is optional (SiteSettings.show_topbar), so what
                # matters is that the chrome wraps the header, bar or no bar.
                self.assertLess(body.index("data-site-chrome"), body.index("<header"))
                self.assertLess(body.index("<header"), body.index("site-chrome__spacer"))

    def test_lightbox_only_where_there_is_a_photo_grid(self):
        for url in published_urls():
            with self.subTest(url=url):
                body = self.body(url)
                self.assertEqual("data-lightbox-root" in body, "data-lightbox=" in body)


class TemplateFileTests(SimpleTestCase):
    def templates(self):
        return list((settings.BASE_DIR / "templates").rglob("*.html"))

    def test_no_template_has_a_byte_order_mark(self):
        """A BOM renders as a stray character at the top of the page."""
        culprits = [str(f) for f in self.templates() if f.read_bytes()[:3] == codecs.BOM_UTF8]
        self.assertEqual(culprits, [], "template(s) saved with a UTF-8 BOM")

    def test_comment_blocks_are_balanced_and_never_nested(self):
        """Django's {% comment %} does not nest: the first {% endcomment %}
        closes it and the rest of the hidden block renders, or the page 500s."""
        for path in self.templates():
            with self.subTest(template=path.name):
                depth = 0
                for tag in re.findall(r"\{% (comment|endcomment)\b", path.read_text(encoding="utf-8")):
                    depth += 1 if tag == "comment" else -1
                    self.assertIn(depth, (0, 1))
                self.assertEqual(depth, 0)


class UploadPlumbingTests(SimpleTestCase):
    """
    What has to be true on the server for an uploaded photograph to be
    reachable.

    Phase 6 is the first thing on this site that writes a file. The failure it
    invites is silent: the console saves the photo, the database row is right,
    the page renders an <img>, and the image 404s because nginx was never told
    about /media/. Nothing in the application can notice that, so the shipped
    nginx config and the environment template are checked here instead.
    """

    def deploy_file(self, name: str) -> str:
        return (settings.BASE_DIR / "deploy" / name).read_text(encoding="utf-8")

    def env_example(self) -> str:
        return (settings.BASE_DIR / ".env.example").read_text(encoding="utf-8")

    def test_media_is_served_from_its_own_url_prefix(self):
        self.assertTrue(settings.MEDIA_URL.startswith("/"))
        self.assertNotEqual(settings.MEDIA_URL, settings.STATIC_URL)
        # An upload reachable under /static/ would be collected, hashed and
        # cached for a year alongside the design build's own files.
        self.assertFalse(settings.MEDIA_URL.startswith(settings.STATIC_URL))
        self.assertFalse(settings.STATIC_URL.startswith(settings.MEDIA_URL))

    def test_nginx_serves_media_from_the_path_the_environment_names(self):
        conf = self.deploy_file("nginx.conf")
        block = re.search(
            r"location\s+" + re.escape(settings.MEDIA_URL) + r"\s*\{(.*?)\n    \}",
            conf, re.S,
        )
        self.assertIsNotNone(block, "deploy/nginx.conf has no location for MEDIA_URL")
        alias = re.search(r"alias\s+(\S+);", block.group(1))
        self.assertIsNotNone(alias, "the media location has no alias")
        documented = re.search(r"^DJANGO_MEDIA_ROOT=(\S+)", self.env_example(), re.M)
        self.assertIsNotNone(documented, ".env.example does not mention DJANGO_MEDIA_ROOT")
        self.assertEqual(alias.group(1).rstrip("/"), documented.group(1).rstrip("/"))

    def test_a_missing_upload_does_not_fall_through_to_django(self):
        """
        Without try_files the / location answers instead and Django renders
        the site's 404 *page* for an image request -- a 404 nobody can see in
        a log full of them.
        """
        conf = self.deploy_file("nginx.conf")
        block = re.search(
            r"location\s+" + re.escape(settings.MEDIA_URL) + r"\s*\{(.*?)\n    \}",
            conf, re.S,
        ).group(1)
        self.assertIn("try_files", block)
        self.assertIn("nosniff", block)

    def test_nginx_accepts_an_upload_as_large_as_django_does(self):
        """
        nginx refuses an over-size body before Django ever sees it, with a
        bare 413. Its limit has to sit above ours so the person gets the
        console's message naming the limit instead.
        """
        size = re.search(r"client_max_body_size\s+(\d+)m;", self.deploy_file("nginx.conf"))
        self.assertIsNotNone(size, "nginx.conf no longer sets client_max_body_size in MB")
        self.assertGreater(
            int(size.group(1)) * 1024 * 1024, settings.UPLOAD_IMAGE_MAX_BYTES,
        )

    def test_the_release_script_makes_the_upload_directory(self):
        """collectstatic rebuilds /static/; nothing rebuilds /media/."""
        release = self.deploy_file("release.sh")
        self.assertIn("MEDIA_ROOT", release)
        self.assertIn("mkdir -p", release)

    def test_the_runbook_says_to_back_up_the_uploads(self):
        """A database backup alone restores a gallery whose every photo 404s."""
        runbook = self.deploy_file("RUNBOOK.md")
        backups = runbook.split("## Backups")[-1]
        self.assertIn("media", backups)

    def test_only_raster_images_may_be_uploaded(self):
        """
        An SVG served from our own origin is a document, and the site's CSP
        lets a same-origin document run scripts. "Upload a photo" must not be
        a way to put one on greensparksolutions.com.
        """
        self.assertNotIn("svg", settings.UPLOAD_IMAGE_EXTENSIONS)
        self.assertEqual(
            set(settings.UPLOAD_IMAGE_EXTENSIONS), {"jpg", "jpeg", "png", "webp"},
        )


class ProjectPageTests(RenderedPages, TestCase):
    """
    Every project has its own page. The design build shipped one detail page
    holding Phase 1's content, and all seven cards pointed at it; then the
    page kept Phase 1's heading, narrative and Gold Standard claims on every
    project, including the unregistered ones.
    """

    def page(self, slug):
        return self.body(reverse("website:project_detail", args=[slug]))

    @staticmethod
    def section(body, start, end):
        i = body.index(start)
        return body[i:body.index(end, i)]

    def test_each_page_is_headed_with_its_own_project(self):
        for project in all_projects():
            with self.subTest(project=project.slug):
                body = self.page(project.slug)
                self.assertIn(f"<h1>{project.title}</h1>", body.replace("&#x27;", "'"))
                details = self.section(body, "key-details", "</dl>")
                self.assertIn(project.location, details)
                self.assertIn(project.stage, details)

    def test_only_registered_projects_claim_gold_standard(self):
        for project in all_projects():
            with self.subTest(project=project.slug):
                main = self.section(self.page(project.slug), "<main", "Other project activities")
                claims = ("registry.goldstandard.org" in main
                          or "registered with Gold Standard" in main
                          or "Gold Standard registered" in main)
                self.assertEqual(claims, project.is_registered)

    def test_programme_row_links_to_the_projects_own_programme(self):
        body = self.page("rooftop-solar-mrv")
        details = self.section(body, "key-details", "</dl>")
        self.assertIn(reverse("website:programme_rooftop_solar"), details)
        self.assertNotIn("Improved Cookstove Programme", details)
        self.assertNotIn("How the Green ICS works", body)

    def test_phase_pages_are_not_phase_1(self):
        for slug in ("green-ics-phase-2", "green-ics-phase-3", "rooftop-solar-mrv", "clean-cooking-scoping-nepal"):
            with self.subTest(project=slug):
                main = self.section(self.page(slug), "<main", "Other project activities")
                self.assertNotIn("Phase 1 brought", main)
                self.assertNotIn("Green ICS — Phase 1</h1>", main)

    def test_related_projects_never_include_the_page_itself(self):
        for project in all_projects():
            with self.subTest(project=project.slug):
                related = self.section(self.page(project.slug), "Other project activities", "</section>")
                own = reverse("website:project_detail", args=[project.slug])
                self.assertNotIn(f'href="{own}"', related)
                self.assertEqual(related.count('class="project-card '), 3)

    def test_unknown_project_is_404(self):
        self.assertEqual(self.client.get("/projects/not-a-project/").status_code, 404)

    def test_every_project_row_is_complete(self):
        for project in all_projects():
            with self.subTest(project=project.slug):
                self.assertTrue(project.description)
                self.assertTrue(project.is_registered or project.card_badge)
                self.assertEqual(project.is_registered, project.filters[0] == "registered")
                reverse(project.programme_url_name)


@override_settings(ENQUIRY_EMAIL_ENABLED=True, ENQUIRY_RECIPIENTS=["info@example.test"])
class EnquiryFormTests(TestCase):
    """
    The contact form used to post to "#" with data-demo="success": visitors
    were thanked and their message went nowhere.
    """

    URL = "/contact-us/"
    AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest", "HTTP_ACCEPT": "application/json"}
    VALID = {
        "name": "Rahim Uddin",
        "email": "rahim@example.test",
        "phone": "+880 1700 000000",
        "enquiry_type": "partner",
        "subject": "carbon",
        "message": "We would like to talk about rooftop solar credits.",
        "website": "",
    }

    def setUp(self):
        cache.clear()

    def test_form_posts_to_the_server_with_a_csrf_token(self):
        body = self.client.get(self.URL).content.decode()
        form = re.search(r'<form[^>]*id="contact-form"[^>]*>', body).group(0)
        self.assertIn(f'action="{self.URL}"', form)
        self.assertIn("data-ajax", form)
        self.assertNotIn("data-demo", form)
        self.assertIn('name="csrfmiddlewaretoken"', body)

    def test_choices_on_the_page_match_the_model(self):
        body = self.client.get(self.URL).content.decode()
        for value in ("general", "partnership", "carbon", "rooftop", "community", "press", "careers"):
            self.assertIn(f'<option value="{value}"', body)
        for value in ("community", "government", "partner", "finance", "other"):
            self.assertIn(f'name="enquiry_type" value="{value}"', body)

    def test_valid_enquiry_is_saved_and_emailed(self):
        response = self.client.post(self.URL, self.VALID, **self.AJAX)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})
        enquiry = Enquiry.objects.get()
        self.assertEqual(enquiry.email, "rahim@example.test")
        self.assertIsNotNone(enquiry.emailed_at)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ["info@example.test"])
        self.assertEqual(sent.reply_to, ["rahim@example.test"])
        self.assertIn("Carbon credits and climate finance", sent.subject)
        self.assertIn("rooftop solar credits", sent.body)

    def test_without_javascript_the_form_redirects_to_a_thank_you(self):
        response = self.client.post(self.URL, self.VALID)
        self.assertRedirects(response, f"{self.URL}?sent=1#contact-form", fetch_redirect_response=False)
        body = self.client.get(f"{self.URL}?sent=1").content.decode()
        self.assertIn('data-state="success"', body)
        self.assertEqual(Enquiry.objects.count(), 1)

    def test_invalid_enquiry_is_rejected_with_field_errors(self):
        data = {**self.VALID, "email": "not-an-email", "message": "short"}
        response = self.client.post(self.URL, data, **self.AJAX)
        self.assertEqual(response.status_code, 400)
        errors = response.json()["errors"]
        self.assertIn("email", errors)
        self.assertIn("message", errors)
        self.assertFalse(Enquiry.objects.exists())

    def test_invalid_enquiry_without_javascript_keeps_what_was_typed(self):
        response = self.client.post(self.URL, {**self.VALID, "email": "nope"})
        self.assertEqual(response.status_code, 400)
        body = response.content.decode()
        self.assertIn('value="Rahim Uddin"', body)
        self.assertIn("rooftop solar credits.</textarea>", body)
        self.assertIn('<option value="carbon" selected>', body)
        self.assertIn("Enter a valid email address", body)

    def test_honeypot_submissions_are_dropped_silently(self):
        response = self.client.post(self.URL, {**self.VALID, "website": "spam.example"}, **self.AJAX)
        self.assertEqual(response.json(), {"ok": True})
        self.assertFalse(Enquiry.objects.exists())
        self.assertEqual(mail.outbox, [])

    @override_settings(ENQUIRY_THROTTLE_COUNT=2)
    def test_floods_are_throttled(self):
        codes = [self.client.post(self.URL, self.VALID, **self.AJAX).status_code for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])
        self.assertEqual(Enquiry.objects.count(), 2)

    def test_a_mail_failure_never_loses_the_enquiry(self):
        with mock.patch("django.core.mail.EmailMessage.send", side_effect=OSError("SMTP down")), \
                self.assertLogs("apps.website.mail", level="ERROR"):
            response = self.client.post(self.URL, self.VALID, **self.AJAX)
        self.assertEqual(response.json(), {"ok": True})
        enquiry = Enquiry.objects.get()
        self.assertIsNone(enquiry.emailed_at)
        self.assertIn("SMTP down", enquiry.email_error)

    @override_settings(ENQUIRY_EMAIL_ENABLED=False)
    def test_without_email_configured_enquiries_wait_in_the_admin(self):
        self.client.post(self.URL, self.VALID, **self.AJAX)
        enquiry = Enquiry.objects.get()
        self.assertEqual(mail.outbox, [])
        self.assertIn("not configured", enquiry.email_error)

    def test_names_cannot_inject_email_headers(self):
        self.client.post(self.URL, {**self.VALID, "name": "Eve\r\nBcc: victim@example.test"}, **self.AJAX)
        self.assertNotIn("\n", mail.outbox[0].subject)

    def test_enquiries_are_listed_in_the_admin(self):
        from django.contrib.auth.models import User
        User.objects.create_superuser("admin", "admin@example.test", "a-long-test-password")
        self.client.login(username="admin", password="a-long-test-password")
        self.client.post(self.URL, self.VALID, **self.AJAX)
        body = self.client.get(f"/{settings.ADMIN_URL}website/enquiry/").content.decode()
        self.assertIn("Rahim Uddin", body)


class ProductionSettingsTests(SimpleTestCase):
    """config.settings.prod refuses to start without the values the live site needs."""

    def run_prod(self, **env):
        base = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
        base.update({"DJANGO_SETTINGS_MODULE": "config.settings.prod", **env})
        return subprocess.run(
            [sys.executable, "-c", "import django; django.setup()"],
            cwd=settings.BASE_DIR, env=base, capture_output=True, text=True,
        )

    GOOD = {
        "DJANGO_SECRET_KEY": "x" * 50,
        "DJANGO_ALLOWED_HOSTS": "example.test",
        "DJANGO_SITE_URL": "https://example.test",
        "DJANGO_DB_PATH": "/tmp/gssl-settings-test/db.sqlite3",
        # prod.py creates MEDIA_ROOT on import; point it somewhere disposable
        # so running the tests never writes into the checkout.
        "DJANGO_MEDIA_ROOT": "/tmp/gssl-settings-test/media",
    }

    def test_starts_with_the_required_values(self):
        self.assertEqual(self.run_prod(**self.GOOD).returncode, 0)

    def test_refuses_to_start_without_each_required_value(self):
        for missing in ("DJANGO_SECRET_KEY", "DJANGO_ALLOWED_HOSTS", "DJANGO_SITE_URL"):
            with self.subTest(missing=missing):
                env = {k: v for k, v in self.GOOD.items() if k != missing}
                result = self.run_prod(**env)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(missing, result.stderr)

    def test_refuses_a_plain_http_site_url(self):
        result = self.run_prod(**{**self.GOOD, "DJANGO_SITE_URL": "http://example.test"})
        self.assertNotEqual(result.returncode, 0)

    def run_deploy_check(self, **env):
        """What release.sh runs before it will let a deploy through."""
        base = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_")}
        base.update({"DJANGO_SETTINGS_MODULE": "config.settings.prod", **env})
        return subprocess.run(
            [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
            cwd=settings.BASE_DIR, env=base, capture_output=True, text=True,
        )

    def test_the_hsts_choices_never_block_a_release(self):
        """
        release.sh stops on any warning, so a setting an operator is told to
        change must not raise one. .env.example says to turn includeSubDomains
        off when a subdomain still serves plain HTTP, and preload is off by
        default -- neither may stop a deploy. Both were silenced only after
        this test caught the release refusing to run.
        """
        # GOOD's placeholder key is 50 identical characters, which the deploy
        # check rightly rejects; this test is about the HSTS warnings alone.
        env = {**self.GOOD, "DJANGO_SECRET_KEY": get_random_secret_key()}
        for subdomains in ("0", "1"):
            with self.subTest(include_subdomains=subdomains):
                result = self.run_deploy_check(
                    **env,
                    DJANGO_HSTS_SECONDS="300",
                    DJANGO_HSTS_INCLUDE_SUBDOMAINS=subdomains,
                    DJANGO_HSTS_PRELOAD="0",
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class ContentDataTests(TestCase):
    def test_project_slugs_are_unique(self):
        slugs = [p.slug for p in all_projects()]
        self.assertEqual(len(set(slugs)), len(slugs))

    def test_every_project_belongs_to_a_programme_whose_page_exists(self):
        for project in all_projects():
            with self.subTest(project=project.slug):
                self.assertTrue(project.programme, "a project with no programme")
                reverse(project.programme_url_name)


class GoldenHtmlTests(TestCase):
    """
    The site renders exactly what it rendered before the CMS existed.

    This is the contract that lets content move into the database one phase at
    a time: every page is compared with the HTML recorded in
    ``apps/website/golden/``, byte for byte, with only the CSRF token masked.

    A failure here means the migration lost or altered something. Fix the
    migration — do not rewrite the golden file. The golden files change only
    when Green Spark asks for a content change, by running

        python manage.py snapshot_pages

    and the diff that produces is what the pull request reviews.
    """

    def test_there_is_a_golden_file_for_every_published_page(self):
        missing = [name for name, _ in parity.targets() if not parity.golden_path(name).exists()]
        self.assertEqual(
            missing, [],
            "no baseline for these pages; run: python manage.py snapshot_pages",
        )

    def test_no_golden_file_is_left_behind_by_a_removed_page(self):
        expected = {parity.golden_path(name) for name, _ in parity.targets()}
        stale = sorted(p.name for p in set(parity.GOLDEN_DIR.glob("*.html")) - expected)
        self.assertEqual(stale, [], "stale baseline(s); run: python manage.py snapshot_pages")

    def test_every_page_renders_exactly_as_it_did(self):
        for name, url in parity.targets():
            with self.subTest(page=name):
                path = parity.golden_path(name)
                if not path.exists():
                    continue  # reported by the test above
                expected = path.read_text(encoding="utf-8")
                actual = parity.render(self.client, url)
                if actual == expected:
                    continue
                self.fail(f"{url} no longer renders as recorded.\n{_first_difference(expected, actual)}")


def _first_difference(expected: str, actual: str) -> str:
    """Where two renders part company, in terms a reviewer can act on."""
    old = expected.splitlines()
    new = actual.splitlines()
    for number, (before, after) in enumerate(zip(old, new), start=1):
        if before != after:
            column = next(
                (i for i, (a, b) in enumerate(zip(before, after)) if a != b),
                min(len(before), len(after)),
            )
            window = slice(max(0, column - 60), column + 60)
            return (
                f"  first change at line {number}, column {column + 1}\n"
                f"  was:  …{before[window]}…\n"
                f"  now:  …{after[window]}…"
            )
    if len(old) != len(new):
        longer, which = (new, "now") if len(new) > len(old) else (old, "was")
        return (
            f"  the two differ in length: was {len(old)} lines, now {len(new)}\n"
            f"  first extra line ({which}): {longer[min(len(old), len(new))][:160]}"
        )
    return "  the two differ in trailing whitespace only"


class ParityMaskTests(SimpleTestCase):
    """
    The harness is only useful if it fails for real reasons. Anything that
    legitimately differs between two renders of the same page has to be masked,
    or the golden files rot and people learn to re-record them without looking.
    """

    def test_the_date_stamp_is_masked(self):
        before = parity.normalise('<body data-now="2026-11-26">')
        after = parity.normalise('<body data-now="2027-03-01">')
        self.assertEqual(before, after)
        self.assertIn('data-now="DATE"', before)

    def test_the_csrf_token_is_masked(self):
        a = parity.normalise('<input name="csrfmiddlewaretoken" value="aaa">')
        b = parity.normalise('<input name="csrfmiddlewaretoken" value="bbb">')
        self.assertEqual(a, b)

    def test_real_content_is_left_alone(self):
        html = '<h1>Climate impact, measured and verified.</h1>'
        self.assertEqual(parity.normalise(html), html)
