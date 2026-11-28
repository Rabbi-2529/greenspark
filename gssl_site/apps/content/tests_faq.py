"""
Tests for the FAQ page and the cookstove page's shorter FAQ.

The thing worth testing here is the numbering. Each accordion item carries an
``aria-controls``, an ``id`` and an ``aria-labelledby`` that have to agree with
each other, and on the FAQ page they run faq-0 to faq-19 across all five
topics rather than restarting in each one. None of that is stored, so these
tests are what stops a future change from quietly breaking the accordion for
anyone using a screen reader.
"""

from django.test import TestCase
from django.urls import reverse

from .models import FaqGroup, FaqItem, FaqPage, Programme


class FaqSeedTests(TestCase):

    def test_the_five_topics_are_seeded_in_page_order(self):
        self.assertEqual(
            [group.anchor for group in FaqGroup.objects.all()],
            ["about", "cooking", "carbon", "programmes", "feedback"],
        )

    def test_the_twenty_questions_are_seeded_under_their_topics(self):
        self.assertEqual(FaqItem.objects.filter(group__isnull=False).count(), 20)
        self.assertEqual(
            [group.questions.count() for group in FaqGroup.objects.all()],
            [4, 5, 5, 2, 4],
        )

    def test_the_cookstove_page_has_six_of_its_own(self):
        stove = Programme.objects.get(key="cookstove")
        self.assertEqual(stove.questions.count(), 6)

    def test_the_cookstove_questions_are_not_the_faq_page_questions(self):
        # It asks one thing the FAQ page does not ask at all.
        self.assertTrue(
            FaqItem.objects.filter(
                programme__key="cookstove",
                question="How much does a Green ICS cost a household?",
            ).exists()
        )
        self.assertFalse(
            FaqItem.objects.filter(
                group__isnull=False,
                question="How much does a Green ICS cost a household?",
            ).exists()
        )

    def test_internal_links_are_stored_as_routes_not_paths(self):
        answer = FaqItem.objects.get(
            question="Can my organisation partner with Green Spark?",
            group__isnull=False,
        ).answer
        self.assertIn('href="route:enquire"', answer)
        self.assertNotIn("/contact-us/", answer)

    def test_a_link_with_a_fragment_keeps_it(self):
        answer = FaqItem.objects.get(
            question="What comes after the priority programmes?"
        ).answer
        self.assertIn('href="route:projects#pipeline"', answer)

    def test_the_curly_quotes_survived_the_move(self):
        answer = FaqItem.objects.get(
            question="Can my organisation partner with Green Spark?",
            group__isnull=False,
        ).answer
        self.assertIn("“Partnership”", answer)

    def test_every_seeded_answer_passes_the_whitelist(self):
        # If one did not, an editor opening it in the console would be told the
        # content we shipped is invalid.
        from django.core.exceptions import ValidationError

        from .richtext import validate

        for item in FaqItem.objects.all():
            try:
                validate(item.answer)
            except ValidationError as problem:
                self.fail(f"{item.question}: {problem.messages}")


class NumberingTests(TestCase):
    """The ids, and which panel starts open."""

    def setUp(self):
        self.body = self.client.get(reverse("website:faq")).content.decode()

    def test_the_ids_run_across_the_whole_page_not_within_each_topic(self):
        for number in range(20):
            self.assertIn(f'aria-controls="faq-{number}"', self.body)
            self.assertIn(f'id="faq-b-{number}"', self.body)
        self.assertNotIn('aria-controls="faq-20"', self.body)

    def test_each_item_points_at_its_own_panel(self):
        for number in range(20):
            self.assertIn(
                f'id="faq-{number}" role="region" aria-labelledby="faq-b-{number}"',
                self.body,
            )

    def test_only_the_first_question_on_the_page_starts_open(self):
        self.assertEqual(self.body.count('aria-expanded="true"'), 1)
        self.assertEqual(self.body.count("accordion__panel is-open"), 1)

    def test_the_first_topic_is_the_one_holding_the_open_panel(self):
        self.assertIn('aria-expanded="true" aria-controls="faq-0"', self.body)

    def test_moving_a_topic_renumbers_the_questions_with_it(self):
        last = FaqGroup.objects.get(anchor="feedback")
        last.sort_order = 0
        last.save(update_fields=["sort_order"])
        body = self.client.get(reverse("website:faq")).content.decode()
        # "Feedback and privacy" has four questions, so it now owns faq-0..3
        # and the open panel, and the questions it used to hold are no longer
        # at the end.
        self.assertIn(
            'aria-controls="faq-0" id="faq-b-0">How can I give feedback', body,
        )
        self.assertEqual(body.count('aria-expanded="true"'), 1)
        for number in range(20):
            self.assertIn(f'aria-controls="faq-{number}"', body)

    def test_moving_a_question_between_topics_renumbers_both(self):
        question = FaqItem.objects.get(
            question="Can my organisation partner with Green Spark?",
            group__isnull=False,
        )
        question.group = FaqGroup.objects.get(anchor="feedback")
        question.save(update_fields=["group"])
        body = self.client.get(reverse("website:faq")).content.decode()
        self.assertEqual(body.count('class="accordion__item"'), 20)
        for number in range(20):
            self.assertIn(f'aria-controls="faq-{number}"', body)
        self.assertNotIn('aria-controls="faq-20"', body)

    def test_adding_a_question_extends_the_run_rather_than_repeating_an_id(self):
        FaqGroup.objects.get(anchor="about").questions.create(
            question="Is this a new question?", answer="It is.", sort_order=99,
        )
        body = self.client.get(reverse("website:faq")).content.decode()
        self.assertIn('aria-controls="faq-20"', body)
        self.assertEqual(
            len({f"faq-{n}" for n in range(21)}),
            sum(body.count(f'aria-controls="faq-{n}"') for n in range(21)),
        )

    def test_the_cookstove_page_numbers_its_own_six_from_zero(self):
        body = self.client.get(
            reverse("website:programme_improved_cookstove")
        ).content.decode()
        for number in range(6):
            self.assertIn(f'aria-controls="faq-{number}"', body)
        self.assertNotIn('aria-controls="faq-6"', body)
        self.assertEqual(body.count('aria-expanded="true"'), 1)


class FaqRenderTests(TestCase):

    def setUp(self):
        self.url = reverse("website:faq")

    def body(self) -> str:
        return self.client.get(self.url).content.decode()

    def test_it_renders_without_a_singleton_row(self):
        self.assertFalse(FaqPage.objects.exists())
        self.assertIn("Frequently asked questions", self.body())
        self.assertFalse(FaqPage.objects.exists(), "rendering the page wrote a row")

    def test_the_topic_list_is_the_topics(self):
        FaqGroup.objects.filter(anchor="cooking").update(title="Cooking at home")
        body = self.body()
        self.assertIn('<a href="#cooking">Cooking at home</a>', body)
        self.assertIn('<h2 class="faq-group__title">Cooking at home</h2>', body)

    def test_a_route_link_in_an_answer_resolves_to_the_page(self):
        self.assertIn(
            f'<a href="{reverse("website:enquire")}">Send us an enquiry</a>', self.body(),
        )

    def test_an_external_link_in_an_answer_keeps_its_new_tab_warning(self):
        self.assertIn(
            'rel="noopener">Phase 1 · GS13141'
            '<span class="visually-hidden"> (opens in a new tab)</span></a>',
            self.body(),
        )

    def test_an_answer_cannot_put_a_script_on_the_page(self):
        item = FaqItem.objects.filter(group__isnull=False).first()
        FaqItem.objects.filter(pk=item.pk).update(
            answer='Hi <script>alert(1)</script><a href="javascript:x">go</a>'
        )
        body = self.body()
        self.assertNotIn("<script>", body)
        self.assertNotIn("javascript:", body)
        self.assertIn("Hi alert(1)go", body)

    def test_an_answer_linking_to_a_route_that_has_gone_does_not_break_the_page(self):
        item = FaqItem.objects.filter(group__isnull=False).first()
        FaqItem.objects.filter(pk=item.pk).update(
            answer='See <a href="route:no_such_page">the old page</a>.'
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("See the old page.", response.content.decode())

    def test_an_empty_topic_renders_an_empty_accordion_rather_than_breaking(self):
        FaqGroup.objects.create(anchor="new", title="Nothing here yet", sort_order=99)
        body = self.body()
        self.assertIn('<a href="#new">Nothing here yet</a>', body)
        self.assertIn('id="new"', body)


class FaqItemPlacementTests(TestCase):

    def test_a_question_with_no_topic_and_no_programme_is_shown_nowhere(self):
        orphan = FaqItem.objects.create(question="Where am I?", answer="Nowhere.")
        self.assertTrue(orphan.shown_nowhere)
        self.assertEqual(orphan.where, "Not shown anywhere yet")
        self.assertNotIn(
            "Where am I?", self.client.get(reverse("website:faq")).content.decode(),
        )

    def test_a_question_can_appear_on_both_pages(self):
        both = FaqItem.objects.create(
            group=FaqGroup.objects.get(anchor="cooking"),
            programme=Programme.objects.get(key="cookstove"),
            question="Does it work in the rain?", answer="Yes.", sort_order=99,
        )
        self.assertIn("and", both.where)
        self.assertIn(
            "Does it work in the rain?",
            self.client.get(reverse("website:faq")).content.decode(),
        )
        self.assertIn(
            "Does it work in the rain?",
            self.client.get(
                reverse("website:programme_improved_cookstove")
            ).content.decode(),
        )
