"""
Seed the privacy policy: thirteen sections, read off the template.

The table of contents is not seeded, because it is not stored: it is these
thirteen rows, rendered as links. The generator that produced this file checked
that the contents list in the template matched the headings exactly before
writing it, and that reassembling the sections gave back the body byte for
byte.

The link to the OAIC keeps its web address because it points off this site. The
email and phone links are kept as ``mailto:`` and ``tel:`` for the same reason.
Nothing here points at a page of ours, so no ``route:`` href appears -- but the
field would accept one.
"""

from django.db import migrations

# anchor, title, body
SECTIONS = [
    (
        "about",
        "About this policy",
        '<p>This policy explains how <strong>Green Spark Solutions '
        'Australia Pty Ltd</strong> (“Green Spark”, “we”, “us”) handles '
        'personal information collected through this website and through '
        'our programmes. Our related company in Bangladesh, Green Spark '
        'Solutions Ltd, runs our field operations and follows this '
        'policy.</p>\n'
        '<p>We aim to handle personal information in line with the '
        'Australian Privacy Principles in the <em>Privacy Act 1988</em> '
        '(Cth) and the privacy laws that apply where we work.</p>',
    ),
    (
        "collect",
        "Information we collect",
        '<p>We collect only what we need. Depending on how you deal with '
        'us, this can include:</p>\n'
        '<ul><li><strong>Enquiries:</strong> your name, organisation, '
        'email address, phone number and message.</li>\n'
        '<li><strong>Feedback and grievances:</strong> your comments and, '
        'if you choose to give them, your name and how to reach you. You '
        'can give feedback without your name.</li>\n'
        '<li><strong>Events and consultations:</strong> registration '
        'details and attendance records.</li>\n'
        '<li><strong>Programme records:</strong> for households taking '
        'part in our programmes, the details needed to install, maintain '
        'and monitor equipment, collected with consent by our field '
        'team.</li>\n'
        '<li><strong>Job applications:</strong> your CV and the details '
        'you send us.</li>\n'
        '<li><strong>Website use:</strong> basic technical information '
        'such as browser type and pages visited, held in server '
        'logs.</li></ul>',
    ),
    (
        "how",
        "How we collect it",
        '<p>We collect information directly from you: when you fill in a '
        'form on this website, send us an email or WhatsApp message, call '
        'us, attend a consultation or take part in a programme. We do not '
        'buy personal information from third parties.</p>',
    ),
    (
        "use",
        "How we use it",
        '<ul><li>To reply to enquiries and feedback, and to record and '
        'answer grievances.</li>\n'
        '<li>To run, monitor and improve our programmes, including the '
        'household visits that carbon standards require.</li>\n'
        '<li>To prepare monitoring reports and the evidence independent '
        'verifiers review.</li>\n'
        '<li>To consider job applications.</li>\n'
        '<li>To keep this website secure and working well.</li></ul>\n'
        '<p><strong>We never publish household names, phone numbers or '
        'village-level locations.</strong> Figures shown on this website '
        'are totals, shown at district level or above.</p>',
    ),
    (
        "share",
        "Who we share it with",
        '<p>We do not sell or rent personal information. We share it only '
        'when needed, with:</p>\n'
        '<ul><li>our related company in Bangladesh, Green Spark Solutions '
        'Ltd;</li>\n'
        '<li>independent verifiers and the carbon standard that registers '
        'our projects, for monitoring and verification;</li>\n'
        '<li>service providers who host this website or help us run our '
        'programmes, under confidentiality obligations;</li>\n'
        '<li>government bodies, where the law requires it.</li></ul>',
    ),
    (
        "overseas",
        "Overseas disclosure",
        '<p>Our team works in Australia and Bangladesh, so personal '
        'information may be held or accessed in both countries. Website '
        'and email providers may store data in other countries. We take '
        'reasonable steps so that anyone who receives your information '
        'protects it in line with this policy.</p>',
    ),
    (
        "cookies",
        "Cookies and browser storage",
        '<p>This website does not use advertising or social media '
        'trackers, and it does not embed third-party maps or video '
        'players. Every photo, video, font and script on the site is '
        'served from our own server, so loading a page does not send your '
        'details to anyone else. The site may also store a small setting '
        'in your browser, for example to remember that you closed a '
        'notice. Our server keeps standard security logs.</p>\n'
        '<p>If we add website analytics in future, we will update this '
        'policy first.</p>',
    ),
    (
        "security",
        "Storage and security",
        '<p>We store personal information on secure systems with access '
        'limited to the staff who need it. Forms on this website are sent '
        'over an encrypted connection, and form data is never placed in '
        'web addresses.</p>',
    ),
    (
        "retention",
        "How long we keep it",
        '<p>We keep personal information only as long as we need it for '
        'the purpose it was collected, or as long as the law or a carbon '
        'standard requires (for example, programme monitoring records for '
        'the life of a project). After that we delete or de-identify '
        'it.</p>',
    ),
    (
        "access",
        "Access and correction",
        '<p>You can ask to see the personal information we hold about '
        'you, or ask us to correct it. Contact us using the details '
        'below. We will reply within 30 days.</p>',
    ),
    (
        "complaints",
        "Privacy complaints",
        '<p>If you have a concern about how we have handled your personal '
        'information, contact us first and we will try to resolve it. If '
        'you are not satisfied with our response, you can contact the '
        'Office of the Australian Information Commissioner at <a '
        'href="https://www.oaic.gov.au" target="_blank" '
        'rel="noopener">oaic.gov.au<span class="visually-hidden"> (opens '
        'in a new tab)</span></a>.</p>',
    ),
    (
        "changes",
        "Changes to this policy",
        '<p>We may update this policy from time to time. The latest '
        'version is always on this page, with the date it was last '
        'updated.</p>',
    ),
    (
        "contact",
        "Contact us",
        '<p><strong>Green Spark Solutions Australia Pty '
        'Ltd</strong><br>Suite 4 &amp; 5, 498 Princes Highway, Rockdale '
        'NSW 2216, Australia</p>\n'
        '<p><strong>Operations base, Bangladesh</strong><br>19/1 Poully, '
        'Joynagar, Gilondo (Monno City), Manikganj Sadar, Manikganj</p>\n'
        '<p>Email <a '
        'href="mailto:info@greensparksolutions.com">info@greensparksolutions.com</a> '
        '· Phone <a href="tel:+61402832972">+61 402 832 972</a></p>',
    ),
]


def seed(apps, schema_editor):
    PolicySection = apps.get_model("content", "PolicySection")
    PolicySection.objects.bulk_create([
        PolicySection(anchor=anchor, title=title, body=body, sort_order=order)
        for order, (anchor, title, body) in enumerate(SECTIONS, start=1)
    ])


def unseed(apps, schema_editor):
    apps.get_model("content", "PolicySection").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [("content", "0026_privacy_page")]

    operations = [migrations.RunPython(seed, unseed)]
