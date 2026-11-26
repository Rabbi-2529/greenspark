"""
Projects.

This model is deliberately shaped like the frozen dataclass it replaces
(``apps.website.content.Project``), down to the property names, because the
templates read those names. Keeping ``filters``, ``photo``, ``badge_class``,
``is_registered``, ``programme_label``, ``programme_url_name`` and
``description`` means the card and the detail page do not have to be rewritten
to be fed from the database — which is the whole point of the parity test.

Three fields exist only because the project grid was hand-written rather than
looped, and the markup has to come back byte for byte: ``reveal_delay``,
``stock_photo`` and ``card_links_to_programme``. They are presentation, and
they are marked as such in the console.
"""

from django.core.exceptions import ValidationError
from django.db import models

from .programmes import Programme

# The first chip on a card decides the badge's colour.
BADGE_CLASSES = {
    "registered": "badge--registered",
    "development": "badge--development",
    "active": "badge--active",
    "certification": "badge--certification",
}

# Every chip the project grid knows how to filter by.
KNOWN_TAGS = set(BADGE_CLASSES) | {"cookstove", "rooftop", "water", "irrigation", "rural", "rice"}


class Project(models.Model):
    slug = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=160)
    summary = models.TextField(help_text="The sentence or two describing the project.")
    card_summary = models.TextField(
        "shorter summary for the card", blank=True,
        help_text="Only if the card needs to be shorter than the summary above. "
                  "Leave empty and the card uses the summary.",
    )
    location = models.CharField(max_length=160)
    stage = models.CharField(max_length=80, help_text="e.g. “Installed · monitoring”.")
    photo = models.CharField(
        max_length=80,
        help_text="The photo's base name under img/photos, without the size or extension.",
    )
    photo_has_large = models.BooleanField(
        "a 1600px version of the photo exists", default=True,
        help_text="Turn off when only the 480 and 960 sizes exist, so the page does "
                  "not point at a file that is not there.",
    )

    programme = models.ForeignKey(
        Programme, null=True, blank=True, on_delete=models.PROTECT, related_name="projects",
    )
    gs_id = models.CharField(
        "Gold Standard ID", max_length=20, blank=True,
        help_text="Only for a project actually registered with Gold Standard, e.g. GS13141. "
                  "Leave empty and the page makes no registration claim.",
    )
    standard = models.CharField(max_length=120, blank=True)
    tags = models.CharField(
        "filter chips", max_length=120, blank=True,
        help_text="Space-separated. The first one sets the badge colour. "
                  "Known: " + ", ".join(sorted(KNOWN_TAGS)),
    )
    proponent = models.CharField(max_length=160, default="Green Spark Solutions Australia Pty Ltd")
    status_label = models.CharField(max_length=60, default="Status")
    status_note = models.CharField(max_length=160, blank=True)
    card_badge = models.CharField(
        max_length=60, blank=True,
        help_text="Shown on the card when there is no Gold Standard registration.",
    )
    stove_detail = models.BooleanField(
        "show the Green ICS detail", default=False,
        help_text="Adds the stove attributes, how-it-works and field photos to the page.",
    )

    # --- presentation, kept so the hand-written grid can be reproduced ---
    reveal_delay = models.PositiveSmallIntegerField(
        default=0,
        help_text="Staggers the card's fade-in: 0, 1 or 2. Presentation only.",
    )
    stock_photo = models.BooleanField(
        default=False,
        help_text="This card still uses a stock photo, and is marked for replacement.",
    )
    card_links_to_programme = models.BooleanField(
        default=False,
        help_text="The card opens the programme page instead of this project's own page.",
    )

    # Two orders, because the site has two. ``sort_order`` is the canonical
    # one, and the “other projects” list on a project page follows it.
    # ``grid_order`` is the order of the cards on the Projects page, which was
    # arranged by hand and is not the same.
    sort_order = models.PositiveIntegerField("order", default=0)
    grid_order = models.PositiveIntegerField("order on the Projects page", default=0)

    class Meta:
        ordering = ["sort_order", "pk"]

    def __str__(self) -> str:
        return self.title

    def clean(self):
        unknown = sorted(set(self.tags.split()) - KNOWN_TAGS)
        if unknown:
            raise ValidationError({"tags": f"Not a chip the grid knows: {', '.join(unknown)}."})
        if self.gs_id and not self.gs_id.upper().startswith("GS"):
            raise ValidationError({"gs_id": "A Gold Standard ID looks like GS13141."})

    # --- the interface the templates already read -------------------------

    @property
    def filters(self) -> list[str]:
        return self.tags.split()

    @property
    def badge_class(self) -> str:
        chips = self.filters
        return BADGE_CLASSES.get(chips[0] if chips else "", "badge--type")

    @property
    def is_registered(self) -> bool:
        """
        Only a registered project may claim registration. The template asks
        this, never the ID directly, so an empty ID cannot show a badge.
        """
        return bool(self.gs_id)

    @property
    def programme_label(self) -> str:
        return self.programme.label if self.programme else ""

    @property
    def programme_url_name(self) -> str:
        return self.programme.route if self.programme else ""

    @property
    def description(self) -> list[str]:
        return [paragraph.body for paragraph in self.paragraphs.all()]

    @property
    def card_route(self) -> str:
        """Where this card's link goes."""
        if self.card_links_to_programme and self.programme:
            return self.programme.route
        return "website:project_detail"

    def related(self, count: int = 3) -> list["Project"]:
        """Other projects, same programme first, in site order."""
        others = [p for p in Project.objects.exclude(pk=self.pk).select_related("programme")]
        others.sort(key=lambda p: p.programme_id != self.programme_id)  # stable
        return others[:count]


class ProjectParagraph(models.Model):
    """One “About the project” paragraph."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="paragraphs")
    body = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]

    def __str__(self) -> str:
        return self.body[:60]


class ProjectAttribute(models.Model):
    """One of the “Key details” rows."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="attributes")
    icon = models.CharField(max_length=40, blank=True)
    title = models.CharField(max_length=120)
    details = models.CharField(max_length=250, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]

    def __str__(self) -> str:
        return self.title


class ProjectImage(models.Model):
    """A photo in the project's own gallery."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="images")
    photo = models.CharField(max_length=80, help_text="Base name under img/photos.")
    alt = models.CharField("alt text", max_length=250, blank=True)
    caption = models.CharField(max_length=250, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]

    def __str__(self) -> str:
        return self.alt or self.photo
