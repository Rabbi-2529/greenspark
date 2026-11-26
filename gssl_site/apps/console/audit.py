"""
Writing the activity log.

One entry per console write. ``record()`` never raises: a failure to log must
not lose the edit that was just saved, so it is logged to stderr and swallowed.

Nothing secret reaches the log. Any field whose name looks like a credential is
replaced with a placeholder, and values are truncated, so the log stays
readable and never becomes a second copy of the content.
"""

from __future__ import annotations

import logging

from .models import AuditEntry

logger = logging.getLogger("apps.console")

# Field names whose values are never written to the log.
SECRET_HINTS = ("password", "token", "secret", "key", "signature", "otp")

VALUE_LIMIT = 200


def _is_secret(field: str) -> bool:
    name = field.lower()
    return any(hint in name for hint in SECRET_HINTS)


def _clean(value) -> object:
    """A loggable, JSON-safe version of a field value."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    if len(text) > VALUE_LIMIT:
        return text[:VALUE_LIMIT] + "…"
    return text


def changes_from_form(form) -> dict:
    """
    The field-level diff a ModelForm just applied.

    Reads ``changed_data`` against the form's initial values, so an unchanged
    field never appears and a save with no edits logs an empty diff.
    """
    diff: dict[str, dict] = {}
    for field in getattr(form, "changed_data", ()):
        if _is_secret(field):
            diff[field] = {"from": "(not logged)", "to": "(changed)"}
            continue
        diff[field] = {
            "from": _clean(form.initial.get(field)),
            "to": _clean(form.cleaned_data.get(field)),
        }
    return diff


def snapshot(obj, fields) -> dict:
    """The values of ``fields`` on ``obj``, for logging a creation or deletion."""
    out: dict[str, object] = {}
    for field in fields or ():
        if _is_secret(field):
            continue
        try:
            out[field] = _clean(getattr(obj, field))
        except Exception:  # a property that needs a saved row, say
            continue
    return out


def record(request, action, *, obj=None, module="", changes=None, note="") -> None:
    """Log one console action. Never raises."""
    try:
        user = getattr(request, "user", None)
        actor = user if (user is not None and user.is_authenticated) else None
        AuditEntry.objects.create(
            actor=actor,
            actor_label=(actor.get_username() if actor else note or "anonymous")[:150],
            action=action,
            module=(module or "")[:60],
            object_id=str(getattr(obj, "pk", "") or "")[:50],
            object_label=(str(obj) if obj is not None else "")[:250],
            changes=changes or {},
            note=note[:250],
        )
    except Exception:
        logger.exception("could not write a console audit entry (action=%s)", action)
