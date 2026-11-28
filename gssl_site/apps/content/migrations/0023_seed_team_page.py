"""
Seed the Our team page: the one leader and the five teams.

Every value is the wording already on the page. The page's headings are not
here: those are field defaults on ``TeamPage``.

The leader's initials are not seeded either. "PR" is what the template carried
for Pankaj Rajbangshi, and it is what the name itself gives, so storing it
would be storing a copy of something already known.
"""

from django.db import migrations

# name, role, organisation, bio
LEADERS = [
    (
        "Pankaj Rajbangshi",
        "Director and CEO",
        "Green Spark Solutions Australia Pty Ltd · Rockdale, NSW",
        "Leads strategy, partnerships and carbon project development from our head "
        "office in Australia.",
    ),
]

# title, body
GROUPS = [
    (
        "Field operations · Manikganj",
        "Field officers who install stoves, show families how to use them and return "
        "for monitoring visits.",
    ),
    (
        "Carbon and monitoring",
        "Project design, monitoring and reporting for programmes held to recognised "
        "carbon standards.",
    ),
    (
        "Engineering and research",
        "Improving the Green ICS with household feedback, and testing clean-energy and "
        "water technologies.",
    ),
    (
        "Community and stakeholder engagement",
        "Consultations, feedback rounds and grievance handling, in Bangla and English.",
    ),
    (
        "Partnerships · Australia",
        "Work with partners, buyers and investors from our head office in Rockdale, NSW.",
    ),
]


def seed(apps, schema_editor):
    TeamLeader = apps.get_model("content", "TeamLeader")
    TeamGroup = apps.get_model("content", "TeamGroup")

    TeamLeader.objects.bulk_create([
        TeamLeader(name=name, role=role, organisation=org, bio=bio, sort_order=order)
        for order, (name, role, org, bio) in enumerate(LEADERS, start=1)
    ])
    TeamGroup.objects.bulk_create([
        TeamGroup(title=title, body=body, sort_order=order)
        for order, (title, body) in enumerate(GROUPS, start=1)
    ])


def unseed(apps, schema_editor):
    apps.get_model("content", "TeamLeader").objects.all().delete()
    apps.get_model("content", "TeamGroup").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [("content", "0022_team_page")]

    operations = [migrations.RunPython(seed, unseed)]
