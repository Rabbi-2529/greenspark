"""
Seed the About Us page's repeated rows.

Every value is the wording already on the page, read off the template rather
than retyped. The page's one-off wording -- its headings, eyebrows and the
careers empty state -- is not here: those are field defaults on ``AboutPage``,
so a fresh database renders the page without this migration having to create a
singleton row at all.

Nothing is seeded into ``JobOpening``. The page is written for an empty table:
it shows the "no open roles right now" paragraph and the two buttons, which is
exactly what it shows today.
"""

from django.db import migrations

# figure, label
STATS = [
    ("2", "offices: Rockdale, NSW and Manikganj, Bangladesh"),
    ("3", "countries: Bangladesh, Nepal and Cambodia"),
    ("2", "cookstove phases registered with Gold Standard"),
]

# title, body
VISION = [
    (
        "Environmental and social impact",
        "We are dedicated to environmentally conscious and compassionate development "
        "in Bangladesh.",
    ),
    (
        "Global access to clean energy",
        "We envision a world where everyone has access to clean energy and a healthy "
        "environment.",
    ),
    (
        "Innovative solutions and community empowerment",
        "By offering innovative solutions and empowering communities, we aim to make a "
        "lasting difference.",
    ),
]

# icon, title, body -- the cards under “Our approach”. These are ApproachItem
# rows of a third kind, alongside the home page's two.
APPROACH = [
    (
        "users",
        "Community engagement",
        "We work closely with local communities to understand their needs and "
        "preferences, so that our solutions are culturally appropriate and sustainable.",
    ),
    (
        "handshake",
        "Partnerships",
        "We collaborate with government agencies, NGOs and private-sector "
        "organisations, drawing on their expertise and resources to maximise our impact.",
    ),
    (
        "flask",
        "Research and development",
        "We invest in research and development to keep improving our products and to "
        "explore new technologies for emerging challenges.",
    ),
]

# icon, title, body
PARTNERS = [
    (
        "users",
        "Communities",
        "Households and the community groups who take part in our programmes.",
    ),
    (
        "building",
        "Local government",
        "Upazila and district officers who help us plan, consult and reach families.",
    ),
    (
        "handshake",
        "NGOs and distributors",
        "Organisations that distribute, install and maintain equipment with us.",
    ),
    (
        "clipboard",
        "Carbon consultants",
        "Specialists who support project design, monitoring and verification.",
    ),
    (
        "coins",
        "Carbon buyers and investors",
        "Buyers of credits from our Gold Standard projects and investors in our pipeline.",
    ),
    (
        "message",
        "Press and job seekers",
        "Journalists covering clean energy and climate, and people who want to join our "
        "teams.",
    ),
]

# title, body
CAREER_AREAS = [
    (
        "Field and community work",
        "Field officers and community facilitators who install, monitor and listen to "
        "households, district by district.",
    ),
    (
        "Carbon and monitoring",
        "Project development, monitoring and reporting for programmes held to "
        "recognised carbon standards.",
    ),
    (
        "Engineering and research",
        "Improving our products and testing clean-energy and water technologies for "
        "rural communities.",
    ),
]


def seed(apps, schema_editor):
    AboutStat = apps.get_model("content", "AboutStat")
    VisionAttribute = apps.get_model("content", "VisionAttribute")
    ApproachItem = apps.get_model("content", "ApproachItem")
    Audience = apps.get_model("content", "Audience")
    CareerArea = apps.get_model("content", "CareerArea")

    AboutStat.objects.bulk_create([
        AboutStat(value=value, label=label, sort_order=order)
        for order, (value, label) in enumerate(STATS, start=1)
    ])
    VisionAttribute.objects.bulk_create([
        VisionAttribute(title=title, body=body, sort_order=order)
        for order, (title, body) in enumerate(VISION, start=1)
    ])
    ApproachItem.objects.bulk_create([
        ApproachItem(kind="about", icon=icon, title=title, body=body, sort_order=order)
        for order, (icon, title, body) in enumerate(APPROACH, start=1)
    ])
    Audience.objects.bulk_create([
        Audience(icon=icon, title=title, body=body, sort_order=order)
        for order, (icon, title, body) in enumerate(PARTNERS, start=1)
    ])
    CareerArea.objects.bulk_create([
        CareerArea(title=title, body=body, sort_order=order)
        for order, (title, body) in enumerate(CAREER_AREAS, start=1)
    ])


def unseed(apps, schema_editor):
    for model in ("AboutStat", "VisionAttribute", "Audience", "CareerArea"):
        apps.get_model("content", model).objects.all().delete()
    apps.get_model("content", "ApproachItem").objects.filter(kind="about").delete()


class Migration(migrations.Migration):

    dependencies = [("content", "0018_about_page")]

    operations = [migrations.RunPython(seed, unseed)]
