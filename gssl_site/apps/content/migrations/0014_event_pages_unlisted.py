"""
Bring the two event detail pages back, unlisted.

They were offline because they still carry the design build's invented events
-- a 2027 Local Stakeholder Consultation in Manikganj and a feedback round to
January 2027. Green Spark asked for the pages back, so the design is reachable
again at its own URLs; unlisted rather than live means nothing links to them
and search engines are told not to index them, which is the right state for a
consultation notice that has not happened. One change in the console makes
them live once the wording is Green Spark's own.
"""

from django.db import migrations

PAGES = ("event_detail", "event_feedback_round")


def unlist(apps, schema_editor):
    Page = apps.get_model("content", "Page")
    Page.objects.filter(name__in=PAGES).update(status="unlisted")


def offline(apps, schema_editor):
    Page = apps.get_model("content", "Page")
    Page.objects.filter(name__in=PAGES).update(status="offline")


class Migration(migrations.Migration):

    dependencies = [("content", "0013_hide_top_bar")]

    operations = [migrations.RunPython(unlist, offline)]
