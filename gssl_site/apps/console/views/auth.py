"""
Signing in and out of the console, and passwords.

The sign-in form is rate-limited the same way the public enquiry form is: a
hashed counter in the cache, so a flood of guesses stops being answered without
ever storing a visitor's address. Failures are logged with the address that was
tried, which is what makes a password-spraying attempt visible afterwards.
"""

from __future__ import annotations

import hashlib
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.core.cache import cache
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView

from .. import audit, roles
from ..forms import ConsolePasswordChangeForm, ConsoleSetPasswordForm, ConsoleAuthenticationForm
from ..mixins import SEEN_KEY, ConsoleAccessMixin
from ..models import AuditEntry
from ..registry import registry

User = get_user_model()


def _attempt_key(request, username: str) -> str:
    """A hashed key per visitor and address. The raw address is never stored."""
    ip = request.META.get("REMOTE_ADDR", "")
    if settings.BEHIND_PROXY:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            ip = forwarded.split(",")[-1].strip()
    seed = f"{ip}:{username.strip().lower()}".encode()
    return "console-login:" + hashlib.sha256(seed).hexdigest()[:32]


def _locked_out(request, username: str) -> bool:
    key = _attempt_key(request, username)
    return (cache.get(key) or 0) >= settings.CONSOLE_LOGIN_MAX_ATTEMPTS


def _count_failure(request, username: str) -> None:
    key = _attempt_key(request, username)
    window = settings.CONSOLE_LOGIN_LOCKOUT_SECONDS
    if cache.add(key, 1, timeout=window):
        return
    try:
        cache.incr(key)
    except ValueError:  # expired between add() and incr()
        cache.add(key, 1, timeout=window)


def _clear_failures(request, username: str) -> None:
    cache.delete(_attempt_key(request, username))


class ConsoleLoginView(LoginView):
    template_name = "console/login.html"
    authentication_form = ConsoleAuthenticationForm
    redirect_authenticated_user = False

    def dispatch(self, request, *args, **kwargs):
        if roles.may_sign_in(request.user):
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def get_default_redirect_url(self):
        return reverse("console:dashboard")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["timed_out"] = self.request.GET.get("timeout") == "1"
        context["locked_out"] = getattr(self, "locked_out", False)
        return context

    def post(self, request, *args, **kwargs):
        username = request.POST.get("username", "")
        if _locked_out(request, username):
            self.locked_out = True
            form = self.get_form()
            context = self.get_context_data(form=form)
            return self.render_to_response(context, status=429)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        _clear_failures(self.request, form.cleaned_data.get("username", ""))
        # Start the idle clock the moment the session begins.
        self.request.session[SEEN_KEY] = int(time.time())
        audit.record(self.request, AuditEntry.LOGIN)
        return response

    def form_invalid(self, form):
        username = form.data.get("username", "")
        _count_failure(self.request, username)
        audit.record(
            self.request,
            AuditEntry.LOGIN_FAILED,
            note=f"tried {username[:60]}" if username else "no address given",
        )
        return super().form_invalid(form)


class ConsoleLogoutView(LogoutView):
    next_page = reverse_lazy("console:login")

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            audit.record(request, AuditEntry.LOGOUT)
        return super().post(request, *args, **kwargs)


class ConsolePasswordChangeView(ConsoleAccessMixin, PasswordChangeView):
    """Changing your own password."""

    template_name = "console/password_change.html"
    form_class = ConsolePasswordChangeForm
    success_url = reverse_lazy("console:dashboard")

    def breadcrumbs(self):
        return [("Your password", "")]

    def form_valid(self, form):
        response = super().form_valid(form)
        audit.record(self.request, AuditEntry.PASSWORD, note="own password")
        messages.success(self.request, "Your password has been changed.")
        return response


class StaffPasswordView(ConsoleAccessMixin, FormView):
    """An administrator setting someone else's password."""

    template_name = "console/password_set.html"
    form_class = ConsoleSetPasswordForm
    required_rank = roles.ADMINISTRATOR

    def dispatch(self, request, *args, **kwargs):
        self.target = None
        return super().dispatch(request, *args, **kwargs)

    def get_target(self):
        if self.target is None:
            try:
                self.target = User.objects.get(pk=self.kwargs["pk"])
            except User.DoesNotExist as exc:
                raise Http404("No such account") from exc
        return self.target

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.get_target()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["target"] = self.get_target()
        context["module"] = registry.get("staff")
        return context

    def breadcrumbs(self):
        staff = registry.get("staff")
        crumbs = []
        if staff:
            crumbs.append((staff.label_plural, staff.url()))
        crumbs.append((f"Password for {self.get_target().get_username()}", ""))
        return crumbs

    def get_success_url(self):
        staff = registry.get("staff")
        return staff.url() if staff else reverse("console:dashboard")

    def form_valid(self, form):
        form.save()
        audit.record(
            self.request, AuditEntry.PASSWORD, obj=self.get_target(), module="staff",
            note="set by an administrator",
        )
        messages.success(
            self.request,
            f"A new password is set for {self.get_target().get_username()}.",
        )
        return super().form_valid(form)
