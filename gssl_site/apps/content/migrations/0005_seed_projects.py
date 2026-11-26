"""
Move the seven projects out of code and into the database.

Every value is read from ``apps.website.content``, the frozen dataclass table
this replaces, so nothing is retyped and nothing can drift. The copy includes
the shared paragraphs, which several projects reuse word for word.

Three presentation fields are filled in from the Projects page's hand-written
grid, so the cards can be rendered from a loop later without the markup
moving: which card is staggered, which still uses a stock photo, and the one
card that opens a programme page instead of a project page.
"""

from django.db import migrations

# The Projects page arranges its cards in its own order, which is not the
# order the projects are listed in everywhere else, and staggers every third
# card's fade-in. Read off the template: slug -> (position, reveal delay).
GRID = {
    "green-ics-phase-1": (1, 0),
    "green-ics-phase-2": (2, 1),
    "rooftop-solar-mrv": (3, 0),
    "green-ics-phase-3": (4, 2),
    "community-monitoring": (5, 0),
    "stove-design-and-manufacturing": (6, 1),
    "clean-cooking-scoping-nepal": (7, 2),
}

# These two cards are marked in the template as still carrying a stock photo.
STOCK_PHOTOS = {"rooftop-solar-mrv", "clean-cooking-scoping-nepal"}

# The rooftop card opens the programme page: the project itself has no detail
# worth publishing yet.
LINKS_TO_PROGRAMME = {"rooftop-solar-mrv"}

# The six programme pages, in the priority order the design build sets out.
PROGRAMMES = [
    ("cookstove", "Improved Cookstove Programme", "programme_improved_cookstove", "active", True),
    ("rooftop", "Rooftop Solar MRV", "programme_rooftop_solar", "feasibility", True),
    ("water", "Safe Drinking Water", "programme_safe_drinking_water", "concept", True),
    ("irrigation", "Solar Irrigation", "programme_solar_irrigation", "feasibility", False),
    ("rural", "Rural Productive-Use Solar", "programme_rural_productive_use_solar", "concept", False),
    ("rice", "Low-Emission Rice", "programme_low_emission_rice", "concept", False),
]


def seed(apps, schema_editor):
    from apps.content.seed_projects import PROGRAMMES_SEED as CODE_PROGRAMMES
    from apps.content.seed_projects import PROJECTS_SEED as PROJECTS

    Programme = apps.get_model("content", "Programme")
    Project = apps.get_model("content", "Project")
    ProjectParagraph = apps.get_model("content", "ProjectParagraph")

    programmes = {}
    for order, (key, label, url_name, stage, priority) in enumerate(PROGRAMMES, start=1):
        programmes[key], _ = Programme.objects.update_or_create(
            key=key,
            defaults={
                "label": label,
                "url_name": url_name,
                "stage": stage,
                "priority": priority,
                # Every programme page is already routed and linked, so these
                # are on. A programme added later starts off, as the model says.
                "show_on_website": True,
                "sort_order": order,
            },
        )

    # The code table is the authority on the two programmes projects use; if it
    # ever disagrees with the list above, it wins.
    for key, (url_name, label) in CODE_PROGRAMMES.items():
        Programme.objects.filter(key=key).update(url_name=url_name, label=label)

    for order, row in enumerate(PROJECTS, start=1):
        slug = row["slug"]
        grid_order, delay = GRID.get(slug, (order, 0))
        project, _ = Project.objects.update_or_create(
            slug=slug,
            defaults={
                "title": row["title"],
                "summary": row["summary"],
                "location": row["location"],
                "stage": row["stage"],
                "photo": row["photo"],
                "programme": programmes.get(row["programme"]),
                "gs_id": row["gs_id"],
                "standard": row["standard"],
                "tags": " ".join(row["filters"]),
                "proponent": row["proponent"],
                "status_label": row["status_label"],
                "status_note": row["status_note"],
                "card_badge": row["card_badge"],
                "stove_detail": row["stove_detail"],
                "sort_order": order,
                "grid_order": grid_order,
                "reveal_delay": delay,
                "stock_photo": slug in STOCK_PHOTOS,
                "card_links_to_programme": slug in LINKS_TO_PROGRAMME,
            },
        )
        project.paragraphs.all().delete()
        for position, body in enumerate(row["description"], start=1):
            ProjectParagraph.objects.create(project=project, body=body, sort_order=position)


def unseed(apps, schema_editor):
    apps.get_model("content", "Project").objects.all().delete()
    apps.get_model("content", "Programme").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [("content", "0004_projects_and_programmes")]

    operations = [migrations.RunPython(seed, unseed)]
