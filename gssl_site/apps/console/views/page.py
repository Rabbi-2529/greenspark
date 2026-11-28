"""
One page of the website, and everything on it.

Green Spark asked for this in their own words: go to Home page, and see every
option on that page. The console's other screens are organised by model --
a HomePage row here, impact figures there, a carousel somewhere else -- which
is how the data is shaped, not how anyone thinks about a website.

This screen is the other way round. It takes a page, and gathers the bands it
is made of and every module whose content appears on it. Each module says
which pages it belongs to (``Module.pages``), so adding content to a page puts
it on this screen without anyone editing a template.
"""

from __future__ import annotations

from django.http import Http404
from django.views.generic import TemplateView

from apps.content.models import Page, Section

from ..mixins import ConsoleAccessMixin
from ..registry import registry


class PageDetailView(ConsoleAccessMixin, TemplateView):
    """Everything editable on one page of the website."""

    template_name = "console/page.html"

    def get_page(self) -> Page:
        try:
            return Page.objects.get(name=self.kwargs["name"])
        except Page.DoesNotExist as exc:
            raise Http404("No such page") from exc

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page = self.get_page()
        user = self.request.user

        context["page"] = page
        context["sections"] = (
            Section.objects.filter(page=page).order_by("sort_order", "pk")
        )
        context["hidden_count"] = sum(1 for s in context["sections"] if not s.visible)
        context["parts"] = self.parts(user, page)

        pages_module = registry.get("pages")
        context["page_url"] = (
            pages_module.row_url(page.pk)
            if pages_module and pages_module.may_view(user)
            else ""
        )
        sections_module = registry.get("sections")
        context["sections_url"] = (
            f"{sections_module.url()}?on_page={page.name}"
            if sections_module and sections_module.may_view(user)
            else ""
        )
        return context

    def parts(self, user, page: Page) -> list[dict]:
        """The content on this page, one entry per module, with its size."""
        out: list[dict] = []
        for module in registry.for_page(user, page.name):
            count = module.model._default_manager.count()
            out.append({
                "module": module,
                "count": count,
                "url": module.url(),
                # A singleton is one record, so send people straight into it
                # rather than to a list with a single row on it.
                "single": module.singleton,
            })
        return out

    def breadcrumbs(self):
        return [("Web", ""), (self.get_page().label, "")]
