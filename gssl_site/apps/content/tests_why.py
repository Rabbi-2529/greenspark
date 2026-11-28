"""
Tests for the Why GSSL page.

The page is UNLISTED, so two things need asserting that the other pages do not
need: that it still answers, and that moving its content into the database did
not quietly publish it.
"""

from django.test import TestCase
from django.urls import reverse

from .models import Page, WhyGsslPage, WhyItem
from .models.pages import UNLISTED


class WhyGsslSeedTests(TestCase):

    def test_the_three_bands_are_seeded_in_order(self):
        self.assertEqual(
            [item.title for item in WhyItem.objects.filter(kind=WhyItem.REASON)],
            [
                "Built with communities",
                "Held to recognised standards",
                "Monitoring you can check",
                "On the ground in three countries",
                "A pipeline beyond cookstoves",
                "Local skills and jobs",
            ],
        )
        self.assertEqual(
            WhyItem.objects.filter(kind=WhyItem.EXPECTATION).count(), 3,
        )
        self.assertEqual(
            [item.title for item in WhyItem.objects.filter(kind=WhyItem.STEP)],
            ["Listen and plan", "Design and test", "Install and train",
             "Monitor and verify"],
        )

    def test_the_curly_apostrophe_survived_the_move(self):
        step = WhyItem.objects.get(kind=WhyItem.STEP, title="Listen and plan")
        self.assertIn("community’s needs", step.body)

    def test_the_cards_and_steps_carry_icons_and_the_plain_cards_do_not(self):
        for item in WhyItem.objects.exclude(kind=WhyItem.EXPECTATION):
            self.assertTrue(item.icon_path, f"{item.title} draws no icon")
        for item in WhyItem.objects.filter(kind=WhyItem.EXPECTATION):
            self.assertEqual(item.icon, "")


class WhyGsslStatusTests(TestCase):
    """Moving the content into the database must not publish the page."""

    def test_the_page_is_still_unlisted(self):
        self.assertEqual(Page.objects.get(name="why_gssl").status, UNLISTED)

    def test_it_answers_and_tells_search_engines_to_stay_away(self):
        response = self.client.get(reverse("website:why_gssl"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("noindex", response.content.decode())

    def test_it_is_not_in_the_sitemap(self):
        sitemap = self.client.get(reverse("website:sitemap")).content.decode()
        self.assertNotIn("/why-gssl/", sitemap)


class WhyGsslRenderTests(TestCase):

    def setUp(self):
        self.url = reverse("website:why_gssl")

    def body(self) -> str:
        return self.client.get(self.url).content.decode()

    def test_it_renders_without_a_singleton_row(self):
        self.assertFalse(WhyGsslPage.objects.exists())
        self.assertIn("Carbon projects that start with communities", self.body())
        self.assertFalse(WhyGsslPage.objects.exists(), "rendering the page wrote a row")

    def test_changing_a_heading_changes_the_page(self):
        WhyGsslPage.objects.create(steps_title="How a project actually runs")
        self.assertIn("How a project actually runs", self.body())

    def test_the_reveal_delays_restart_on_each_row_of_three(self):
        # The cards sit in a three-column grid, so the stagger belongs to the
        # row, not to the whole list: card 4 starts again at no delay.
        body = self.body()
        self.assertIn('<article class="attr-card" data-reveal>'
                      '<span class="attr-card__icon">', body)
        self.assertIn("Monitoring you can check", body)
        cards = body.split('<article class="attr-card')
        classes = [card.split('"', 1)[0] for card in cards[1:7]]
        self.assertEqual(
            classes, ["", " reveal-d1", " reveal-d2", "", " reveal-d1", " reveal-d2"],
        )

    def test_the_step_count_drives_the_grid(self):
        self.assertIn('class="process process--4"', self.body())
        WhyItem.objects.filter(kind=WhyItem.STEP, title="Monitor and verify").delete()
        self.assertIn('class="process process--3"', self.body())

    def test_a_step_with_no_icon_renders_without_an_empty_svg(self):
        WhyItem.objects.filter(kind=WhyItem.STEP).update(icon="")
        body = self.body()
        self.assertIn('<h3 class="process__title">Listen and plan</h3>', body)
        self.assertNotIn('<h3 class="process__title"><svg', body)

    def test_a_point_naming_an_icon_that_has_gone_still_renders(self):
        WhyItem.objects.update(icon="no-such-icon")
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_a_new_reason_appears_without_touching_a_template(self):
        WhyItem.objects.create(
            kind=WhyItem.REASON, icon="leaf", title="A seventh reason",
            body="Because there is one.", sort_order=99,
        )
        self.assertIn("A seventh reason", self.body())

    def test_reordering_the_steps_reorders_the_page(self):
        first = WhyItem.objects.get(kind=WhyItem.STEP, title="Listen and plan")
        first.sort_order = 99
        first.save(update_fields=["sort_order"])
        body = self.body()
        self.assertLess(body.index("Monitor and verify"), body.index("Listen and plan"))


class WhyGsslSingletonTests(TestCase):

    def test_there_is_only_ever_one(self):
        WhyGsslPage.objects.create(hero_title="First")
        WhyGsslPage.objects.create(hero_title="Second")
        self.assertEqual(WhyGsslPage.objects.count(), 1)
