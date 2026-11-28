"""
The home page's project carousel.

It is not the Projects grid with different styling. It shows five of the seven
projects, in an order someone chose, with shorter copy than the project pages
carry and three facts picked per card — "Stoves: 20,000+ installed" on one,
"Visits: Every year" on another. One card points at a programme rather than a
project. So the slides are their own records that reference a project, not a
filtered view of the Project table.

What is *derived* rather than stored: the slide number and the active flag
come from row order, and the Gold Standard registry link comes from the
project's own ``gs_id``. Reordering in the console cannot put them out of step.
"""

from django.db import models

from ..richtext import validate as validate_inline


class CarouselSlide(models.Model):
    """One card in the home page carousel."""

    title = models.CharField(max_length=160)
    text = models.TextField(
        help_text="Two sentences at most. The card is small and the text does "
                  "not scroll.",
        validators=[validate_inline],
    )
    project = models.ForeignKey(
        "content.Project", null=True, blank=True, on_delete=models.CASCADE,
        related_name="carousel_slides",
        help_text="The project this card links to. Leave empty if it points at "
                  "a programme instead.",
    )
    programme = models.ForeignKey(
        "content.Programme", null=True, blank=True, on_delete=models.CASCADE,
        related_name="carousel_slides",
        help_text="Used only when there is no project.",
    )
    link_label = models.CharField(max_length=60, default="View project")
    registered = models.BooleanField(
        "show the Gold Standard certificate", default=False,
        help_text="Puts the certificate logo and the “Gold Standard registered” "
                  "badge at the top of the card, instead of the small badges below.",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]

    def __str__(self) -> str:
        return self.title

    @property
    def url_name(self) -> str:
        """The route this card links to, or "" if it links nowhere."""
        if self.project_id:
            return "website:project_detail"
        if self.programme_id:
            return f"website:{self.programme.url_name}"
        return ""

    @property
    def registry_url(self) -> str:
        return self.project.registry_url if self.project_id else ""

    @property
    def registry_label(self) -> str:
        return self.project.registry_label if self.project_id else ""


class SlideBadge(models.Model):
    """A small badge on a carousel card, e.g. “Active” or “In pipeline”."""

    PRIORITY = "priority"
    DEVELOPMENT = "development"
    ACTIVE = "active"
    VARIANTS = [
        (PRIORITY, "Priority — dark"),
        (DEVELOPMENT, "In development / in pipeline — grey"),
        (ACTIVE, "Active — green"),
    ]

    slide = models.ForeignKey(
        CarouselSlide, on_delete=models.CASCADE, related_name="badges"
    )
    label = models.CharField(max_length=40)
    variant = models.CharField(max_length=20, choices=VARIANTS, default=DEVELOPMENT)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]

    def __str__(self) -> str:
        return self.label


class SlideFact(models.Model):
    """One of the three facts listed on a carousel card."""

    slide = models.ForeignKey(
        CarouselSlide, on_delete=models.CASCADE, related_name="facts"
    )
    label = models.CharField(max_length=40, help_text="e.g. “Standard”, “Country”.")
    value = models.CharField(max_length=80)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]

    def __str__(self) -> str:
        return f"{self.label}: {self.value}"
