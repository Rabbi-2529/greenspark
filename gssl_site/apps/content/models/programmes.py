"""
Programmes — the six things Green Spark does.

Phase 3 needs a programme mainly as the thing a project belongs to: its name,
its colour hook and the page it links to. The richer fields the programme
pages themselves need (body copy, attributes, how-it-works steps) arrive with
those pages.

``url_name`` is the name of a route in ``apps.website.pages``, not a path, for
the same reason Phase 2 kept routes in code: ``{% url %}`` resolves it, so a
route can move without anything here changing.
"""

from django.db import models

from ..richtext import validate as validate_inline


class Programme(models.Model):
    CONCEPT = "concept"
    FEASIBILITY = "feasibility"
    PILOT = "pilot"
    ACTIVE = "active"
    STAGE_CHOICES = [
        (CONCEPT, "Concept"),
        (FEASIBILITY, "Feasibility"),
        (PILOT, "Pilot"),
        (ACTIVE, "Active"),
    ]

    key = models.SlugField(
        max_length=40, unique=True,
        help_text="Short name used in the templates and as the colour hook. Not editable.",
    )
    label = models.CharField(
        max_length=120,
        help_text="How the programme is named on a project page, e.g. “Rooftop Solar MRV”.",
    )
    url_name = models.SlugField(
        max_length=60,
        help_text="The route name of this programme's page in the site's route map.",
    )
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default=CONCEPT, blank=True)
    summary = models.TextField(blank=True, validators=[validate_inline])

    priority = models.BooleanField(
        "lead programme", default=False,
        help_text="The three programmes the site leads with.",
    )
    show_on_website = models.BooleanField(
        default=False,
        help_text="Off by default: a programme in development is not public until Green Spark says so.",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "label"]

    def __str__(self) -> str:
        return self.label

    @property
    def route(self) -> str:
        """What ``{% url %}`` needs: the namespaced route name."""
        return f"website:{self.url_name}"


class ProgrammeAttribute(models.Model):
    """One of the icon / title / text rows on a programme page."""

    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name="attributes")
    icon = models.CharField(max_length=40, blank=True)
    title = models.CharField(max_length=160)
    text = models.TextField(blank=True, validators=[validate_inline])
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]

    def __str__(self) -> str:
        return self.title


class ProgrammeStep(models.Model):
    """One step of a programme's “how it works”."""

    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name="steps")
    title = models.CharField(max_length=160)
    text = models.TextField(blank=True, validators=[validate_inline])
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]

    def __str__(self) -> str:
        return self.title
