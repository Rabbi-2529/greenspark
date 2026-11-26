"""
Console models.

The console owns one model: the record of what staff did in it. Content models
live in apps.content (see CMS-PLAN.md); this is about the panel itself, so it
stays here.

Every write the console makes is logged, including the field-level diff, so a
change to the live site can always be traced to a person and a time. Entries
keep the actor's name as text as well as a foreign key, so deleting an account
does not erase its history.
"""

from django.conf import settings
from django.db import models


class AuditEntry(models.Model):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    PUBLISH = "publish"
    UNPUBLISH = "unpublish"
    REORDER = "reorder"
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD = "password"

    ACTIONS = [
        (CREATE, "created"),
        (UPDATE, "changed"),
        (DELETE, "deleted"),
        (PUBLISH, "published"),
        (UNPUBLISH, "unpublished"),
        (REORDER, "reordered"),
        (LOGIN, "signed in"),
        (LOGIN_FAILED, "failed sign-in"),
        (LOGOUT, "signed out"),
        (PASSWORD, "set a password"),
    ]

    at = models.DateTimeField("when", auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True, on_delete=models.SET_NULL,
        related_name="console_audit_entries",
    )
    # Kept as text so history survives the account being deleted.
    actor_label = models.CharField("who", max_length=150, blank=True)
    action = models.CharField(max_length=20, choices=ACTIONS, db_index=True)

    module = models.CharField(max_length=60, blank=True)
    object_id = models.CharField(max_length=50, blank=True)
    object_label = models.CharField("what", max_length=250, blank=True)

    # {field: {"from": ..., "to": ...}} — never holds a password or a token.
    changes = models.JSONField(default=dict, blank=True)
    note = models.CharField(max_length=250, blank=True)

    class Meta:
        ordering = ["-at"]
        verbose_name = "activity entry"
        verbose_name_plural = "activity"
        indexes = [models.Index(fields=["module", "object_id"])]

    def __str__(self) -> str:
        who = self.actor_label or "someone"
        what = self.object_label or self.module or "the console"
        return f"{who} {self.get_action_display()} {what}"

    @property
    def changed_fields(self) -> list[str]:
        return sorted(self.changes) if isinstance(self.changes, dict) else []
