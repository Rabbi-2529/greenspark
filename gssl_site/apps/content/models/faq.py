"""
The FAQ page, and the shorter FAQ on a programme page.

The hard part of this page is not the words, it is the numbering. Every
accordion item carries three ids that have to agree with each other --

    <button aria-expanded="true" aria-controls="faq-0" id="faq-b-0">
    <div class="accordion__panel is-open" id="faq-0" aria-labelledby="faq-b-0">

-- and on the FAQ page they run ``faq-0`` to ``faq-19`` across all five groups,
not from zero within each one. So the number is not a field. It is the row's
position on the page, worked out at render time by ``number_questions`` below,
which means moving a question, reordering a group or moving a question from one
group to another renumbers everything after it and the aria wiring follows.
Storing the number would make that an editor's problem, and a silent one: a
mismatched ``aria-controls`` breaks the accordion only for someone using a
screen reader.

"Open" is derived the same way. Exactly one item on a page starts open -- the
first -- and which one that is follows from the order.
"""

from django.db import models

from ..richtext import ALLOWED_TAGS_HELP
from ..richtext import render as render_inline
from ..richtext import to_text
from ..richtext import validate as validate_inline
from .base import Singleton


def number_questions(questions, start: int = 0) -> list:
    """
    The questions in order, each told where it sits on the page.

    ``number`` builds the ids; ``is_open`` is true for the first item on the
    page and nothing else. Both are attached to the instances rather than
    saved, so they cannot be edited out of step with the order.
    """
    items = list(questions)
    for offset, item in enumerate(items, start=start):
        item.number = offset
        item.is_open = offset == 0
    return items


class FaqPage(Singleton):
    """The wording on the FAQ page that there is only one of."""

    hero_tag = models.CharField("hero eyebrow", max_length=60, default="Help centre")
    hero_title = models.CharField(
        "hero heading", max_length=200, default="Frequently asked questions",
    )
    hero_lead = models.TextField(
        default="Clear answers about our programmes, Gold Standard registration, "
                "feedback and privacy.",
    )
    closing_title = models.CharField(
        "closing heading", max_length=200, default="Still have a question?",
    )
    closing_text = models.TextField(
        default="Send us an enquiry or share feedback, in Bangla or English. We usually "
                "reply within one working day.",
    )
    enquire_label = models.CharField(max_length=60, default="Enquire")

    class Meta:
        verbose_name = "FAQ page"
        verbose_name_plural = "FAQ page"

    def __str__(self) -> str:
        return self.hero_title


class FaqGroup(models.Model):
    """
    One topic on the FAQ page: a heading, and the questions under it.

    The topic list at the top of the page is these rows. Its links are the
    anchors and its labels are the titles, so a renamed topic renames its own
    link and cannot be left pointing at a heading that no longer says that.
    """

    anchor = models.SlugField(
        max_length=40, unique=True,
        help_text="The part after the # in a link to this topic, e.g. “carbon”. "
                  "Changing it breaks any link anyone has saved to this topic.",
    )
    title = models.CharField(max_length=160)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]
        verbose_name = "FAQ topic"
        verbose_name_plural = "FAQ topics"

    def __str__(self) -> str:
        return self.title

    @classmethod
    def with_questions(cls) -> list:
        """
        The topics, each carrying its questions numbered across the whole page.

        One query for the topics and one for the questions, and the numbering
        runs through them in page order -- see the module docstring for why it
        is not a field.
        """
        groups = list(cls.objects.prefetch_related("questions"))
        number = 0
        for group in groups:
            group.numbered = number_questions(group.questions.all(), start=number)
            number += len(group.numbered)
        return groups


class FaqItem(models.Model):
    """
    One question and its answer.

    A question belongs to a topic on the FAQ page, to a programme page, or to
    both: the cookstove page asks six of its own, in shorter words than the FAQ
    page uses, so they are their own rows rather than a filtered view of it.
    Setting both is allowed and means one answer appearing in both places,
    which is sometimes exactly what is wanted; setting neither means an answer
    nobody can read, so the console says so rather than hiding it.
    """

    group = models.ForeignKey(
        FaqGroup, null=True, blank=True, on_delete=models.CASCADE,
        related_name="questions",
        help_text="The topic this appears under on the FAQ page.",
    )
    programme = models.ForeignKey(
        "content.Programme", null=True, blank=True, on_delete=models.CASCADE,
        related_name="questions",
        help_text="Set this to put the question on a programme page as well, or "
                  "instead.",
    )
    question = models.CharField(max_length=250)
    answer = models.TextField(
        validators=[validate_inline],
        help_text="A paragraph. Links and light emphasis are allowed "
                  f"({ALLOWED_TAGS_HELP}); link to a page on this site with "
                  "href=&quot;route:enquire&quot; rather than a web address, so the "
                  "link survives the page moving.",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]
        verbose_name = "question"
        verbose_name_plural = "questions"

    def __str__(self) -> str:
        return self.question

    @property
    def answer_html(self):
        return render_inline(self.answer)

    @property
    def answer_words(self) -> str:
        """The answer without its markup, for a console list column."""
        return to_text(self.answer)

    @property
    def shown_nowhere(self) -> bool:
        """A question with no topic and no programme is on no page at all."""
        return self.group_id is None and self.programme_id is None

    @property
    def where(self) -> str:
        """Which page or pages this answer appears on, for the console list."""
        if self.shown_nowhere:
            return "Not shown anywhere yet"
        places = []
        if self.group_id:
            places.append(self.group.title)
        if self.programme_id:
            places.append(self.programme.label)
        return " and ".join(places)
