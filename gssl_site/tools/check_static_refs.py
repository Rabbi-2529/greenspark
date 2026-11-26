"""
Render every published page and confirm each /static/ URL it references
exists on disk. Pages marked OFFLINE in pages.py answer 404 and are skipped.

Catches asset paths that survive conversion but would 404 in the browser.

Usage:  python tools/check_static_refs.py
"""

from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.test import Client  # noqa: E402
from django.urls import reverse  # noqa: E402

from apps.content.models import Project  # noqa: E402
from apps.website.pages import PAGES  # noqa: E402

# Client() talks to "testserver"; outside the test runner that must be allowed.
if "testserver" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append("testserver")

STATIC_DIR = settings.STATICFILES_DIRS[0]
# Includes data-* attributes: the hero video and lightbox keep URLs there.
REF = re.compile(r'(?:src|href|srcset|poster|content|data-[a-z-]+)="([^"]*)"')


def static_paths(html: str) -> set[str]:
    found: set[str] = set()
    for value in REF.findall(html):
        for candidate in re.split(r"\s*,\s*", value):      # srcset
            url = candidate.strip().split(" ")[0]
            if url.startswith(settings.STATIC_URL):
                found.add(url[len(settings.STATIC_URL):])
    return found


def main() -> int:
    client = Client()
    missing: dict[str, set[str]] = defaultdict(set)
    checked: set[str] = set()
    pages = 0

    urls = [reverse(f"website:{p.name}") for p in PAGES if p.is_published]
    urls += [
        reverse("website:project_detail", args=[slug])
        for slug in Project.objects.values_list("slug", flat=True)
    ]

    for url in urls:
        response = client.get(url)
        if response.status_code != 200:
            print(f"FAIL {url} -> HTTP {response.status_code}")
            return 1
        pages += 1
        for rel in static_paths(response.content.decode()):
            checked.add(rel)
            if not (STATIC_DIR / rel).is_file():
                missing[rel].add(url)

    print(f"{pages} pages rendered, {len(checked)} distinct static references checked")
    if missing:
        print(f"\n{len(missing)} MISSING file(s):")
        for rel, where in sorted(missing.items()):
            print(f"  {rel}\n      referenced by: {', '.join(sorted(where))}")
        return 1
    print("every referenced static file exists")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
