"""
Seed the home page carousel with the five cards the template carried.

Every word is read off the template rather than retyped, including the facts,
which are not the project's own attributes: the carousel says "Gold Standard"
where the project record says "Gold Standard (registered)", and it picks a
different third fact per card.
"""

from django.db import migrations

# title, text, project slug, programme key, link label, registered,
# [(badge label, variant)], [(fact label, fact value)]
SLIDES = [
    (
        "Green ICS — Phase 1",
        "The first phase of our improved cookstove programme: stoves installed "
        "with households who cook with firewood and biomass.",
        "green-ics-phase-1", None, "View project", True, [],
        [("Standard", "Gold Standard"), ("Country", "Bangladesh"),
         ("Stoves", "20,000+ installed")],
    ),
    (
        "Green ICS — Phase 2",
        "Expanding the programme to more households, with the same design, "
        "training and monitoring as Phase 1.",
        "green-ics-phase-2", None, "View project", True, [],
        [("Standard", "Gold Standard"), ("Country", "Bangladesh"),
         ("Stoves", "50,000 planned")],
    ),
    (
        "Rooftop Solar MRV",
        "Rooftop solar systems on homes and businesses brought together as one "
        "carbon programme, with every system measured, reported and verified.",
        None, "rooftop", "View programme", False,
        [("Priority 02", "priority"), ("In development", "development")],
        [("Standard", "To be confirmed"), ("Country", "Bangladesh"),
         ("Stage", "In development")],
    ),
    (
        "Green ICS — Phase 3",
        "The next phase of the programme is in preparation. Details will be "
        "published once it is registered.",
        "green-ics-phase-3", None, "View project", False,
        [("In pipeline", "development")],
        [("Standard", "To be confirmed"), ("Country", "Bangladesh"),
         ("Stage", "Pipeline")],
    ),
    (
        "Community monitoring and maintenance",
        "Field officers visit households, check stoves, replace parts and "
        "record use for the monitoring report.",
        "community-monitoring", None, "View project", False,
        [("Active", "active")],
        [("Activity", "Monitoring"), ("Country", "Bangladesh"),
         ("Visits", "Every year")],
    ),
]


def seed(apps, schema_editor):
    Project = apps.get_model("content", "Project")
    Programme = apps.get_model("content", "Programme")
    Slide = apps.get_model("content", "CarouselSlide")
    Badge = apps.get_model("content", "SlideBadge")
    Fact = apps.get_model("content", "SlideFact")

    for order, row in enumerate(SLIDES, start=1):
        title, text, slug, prog_key, label, registered, badges, facts = row
        slide, _ = Slide.objects.update_or_create(
            title=title,
            defaults={
                "text": text,
                "project": Project.objects.filter(slug=slug).first() if slug else None,
                "programme": (
                    Programme.objects.filter(key=prog_key).first() if prog_key else None
                ),
                "link_label": label,
                "registered": registered,
                "sort_order": order,
            },
        )
        slide.badges.all().delete()
        for i, (blabel, variant) in enumerate(badges, start=1):
            Badge.objects.create(
                slide=slide, label=blabel, variant=variant, sort_order=i
            )
        slide.facts.all().delete()
        for i, (flabel, value) in enumerate(facts, start=1):
            Fact.objects.create(slide=slide, label=flabel, value=value, sort_order=i)


def unseed(apps, schema_editor):
    apps.get_model("content", "CarouselSlide").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [("content", "0016_carousel")]

    operations = [migrations.RunPython(seed, unseed)]
