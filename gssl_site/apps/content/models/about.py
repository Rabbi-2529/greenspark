"""
The About Us page, including the Careers band at the foot of it.

Every default below is the wording the template carried, so a database with no
rows in it renders the page exactly as it rendered before -- which is what the
golden HTML test checks.

Nothing here stores a reveal delay, a card number or whether a role is the
first one: those follow from the order the rows are in, so the template works
them out and reordering in the console cannot put them out of step.
"""

from django.db import models

from ..icons import CHOICES as ICON_CHOICES
from ..icons import IconMixin
from ..richtext import render as render_inline
from ..richtext import validate as validate_inline
from .base import Singleton

ICON_HELP = "Chosen from the site's icon set. Leave empty for a card with no icon."


class AboutPage(Singleton):
    """The wording on About Us that there is only one of."""

    # --- the hero ---
    hero_tag = models.CharField("hero eyebrow", max_length=60, default="About us")
    hero_title = models.CharField(
        "hero heading", max_length=200,
        default="Clean energy and healthier homes, built with communities",
    )
    hero_lead = models.TextField(
        default="Green Spark Solutions Australia drives sustainable development, clean "
                "energy access and community empowerment, from our head office in "
                "Rockdale, NSW, and our operations base in Manikganj, Bangladesh.",
    )
    meet_label = models.CharField(
        "video button", max_length=60, default="Meet GSSL",
        help_text="Opens the introduction video.",
    )

    # --- who we are ---
    intro_tag = models.CharField("intro eyebrow", max_length=60, default="Who we are")
    intro_text = models.TextField(
        "intro paragraph",
        default="We are carbon project developers who work in Bangladesh, Nepal and "
                "Cambodia. With local communities, government agencies, NGOs and "
                "private-sector partners, we develop programmes in clean cooking, "
                "<mark>clean energy</mark>, safe water and low-emission farming.",
        validators=[validate_inline],
        help_text="One paragraph. &lt;mark&gt; highlights a phrase as the paragraph "
                  "reveals itself; &lt;strong&gt;, &lt;em&gt; and a link are allowed too.",
    )

    # --- our vision ---
    vision_tag = models.CharField("vision eyebrow", max_length=60, default="Our vision")
    vision_title = models.CharField(
        "vision heading", max_length=200,
        default="A world where everyone has clean energy and a healthy environment",
    )
    vision_lead = models.TextField(
        default="Green Spark Solutions Australia drives sustainable development, clean "
                "energy access and community empowerment.",
    )

    # --- our approach ---
    approach_tag = models.CharField("approach eyebrow", max_length=60, default="Our approach")
    approach_title = models.CharField(
        "approach heading", max_length=200,
        default="A holistic approach to every project",
    )
    approach_lead = models.TextField(
        default="We focus on three things that make programmes last.",
    )

    # --- who we work with ---
    partners_tag = models.CharField(
        "partners eyebrow", max_length=60, default="Who we work with",
    )
    partners_title = models.CharField(
        "partners heading", max_length=200,
        default="Partners from the village to the carbon market",
    )

    # --- careers ---
    careers_tag = models.CharField("careers eyebrow", max_length=60, default="Careers at GSSL")
    careers_title = models.CharField(
        "careers heading", max_length=200, default="Build a cleaner planet with us",
    )
    careers_lead = models.TextField(
        default="We work with people who care about communities and the environment, in "
                "Australia and in Bangladesh. If that sounds like you, we would like to "
                "hear from you.",
    )
    roles_title = models.CharField(
        "open roles heading", max_length=120, default="Open roles",
    )
    no_roles_text = models.TextField(
        "when there are no open roles",
        default="There are no open roles right now. Send your CV and a short note about "
                "the work you are looking for, and we will keep it in mind when a role "
                "opens.",
        help_text="Shown instead of the list whenever no role is published. The page has "
                  "to read correctly with none, because most of the time there are none.",
    )
    cv_label = models.CharField(
        "CV button", max_length=60, default="Send your CV",
    )
    cv_email = models.EmailField(
        "CV button goes to", default="info@greensparksolutions.com",
    )
    cv_subject = models.CharField(
        "CV email subject", max_length=120, default="Careers at GSSL",
    )
    enquire_label = models.CharField(
        "enquiry button", max_length=60, default="Enquire",
    )

    class Meta:
        verbose_name = "About Us page"
        verbose_name_plural = "About Us page"

    def __str__(self) -> str:
        return self.hero_title

    @property
    def intro_html(self):
        return render_inline(self.intro_text)

    @property
    def cv_mailto(self) -> str:
        """
        The Send-your-CV link.

        The subject is quoted the way a mail client needs it, here rather than
        in the template, so an editor typing a subject with a space or an
        ampersand in it cannot produce a broken link.
        """
        from urllib.parse import quote

        if not self.cv_email:
            return ""
        if not self.cv_subject:
            return f"mailto:{self.cv_email}"
        return f"mailto:{self.cv_email}?subject={quote(self.cv_subject)}"


class VisionAttribute(models.Model):
    """One of the points under “Our vision”."""

    title = models.CharField(max_length=160)
    body = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]
        verbose_name = "vision point"
        verbose_name_plural = "vision points"

    def __str__(self) -> str:
        return self.title


class AboutStat(models.Model):
    """
    One of the three figures beside “Who we are”: 2 offices, 3 countries,
    2 registered phases.

    Not a ``Counter``. A counter is a claim about impact that a publisher has to
    approve and that animates up to a number; these are facts about the company
    that do not animate and do not belong in the impact band.
    """

    value = models.CharField(
        "figure", max_length=20, help_text="Exactly as it should read, e.g. “2”.",
    )
    label = models.CharField(
        max_length=160,
        help_text="Reads on from the figure, e.g. “offices: Rockdale, NSW and Manikganj, "
                  "Bangladesh”.",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]
        verbose_name = "About Us figure"
        verbose_name_plural = "About Us figures"

    def __str__(self) -> str:
        return f"{self.value} {self.label}"


class Audience(IconMixin, models.Model):
    """One of the partner types under “Who we work with”."""

    icon = models.CharField(max_length=40, blank=True, choices=ICON_CHOICES, help_text=ICON_HELP)
    title = models.CharField(max_length=160)
    body = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]
        verbose_name = "partner type"
        verbose_name_plural = "partner types"

    def __str__(self) -> str:
        return self.title


class CareerArea(models.Model):
    """One of the kinds of work the Careers band describes."""

    title = models.CharField(max_length=160)
    body = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]
        verbose_name = "area of work"
        verbose_name_plural = "areas of work"

    def __str__(self) -> str:
        return self.title


class JobOpening(models.Model):
    """
    One open role.

    Nothing ships in this table, and the page is written for that: with no
    published role the Careers band shows ``AboutPage.no_roles_text`` and the
    two buttons, exactly as it does today. Publishing a role is what makes the
    list appear.

    The design build never drew a role -- its ``job-openings`` loop is empty in
    the frozen build too -- so the markup for one is new, and uses only classes
    the site already has. The golden harness therefore proves the *empty* case,
    which is what ships; a test covers the populated one.
    """

    FULL_TIME = "Full time"
    PART_TIME = "Part time"
    CONTRACT = "Contract"
    VOLUNTEER = "Volunteer"
    TYPE_CHOICES = [
        (FULL_TIME, FULL_TIME),
        (PART_TIME, PART_TIME),
        (CONTRACT, CONTRACT),
        (VOLUNTEER, VOLUNTEER),
    ]

    title = models.CharField(max_length=160)
    location = models.CharField(
        max_length=120, blank=True, help_text="e.g. “Manikganj, Bangladesh”.",
    )
    employment_type = models.CharField(
        "type", max_length=40, blank=True, choices=TYPE_CHOICES,
    )
    summary = models.TextField(help_text="Two or three sentences about the role.")
    closes_on = models.DateField(
        "applications close", null=True, blank=True,
        help_text="Leave empty for a role with no closing date.",
    )
    apply_email = models.EmailField(
        "apply by email", blank=True,
        help_text="Leave both this and the link empty and the role has no apply button.",
    )
    apply_url = models.URLField("apply at", blank=True)
    apply_label = models.CharField(max_length=60, default="Apply for this role")
    published = models.BooleanField(
        "on the website", default=False,
        help_text="Off until the role is ready to be seen. Nothing is shown while every "
                  "role is off.",
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "pk"]
        verbose_name = "open role"
        verbose_name_plural = "open roles"

    def __str__(self) -> str:
        return self.title

    @property
    def meta(self) -> str:
        """Where and what kind, on one line, with neither one required."""
        return " · ".join(part for part in (self.location, self.employment_type) if part)

    @property
    def apply_href(self) -> str:
        """
        Where the apply button goes, or "" for a role with no way to apply yet.

        A link wins over an email address when both are filled in, and a role
        with neither renders without a button rather than with one that goes
        nowhere.
        """
        if self.apply_url:
            return self.apply_url
        if self.apply_email:
            from urllib.parse import quote

            return f"mailto:{self.apply_email}?subject={quote(self.title)}"
        return ""
