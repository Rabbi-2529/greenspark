"""
The privacy policy.

The plan asked for one rich-text body and a pair of retention fields. The page
is thirteen headed sections with a thirteen-entry table of contents above them,
and the contents list has to agree with the headings exactly -- same words,
same anchors, same order. One body field makes keeping them in agreement an
editor's job, and the usual way a privacy policy goes wrong is that someone
edits a heading and forgets the link to it.

So the sections are rows and the contents list is derived from them. There is
no separate retention field either: "how long we keep it" is one of the
thirteen sections, written as prose, and splitting a sentence into a number and
a unit would not survive the first review by a lawyer.

The policy still needs that review. The note at the top of the template says
so, and it stays there until it has happened.
"""

from datetime import date

from django.db import models

from ..richtext import ALLOWED_TAGS_HELP
from ..richtext import render as render_inline
from ..richtext import to_text
from ..richtext import validate as validate_inline
from .base import Singleton


class PrivacyPage(Singleton):
    """The heading and the date at the top of the policy."""

    hero_tag = models.CharField("hero eyebrow", max_length=60, default="Legal")
    hero_title = models.CharField(
        "hero heading", max_length=200, default="Privacy policy",
    )
    updated_label = models.CharField(
        max_length=60, default="Last updated",
        help_text="Reads before the date, e.g. “Last updated 25 November 2026”.",
    )
    updated_on = models.DateField(
        "last updated",
        default=date(2026, 11, 25),
        help_text="Shown on the page and given to search engines in a form they can "
                  "read. Change it whenever the policy changes.",
    )

    class Meta:
        verbose_name = "privacy policy"
        verbose_name_plural = "privacy policy"

    def __str__(self) -> str:
        return self.hero_title


class PolicySection(models.Model):
    """One headed section of the policy."""

    anchor = models.SlugField(
        max_length=40, unique=True,
        help_text="The part after the # in a link to this section, e.g. “retention”. "
                  "Changing it breaks any link anyone has saved, and a privacy policy "
                  "is the sort of page people link to a particular part of.",
    )
    title = models.CharField(
        max_length=160, help_text="Appears as the heading and in the contents list.",
    )
    body = models.TextField(
        validators=[validate_inline],
        help_text="Paragraphs and lists. The tags allowed here are "
                  f"{ALLOWED_TAGS_HELP}; link to a page on this site with "
                  "href=&quot;route:enquire&quot; rather than a web address.",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]
        verbose_name = "policy section"
        verbose_name_plural = "policy sections"

    def __str__(self) -> str:
        return self.title

    @property
    def body_html(self):
        return render_inline(self.body)

    @property
    def body_words(self) -> str:
        """The prose without its markup, for a console list column."""
        return to_text(self.body)
