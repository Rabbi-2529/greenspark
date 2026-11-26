"""
The four records behind the site's chrome.

These fill the top bar, the footer, the contact page and the notice bar. Every
default below is the value the template carried before Phase 2, so a fresh
database renders the site exactly as it rendered before — which is what the
parity test checks.
"""

from django.db import models
from django.utils import timezone

from .base import Singleton


class SiteSettings(Singleton):
    site_name = models.CharField(max_length=120, default="Green Spark Solutions Australia")
    legal_name = models.CharField(
        max_length=160, default="Green Spark Solutions Australia Pty Ltd",
        help_text="The registered company name, used where a legal name is needed.",
    )
    abn = models.CharField("ABN", max_length=20, blank=True)
    default_og_image = models.CharField(
        "default share image", max_length=200,
        default="img/illustrations/dawn-paddy-1280.jpg",
        help_text="Used when a page has no share image of its own.",
    )
    show_topbar = models.BooleanField(
        "show the top bar", default=True,
        help_text="The thin dark strip above the menu, with WhatsApp, the email "
                  "address, opening hours and the language switch. Turn it off to "
                  "start the page at the logo instead.",
    )

    class Meta:
        verbose_name = "site settings"
        verbose_name_plural = "site settings"

    def __str__(self) -> str:
        return self.site_name


class ContactDetails(Singleton):
    """
    One company, one phone number — see the design build's README §6. The
    addresses appear in the footer only.
    """

    whatsapp_number = models.CharField(
        max_length=20, default="61402832972",
        help_text="Digits only, with the country code and no plus sign. Used to build the WhatsApp link.",
    )
    phone_display = models.CharField(
        "phone, as written", max_length=40, default="+61 402 832 972",
        help_text="How the number is shown on the page.",
    )
    email = models.EmailField(default="info@greensparksolutions.com")
    hours = models.CharField(
        "opening hours", max_length=120, default="Every day, 9 AM – 5 PM",
    )

    australia_address = models.TextField(
        "Australia — head office", blank=True,
        help_text="Shown in the footer.",
    )
    australia_map_url = models.URLField("Australia — map link", blank=True)
    bangladesh_address = models.TextField("Bangladesh — operations", blank=True)
    bangladesh_map_url = models.URLField("Bangladesh — map link", blank=True)

    class Meta:
        verbose_name = "contact details"
        verbose_name_plural = "contact details"

    def __str__(self) -> str:
        return self.email

    @property
    def whatsapp_url(self) -> str:
        return f"https://wa.me/{self.whatsapp_number}"

    @property
    def whatsapp_label(self) -> str:
        return f"WhatsApp {self.phone_display}"


class SocialLinks(Singleton):
    """
    An empty address hides that icon — that is how the design build works, and
    it is why these are blank rather than pointing at a platform's home page.
    A link to facebook.com with no profile behind it is worse than no link.
    """

    facebook = models.URLField(blank=True)
    youtube = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    whatsapp = models.URLField(blank=True, default="https://wa.me/61402832972")
    x = models.URLField("X (Twitter)", blank=True)

    class Meta:
        verbose_name = "social links"
        verbose_name_plural = "social links"

    def __str__(self) -> str:
        return f"{len(self.active())} link(s) shown"

    # The order icons appear in, and the label each one carries.
    PLATFORMS = (
        ("facebook", "Facebook"),
        ("youtube", "YouTube"),
        ("linkedin", "LinkedIn"),
        ("whatsapp", "WhatsApp"),
        ("x", "X"),
    )

    def active(self) -> list[dict]:
        return [
            {"key": key, "label": label, "url": getattr(self, key)}
            for key, label in self.PLATFORMS
            if getattr(self, key)
        ]


class NoticeBar(Singleton):
    """
    The strip above the header. It shows only inside its window, so a
    consultation notice takes itself down rather than going stale.
    """

    enabled = models.BooleanField("turned on", default=False)
    text = models.CharField(max_length=250, blank=True)
    link_label = models.CharField(max_length=60, blank=True)
    link_url = models.CharField(max_length=250, blank=True)
    starts_at = models.DateField(null=True, blank=True)
    ends_at = models.DateField(
        null=True, blank=True,
        help_text="The last day it shows. Leave both dates empty to show it until turned off.",
    )

    class Meta:
        verbose_name = "notice bar"
        verbose_name_plural = "notice bar"

    def __str__(self) -> str:
        return self.text or "no notice"

    @property
    def is_showing(self) -> bool:
        if not self.enabled or not self.text:
            return False
        today = timezone.localdate()
        if self.starts_at and today < self.starts_at:
            return False
        if self.ends_at and today > self.ends_at:
            return False
        return True
