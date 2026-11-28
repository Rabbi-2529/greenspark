"""
The Why GSSL page.

The page is UNLISTED -- routed, noindex, linked from nothing -- because Green
Spark hid it from the menus and its content leads What We Do instead. That is a
status on its ``Page`` row, not a reason to leave the words in a template: it is
reachable by link and someone will want to change it before it comes back.

Every default is the wording the template carried, so a database with no rows
renders the page exactly as it rendered before.
"""

from django.db import models

from ..richtext import validate as validate_inline

from ..icons import CHOICES as ICON_CHOICES
from ..icons import IconMixin
from .base import Singleton


class WhyGsslPage(Singleton):
    """The wording on Why GSSL that there is only one of."""

    hero_tag = models.CharField("hero eyebrow", max_length=60, default="Why GSSL")
    hero_title = models.CharField(
        "hero heading", max_length=200,
        default="Carbon projects that start with communities",
    )
    hero_lead = models.TextField(
        default="Green Spark Solutions Australia develops carbon projects and "
                "clean-energy programmes with communities in Bangladesh, Nepal and "
                "Cambodia. Here is what partners, buyers and communities can expect "
                "from us.",
        validators=[validate_inline],
    )
    enquire_label = models.CharField(max_length=60, default="Enquire")
    whatsapp_label = models.CharField(max_length=60, default="WhatsApp us")

    reasons_tag = models.CharField(
        "reasons eyebrow", max_length=60, default="What sets us apart",
    )
    reasons_title = models.CharField(
        "reasons heading", max_length=200,
        default="Six reasons partners work with Green Spark",
        help_text="Counts the reasons below in words, so change it if you add or "
                  "remove one.",
    )

    expectations_tag = models.CharField(
        "expectations eyebrow", max_length=60, default="Working with us",
    )
    expectations_title = models.CharField(
        "expectations heading", max_length=200, default="What each partner can expect",
    )

    steps_tag = models.CharField("steps eyebrow", max_length=60, default="How we work")
    steps_title = models.CharField(
        "steps heading", max_length=200,
        default="From first conversation to verified result",
    )

    class Meta:
        verbose_name = "Why GSSL page"
        verbose_name_plural = "Why GSSL page"

    def __str__(self) -> str:
        return self.hero_title


class WhyItem(IconMixin, models.Model):
    """
    One point on Why GSSL.

    Three bands, one model, the way ``ApproachItem`` holds the home page's two:
    they are all short icon / title / text rows and keeping them together means
    one console list with a filter on it rather than three lists of three.

    The plan put the middle band on a shared ``Audience`` model with a scope
    field spanning this page and About Us. They share no markup -- About's
    partner grid has an icon and a different card -- so a scope field would have
    produced one console list where half the rows could not be used on either
    page. A third kind here is the smaller lie.

    Nothing stores a step number or a reveal delay. The step numbers come from a
    CSS counter, and the delays from row order.
    """

    REASON = "reason"
    EXPECTATION = "expectation"
    STEP = "step"
    KIND_CHOICES = [
        (REASON, "“What sets us apart” — card with an icon"),
        (EXPECTATION, "“Working with us” — plain card"),
        (STEP, "“How we work” — numbered step"),
    ]

    kind = models.CharField(max_length=20, choices=KIND_CHOICES, db_index=True)
    icon = models.CharField(
        max_length=40, blank=True, choices=ICON_CHOICES,
        help_text="Used by the “what sets us apart” cards and the numbered steps. "
                  "The plain cards have no icon.",
    )
    title = models.CharField(max_length=160)
    body = models.TextField(validators=[validate_inline])
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]
        verbose_name = "Why GSSL point"
        verbose_name_plural = "Why GSSL points"

    def __str__(self) -> str:
        return self.title
