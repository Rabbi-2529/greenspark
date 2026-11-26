"""
The four bands that were hidden in code.

Until now these were wrapped in ``{% comment %}``, so showing one again meant
editing a template and deploying. They are switches in the console instead,
turned off here, and each one carries the reason it is off so nobody turns it
back on without knowing what is in it.

Nothing changes on the site: a commented-out band and a band with its switch
off both render nothing.
"""

from django.db import migrations

HIDDEN = {
    ("home", "where"): (
        "The district map and impact counters. Hidden at Green Spark's request — "
        "the figures are design-build samples and need approving first."
    ),
    ("home", "news"): (
        "News & insights on the home page. Hidden at Green Spark's request — "
        "all three posts are design-build samples, not real articles."
    ),
    ("home", "events"): (
        "The “Have your say” events band. Hidden at Green Spark's request."
    ),
    ("programme_improved_cookstove", "where"): (
        "“Where the programme works” — the district map and the counters "
        "(8+ years, 95,000 people, 10 districts, 38,400 visits). Hidden until "
        "Green Spark approves those figures."
    ),
}


def hide(apps, schema_editor):
    Section = apps.get_model("content", "Section")
    for (page_name, key), reason in HIDDEN.items():
        Section.objects.filter(page__name=page_name, key=key).update(
            visible=False, blurb=reason,
        )


def show(apps, schema_editor):
    Section = apps.get_model("content", "Section")
    for page_name, key in HIDDEN:
        Section.objects.filter(page__name=page_name, key=key).update(visible=True)


class Migration(migrations.Migration):

    dependencies = [("content", "0002_seed_site_map")]

    operations = [migrations.RunPython(hide, show)]
