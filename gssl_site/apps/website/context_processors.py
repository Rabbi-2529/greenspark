"""
Values every template needs.

The site's chrome — the top bar, the header, the footer — is rendered on every
page, so what it needs has to be here rather than in one view. That means a
couple of small queries per request; both are tiny and indexed, and the site
already reads its page record per request.

Everything degrades to the field defaults if the database cannot be reached,
so the 500 page still renders when the database is the thing that broke.
"""

from django.conf import settings
from django.db import DatabaseError


def site(request):
    from apps.content.models import Project, SiteSettings

    try:
        # filter().first() rather than load(): a context processor must not
        # write a row on a GET, and an unsaved instance carries the same
        # defaults the migration would have given it.
        site_settings = SiteSettings.objects.filter(pk=1).first() or SiteSettings()
        nav_projects = list(
            Project.objects.order_by("sort_order", "pk").only("slug", "title")
        )
    except DatabaseError:
        site_settings = SiteSettings()
        nav_projects = []

    return {
        "site_url": settings.SITE_URL,
        "site_name": settings.SITE_NAME,
        "site_settings": site_settings,
        "nav_projects": nav_projects,
    }
