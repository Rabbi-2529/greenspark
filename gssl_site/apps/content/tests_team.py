"""
Tests for the Our team page.

The interesting one is the circle beside a leader's name. It holds initials,
and the template no longer holds them: they are worked out from the name, so
correcting a spelling corrects the circle too. Everything else here is the
usual -- the page follows the database, and a half-filled record renders
without an empty element.
"""

from django.test import TestCase
from django.urls import reverse

from .models import TeamGroup, TeamLeader, TeamPage


class TeamSeedTests(TestCase):

    def test_the_leader_is_seeded(self):
        leader = TeamLeader.objects.get()
        self.assertEqual(leader.name, "Pankaj Rajbangshi")
        self.assertEqual(leader.role, "Director and CEO")
        self.assertIn("Rockdale, NSW", leader.organisation)

    def test_the_five_teams_are_seeded_in_order(self):
        self.assertEqual(
            [group.title for group in TeamGroup.objects.all()],
            [
                "Field operations · Manikganj",
                "Carbon and monitoring",
                "Engineering and research",
                "Community and stakeholder engagement",
                "Partnerships · Australia",
            ],
        )

    def test_the_initials_are_not_stored(self):
        # "PR" is what the name gives, so storing a copy of it would only give
        # it somewhere to go wrong.
        self.assertEqual(TeamLeader.objects.get().initials, "")


class MonogramTests(TestCase):
    """What goes in the circle."""

    def monogram(self, name, initials=""):
        return TeamLeader(name=name, initials=initials).monogram

    def test_a_first_and_last_name_give_two_letters(self):
        self.assertEqual(self.monogram("Pankaj Rajbangshi"), "PR")

    def test_a_middle_name_is_skipped(self):
        self.assertEqual(self.monogram("Anna Maria Fletcher"), "AF")

    def test_one_name_gives_one_letter(self):
        self.assertEqual(self.monogram("Pankaj"), "P")

    def test_a_lower_case_name_still_gives_capitals(self):
        self.assertEqual(self.monogram("ada lovelace"), "AL")

    def test_an_override_wins_for_the_names_the_rule_gets_wrong(self):
        self.assertEqual(self.monogram("Md. Shahidul Islam", initials="MSI"), "MSI")

    def test_an_empty_name_gives_an_empty_circle_rather_than_an_error(self):
        self.assertEqual(self.monogram(""), "")

    def test_correcting_the_name_corrects_the_circle(self):
        leader = TeamLeader.objects.get()
        leader.name = "Pankaj Rajbongshi"
        leader.save(update_fields=["name"])
        body = self.client.get(reverse("website:team")).content.decode()
        self.assertIn('aria-hidden="true">PR</span>', body)
        self.assertIn("Pankaj Rajbongshi", body)


class TeamRenderTests(TestCase):

    def setUp(self):
        self.url = reverse("website:team")

    def body(self) -> str:
        return self.client.get(self.url).content.decode()

    def test_it_renders_without_a_singleton_row(self):
        self.assertFalse(TeamPage.objects.exists())
        self.assertIn("The people behind Green Spark", self.body())
        self.assertFalse(TeamPage.objects.exists(), "rendering the page wrote a row")

    def test_changing_a_heading_changes_the_page(self):
        TeamPage.objects.create(groups_title="Six teams, one way of working")
        self.assertIn("Six teams, one way of working", self.body())

    def test_a_second_leader_appears_without_touching_a_template(self):
        TeamLeader.objects.create(
            name="Rupa Das", role="Head of monitoring",
            organisation="Green Spark Solutions Ltd · Manikganj",
            bio="Runs the monitoring programme.", sort_order=2,
        )
        body = self.body()
        self.assertIn("Rupa Das", body)
        self.assertIn('aria-hidden="true">RD</span>', body)

    def test_a_leader_with_no_company_or_bio_yet_has_no_empty_paragraphs(self):
        TeamLeader.objects.update(organisation="", bio="")
        body = self.body()
        self.assertIn("Pankaj Rajbangshi", body)
        self.assertNotIn('<p class="team-card__org"></p>', body)
        self.assertNotIn('<p class="team-card__bio"></p>', body)

    def test_reordering_the_teams_reorders_the_page(self):
        last = TeamGroup.objects.last()
        last.sort_order = 0
        last.save(update_fields=["sort_order"])
        body = self.body()
        self.assertLess(
            body.index("Partnerships · Australia"),
            body.index("Field operations · Manikganj"),
        )

    def test_a_new_team_appears_without_touching_a_template(self):
        TeamGroup.objects.create(
            title="Data and reporting", body="Keeps the numbers.", sort_order=99,
        )
        self.assertIn("Data and reporting", self.body())


class TeamSingletonTests(TestCase):

    def test_there_is_only_ever_one(self):
        TeamPage.objects.create(hero_title="First")
        TeamPage.objects.create(hero_title="Second")
        self.assertEqual(TeamPage.objects.count(), 1)
