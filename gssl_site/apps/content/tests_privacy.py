"""
Tests for the privacy policy.

Two things matter on this page. The contents list has to agree with the
headings, because the usual way a policy page goes wrong is a heading edited
and the link to it left behind -- so the list is derived, and these tests prove
it follows. And the body is the one genuinely rich-text field on the site, so
there are tests that it keeps its lists and emphasis and refuses everything
else.
"""

from datetime import date

from django.test import TestCase
from django.urls import reverse

from .models import PolicySection, PrivacyPage


class PolicySeedTests(TestCase):

    def test_the_thirteen_sections_are_seeded_in_page_order(self):
        self.assertEqual(
            [section.anchor for section in PolicySection.objects.all()],
            ["about", "collect", "how", "use", "share", "overseas", "cookies",
             "security", "retention", "access", "complaints", "changes", "contact"],
        )

    def test_the_lists_and_emphasis_came_across(self):
        collect = PolicySection.objects.get(anchor="collect")
        self.assertIn("<ul><li><strong>Enquiries:</strong>", collect.body)
        about = PolicySection.objects.get(anchor="about")
        self.assertIn("<em>Privacy Act 1988</em>", about.body)

    def test_the_contact_section_kept_its_line_breaks_and_ampersand(self):
        contact = PolicySection.objects.get(anchor="contact")
        self.assertIn("<br>", contact.body)
        self.assertIn("Suite 4 &amp; 5", contact.body)

    def test_the_oaic_link_kept_its_new_tab_warning(self):
        complaints = PolicySection.objects.get(anchor="complaints")
        self.assertIn('target="_blank" rel="noopener"', complaints.body)
        self.assertIn("(opens in a new tab)", complaints.body)

    def test_every_seeded_section_passes_the_whitelist(self):
        from django.core.exceptions import ValidationError

        from .richtext import validate

        for section in PolicySection.objects.all():
            try:
                validate(section.body)
            except ValidationError as problem:
                self.fail(f"{section.anchor}: {problem.messages}")


class ContentsListTests(TestCase):
    """The list at the top of the page is the sections themselves."""

    def body(self) -> str:
        return self.client.get(reverse("website:privacy")).content.decode()

    def test_every_section_is_in_the_contents_list_and_has_a_heading(self):
        body = self.body()
        for section in PolicySection.objects.all():
            self.assertIn(f'<a href="#{section.anchor}">{section.title}</a>', body)
            self.assertIn(f'<h2 id="{section.anchor}">{section.title}</h2>', body)

    def test_renaming_a_section_renames_its_own_link(self):
        PolicySection.objects.filter(anchor="retention").update(
            title="How long we hold on to it",
        )
        body = self.body()
        self.assertIn('<a href="#retention">How long we hold on to it</a>', body)
        self.assertIn('<h2 id="retention">How long we hold on to it</h2>', body)
        self.assertNotIn("How long we keep it", body)

    def test_reordering_a_section_reorders_the_contents_list_with_it(self):
        PolicySection.objects.filter(anchor="contact").update(sort_order=0)
        body = self.body()
        toc = body[body.index('class="policy__toc"'):body.index("</nav>", body.index('class="policy__toc"'))]
        self.assertLess(toc.index("#contact"), toc.index("#about"))
        self.assertLess(body.index('<h2 id="contact">'), body.index('<h2 id="about">'))

    def test_a_new_section_appears_in_both_places(self):
        PolicySection.objects.create(
            anchor="analytics", title="Website analytics",
            body="<p>We do not use any.</p>", sort_order=99,
        )
        body = self.body()
        self.assertIn('<a href="#analytics">Website analytics</a>', body)
        self.assertIn('<h2 id="analytics">Website analytics</h2>', body)
        self.assertIn("<p>We do not use any.</p>", body)


class PrivacyRenderTests(TestCase):

    def setUp(self):
        self.url = reverse("website:privacy")

    def body(self) -> str:
        return self.client.get(self.url).content.decode()

    def test_it_renders_without_a_singleton_row(self):
        self.assertFalse(PrivacyPage.objects.exists())
        self.assertIn("Privacy policy", self.body())
        self.assertFalse(PrivacyPage.objects.exists(), "rendering the page wrote a row")

    def test_the_date_is_shown_twice_in_two_forms_from_one_field(self):
        self.assertIn('<time datetime="2026-11-25">25 November 2026</time>', self.body())

    def test_changing_the_date_changes_both_forms_of_it(self):
        PrivacyPage.objects.create(updated_on=date(2027, 3, 1))
        self.assertIn('<time datetime="2027-03-01">1 March 2027</time>', self.body())

    def test_a_section_cannot_put_a_script_on_the_page(self):
        PolicySection.objects.filter(anchor="about").update(
            body='<p>Hello</p><script>alert(1)</script>'
        )
        body = self.body()
        self.assertNotIn("<script>", body)
        self.assertIn("<p>Hello</p>", body)

    def test_a_section_cannot_put_an_inline_style_on_the_page(self):
        # The site's CSP forbids inline styles and the console's tests assert
        # none is on any page; a content field must not be the way round it.
        PolicySection.objects.filter(anchor="about").update(
            body='<p style="color:red">Red</p>'
        )
        body = self.body()
        self.assertNotIn("style=", body[body.index('class="policy__body"'):])
        self.assertIn("<p>Red</p>", body)

    def test_an_empty_section_renders_a_heading_and_nothing_under_it(self):
        PolicySection.objects.filter(anchor="about").update(body="")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('<h2 id="about">About this policy</h2>', response.content.decode())


class PrivacySingletonTests(TestCase):

    def test_there_is_only_ever_one(self):
        PrivacyPage.objects.create(hero_title="First")
        PrivacyPage.objects.create(hero_title="Second")
        self.assertEqual(PrivacyPage.objects.count(), 1)
