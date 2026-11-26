"""
The one card whose wording differed from its project.

The Projects page was hand-written, and its rooftop card carried a shorter
line than the project's own summary. Converting the grid to a loop would have
quietly lengthened it, so the shorter wording is stored and the card keeps
saying what it has always said.

Found by the parity test, which is exactly the kind of thing it is for.
"""

from django.db import migrations

SHORTER = {
    "rooftop-solar-mrv": (
        "Rooftop solar systems on homes and businesses brought together as one "
        "carbon programme, measured, reported and verified."
    ),
}


def seed(apps, schema_editor):
    Project = apps.get_model("content", "Project")
    for slug, text in SHORTER.items():
        Project.objects.filter(slug=slug).update(card_summary=text)


def unseed(apps, schema_editor):
    Project = apps.get_model("content", "Project")
    Project.objects.filter(slug__in=SHORTER).update(card_summary="")


class Migration(migrations.Migration):

    dependencies = [("content", "0006_project_card_summary")]

    operations = [migrations.RunPython(seed, unseed)]
