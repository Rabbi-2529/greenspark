"""
Turn the top bar off.

Green Spark asked for the strip above the menu -- WhatsApp, the email address,
the opening hours and the language switch -- to go. It is a switch rather than
deleted markup, so this records their decision in the database and they can
put it back from the console without a deploy.
"""

from django.db import migrations


def hide(apps, schema_editor):
    SiteSettings = apps.get_model("content", "SiteSettings")
    SiteSettings.objects.update_or_create(pk=1, defaults={"show_topbar": False})


def show(apps, schema_editor):
    SiteSettings = apps.get_model("content", "SiteSettings")
    SiteSettings.objects.filter(pk=1).update(show_topbar=True)


class Migration(migrations.Migration):

    dependencies = [("content", "0012_site_show_topbar")]

    operations = [migrations.RunPython(hide, show)]
