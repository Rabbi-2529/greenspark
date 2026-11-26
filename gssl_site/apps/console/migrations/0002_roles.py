"""
The three console roles, as groups.

The console checks a rank, not a permission list, so these groups carry no
permissions — the name is the role. Creating them here means a fresh install
has the roles ready before anyone opens the staff screen.
"""

from django.db import migrations

GROUPS = ["Editors", "Publishers", "Administrators"]


def create_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for name in GROUPS:
        Group.objects.get_or_create(name=name)


def remove_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=GROUPS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("console", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_roles, remove_roles),
    ]
