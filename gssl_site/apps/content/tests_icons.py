"""
Tests for the two pieces of shared machinery Phase 5 needed.

The icon library and the limited-HTML field are not content: they are what lets
content carry an icon and a link without carrying markup an editor could break
the site with. Both are tested against the templates themselves, because the
templates are what the golden HTML harness holds the site to.
"""

import re
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from . import icons, richtext

TEMPLATES = Path(settings.BASE_DIR) / "templates"

# Every icon on the site is drawn this way: a stroke path and its echo.
ICON_SVG = re.compile(
    r'<svg class="icon[^"]*"[^>]*>'
    r'<path d="([^"]*)"/>'
    r'<path class="icon__echo" d="([^"]*)"/>'
    r"</svg>"
)


def icon_pairs_in_templates() -> set[tuple[str, str]]:
    found = set()
    for path in sorted(TEMPLATES.rglob("*.html")):
        found.update(ICON_SVG.findall(path.read_text(encoding="utf-8")))
    return found


class IconLibraryTests(TestCase):
    """The library has to be able to draw every icon the site already draws."""

    def test_every_icon_in_the_templates_is_in_the_library(self):
        known = {(icon.path, icon.echo) for icon in icons.ICONS.values()}
        missing = icon_pairs_in_templates() - known
        self.assertEqual(missing, set(), "an icon in a template is not in icons.py")

    def test_no_two_icons_share_a_drawing(self):
        drawings = [(icon.path, icon.echo) for icon in icons.ICONS.values()]
        self.assertEqual(len(drawings), len(set(drawings)))

    def test_every_icon_has_a_name_a_person_would_recognise(self):
        unlabelled = [name for name, icon in icons.ICONS.items() if not icon.label]
        self.assertEqual(unlabelled, [])

    def test_the_path_data_needs_no_escaping(self):
        # If it ever did, every rewired loop would differ from its golden file
        # by an &amp; or a &quot;, so this is worth asserting rather than
        # discovering.
        allowed = set("0123456789.,- ")
        for name, icon in icons.ICONS.items():
            for drawing in (icon.path, icon.echo):
                stray = {c for c in drawing if not (c.isalpha() or c in allowed)}
                self.assertEqual(stray, set(), f"{name} has {stray} in its path data")

    def test_the_choices_are_offered_in_alphabetical_order_of_label(self):
        labels = [label for _, label in icons.CHOICES]
        self.assertEqual(labels, sorted(labels))

    def test_a_row_with_no_icon_draws_nothing(self):
        class Row(icons.IconMixin):
            icon = ""

        self.assertEqual(Row().icon_path, "")
        self.assertEqual(Row().icon_echo, "")

    def test_a_row_naming_an_icon_that_has_gone_draws_nothing(self):
        class Row(icons.IconMixin):
            icon = "no-such-icon"

        self.assertEqual(Row().icon_path, "")
        self.assertEqual(Row().icon_echo, "")


class InlineHtmlTests(TestCase):
    """What an editor may type into a policy section or an FAQ answer."""

    def test_plain_words_come_back_unchanged(self):
        self.assertEqual(richtext.render("Just words."), "Just words.")

    def test_the_tags_the_pages_use_are_kept(self):
        markup = "<p>A <strong>bold</strong> and <em>italic</em> <mark>mark</mark>.</p>"
        self.assertEqual(richtext.render(markup), markup)

    def test_a_list_is_kept(self):
        markup = "<ul><li>One</li>\n<li>Two</li></ul>"
        self.assertEqual(richtext.render(markup), markup)

    def test_an_ampersand_is_escaped_the_way_django_escapes_one(self):
        self.assertEqual(richtext.render("Suite 4 & 5"), "Suite 4 &amp; 5")
        self.assertEqual(richtext.render("Suite 4 &amp; 5"), "Suite 4 &amp; 5")

    def test_an_external_link_keeps_its_target_and_rel(self):
        markup = (
            '<a href="https://www.oaic.gov.au" target="_blank" rel="noopener">'
            'oaic.gov.au<span class="visually-hidden"> (opens in a new tab)</span></a>'
        )
        self.assertEqual(richtext.render(markup), markup)

    def test_a_route_link_resolves_to_the_page_it_names(self):
        rendered = richtext.render('<a href="route:enquire">Send us an enquiry</a>')
        self.assertEqual(
            rendered, f'<a href="{reverse("website:enquire")}">Send us an enquiry</a>'
        )

    def test_a_route_link_keeps_its_fragment(self):
        rendered = richtext.render('<a href="route:projects#pipeline">pipeline</a>')
        self.assertEqual(
            rendered, f'<a href="{reverse("website:projects")}#pipeline">pipeline</a>'
        )

    def test_a_link_to_a_route_that_has_gone_renders_as_its_own_words(self):
        # An editor's paragraph must never be able to 500 the page it is on.
        self.assertEqual(
            richtext.render('<p>See <a href="route:gone">the old page</a>.</p>'),
            "<p>See the old page.</p>",
        )

    def test_a_script_is_dropped_and_refused(self):
        self.assertEqual(richtext.render("<script>alert(1)</script>"), "alert(1)")
        with self.assertRaises(ValidationError):
            richtext.validate("<script>alert(1)</script>")

    def test_an_event_handler_is_dropped_and_refused(self):
        self.assertEqual(
            richtext.render('<p onclick="go()">Hello</p>'), "<p>Hello</p>"
        )
        with self.assertRaises(ValidationError):
            richtext.validate('<p onclick="go()">Hello</p>')

    def test_an_inline_style_is_dropped_and_refused(self):
        self.assertEqual(
            richtext.render('<p style="color:red">Hello</p>'), "<p>Hello</p>"
        )
        with self.assertRaises(ValidationError):
            richtext.validate('<p style="color:red">Hello</p>')

    def test_a_javascript_link_is_dropped_and_refused(self):
        self.assertEqual(
            richtext.render('<a href="javascript:alert(1)">click</a>'), "click"
        )
        with self.assertRaises(ValidationError):
            richtext.validate('<a href="javascript:alert(1)">click</a>')

    def test_an_image_is_dropped_and_refused(self):
        self.assertEqual(richtext.render('<img src="x" onerror="go()">'), "")
        with self.assertRaises(ValidationError):
            richtext.validate('<img src="x" onerror="go()">')

    def test_a_span_may_only_be_the_screen_reader_one(self):
        self.assertEqual(
            richtext.render('<span class="badge">x</span>'), "x"
        )
        with self.assertRaises(ValidationError):
            richtext.validate('<span class="badge">x</span>')

    def test_an_unclosed_tag_is_closed_and_refused(self):
        self.assertEqual(richtext.render("<p>Hello"), "<p>Hello</p>")
        with self.assertRaises(ValidationError):
            richtext.validate("<p>Hello")

    def test_the_error_names_the_tag_that_was_the_problem(self):
        with self.assertRaises(ValidationError) as caught:
            richtext.validate("<iframe src='x'></iframe>")
        self.assertIn("iframe", " ".join(caught.exception.messages))

    def test_empty_is_fine(self):
        self.assertEqual(richtext.render(""), "")
        self.assertIsNone(richtext.validate(""))

    def test_the_words_can_be_read_without_the_markup(self):
        self.assertEqual(
            richtext.to_text('<p>A <a href="route:enquire">link</a> here.</p>'),
            "A link here.",
        )
