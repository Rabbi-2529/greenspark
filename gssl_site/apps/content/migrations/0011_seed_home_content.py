"""
Seed the home page's approach cards, impact figures and districts.

Every value is the wording already on the page, read off the template rather
than retyped. The figures come in **unapproved**: the design build's README
§11 lists all of them as sample data awaiting Green Spark's sign-off, and they
sit inside a band that is hidden, so nothing changes on the site either way.
Ticking “approved for the site” is a deliberate act by someone who has checked
the number.
"""

from datetime import date

from django.db import migrations

# title, body, link label, link route, link fragment
HIGHLIGHTS = [
    (
        "Rooftop solar MRV, aggregated into one programme",
        "Generation from many rooftops is measured, reported and verified as a single "
        "carbon programme, so more owners can take part.",
        "Rooftop Solar MRV", "programme_rooftop_solar", "",
    ),
    (
        "About Green Spark",
        "Carbon project developers working with communities in Bangladesh, Nepal and "
        "Cambodia, with projects registered to recognised standards.",
        "View projects", "projects", "",
    ),
    (
        "Our approach",
        "We plan each programme with households, local government and NGOs, then monitor "
        "it so partners and buyers can rely on the record.",
        "Our approach", "about", "#approach",
    ),
]

ATTRIBUTES = [
    (
        "Community engagement",
        "We work closely with local communities to understand their needs and preferences, "
        "so that our solutions are culturally appropriate and sustainable.",
    ),
    (
        "Partnerships",
        "We collaborate with government agencies, NGOs and private-sector organisations, "
        "drawing on their expertise and resources to maximise our impact.",
    ),
    (
        "Research and development",
        "We invest in research and development to keep improving our products and to "
        "explore new technologies for emerging challenges.",
    ),
]

# label, as written, count, suffix, estimated
COUNTERS = [
    ("Years of experience", "8+", 8, "+", False),
    ("Improved cookstoves installed (Phase 1)", "20,000+", 20000, "+", False),
    ("People benefiting", "95,000", 95000, "", True),
    ("Districts reached", "10", 10, "", False),
    ("Monitoring visits", "38,400", 38400, "", False),
    ("Firewood saved per year", "—", None, "", False),
]

AS_OF = date(2026, 9, 30)

DISTRICTS = [
    ("Dhaka", "Dhaka division", False),
    ("Faridpur", "Dhaka division", False),
    ("Gazipur", "Dhaka division", False),
    ("Manikganj", "Operations base", True),
    ("Munshiganj", "Dhaka division", False),
    ("Narayanganj", "Dhaka division", False),
    ("Pabna", "Rajshahi division", False),
    ("Rajbari", "Dhaka division", False),
    ("Sirajganj", "Rajshahi division", False),
    ("Tangail", "Dhaka division", False),
]


def seed(apps, schema_editor):
    ApproachItem = apps.get_model("content", "ApproachItem")
    Counter = apps.get_model("content", "Counter")
    District = apps.get_model("content", "District")

    for order, (title, body, label, route, fragment) in enumerate(HIGHLIGHTS, start=1):
        ApproachItem.objects.update_or_create(
            kind="highlight", title=title,
            defaults={
                "body": body, "link_label": label, "link_route": route,
                "link_fragment": fragment, "sort_order": order,
            },
        )

    for order, (title, body) in enumerate(ATTRIBUTES, start=1):
        ApproachItem.objects.update_or_create(
            kind="attribute", title=title,
            defaults={"body": body, "sort_order": order},
        )

    for order, (label, display, count, suffix, estimated) in enumerate(COUNTERS, start=1):
        Counter.objects.update_or_create(
            label=label,
            defaults={
                "display": display, "count": count, "suffix": suffix,
                "estimated": estimated, "as_of": AS_OF,
                "published": False,   # Green Spark approves these, not us.
                "sort_order": order,
            },
        )

    for order, (name, division, is_base) in enumerate(DISTRICTS, start=1):
        District.objects.update_or_create(
            name=name,
            defaults={"division": division, "is_base": is_base, "sort_order": order},
        )


def unseed(apps, schema_editor):
    for model in ("ApproachItem", "Counter", "District"):
        apps.get_model("content", model).objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [("content", "0010_home_content")]

    operations = [migrations.RunPython(seed, unseed)]
