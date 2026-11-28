"""
Tests for the About Us page.

The golden HTML test proves the page still renders byte for byte what it
rendered before. What it cannot prove is that the page follows the database
*afterwards* -- that changing a heading changes the page, that reordering the
cards moves the reveal delays with them, and that the Careers band reads
correctly both with no published role and with several. That is what is here.
"""

from datetime import date

from django.test import TestCase
from django.urls import reverse

from .models import (
    AboutPage, AboutStat, ApproachItem, Audience, CareerArea, JobOpening,
    VisionAttribute,
)


class AboutSeedTests(TestCase):
    """The migration brought the template's own wording into the database."""

    def test_the_three_figures_are_seeded_in_order(self):
        self.assertEqual(
            [stat.value for stat in AboutStat.objects.all()], ["2", "3", "2"],
        )
        self.assertTrue(
            AboutStat.objects.first().label.startswith("offices: Rockdale"),
        )

    def test_the_three_vision_points_are_seeded_in_order(self):
        self.assertEqual(
            [item.title for item in VisionAttribute.objects.all()],
            [
                "Environmental and social impact",
                "Global access to clean energy",
                "Innovative solutions and community empowerment",
            ],
        )

    def test_the_approach_cards_are_a_third_kind_of_approach_item(self):
        titles = [
            item.title
            for item in ApproachItem.objects.filter(kind=ApproachItem.ABOUT)
        ]
        self.assertEqual(
            titles, ["Community engagement", "Partnerships", "Research and development"],
        )

    def test_the_home_page_cards_are_untouched_by_the_new_kind(self):
        self.assertEqual(
            ApproachItem.objects.filter(kind=ApproachItem.HIGHLIGHT).count(), 3,
        )
        self.assertEqual(
            ApproachItem.objects.filter(kind=ApproachItem.ATTRIBUTE).count(), 3,
        )

    def test_only_the_about_cards_carry_an_icon(self):
        for item in ApproachItem.objects.exclude(kind=ApproachItem.ABOUT):
            self.assertEqual(item.icon, "")
        for item in ApproachItem.objects.filter(kind=ApproachItem.ABOUT):
            self.assertTrue(item.icon_path, f"{item.title} draws no icon")

    def test_the_six_partner_types_are_seeded_with_icons(self):
        partners = list(Audience.objects.all())
        self.assertEqual(len(partners), 6)
        self.assertEqual(partners[0].title, "Communities")
        self.assertEqual(partners[-1].title, "Press and job seekers")
        for partner in partners:
            self.assertTrue(partner.icon_path, f"{partner.title} draws no icon")

    def test_the_three_areas_of_work_are_seeded(self):
        self.assertEqual(CareerArea.objects.count(), 3)

    def test_no_role_ships_published(self):
        # The band's empty state is what the site shows, and it has to be what
        # a fresh database shows too.
        self.assertEqual(JobOpening.objects.count(), 0)


class AboutRenderTests(TestCase):
    """The page follows the database once someone changes something."""

    def setUp(self):
        self.url = reverse("website:about")

    def body(self) -> str:
        return self.client.get(self.url).content.decode()

    def test_it_renders_without_a_singleton_row(self):
        # Nothing seeds AboutPage: the field defaults are the wording, so the
        # page has to render from an unsaved instance.
        self.assertFalse(AboutPage.objects.exists())
        self.assertIn("Clean energy and healthier homes, built with communities", self.body())
        self.assertFalse(AboutPage.objects.exists(), "rendering the page wrote a row")

    def test_changing_the_hero_heading_changes_the_page(self):
        AboutPage.objects.create(hero_title="Something else entirely")
        self.assertIn("Something else entirely", self.body())

    def test_the_intro_paragraph_keeps_its_highlight(self):
        self.assertIn("<mark>clean energy</mark>", self.body())

    def test_the_intro_paragraph_cannot_smuggle_a_script_onto_the_page(self):
        AboutPage.objects.create(intro_text="Hello <script>alert(1)</script>")
        body = self.body()
        self.assertNotIn("<script>alert(1)</script>", body)
        self.assertIn("Hello alert(1)", body)

    def test_the_vision_cards_are_numbered_by_their_order(self):
        body = self.body()
        self.assertIn('class="attr-card attr-card--plain" data-reveal>'
                      '<h3 class="attr-card__title glow-text">'
                      "Environmental and social impact", body)
        self.assertIn('class="attr-card attr-card--plain reveal-d2" data-reveal>'
                      '<h3 class="attr-card__title glow-text">'
                      "Innovative solutions and community empowerment", body)

    def test_reordering_the_vision_cards_moves_the_delays_with_them(self):
        first, *_, last = list(VisionAttribute.objects.all())
        first.sort_order, last.sort_order = last.sort_order, first.sort_order
        first.save(update_fields=["sort_order"])
        last.save(update_fields=["sort_order"])
        body = self.body()
        self.assertIn(f'attr-card--plain" data-reveal><h3 class="attr-card__title '
                      f'glow-text">{last.title}', body)
        self.assertIn(f'reveal-d2" data-reveal><h3 class="attr-card__title '
                      f'glow-text">{first.title}', body)

    def test_a_partner_type_with_no_icon_renders_without_an_empty_icon(self):
        Audience.objects.update(icon="")
        body = self.body()
        self.assertNotIn('<span class="impact-grid__icon"></span>', body)
        self.assertNotIn('<span class="impact-grid__icon"><svg', body)
        self.assertIn("Communities", body)

    def test_a_partner_type_naming_an_icon_that_has_gone_still_renders(self):
        Audience.objects.update(icon="no-such-icon")
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_a_new_partner_type_appears_without_touching_a_template(self):
        Audience.objects.create(
            icon="leaf", title="Tree planters", body="They plant trees.", sort_order=99,
        )
        self.assertIn("Tree planters", self.body())


class CareersBandTests(TestCase):
    """With no role published the band has to read exactly as it does today."""

    def setUp(self):
        self.url = reverse("website:about")

    def body(self) -> str:
        return self.client.get(self.url).content.decode()

    def test_with_no_roles_the_empty_state_shows(self):
        self.assertIn("There are no open roles right now", self.body())

    def test_an_unpublished_role_is_not_shown_and_the_empty_state_stays(self):
        # A title the page does not already contain: the seeded areas of work
        # talk about field officers too.
        JobOpening.objects.create(title="Kiln technician", summary="Fire bricks.")
        body = self.body()
        self.assertNotIn("Kiln technician", body)
        self.assertIn("There are no open roles right now", body)

    def test_publishing_a_role_lists_it_and_drops_the_empty_state(self):
        JobOpening.objects.create(
            title="Field officer", location="Manikganj, Bangladesh",
            employment_type=JobOpening.FULL_TIME, summary="Install stoves.",
            published=True,
        )
        body = self.body()
        self.assertIn("Field officer", body)
        self.assertIn("Manikganj, Bangladesh · Full time", body)
        self.assertNotIn("There are no open roles right now", body)
        self.assertNotIn("empty state: shown when there are no published openings", body)

    def test_a_role_with_no_location_or_type_has_no_empty_meta_line(self):
        JobOpening.objects.create(title="Volunteer", summary="Help out.", published=True)
        body = self.body()
        self.assertIn("Volunteer", body)
        self.assertNotIn('<p class="attr-card__text text-muted-gs"></p>', body)

    def test_a_closing_date_is_shown_as_a_date_a_machine_can_read(self):
        JobOpening.objects.create(
            title="Analyst", summary="Numbers.", closes_on=date(2027, 1, 31),
            published=True,
        )
        self.assertIn('<time datetime="2027-01-31">31 January 2027</time>', self.body())

    def test_a_role_with_no_way_to_apply_renders_without_an_apply_link(self):
        JobOpening.objects.create(title="Analyst", summary="Numbers.", published=True)
        body = self.body()
        self.assertIn("Analyst", body)
        self.assertNotIn("Apply for this role", body)

    def test_an_email_only_role_gets_a_mailto_with_the_role_in_the_subject(self):
        JobOpening.objects.create(
            title="Field officer", summary="Install stoves.",
            apply_email="jobs@example.com", published=True,
        )
        self.assertIn(
            'href="mailto:jobs@example.com?subject=Field%20officer"', self.body(),
        )

    def test_a_link_wins_over_an_email_address(self):
        role = JobOpening.objects.create(
            title="Analyst", summary="Numbers.", apply_email="jobs@example.com",
            apply_url="https://example.com/apply", published=True,
        )
        self.assertEqual(role.apply_href, "https://example.com/apply")

    def test_the_cv_button_quotes_its_subject(self):
        page = AboutPage.objects.create(cv_subject="Careers at GSSL")
        self.assertEqual(
            page.cv_mailto,
            "mailto:info@greensparksolutions.com?subject=Careers%20at%20GSSL",
        )

    def test_a_cv_subject_with_an_ampersand_in_it_still_makes_one_link(self):
        page = AboutPage.objects.create(cv_subject="Jobs & volunteering")
        self.assertIn("subject=Jobs%20%26%20volunteering", page.cv_mailto)

    def test_clearing_the_cv_address_drops_the_link_rather_than_breaking_it(self):
        page = AboutPage.objects.create(cv_email="")
        self.assertEqual(page.cv_mailto, "")


class AboutSingletonTests(TestCase):

    def test_there_is_only_ever_one(self):
        AboutPage.objects.create(hero_title="First")
        AboutPage.objects.create(hero_title="Second")
        self.assertEqual(AboutPage.objects.count(), 1)
        self.assertEqual(AboutPage.objects.get().hero_title, "Second")
