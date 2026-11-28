"""
The home page's own content: how Green Spark describes its approach, the
impact figures, and the districts on the map.

Nothing here stores a reveal delay or a card number. Those follow from the
order the rows are in — first card open, cards numbered 01, 02, 03, every
third one staggered — so the template works them out and an editor cannot get
them out of step by reordering.
"""

from django.db import models

from ..icons import CHOICES as ICON_CHOICES
from ..icons import IconMixin
from .base import Singleton


class ApproachItem(IconMixin, models.Model):
    """
    A point about how Green Spark works.

    Three shapes, one model, because they are the same thing said three times:
    the expanding cards under “Why Green Spark” and the plain cards under
    “A holistic approach” on the home page, and the cards under “Our approach”
    on About Us — which are the only ones that carry an icon.
    """

    HIGHLIGHT = "highlight"
    ATTRIBUTE = "attribute"
    ABOUT = "about"
    KIND_CHOICES = [
        (HIGHLIGHT, "Home — “Why Green Spark” expanding card"),
        (ATTRIBUTE, "Home — “A holistic approach” plain card"),
        (ABOUT, "About Us — “Our approach” card with an icon"),
    ]

    kind = models.CharField(max_length=20, choices=KIND_CHOICES, db_index=True)
    icon = models.CharField(
        max_length=40, blank=True, choices=ICON_CHOICES,
        help_text="Shown only on the About Us cards. The home page's cards have no icon.",
    )
    title = models.CharField(max_length=160)
    body = models.TextField()
    link_label = models.CharField(
        max_length=80, blank=True,
        help_text="Leave empty for no link.",
    )
    link_route = models.SlugField(
        "link target", max_length=60, blank=True,
        help_text="The route name of the page this points at, e.g. programme_rooftop_solar.",
    )
    link_fragment = models.CharField(
        max_length=60, blank=True,
        help_text="An anchor on that page, e.g. #approach. Include the #.",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]

    def __str__(self) -> str:
        return self.title

    @property
    def route(self) -> str:
        return f"website:{self.link_route}" if self.link_route else ""


class Counter(models.Model):
    """
    One impact figure.

    A figure is not shown until someone ticks ``published``, and it carries the
    date it was true. The design build's README is explicit that the current
    numbers are Green Spark's to approve before they appear as fact.
    """

    label = models.CharField(max_length=120)
    display = models.CharField(
        "as written", max_length=40,
        help_text="Exactly as it should read, e.g. “20,000+”. Use an em dash for a figure "
                  "that is not measured yet.",
    )
    count = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="The number the counter animates up to. Leave empty for a figure that has none.",
    )
    suffix = models.CharField(max_length=8, blank=True, help_text="e.g. “+”.")
    estimated = models.BooleanField(
        default=False, help_text="Adds the “Estimated” badge.",
    )
    note = models.CharField(max_length=160, blank=True)
    as_of = models.DateField(
        "true as of", null=True, blank=True,
        help_text="The date this figure was measured.",
    )
    published = models.BooleanField(
        "approved for the site", default=False,
        help_text="Off until Green Spark has approved the figure.",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]

    def __str__(self) -> str:
        return f"{self.display} {self.label}"

    @property
    def is_pending(self) -> bool:
        """No number to count up to yet, so the page says so instead."""
        return self.count is None


class District(models.Model):
    """A district highlighted on the Bangladesh map."""

    name = models.CharField(max_length=80, unique=True)
    division = models.CharField(
        max_length=80,
        help_text="Shown under the name, e.g. “Dhaka division” or “Operations base”.",
    )
    is_base = models.BooleanField("operations base", default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name


class HomePage(Singleton):
    """
    The home page's hero: the wording, and which video plays behind it.

    Every default below is the text the template carried, so a fresh database
    renders the page exactly as it rendered before — which is what the golden
    HTML test checks.

    The six video and poster files follow the design build's naming, so one
    name covers all of them: <name>-poster.jpg/.webp and <name>.webm/.mp4 for
    the wide crop, and <name>-mobile-poster.* and <name>-mobile.* for the tall
    one. Uploading a new set means six files with matching names, not six
    fields to keep in step.
    """

    heading = models.CharField(
        "page heading", max_length=250,
        default="Green Spark Solutions Australia: carbon projects and clean energy "
                "for communities in Bangladesh, Nepal and Cambodia",
        help_text="The page's real <h1>. It is read by search engines and screen "
                  "readers but not shown, so it can be fuller than the headline.",
    )
    welcome_tag = models.CharField(max_length=40, default="Welcome")
    welcome_text = models.CharField(
        max_length=120, default="to Green Spark Solutions",
    )
    title = models.CharField(
        "headline", max_length=160, default="Climate impact, measured and verified.",
    )
    lead = models.TextField(
        default="Green Spark aggregates rooftop solar, clean cooking and safe water "
                "into verified carbon programmes that buyers and investors can trust.",
        help_text="Two lines at most: it sits over the video and competes with it.",
    )
    meet_label = models.CharField(
        "video button", max_length=60, default="Meet GSSL",
        help_text="Opens the introduction video.",
    )
    scroll_label = models.CharField(max_length=40, default="Scroll")
    pause_label = models.CharField(
        max_length=80, default="Pause background video",
        help_text="Read out by screen readers; not shown on the page.",
    )
    video_name = models.SlugField(
        "video set", max_length=60, default="gs-hero",
        help_text="The shared name of the six files in static/video/hero/.",
    )

    class Meta:
        verbose_name = "home page"
        verbose_name_plural = "home page"

    def __str__(self) -> str:
        return self.title

    # The six files, derived rather than stored, so they cannot drift apart.
    @property
    def poster_wide(self) -> str:
        return f"video/hero/{self.video_name}-poster"

    @property
    def poster_tall(self) -> str:
        return f"video/hero/{self.video_name}-mobile-poster"

    @property
    def video_wide(self) -> str:
        return f"video/hero/{self.video_name}"

    @property
    def video_tall(self) -> str:
        return f"video/hero/{self.video_name}-mobile"
