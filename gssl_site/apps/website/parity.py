"""
The parity harness: proof that moving content into the database changed
nothing a visitor can see.

Every published page is rendered and stored under ``golden/`` as the HTML the
site served before the CMS existed. A test re-renders the same pages and
compares byte for byte. Any difference fails, so a lossy migration is caught in
CI rather than in front of Green Spark.

When a golden file does change, it changes because Green Spark asked for a
content change — and then the diff in the pull request shows exactly what
visitors will see differently. That is the point: the diff is the review.

    python manage.py snapshot_pages          # rewrite the golden files
    python manage.py test apps.website       # prove the pages still match

Nothing here is used at runtime.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings
from django.urls import reverse

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"

# Values that legitimately differ between two renders of the same page.
MASKS = (
    # A fresh CSRF token every time.
    (re.compile(r'(name="csrfmiddlewaretoken" value=")[^"]*(")'), r"\1CSRF-TOKEN\2"),
    (re.compile(r'(<meta name="csrf-token" content=")[^"]*(")'), r"\1CSRF-TOKEN\2"),
)


def targets() -> list[tuple[str, str]]:
    """[(golden file stem, url)] for every page the harness covers."""
    from apps.content.models import Project

    from .pages import PAGES

    rows = [(page.name, reverse(f"website:{page.name}")) for page in PAGES if page.is_published]
    rows += [
        (f"project_{slug.replace('-', '_')}",
         reverse("website:project_detail", args=[slug]))
        for slug in Project.objects.values_list("slug", flat=True)
    ]
    return rows


def normalise(html: str) -> str:
    for pattern, replacement in MASKS:
        html = pattern.sub(replacement, html)
    return html


def render(client, url: str) -> str:
    response = client.get(url)
    if response.status_code != 200:
        raise RuntimeError(f"{url} answered HTTP {response.status_code}, not 200")
    return normalise(response.content.decode())


def golden_path(name: str) -> Path:
    return GOLDEN_DIR / f"{name}.html"


def allow_testserver() -> None:
    """django.test.Client talks to 'testserver'; outside the runner, allow it."""
    if "testserver" not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS.append("testserver")
