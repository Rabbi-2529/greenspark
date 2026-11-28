"""
The Our team page.

Every default is the wording the template carried, so a database with no rows
renders the page exactly as it rendered before.

No ``TeamMember``. The plan asked for ``TeamGroup`` + ``TeamMember``, but the
design build's teams band is five headed paragraphs describing how the work is
divided -- there is no list of people under a team anywhere in the markup, and
the page says five teams rather than naming thirty staff. A model for rows that
nothing renders is a worse thing to hand Green Spark than none, so the
deviation is recorded in CMS-PLAN.md and the band is ``TeamGroup`` alone.
"""

from django.db import models

from .base import Singleton


class TeamPage(Singleton):
    """The wording on Our team that there is only one of."""

    hero_tag = models.CharField("hero eyebrow", max_length=60, default="About Us")
    hero_title = models.CharField(
        "hero heading", max_length=200, default="The people behind Green Spark",
    )
    hero_lead = models.TextField(
        default="A team in Australia and Bangladesh, working with communities, local "
                "government and partners on clean energy and carbon projects.",
    )

    leaders_tag = models.CharField(
        "leadership eyebrow", max_length=60, default="Leadership",
    )
    leaders_title = models.CharField(
        "leadership heading", max_length=200, default="Leading our work",
    )
    leaders_lead = models.TextField(
        "leadership standfirst",
        default="Two companies, one team: Green Spark Solutions Australia Pty Ltd and "
                "Green Spark Solutions Ltd in Bangladesh.",
    )

    groups_tag = models.CharField("teams eyebrow", max_length=60, default="Our teams")
    groups_title = models.CharField(
        "teams heading", max_length=200, default="How we are organised",
    )
    groups_lead = models.TextField(
        "teams standfirst",
        default="Five teams share one way of working: built with communities and "
                "measured with care.",
        help_text="Counts the teams below in words, so change it if you add or remove "
                  "one.",
    )

    join_tag = models.CharField("careers eyebrow", max_length=60, default="Careers")
    join_title = models.CharField(
        "careers heading", max_length=200, default="Join the team",
    )
    join_lead = models.TextField(
        "careers standfirst",
        default="We work with people who care about communities and the environment, in "
                "Australia and in Bangladesh.",
    )
    join_label = models.CharField(
        "careers button", max_length=60, default="Careers at GSSL",
        help_text="Goes to the Careers band on About Us.",
    )

    class Meta:
        verbose_name = "Our team page"
        verbose_name_plural = "Our team page"

    def __str__(self) -> str:
        return self.hero_title


class TeamLeader(models.Model):
    """One person on the leadership band."""

    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120, help_text="e.g. “Director and CEO”.")
    organisation = models.CharField(
        max_length=200, blank=True,
        help_text="The company and the office, e.g. “Green Spark Solutions Australia "
                  "Pty Ltd · Rockdale, NSW”.",
    )
    bio = models.TextField(blank=True, help_text="Two sentences at most.")
    initials = models.CharField(
        max_length=4, blank=True,
        help_text="Shown in the circle. Left empty it is worked out from the name, "
                  "which is right for most names and wrong for some.",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]
        verbose_name = "team leader"
        verbose_name_plural = "team leaders"

    def __str__(self) -> str:
        return self.name

    @property
    def monogram(self) -> str:
        """
        What goes in the circle.

        Derived from the name so it cannot fall out of step with it, with an
        override for the names this rule gets wrong -- an honorific first, a
        single name, a name that reads better with three letters.
        """
        if self.initials:
            return self.initials
        parts = self.name.split()
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0][:1].upper()
        return (parts[0][:1] + parts[-1][:1]).upper()


class TeamGroup(models.Model):
    """One of the teams on the “How we are organised” band."""

    title = models.CharField(
        max_length=160, help_text="e.g. “Field operations · Manikganj”.",
    )
    body = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]
        verbose_name = "team"
        verbose_name_plural = "teams"

    def __str__(self) -> str:
        return self.title
