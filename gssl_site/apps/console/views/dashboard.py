"""
The console's front page.

What someone signing in needs to know first: whether anything is waiting for
them, and what changed since they were last here.
"""

from __future__ import annotations

from django.views.generic import TemplateView

from ..mixins import ConsoleAccessMixin
from ..models import AuditEntry
from ..registry import registry


class DashboardView(ConsoleAccessMixin, TemplateView):
    template_name = "console/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["waiting"] = self.waiting()
        context["recent"] = AuditEntry.objects.exclude(
            action__in=[AuditEntry.LOGIN, AuditEntry.LOGOUT, AuditEntry.LOGIN_FAILED]
        ).select_related("actor")[:12]
        context["tiles"] = self.tiles()
        return context

    def waiting(self) -> list[dict]:
        """Counts that mean someone has something to do."""
        out: list[dict] = []
        enquiries = registry.get("enquiries")
        if enquiries and enquiries.may_view(self.request.user):
            unhandled = enquiries.model._default_manager.filter(handled=False).count()
            out.append({
                "label": "Enquiries to answer",
                "count": unhandled,
                "url": enquiries.url() + "?handled=0",
                "tone": "warn" if unhandled else "calm",
                "empty": "Nothing waiting",
            })
        return out

    def tiles(self) -> list[dict]:
        """One tile per module this user may open, with its row count."""
        out = []
        for module in registry.all():
            if not module.may_view(self.request.user):
                continue
            out.append({
                "module": module,
                "count": module.queryset().count(),
            })
        return out

    def breadcrumbs(self):
        return []
