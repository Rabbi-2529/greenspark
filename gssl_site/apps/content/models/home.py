"""
The home page's own content: how Green Spark describes its approach, the
impact figures, and the districts on the map.

Nothing here stores a reveal delay or a card number. Those follow from the
order the rows are in — first card open, cards numbered 01, 02, 03, every
third one staggered — so the template works them out and an editor cannot get
them out of step by reordering.
"""

from django.db import models


class ApproachItem(models.Model):
    """
    A point about how Green Spark works.

    Two shapes, one model, because they are the same thing said twice: the
    expanding cards under “Why Green Spark”, and the plain cards under
    “A holistic approach”.
    """

    HIGHLIGHT = "highlight"
    ATTRIBUTE = "attribute"
    KIND_CHOICES = [
        (HIGHLIGHT, "Why Green Spark — expanding card"),
        (ATTRIBUTE, "A holistic approach — plain card"),
    ]

    kind = models.CharField(max_length=20, choices=KIND_CHOICES, db_index=True)
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
