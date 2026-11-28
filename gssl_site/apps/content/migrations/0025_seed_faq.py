"""
Seed the FAQ page's five topics and twenty questions, and the six questions on
the cookstove programme page.

Read off the two templates rather than retyped, including the curly quotes in
“Partnership” and “Gold Standard registered”, the middle dot in the registry
link labels, and the ``&amp;`` in the registry URLs.

Internal links are stored as ``route:`` hrefs rather than paths -- the
templates carried ``{% url 'website:enquire' %}`` and the field carries
``route:enquire``, resolved when the page renders. Routes stay in code, so an
answer cannot be left pointing at a page that has moved.

Nothing here holds a question *number*. The ``faq-0`` to ``faq-19`` ids come
from row order at render time; see apps/content/models/faq.py.

The cookstove page's six are their own rows, not a filtered view of the FAQ
page's twenty: it asks several of the same things in shorter words, and one
thing the FAQ page does not ask at all ("How much does a Green ICS cost a
household?").
"""

from django.db import migrations

# anchor, title, [(question, answer), ...]
GROUPS = [
    (
        "about",
        "About Green Spark",
        [
            (
                'What does Green Spark Solutions do?',
                'We develop carbon projects and clean-energy programmes with '
                'communities in Bangladesh, Nepal and Cambodia. Clean '
                'cooking, rooftop solar MRV and safe drinking water lead our '
                'work, designed to improve community health and reduce harm '
                'to the environment.',
            ),
            (
                'Where are you based?',
                'Our head office is in Rockdale, NSW, Australia. Our '
                'operations base is in Manikganj, Bangladesh, where our field '
                'team works with households across the programme districts.',
            ),
            (
                'Who do you work with?',
                'Households, local government, NGOs, manufacturers and '
                'distributors, carbon consultants, and buyers and investors '
                'who want carbon credits they can trust.',
            ),
            (
                'Can my organisation partner with Green Spark?',
                'Yes. <a href="route:enquire">Send us an enquiry</a> and '
                'choose “Partnership” as the subject. We usually reply within '
                'one working day.',
            ),
        ],
    ),
    (
        "cooking",
        "Clean cooking",
        [
            (
                'What is the Green ICS?',
                'The Green ICS is an improved cookstove designed with '
                'Bangladeshi households who cook with firewood and other '
                'biomass. It is designed to burn fuel more efficiently and to '
                'send less smoke into the kitchen.',
            ),
            (
                'How can an improved cookstove help a household?',
                'The stove is designed to burn wood more completely and to '
                'carry smoke out of the kitchen. This can reduce smoke '
                'indoors, the firewood a family needs and the time spent '
                'gathering it.',
            ),
            (
                'Who installs and maintains the stove?',
                'Trained field officers install each stove, show the family '
                'how to use it and return for monitoring visits. Spare parts '
                'such as the strainer, ring and cap can be replaced.',
            ),
            (
                'Does a household pay for the stove?',
                'This depends on the phase of the programme and the partner '
                'in your area. <a href="route:enquire">Contact our team</a> '
                'and we will explain the options available to you.',
            ),
            (
                'Which areas does the programme cover?',
                'The Improved Cookstove Programme runs in districts of the '
                'Dhaka and Rajshahi divisions, from our operations base in '
                'Manikganj. See the <a href="route:home">map on our home '
                'page</a>.',
            ),
        ],
    ),
    (
        "carbon",
        "Carbon credits and Gold Standard",
        [
            (
                'What is a carbon credit?',
                'A carbon credit represents one tonne of carbon dioxide, or '
                'the equivalent in other greenhouse gases, reduced or avoided '
                'and verified under a recognised standard. Credits from our '
                'projects come from the change households make, such as '
                'cooking with an efficient stove.',
            ),
            (
                'What does “Gold Standard registered” mean?',
                'Gold Standard is an independent standard for climate and '
                'development projects. Registration means the project design '
                'has been reviewed against its rules before carbon credits '
                'can be issued.',
            ),
            (
                'Which of your projects are registered?',
                'Phase 1 and Phase 2 of the Improved Cookstove Programme. '
                'Each has a public page on the Gold Standard Impact Registry: '
                '<a '
                'href="https://registry.goldstandard.org/projects?q=GS13141&amp;page=1&amp;countries=BD" '
                'target="_blank" rel="noopener">Phase 1 · GS13141<span '
                'class="visually-hidden"> (opens in a new tab)</span></a> and '
                '<a '
                'href="https://registry.goldstandard.org/projects?q=GS23304&amp;page=1&amp;countries=BD" '
                'target="_blank" rel="noopener">Phase 2 · GS23304<span '
                'class="visually-hidden"> (opens in a new tab)</span></a>.',
            ),
            (
                'How are results monitored?',
                'Field officers visit households, check that stoves are in '
                'use and in good condition, and keep a record for every '
                'installation. An independent verifier reviews the results '
                'before credits are issued.',
            ),
            (
                'Can I buy carbon credits from Green Spark?',
                'We talk with buyers and investors directly. <a '
                'href="route:enquire">Send us an enquiry</a> and tell us what '
                'you are looking for.',
            ),
        ],
    ),
    (
        "programmes",
        "Programmes in development",
        [
            (
                'What are rooftop solar MRV and safe drinking water?',
                'They are our second and third priority programmes, both in '
                'development. Rooftop solar MRV brings rooftop systems '
                'together as one carbon programme; the safe drinking water '
                'programme uses small household filters. We will share more '
                'as each one is approved.',
            ),
            (
                'What comes after the priority programmes?',
                'Solar irrigation, rural productive-use solar and '
                'low-emission rice, in that order. They are at concept or '
                'feasibility stage. See <a '
                'href="route:projects#pipeline">projects in pipeline</a>.',
            ),
        ],
    ),
    (
        "feedback",
        "Feedback and privacy",
        [
            (
                'How can I give feedback or raise a concern?',
                'At any time, using our <a href="route:enquire">contact '
                'form</a>, by WhatsApp or phone on +61 402 832 972, or in '
                'person at our Manikganj office. During consultations and '
                'feedback rounds, every comment is recorded and answered.',
            ),
            (
                'Can I give feedback without my name?',
                'Yes. You can choose not to give your name. If you would like '
                'a reply, add a phone number or email address so we can reach '
                'you.',
            ),
            (
                'Can I contact you in Bangla?',
                'Yes. Our team in Bangladesh speaks Bangla and English, and '
                'consultations are held in Bangla.',
            ),
            (
                'How do you use my personal information?',
                'Only to respond to you and to run our programmes, as set out '
                'in our <a href="route:privacy">privacy policy</a>. We never '
                'publish household names, phone numbers or village-level '
                'locations.',
            ),
        ],
    ),
]

# (question, answer) -- on the Improved Cookstove programme page.
COOKSTOVE = [
    (
        'What is the Green ICS?',
        'The Green ICS is an improved cookstove designed with Bangladeshi '
        'households who cook with firewood and other biomass. It is designed '
        'to burn fuel more efficiently and to send less smoke into the '
        'kitchen.',
    ),
    (
        'How much does a Green ICS cost a household?',
        'Pricing depends on the phase of the programme and the partner who '
        'distributes the stove in your area. Message us on WhatsApp and we '
        'will explain the options available to you.',
    ),
    (
        'Who installs and maintains the stove?',
        'Trained Green ICS field officers install each stove, show the family '
        'how to use it and return for monitoring visits. Spare parts such as '
        'the strainer, ring and cap can be replaced.',
    ),
    (
        'What does “Gold Standard registered” mean?',
        'Phase 1 and Phase 2 of our cookstove programme are registered with '
        'Gold Standard, an independent standard for climate and development '
        'projects. Registration means the project design has been reviewed '
        'against its rules before carbon credits can be issued.',
    ),
    (
        'How can I give feedback or raise a concern?',
        'You can give feedback at any time on WhatsApp, using our contact '
        'form, by phone, or in person at our Manikganj office. During '
        'consultations and feedback rounds, every comment is recorded and '
        'answered.',
    ),
    (
        'Can my organisation partner with Green Spark?',
        'Yes. We work with government agencies, NGOs, distributors and carbon '
        'consultants. Use the contact form and choose “Partnership” as the '
        'subject.',
    ),
]


def seed(apps, schema_editor):
    FaqGroup = apps.get_model("content", "FaqGroup")
    FaqItem = apps.get_model("content", "FaqItem")
    Programme = apps.get_model("content", "Programme")

    for group_order, (anchor, title, questions) in enumerate(GROUPS, start=1):
        group = FaqGroup.objects.create(
            anchor=anchor, title=title, sort_order=group_order,
        )
        FaqItem.objects.bulk_create([
            FaqItem(group=group, question=question, answer=answer, sort_order=order)
            for order, (question, answer) in enumerate(questions, start=1)
        ])

    # The cookstove page's own six. If the programme row is missing there is
    # nothing to hang them on, and the page keeps its empty accordion rather
    # than the migration failing.
    stove = Programme.objects.filter(key="cookstove").first()
    if stove is not None:
        FaqItem.objects.bulk_create([
            FaqItem(programme=stove, question=question, answer=answer, sort_order=order)
            for order, (question, answer) in enumerate(COOKSTOVE, start=1)
        ])


def unseed(apps, schema_editor):
    apps.get_model("content", "FaqItem").objects.all().delete()
    apps.get_model("content", "FaqGroup").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [("content", "0024_faq_page")]

    operations = [migrations.RunPython(seed, unseed)]
