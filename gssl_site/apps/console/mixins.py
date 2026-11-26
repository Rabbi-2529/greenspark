"""
Access control for every console view.

One mixin does four things in order: require a signed-in staff account, expire
an idle session, require the rank the view asks for, and put the sidebar on the
page. Every console view uses it, so forgetting it is the only way to leave a
page open, and a test walks every registered URL to prove none is.
"""

from __future__ import annotations

import time

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect, render
from django.urls import reverse

from . import audit, roles
from .models import AuditEntry
from .registry import registry

SEEN_KEY = "console_seen_at"
# Don't rewrite the session on every single request.
TOUCH_EVERY = 60


class ConsoleAccessMixin:
    required_rank = roles.VIEWER

    # --- the gate ---

    def dispatch(self, request, *args, **kwargs):
        if not roles.may_sign_in(request.user):
            return redirect_to_login(
                request.get_full_path(), reverse("console:login"), "next"
            )

        expired = self.expire_if_idle(request)
        if expired is not None:
            return expired

        refused = self.check_access(request)
        if refused is not None:
            return refused

        return super().dispatch(request, *args, **kwargs)

    def check_access(self, request):
        """
        Whether this signed-in staff member may see this page. Returns a
        response to send instead, or None to carry on. Module views override
        it to ask the module.
        """
        if not roles.has_rank(request.user, self.required_rank):
            return self.refuse(request)
        return None

    def expire_if_idle(self, request):
        """Sign out a session that has sat untouched for too long."""
        now = int(time.time())
        seen = request.session.get(SEEN_KEY)
        if seen and now - seen > settings.CONSOLE_IDLE_SECONDS:
            audit.record(request, AuditEntry.LOGOUT, note="idle timeout")
            logout(request)
            return redirect(f"{reverse('console:login')}?timeout=1")
        if not seen or now - seen > TOUCH_EVERY:
            request.session[SEEN_KEY] = now
        return None

    def refuse(self, request):
        context = {
            "console_nav": registry.nav(request.user),
            "console_role": roles.label_of(request.user),
            "needed": roles.RANK_LABELS.get(self.required_rank, "a higher role"),
        }
        return render(request, "console/refused.html", context, status=403)

    # --- shared context ---

    def console_base_context(self, **kwargs) -> dict:
        """
        The shell's own context: sidebar, role, breadcrumbs.

        A plain ``View`` has no ``get_context_data``, so the views that render
        by hand call this instead of reaching for super().
        """
        context = {
            "console_nav": registry.nav(self.request.user),
            "console_role": roles.label_of(self.request.user),
            "console_rank": roles.rank_of(self.request.user),
            "breadcrumbs": self.breadcrumbs(),
        }
        context.update(kwargs)
        return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for key, value in self.console_base_context().items():
            context.setdefault(key, value)
        return context

    def breadcrumbs(self) -> list[tuple[str, str]]:
        """[(label, url or "")]; the last one is the current page."""
        return []
