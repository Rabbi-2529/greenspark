"""
Mark the photos that have no 1600px version.

Checked against what is actually on disk rather than written out by hand, so
this stays right if the missing sizes are generated later: anything with a
1600px file keeps the flag on.
"""

from pathlib import Path

from django.conf import settings
from django.db import migrations


def mark(apps, schema_editor):
    Project = apps.get_model("content", "Project")
    photos = Path(settings.STATICFILES_DIRS[0]) / "img" / "photos"

    for project in Project.objects.all():
        has_large = (photos / f"{project.photo}-1600.webp").is_file()
        if project.photo_has_large != has_large:
            project.photo_has_large = has_large
            project.save(update_fields=["photo_has_large"])


def unmark(apps, schema_editor):
    apps.get_model("content", "Project").objects.update(photo_has_large=True)


class Migration(migrations.Migration):

    dependencies = [("content", "0008_project_photo_has_large")]

    operations = [migrations.RunPython(mark, unmark)]
