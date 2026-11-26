"""
Tests for the content models.

The ones that matter are the section switches: turning a band off has to take
that band off the page and leave everything else exactly as it was. The
golden-HTML test in apps.website proves the second half when nothing is
hidden; these prove the first half, and that the default is always "shown".
"""

from datetime import timedelta

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.website import parity

from .models import (
    ApproachItem, ContactDetails, Counter, District, NoticeBar, Page, Section,
    SectionVisibility, SiteSettings, SocialLinks,
)
from .models.pages import LIVE, OFFLINE, UNLISTED
from .seed import PAGES_SEED


class SeedTests(TestCase):
    """The migration brought the templates' own wording into the database."""

    def test_every_page_in_the_route_map_has_a_row(self):
        from apps.website.pages import PAGES
        names = set(Page.objects.values_list("name", flat=True))
        missing = [page.name for page in PAGES if page.name not in names]
        self.assertEqual(missing, [])

    def test_the_slug_driven_project_page_has_a_row_too(self):
        self.assertTrue(Page.objects.filter(name="project_detail").exists())

    def test_every_seeded_section_landed(self):
        expected = sum(len(row["sections"]) for row in PAGES_SEED)
        self.assertEqual(Section.objects.count(), expected)

    def test_only_the_bands_green_spark_asked_to_hide_start_hidden(self):
        hidden = set(
            Section.objects.filter(visible=False).values_list("page__name", "key")
        )
        self.assertEqual(hidden, {
            ("home", "where"),
            ("home", "news"),
            ("home", "events"),
            ("programme_improved_cookstove", "where"),
        })

    def test_a_band_hidden_in_code_says_why_it_is_off(self):
        section = Section.objects.get(page__name="home", key="news")
        self.assertFalse(section.visible)
        self.assertIn("design-build samples", section.blurb)

    def test_a_band_that_used_to_need_a_deploy_can_now_be_switched_on(self):
        """
        These four were wrapped in {% comment %}. Showing one meant editing a
        template; now it is a switch, and the markup really does come back.
        """
        url = reverse("website:home")
        self.assertNotIn("Have your say", self.client.get(url).content.decode())
        Section.objects.filter(page__name="home", key="events").update(visible=True)
        self.assertIn("Have your say", self.client.get(url).content.decode())

    def test_titles_came_across_intact(self):
        home = Page.objects.get(name="home")
        self.assertIn("Green Spark Solutions Australia", home.title)
        self.assertIn("Gold Standard", home.meta_description)

    def test_a_page_offline_in_the_route_map_is_offline_in_the_database(self):
        self.assertEqual(Page.objects.get(name="news").status, OFFLINE)

    def test_the_section_the_screenshot_pointed_at_is_there(self):
        section = Section.objects.get(page__name="home", key="approach")
        self.assertEqual(section.label, "A holistic approach, built with communities")


class SectionVisibilityTests(TestCase):
    """A key with no row is shown. Nothing may disappear by accident."""

    def test_an_unknown_key_is_visible(self):
        self.assertTrue(SectionVisibility()["anything_at_all"])

    def test_a_known_key_answers_what_it_was_told(self):
        visibility = SectionVisibility({"approach": False, "intro": True})
        self.assertFalse(visibility["approach"])
        self.assertTrue(visibility["intro"])

    def test_a_page_with_no_rows_shows_everything(self):
        Section.objects.filter(page__name="home").delete()
        body = self.client.get(reverse("website:home")).content.decode()
        self.assertIn("A holistic approach, built with communities", body)


class HidingASectionTests(TestCase):
    """Turning a section off takes that band off the page, and only that band."""

    def setUp(self):
        self.url = reverse("website:home")
        self.before = self.client.get(self.url).content.decode()

    def hide(self, key):
        Section.objects.filter(page__name="home", key=key).update(visible=False)
        return self.client.get(self.url).content.decode()

    def test_the_hidden_band_goes(self):
        after = self.hide("approach")
        self.assertIn("A holistic approach, built with communities", self.before)
        self.assertNotIn("A holistic approach, built with communities", after)

    def test_the_page_still_renders(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)
        Section.objects.filter(page__name="home", key="approach").update(visible=False)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_the_neighbouring_bands_stay(self):
        after = self.hide("approach")
        for still_there in (
            "Why Green Spark",                   # a band before it
            "Project activities on the ground",  # the band after it
            "Next in our pipeline",
        ):
            with self.subTest(text=still_there):
                self.assertIn(still_there, after)

    def test_the_chrome_stays(self):
        after = self.hide("approach")
        self.assertIn("site-header", after)
        self.assertIn("</footer>", after)

    def test_hiding_removes_only_that_block(self):
        """
        What is left must be the original page minus one contiguous run —
        not a page that has been re-rendered differently somewhere else.
        """
        after = self.hide("approach")
        start = self.before.index('<section class="section" aria-labelledby="approach-title"')
        end = self.before.index("</section>", start) + len("</section>")
        self.assertEqual(after, self.before[:start] + self.before[end:])

    def test_turning_it_back_on_restores_the_page_exactly(self):
        self.hide("approach")
        Section.objects.filter(page__name="home", key="approach").update(visible=True)
        self.assertEqual(self.client.get(self.url).content.decode(), self.before)

    def test_every_section_on_every_page_can_be_hidden_without_breaking_it(self):
        for row in PAGES_SEED:
            page = Page.objects.get(name=row["name"])
            if page.status == OFFLINE or row["name"] == "project_detail":
                continue
            url = reverse(f"website:{row['name']}")
            for key, _label, _blurb in row["sections"]:
                with self.subTest(page=row["name"], section=key):
                    Section.objects.filter(page=page, key=key).update(visible=False)
                    try:
                        self.assertEqual(self.client.get(url).status_code, 200)
                    finally:
                        Section.objects.filter(page=page, key=key).update(visible=True)


class PageStatusTests(TestCase):
    """Status is read per request, so the console can take a page down."""

    def test_taking_a_live_page_offline_makes_it_404(self):
        self.assertEqual(self.client.get(reverse("website:faq")).status_code, 200)
        Page.objects.filter(name="faq").update(status=OFFLINE)
        self.assertEqual(self.client.get(reverse("website:faq")).status_code, 404)

    def test_bringing_an_offline_page_back_makes_it_200(self):
        self.assertEqual(self.client.get(reverse("website:news")).status_code, 404)
        Page.objects.filter(name="news").update(status=LIVE)
        self.assertEqual(self.client.get(reverse("website:news")).status_code, 200)

    def test_an_unlisted_page_is_noindex_and_out_of_the_sitemap(self):
        Page.objects.filter(name="faq").update(status=UNLISTED)
        body = self.client.get(reverse("website:faq")).content.decode()
        self.assertIn('name="robots" content="noindex"', body)
        sitemap = self.client.get(reverse("website:sitemap")).content.decode()
        self.assertNotIn(reverse("website:faq"), sitemap)

    def test_a_live_page_is_listed_and_indexable(self):
        # faq ships unlisted, so this uses a page that is live.
        body = self.client.get(reverse("website:about")).content.decode()
        self.assertNotIn('name="robots" content="noindex"', body)
        self.assertIn(self.loc("about"), self.sitemap())

    def test_the_sitemap_follows_the_database_not_the_code_map(self):
        self.assertIn(self.loc("about"), self.sitemap())
        Page.objects.filter(name="about").update(status=OFFLINE)
        self.assertNotIn(self.loc("about"), self.sitemap())

    def sitemap(self) -> str:
        return self.client.get(reverse("website:sitemap")).content.decode()

    def loc(self, name: str) -> str:
        """
        The page's own <loc> line.

        Matching on the path alone would be wrong: /about-us/ is a prefix of
        /about-us/team/, so a loose check passes even when the page has gone.
        """
        return f"<loc>{settings.SITE_URL}{reverse(f'website:{name}')}</loc>"

    def test_a_page_with_no_row_still_renders_from_the_code_map(self):
        """A fresh install, before the seed migration, must still serve the site."""
        Page.objects.all().delete()
        for name in ("home", "about", "faq"):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(f"website:{name}")).status_code, 200)

    def test_with_no_rows_at_all_every_page_still_serves(self):
        """
        Losing the content rows must not take the site down. It changes what
        the site shows — see the next test — but every page still answers.
        """
        Page.objects.all().delete()
        for name, url in parity.targets():
            with self.subTest(page=name):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_with_no_rows_the_hidden_bands_come_back_rather_than_the_page_emptying(self):
        """
        The deliberate trade-off. An unknown switch means "shown", so a
        missing row can never silently delete a band of the site; the cost is
        that wiping the table un-hides the four bands Green Spark asked to
        hide. Showing too much is recoverable from the console. Showing
        nothing, with no way to tell why, is not.
        """
        Page.objects.all().delete()
        body = self.client.get(reverse("website:home")).content.decode()
        self.assertIn("Have your say", body)


class SingletonTests(TestCase):

    def test_load_creates_the_one_row_and_then_reuses_it(self):
        first = SiteSettings.load()
        second = SiteSettings.load()
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_saving_can_never_make_a_second_row(self):
        SiteSettings.load()
        extra = SiteSettings(site_name="Another one")
        extra.save()
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(SiteSettings.objects.get().site_name, "Another one")

    def test_deleting_does_nothing(self):
        settings_row = SiteSettings.load()
        settings_row.delete()
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_the_defaults_are_the_values_the_site_already_carried(self):
        contact = ContactDetails.load()
        self.assertEqual(contact.email, "info@greensparksolutions.com")
        self.assertEqual(contact.phone_display, "+61 402 832 972")
        self.assertEqual(contact.whatsapp_url, "https://wa.me/61402832972")


class SocialLinksTests(TestCase):

    def test_an_empty_address_hides_that_icon(self):
        links = SocialLinks.load()
        links.facebook = ""
        links.linkedin = "https://www.linkedin.com/company/example"
        links.save()
        shown = {item["key"] for item in SocialLinks.load().active()}
        self.assertIn("linkedin", shown)
        self.assertNotIn("facebook", shown)

    def test_only_whatsapp_is_set_to_begin_with(self):
        self.assertEqual([item["key"] for item in SocialLinks.load().active()], ["whatsapp"])


class NoticeBarTests(TestCase):

    def test_it_stays_down_until_it_is_turned_on(self):
        self.assertFalse(NoticeBar.load().is_showing)

    def test_it_needs_words_as_well_as_a_switch(self):
        bar = NoticeBar.load()
        bar.enabled = True
        bar.save()
        self.assertFalse(bar.is_showing)

    def test_it_shows_inside_its_window(self):
        today = timezone.localdate()
        bar = NoticeBar.load()
        bar.enabled = True
        bar.text = "Feedback round open until 9 January."
        bar.starts_at = today - timedelta(days=1)
        bar.ends_at = today + timedelta(days=1)
        bar.save()
        self.assertTrue(bar.is_showing)

    def test_it_takes_itself_down_when_the_window_closes(self):
        today = timezone.localdate()
        bar = NoticeBar.load()
        bar.enabled = True
        bar.text = "Feedback round closed."
        bar.starts_at = today - timedelta(days=30)
        bar.ends_at = today - timedelta(days=1)
        bar.save()
        self.assertFalse(bar.is_showing)

    def test_it_waits_for_its_start_date(self):
        today = timezone.localdate()
        bar = NoticeBar.load()
        bar.enabled = True
        bar.text = "Consultation coming up."
        bar.starts_at = today + timedelta(days=3)
        bar.save()
        self.assertFalse(bar.is_showing)

    def test_with_no_dates_it_shows_until_turned_off(self):
        bar = NoticeBar.load()
        bar.enabled = True
        bar.text = "Always on for now."
        bar.save()
        self.assertTrue(bar.is_showing)


class ApproachItemTests(TestCase):
    """The two approach bands on the home page come from the database."""

    def setUp(self):
        self.url = reverse("website:home")

    def test_the_seeded_wording_is_on_the_page(self):
        body = self.client.get(self.url).content.decode()
        self.assertIn("Community engagement", body)
        self.assertIn("Rooftop solar MRV, aggregated into one programme", body)

    def test_editing_a_point_changes_the_page(self):
        item = ApproachItem.objects.get(kind=ApproachItem.ATTRIBUTE, title="Partnerships")
        item.title = "Working with others"
        item.save()
        body = self.client.get(self.url).content.decode()
        self.assertIn("Working with others", body)
        self.assertNotIn("<h3 class=\"attr-card__title glow-text\">Partnerships</h3>", body)

    def test_the_first_card_is_the_open_one(self):
        body = self.client.get(self.url).content.decode()
        self.assertEqual(body.count('aria-expanded="true"'), 1)
        self.assertIn('<div class="xcard is-active">', body)

    def test_the_cards_are_numbered_in_order(self):
        body = self.client.get(self.url).content.decode()
        for number in ("01", "02", "03"):
            self.assertIn(f'<span class="xcard__num">{number}</span>', body)

    def test_reordering_moves_the_open_card(self):
        """The numbering and the open card follow the order, not a stored flag."""
        first, second = ApproachItem.objects.filter(kind=ApproachItem.HIGHLIGHT)[:2]
        first.sort_order, second.sort_order = second.sort_order, first.sort_order
        first.save()
        second.save()
        body = self.client.get(self.url).content.decode()
        opened = body.split('<div class="xcard is-active">')[1].split("</button>")[0]
        self.assertIn(second.title, opened)

    def test_a_point_with_no_link_renders_no_link(self):
        # These arrow links appear elsewhere on the page too, so count the
        # change rather than the total.
        before = self.client.get(self.url).content.decode().count('class="link-arrow "')
        item = ApproachItem.objects.filter(kind=ApproachItem.HIGHLIGHT).first()
        item.link_label = ""
        item.save()
        after = self.client.get(self.url).content.decode().count('class="link-arrow "')
        self.assertEqual(after, before - 1)


class CounterTests(TestCase):
    """An impact figure is a claim, so it stays off until someone approves it."""

    def test_the_seeded_figures_all_start_unapproved(self):
        self.assertEqual(Counter.objects.filter(published=True).count(), 0)
        self.assertEqual(Counter.objects.count(), 6)

    def test_every_figure_records_the_date_it_was_true(self):
        self.assertEqual(Counter.objects.filter(as_of__isnull=True).count(), 0)

    def test_the_estimated_figure_is_marked_as_one(self):
        self.assertTrue(Counter.objects.get(label="People benefiting").estimated)

    def test_a_figure_with_nothing_measured_yet_has_no_count(self):
        self.assertIsNone(Counter.objects.get(label="Firewood saved per year").count)


class DistrictTests(TestCase):

    def test_the_ten_districts_are_seeded_in_order(self):
        names = list(District.objects.values_list("name", flat=True))
        self.assertEqual(len(names), 10)
        self.assertEqual(names, sorted(names))

    def test_manikganj_is_the_base(self):
        base = District.objects.filter(is_base=True)
        self.assertEqual([d.name for d in base], ["Manikganj"])


class TopBarSwitchTests(TestCase):
    """
    The thin strip above the menu is site-wide chrome, not a page band, so it
    is a setting rather than a Section. Green Spark asked for it off, which
    migration 0013 records; the field itself still defaults to on, so the
    switch means "off" rather than "never existed" and they can put it back
    from the console.
    """

    MARKER = "site-topbar__wa"

    def test_the_field_still_defaults_to_on(self):
        self.assertTrue(SiteSettings().show_topbar)

    def test_it_is_off_as_shipped(self):
        self.assertFalse(SiteSettings.load().show_topbar)
        for name in ("home", "projects", "about", "enquire"):
            with self.subTest(page=name):
                self.assertNotContains(
                    self.client.get(reverse(f"website:{name}")), self.MARKER
                )

    def test_turning_it_back_on_restores_it_everywhere(self):
        row = SiteSettings.load()
        row.show_topbar = True
        row.save()
        for name in ("home", "projects", "about", "enquire"):
            with self.subTest(page=name):
                self.assertContains(
                    self.client.get(reverse(f"website:{name}")), self.MARKER
                )

    def test_the_switch_changes_nothing_but_the_bar(self):
        row = SiteSettings.load()
        row.show_topbar = True
        row.save()
        before = self.client.get(reverse("website:home")).content.decode()
        row.show_topbar = False
        row.save()
        after = self.client.get(reverse("website:home")).content.decode()

        # Only the top bar goes: what is left is what was left, in order.
        # The empty template line leaves blank lines behind where the bar
        # was, so runs of them are collapsed on both sides -- whitespace
        # between block elements is not something a reader can see.
        import re

        start = before.index('<div class="site-topbar">')
        end = before.index('<header', start)
        expected = before[:start] + before[end:]
        def squash(text):
            return re.sub(r"\n{2,}", "\n", text)

        self.assertEqual(squash(expected), squash(after))


class NavProjectTests(TestCase):
    """
    The Projects menu lists every project by name, and Home leads the menu.
    Both appear on every page, so they come from the context processor rather
    than a view.
    """

    def test_home_is_the_first_item_in_the_menu(self):
        body = self.client.get(reverse("website:about")).content.decode()
        nav = body[body.index('<ul class="site-nav__list">'):]
        self.assertLess(nav.index(">Home</a>"), nav.index("What We Do"))

    def test_every_project_is_named_in_the_menu(self):
        from .models import Project

        body = self.client.get(reverse("website:enquire")).content.decode()
        titles = list(Project.objects.values_list("title", flat=True))
        self.assertTrue(titles, "no projects to check")
        for title in titles:
            with self.subTest(project=title):
                self.assertIn(f"<strong>{title}</strong>", body)

    def test_a_new_project_appears_without_touching_a_template(self):
        from .models import Programme, Project

        Project.objects.create(
            slug="a-new-one", title="A New One", summary="Added in the console.",
            location="Somewhere", stage="Scoping", photo="safe-water",
            programme=Programme.objects.first(),
        )
        body = self.client.get(reverse("website:home")).content.decode()
        self.assertIn("<strong>A New One</strong>", body)
        self.assertIn('href="/projects/a-new-one/"', body)
