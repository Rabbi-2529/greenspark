"""Shared model behaviour."""

from django.db import models


class Singleton(models.Model):
    """
    A record there is only ever one of.

    Site settings, contact details and the like are a single form in the
    console, not a list. Forcing the primary key to 1 means a second row cannot
    be created by accident, and ``load()`` always answers with the one row,
    creating it from the field defaults on a fresh database.
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        kwargs.pop("force_insert", None)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """There is nothing sensible to delete to."""
        return (0, {})

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
