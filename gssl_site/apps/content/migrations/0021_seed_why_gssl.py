"""
Seed the Why GSSL page's three bands.

Every value is the wording already on the page, read off the template rather
than retyped -- including the curly apostrophe in “the community’s needs”.

The page's headings and eyebrows are not here: those are field defaults on
``WhyGsslPage``, so a fresh database renders the page without this migration
having to create a singleton row at all.
"""

from django.db import migrations

# icon, title, body -- “What sets us apart”.
REASONS = [
    ("users", "Built with communities",
     "We plan each programme with households, local government and NGOs, so that "
     "it fits local needs and lasts."),
    ("shield-check", "Held to recognised standards",
     "Phase 1 and Phase 2 of our cookstove programme are registered with Gold "
     "Standard."),
    ("clipboard", "Monitoring you can check",
     "Field officers visit households, check equipment and keep a clear record "
     "for every installation, ready for independent verification."),
    ("globe", "On the ground in three countries",
     "Head office in Rockdale, NSW, an operations base in Manikganj, Bangladesh, "
     "and work in Nepal and Cambodia."),
    ("layers", "A pipeline beyond cookstoves",
     "Safe drinking water, solar irrigation, rooftop solar, rural productive-use "
     "solar and low-emission rice programmes are in development."),
    ("wrench", "Local skills and jobs",
     "We train field officers and local makers to install, produce and repair "
     "equipment close to the families who use it."),
]

# title, body -- “Working with us”. No icon: these are plain cards.
EXPECTATIONS = [
    ("Communities and local government",
     "Consultations before and during each project, a feedback channel that is "
     "always open, and every comment recorded and answered."),
    ("Partners and distributors",
     "Clear roles, shared training and one team to work with, from design to "
     "monitoring."),
    ("Carbon buyers and investors",
     "Projects registered with Gold Standard, documented monitoring, and early "
     "sight of the programmes in our pipeline."),
]

# icon, title, body -- “How we work”. The step numbers are a CSS counter, so
# nothing here holds one.
STEPS = [
    ("message", "Listen and plan",
     "We start with the community’s needs and the local context."),
    ("flask", "Design and test",
     "We design the programme and test it with local partners."),
    ("wrench", "Install and train",
     "Trained field officers install equipment and show families how to use it."),
    ("chart", "Monitor and verify",
     "We return for monitoring visits and prepare records for independent "
     "verification."),
]


def seed(apps, schema_editor):
    WhyItem = apps.get_model("content", "WhyItem")
    rows = []
    for order, (icon, title, body) in enumerate(REASONS, start=1):
        rows.append(WhyItem(kind="reason", icon=icon, title=title, body=body,
                            sort_order=order))
    for order, (title, body) in enumerate(EXPECTATIONS, start=1):
        rows.append(WhyItem(kind="expectation", icon="", title=title, body=body,
                            sort_order=order))
    for order, (icon, title, body) in enumerate(STEPS, start=1):
        rows.append(WhyItem(kind="step", icon=icon, title=title, body=body,
                            sort_order=order))
    WhyItem.objects.bulk_create(rows)


def unseed(apps, schema_editor):
    apps.get_model("content", "WhyItem").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [("content", "0020_why_gssl_page")]

    operations = [migrations.RunPython(seed, unseed)]
