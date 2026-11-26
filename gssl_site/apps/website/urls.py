"""URL patterns, generated from the single site map in pages.py."""

from django.urls import path
from django.views.generic import RedirectView

from .pages import PAGES
from .views import (
    EnquireView, HomeView, ProjectDetailView, ProjectsView, StaticPageView,
    robots_txt, sitemap_xml,
)

app_name = "website"

# Pages with a view of their own; every other row uses StaticPageView.
VIEWS = {"enquire": EnquireView, "home": HomeView, "projects": ProjectsView}

urlpatterns = [
    # Offline pages stay registered so {% url %} keeps resolving; their view
    # answers 404.
    path(page.route, VIEWS.get(page.name, StaticPageView).as_view(page=page), name=page.name)
    for page in PAGES
] + [
    # One page per project, driven by the Project table.
    path("projects/<slug:slug>/", ProjectDetailView.as_view(), name="project_detail"),
    # The three Gold Standard consultation notices lived at these paths on the
    # old site. The apex now points here and we do not have their text, so they
    # 404ed -- these are public compliance records and a dead link is the worst
    # answer. A temporary 302 to the events page keeps them reachable; replace
    # each one with the real notice at the same path and delete its redirect.
    *[
        path(f"events/{slug}/", RedirectView.as_view(pattern_name="website:events"),
             name=f"notice_{slug.replace('-', '_')}")
        for slug in (
            "green-ics-bangladesh",
            "green-ics-bangladesh-part-two",
            "green-ics-bangladesh-part-three",
        )
    ],
    path("robots.txt", robots_txt, name="robots"),
    path("sitemap.xml", sitemap_xml, name="sitemap"),
]
