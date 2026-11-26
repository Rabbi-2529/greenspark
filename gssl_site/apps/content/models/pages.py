"""
The site map, and the bands of content on each page.

**Routes stay in code.** ``apps.website.pages`` keeps the route, the template
and the nav key for every page, because a URLconf is built once when the
process starts: reading routes from the database there would fail on a fresh
install before ``migrate``, and a changed route would not take effect until a
restart. Routes are structure, not content.

What *is* content lives here: the page's title and meta description, whether
it is published, and which bands of the page are shown. Those are read per
request, so a change in the console takes effect on the next page load.
"""

from django.db import models

LIVE = "live"
UNLISTED = "unlisted"
OFFLINE = "offline"


class SectionVisibility(dict):
    """
    What ``{% if sections.approach %}`` asks.

    A key with no row is **visible**. That matters: a typo in a template, or a
    section added in code before anyone has opened the console, must leave the
    page as it was rather than silently deleting a band of the site.
    """

    def __missing__(self, key):
        return True


class PageQuerySet(models.QuerySet):
    def live(self):
        return self.filter(status=LIVE)

    def published(self):
        return self.exclude(status=OFFLINE)


class Page(models.Model):
    """One row per page of the site, matching a name in apps.website.pages."""

    STATUS_CHOICES = [
        (LIVE, "Live — linked from the site and listed for search engines"),
        (UNLISTED, "Unlisted — reachable by link only, kept out of search"),
        (OFFLINE, "Offline — answers “page not found”"),
    ]

    name = models.SlugField(
        max_length=60, unique=True,
        help_text="Matches the page's name in the site's route map. Not editable here.",
    )
    label = models.CharField(
        max_length=80,
        help_text="What this page is called in the console.",
    )
    title = models.CharField(
        "browser title", max_length=250,
        help_text="Shown in the browser tab and as the headline in search results.",
    )
    meta_description = models.TextField(
        "search description", blank=True, max_length=400,
        help_text="One sentence, about 160 characters, shown under the title in search results.",
    )
    og_image = models.CharField(
        "share image", max_length=200, blank=True,
        help_text="The picture used when the page is shared on social media.",
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=LIVE, db_index=True)
    sort_order = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PageQuerySet.as_manager()

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.label or self.name

    @property
    def is_published(self) -> bool:
        return self.status != OFFLINE

    @property
    def in_sitemap(self) -> bool:
        return self.status == LIVE

    def visibility(self) -> SectionVisibility:
        return SectionVisibility(
            {section.key: section.visible for section in self.sections.all()}
        )

    # --- lookups used on every request ---

    @classmethod
    def by_name(cls, name: str):
        """The row for a page, or None when the database has none yet."""
        return cls.objects.filter(name=name).first()

    @classmethod
    def visibility_for(cls, name: str) -> SectionVisibility:
        rows = Section.objects.filter(page__name=name).values_list("key", "visible")
        return SectionVisibility(dict(rows))


class Section(models.Model):
    """
    One band of a page that can be shown or hidden.

    ``key`` is what the template asks for: a section wrapped in
    ``{% if sections.approach %}`` needs a row with key ``approach``. Keys are
    snake_case because a Django template cannot look up a name with a hyphen.

    Hiding is all this does. Re-ordering the bands of a page would change the
    markup order, which the parity test exists to prevent, so the order here is
    only the order the console lists them in.
    """

    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="sections")
    key = models.SlugField(max_length=60)
    label = models.CharField(
        max_length=120,
        help_text="What this band of the page is called in the console.",
    )
    blurb = models.CharField(
        max_length=250, blank=True,
        help_text="A line of the real wording, so it is obvious which band this is.",
    )
    visible = models.BooleanField(
        "shown on the site", default=True,
        help_text="Turn this off to take the band off the page. Nothing is deleted.",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["page__sort_order", "sort_order", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["page", "key"], name="unique_section_key_per_page"),
        ]

    def __str__(self) -> str:
        return f"{self.page} — {self.label}"
