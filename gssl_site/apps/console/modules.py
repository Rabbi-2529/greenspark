"""
What the console can edit.

Phase 1 registers only what already exists: the enquiries the contact form
collects, the staff accounts that sign in here, and the activity log. The
content modules arrive with their models, phase by phase (CMS-PLAN.md §6), and
each one is a few lines in this file.

Keeping every registration in one place means the sidebar, the URLs and the
permissions all come from a single readable list.
"""

from django.contrib.auth import get_user_model

from . import roles
from .forms import ProgrammeForm, ProjectForm, StaffCreateForm, StaffForm
from .models import AuditEntry
from .registry import Column, Filter, Inline, Module, registry

from apps.content.models import (
    AboutPage, AboutStat, ApproachItem, Audience, CarouselSlide, CareerArea,
    ContactDetails, Counter, District, HomePage, JobOpening, NoticeBar, Page,
    Programme, ProgrammeAttribute, ProgrammeStep, Project, ProjectAttribute,
    ProjectImage, ProjectParagraph, Section, SiteSettings, SlideBadge,
    SlideFact, SocialLinks, VisionAttribute, WhyGsslPage, WhyItem
)
from apps.website.models import ENQUIRY_SUBJECTS, ENQUIRY_TYPES, Enquiry

User = get_user_model()


def page_choices():
    """Built when the filter is rendered, not when this module is imported."""
    return [(page.name, page.label) for page in Page.objects.all()]


# --- The site map -----------------------------------------------------------

registry.register(Module(
    slug="pages",
    model=Page,
    label="Page",
    label_plural="Pages",
    group="Content",
    icon="page",
    blurb="Every page of the site: what it is called for search engines, and whether it is published.",

    # Pages are not created or deleted here: a page needs a route and a
    # template, which are code. This is where its wording and status live.
    can_create=False,
    can_delete=False,
    fields=("label", "title", "meta_description", "og_image", "status"),
    columns=(
        Column("label", "Page", link=True),
        Column("name", "Key", kind="muted"),
        Column("title", "Browser title", truncate=55),
        Column("status", "Status", kind="badge"),
        Column("updated_at", "Last changed", kind="datetime"),
    ),
    search_fields=("label", "name", "title", "meta_description"),
    filters=(Filter("status", "Status", choices=tuple(Page.STATUS_CHOICES)),),
    ordering=("sort_order", "name"),
    view_rank=roles.EDITOR,
    edit_rank=roles.EDITOR,
))


registry.register(Module(
    slug="sections",
    model=Section,
    label="Section",
    label_plural="Page sections",
    group="Content",
    icon="layers",
    blurb="Every band of content on every page. Turn one off to take it off the site; nothing is deleted.",

    # Sections come from the templates, so they are not added or removed here.
    can_create=False,
    can_delete=False,
    fields=("label", "blurb", "visible"),
    publish_field="visible",
    publish_text="Show",
    unpublish_text="Hide",
    publish_done="is back on the page",
    unpublish_done="is hidden from the page",
    columns=(
        Column("page__label", "Page"),
        Column("label", "Section", link=True),
        Column("key", "Key", kind="muted"),
        Column("visible", "Shown", kind="bool", align="center"),
    ),
    search_fields=("label", "key", "blurb", "page__label"),
    filters=(
        # Not "page": the list uses that for paging.
        Filter("on_page", "Page", lookup="page__name", choices=page_choices),
        Filter("visible", "Shown", kind="bool"),
    ),
    ordering=("page__sort_order", "sort_order"),
    select_related=("page",),
    per_page=100,
    view_rank=roles.EDITOR,
    edit_rank=roles.EDITOR,
))


# --- Projects and programmes ------------------------------------------------

def programme_choices():
    return [(p.key, p.label) for p in Programme.objects.all()]


registry.register(Module(
    slug="projects",
    model=Project,
    label="Project",
    label_plural="Projects",
    group="Projects",
    icon="layers",
    blurb="The seven projects: what each page says, and how its card looks on the Projects page.",

    form_class=ProjectForm,
    inlines=(
        Inline(
            model=ProjectParagraph,
            label_plural="“About the project” paragraphs",
            fields=("body", "sort_order"),
            order_field="sort_order",
            extra=1,
        ),
        Inline(
            model=ProjectAttribute,
            label_plural="Key details",
            fields=("icon", "title", "details", "sort_order"),
            order_field="sort_order",
            extra=1,
        ),
        Inline(
            model=ProjectImage,
            label_plural="Photos on the project page",
            fields=("photo", "alt", "caption", "sort_order"),
            order_field="sort_order",
            extra=1,
        ),
    ),
    columns=(
        Column("title", "Project", link=True),
        Column("programme__label", "Programme", kind="muted"),
        Column("location", "Where", truncate=40),
        Column("stage", "Stage", kind="badge"),
        Column("gs_id", "Gold Standard", kind="muted"),
        Column("sort_order", "Order", align="center"),
    ),
    search_fields=("title", "summary", "location", "stage", "gs_id", "slug"),
    filters=(
        Filter("programme", "Programme", lookup="programme__key", choices=programme_choices),
        Filter("stove_detail", "Green ICS detail", kind="bool"),
    ),
    ordering=("sort_order", "pk"),
    select_related=("programme",),
    order_field="sort_order",
    view_rank=roles.EDITOR,
    edit_rank=roles.EDITOR,
    delete_rank=roles.PUBLISHER,
))


registry.register(Module(
    slug="programmes",
    model=Programme,
    label="Programme",
    label_plural="Programmes",
    group="Projects",
    icon="page",
    blurb="The six programmes. “Show on website” is off for anything Green Spark has not made public.",

    form_class=ProgrammeForm,
    can_create=False,
    can_delete=False,
    publish_field="show_on_website",
    publish_text="Show on the site",
    unpublish_text="Hide from the site",
    publish_done="is shown on the site",
    unpublish_done="is hidden from the site",
    inlines=(
        Inline(
            model=ProgrammeAttribute,
            label_plural="Attributes",
            fields=("icon", "title", "text", "sort_order"),
            order_field="sort_order",
            extra=1,
        ),
        Inline(
            model=ProgrammeStep,
            label_plural="How it works",
            fields=("title", "text", "sort_order"),
            order_field="sort_order",
            extra=1,
        ),
    ),
    columns=(
        Column("label", "Programme", link=True),
        Column("key", "Key", kind="muted"),
        Column("stage", "Stage", kind="badge"),
        Column("priority", "Lead", kind="bool", align="center"),
        Column("show_on_website", "On the site", kind="bool", align="center"),
    ),
    search_fields=("label", "key", "summary"),
    filters=(Filter("show_on_website", "On the site", kind="bool"),),
    ordering=("sort_order", "label"),
    order_field="sort_order",
    view_rank=roles.EDITOR,
    edit_rank=roles.EDITOR,
))


# --- The home page ----------------------------------------------------------

registry.register(Module(
    slug="approach",
    model=ApproachItem,
    label="Approach point",
    label_plural="Approach points",
    group="Content",
    icon="layers",
    blurb="The “Why Green Spark” and “A holistic approach” points on the home page, and “Our approach” on About Us.",

    fields=("kind", "icon", "title", "body", "link_label", "link_route",
            "link_fragment", "sort_order"),
    columns=(
        Column("title", "Point", link=True),
        Column("kind", "Where", kind="badge"),
        Column("body", "Wording", kind="muted", sortable=False, truncate=60),
        Column("link_label", "Link", kind="muted"),
        Column("sort_order", "Order", align="center"),
    ),
    search_fields=("title", "body", "link_label"),
    filters=(Filter("kind", "Where", choices=tuple(ApproachItem.KIND_CHOICES)),),
    ordering=("kind", "sort_order"),
    order_field="sort_order",
    view_rank=roles.EDITOR,
    edit_rank=roles.EDITOR,
))


registry.register(Module(
    slug="counters",
    model=Counter,
    label="Impact figure",
    label_plural="Impact figures",
    group="Content",
    icon="history",
    blurb="The counters on the home and cookstove pages. A figure stays off the site until it is approved.",

    can_create=True,
    fields=("label", "display", "count", "suffix", "estimated", "note", "as_of", "sort_order"),
    publish_field="published",
    publish_text="Approve",
    unpublish_text="Withdraw",
    publish_done="is approved and will show on the site",
    unpublish_done="is withdrawn from the site",
    columns=(
        Column("display", "Figure", link=True),
        Column("label", "What it counts"),
        Column("estimated", "Estimated", kind="bool", align="center"),
        Column("as_of", "True as of", kind="date"),
        Column("published", "Approved", kind="bool", align="center"),
    ),
    search_fields=("label", "display", "note"),
    filters=(
        Filter("published", "Approved", kind="bool"),
        Filter("estimated", "Estimated", kind="bool"),
    ),
    ordering=("sort_order", "pk"),
    order_field="sort_order",
    view_rank=roles.EDITOR,
    # Publishing a figure is a claim about impact: that takes a publisher.
    edit_rank=roles.PUBLISHER,
    delete_rank=roles.PUBLISHER,
))


registry.register(Module(
    slug="districts",
    model=District,
    label="District",
    label_plural="Districts",
    group="Content",
    icon="page",
    blurb="The districts highlighted on the Bangladesh map.",

    fields=("name", "division", "is_base", "sort_order"),
    columns=(
        Column("name", "District", link=True),
        Column("division", "Shown as"),
        Column("is_base", "Base", kind="bool", align="center"),
        Column("sort_order", "Order", align="center"),
    ),
    search_fields=("name", "division"),
    ordering=("sort_order", "name"),
    order_field="sort_order",
    view_rank=roles.EDITOR,
    edit_rank=roles.EDITOR,
))


# --- About Us ---------------------------------------------------------------

registry.register(Module(
    slug="about-page",
    model=AboutPage,
    label="About Us page",
    label_plural="About Us page",
    group="Content",
    icon="page",
    blurb="Every heading and paragraph on About Us that there is only one of, "
          "including the Careers band at the foot of it.",
    singleton=True,
    can_create=False,
    can_delete=False,
    fieldsets=(
        ("The hero", ("hero_tag", "hero_title", "hero_lead", "meet_label")),
        ("Who we are", ("intro_tag", "intro_text")),
        ("Our vision", ("vision_tag", "vision_title", "vision_lead")),
        ("Our approach", ("approach_tag", "approach_title", "approach_lead")),
        ("Who we work with", ("partners_tag", "partners_title")),
        ("Careers at GSSL", ("careers_tag", "careers_title", "careers_lead",
                             "roles_title", "no_roles_text", "cv_label",
                             "cv_email", "cv_subject", "enquire_label")),
    ),
    columns=(Column("hero_title", "Heading", link=True),),
    view_rank=roles.EDITOR,
    edit_rank=roles.EDITOR,
))


registry.register(Module(
    slug="about-figures",
    model=AboutStat,
    label="About Us figure",
    label_plural="About Us figures",
    group="Content",
    icon="history",
    blurb="The three figures beside “Who we are”. Not impact figures: these are "
          "facts about the company and need no approval.",
    fields=("value", "label", "sort_order"),
    columns=(
        Column("value", "Figure", link=True),
        Column("label", "Reads on as"),
        Column("sort_order", "Order", align="center"),
    ),
    search_fields=("value", "label"),
    ordering=("sort_order", "pk"),
    order_field="sort_order",
    view_rank=roles.EDITOR,
    edit_rank=roles.EDITOR,
))


registry.register(Module(
    slug="vision",
    model=VisionAttribute,
    label="Vision point",
    label_plural="Vision points",
    group="Content",
    icon="layers",
    blurb="The points under “Our vision” on About Us.",
    fields=("title", "body", "sort_order"),
    columns=(
        Column("title", "Point", link=True),
        Column("body", "Wording", kind="muted", sortable=False, truncate=70),
        Column("sort_order", "Order", align="center"),
    ),
    search_fields=("title", "body"),
    ordering=("sort_order", "pk"),
    order_field="sort_order",
    view_rank=roles.EDITOR,
    edit_rank=roles.EDITOR,
))


registry.register(Module(
    slug="partners",
    model=Audience,
    label="Partner type",
    label_plural="Partner types",
    group="Content",
    icon="people",
    blurb="Who Green Spark works with, on About Us: from households to carbon buyers.",
    fields=("icon", "title", "body", "sort_order"),
    columns=(
        Column("title", "Partner", link=True),
        Column("icon", "Icon", kind="muted"),
        Column("body", "Wording", kind="muted", sortable=False, truncate=60),
        Column("sort_order", "Order", align="center"),
    ),
    search_fields=("title", "body"),
    ordering=("sort_order", "pk"),
    order_field="sort_order",
    view_rank=roles.EDITOR,
    edit_rank=roles.EDITOR,
))


registry.register(Module(
    slug="career-areas",
    model=CareerArea,
    label="Area of work",
    label_plural="Areas of work",
    group="Content",
    icon="layers",
    blurb="The kinds of work described in the Careers band on About Us.",
    fields=("title", "body", "sort_order"),
    columns=(
        Column("title", "Area", link=True),
        Column("body", "Wording", kind="muted", sortable=False, truncate=70),
        Column("sort_order", "Order", align="center"),
    ),
    search_fields=("title", "body"),
    ordering=("sort_order", "pk"),
    order_field="sort_order",
    view_rank=roles.EDITOR,
    edit_rank=roles.EDITOR,
))


registry.register(Module(
    slug="openings",
    model=JobOpening,
    label="Open role",
    label_plural="Open roles",
    group="Content",
    icon="inbox",
    blurb="Roles listed on About Us. With none published the page shows its "
          "“no open roles right now” paragraph instead, which is how it ships.",
    fields=("title", "location", "employment_type", "summary", "closes_on",
            "apply_email", "apply_url", "apply_label", "sort_order"),
    publish_field="published",
    publish_text="Put on the website",
    unpublish_text="Take off the website",
    publish_done="is on the website",
    unpublish_done="is off the website",
    columns=(
        Column("title", "Role", link=True),
        Column("location", "Where"),
        Column("employment_type", "Type", kind="badge"),
        Column("closes_on", "Closes", kind="date"),
        Column("published", "On the site", kind="bool", align="center"),
    ),
    search_fields=("title", "location", "summary"),
    filters=(
        Filter("published", "On the site", kind="bool"),
        Filter("employment_type", "Type", choices=tuple(JobOpening.TYPE_CHOICES)),
    ),
    ordering=("sort_order", "pk"),
    order_field="sort_order",
    view_rank=roles.EDITOR,
    edit_rank=roles.EDITOR,
))


# --- Why GSSL ---------------------------------------------------------------

registry.register(Module(
    slug="why-page",
    model=WhyGsslPage,
    label="Why GSSL page",
    label_plural="Why GSSL page",
    group="Content",
    icon="page",
    blurb="The headings on Why GSSL. The page is unlisted — reachable by link, "
          "kept out of search — which is set on its row under Pages.",
    singleton=True,
    can_create=False,
    can_delete=False,
    fieldsets=(
        ("The hero", ("hero_tag", "hero_title", "hero_lead", "enquire_label",
                      "whatsapp_label")),
        ("What sets us apart", ("reasons_tag", "reasons_title")),
        ("Working with us", ("expectations_tag", "expectations_title")),
        ("How we work", ("steps_tag", "steps_title")),
    ),
    columns=(Column("hero_title", "Heading", link=True),),
    view_rank=roles.EDITOR,
    edit_rank=roles.EDITOR,
))


registry.register(Module(
    slug="why-points",
    model=WhyItem,
    label="Why GSSL point",
    label_plural="Why GSSL points",
    group="Content",
    icon="layers",
    blurb="The reasons, the expectations and the numbered steps on Why GSSL.",
    fields=("kind", "icon", "title", "body", "sort_order"),
    columns=(
        Column("title", "Point", link=True),
        Column("kind", "Band", kind="badge"),
        Column("icon", "Icon", kind="muted"),
        Column("body", "Wording", kind="muted", sortable=False, truncate=60),
        Column("sort_order", "Order", align="center"),
    ),
    search_fields=("title", "body"),
    filters=(Filter("kind", "Band", choices=tuple(WhyItem.KIND_CHOICES)),),
    ordering=("kind", "sort_order"),
    order_field="sort_order",
    view_rank=roles.EDITOR,
    edit_rank=roles.EDITOR,
))


# --- Settings ---------------------------------------------------------------

registry.register(Module(
    slug="carousel",
    model=CarouselSlide,
    label="Carousel card",
    label_plural="Home carousel",
    group="Content",
    icon="page",
    blurb="The five project cards that slide across the home page.",
    fields=("title", "text", "project", "programme", "link_label", "registered",
            "sort_order"),
    inlines=(
        Inline(
            model=SlideBadge, label="Badge", label_plural="Badges",
            fields=("label", "variant", "sort_order"),
            fk_name="slide", order_field="sort_order", extra=1,
        ),
        Inline(
            model=SlideFact, label="Fact", label_plural="Facts",
            fields=("label", "value", "sort_order"),
            fk_name="slide", order_field="sort_order", extra=1,
        ),
    ),
    columns=(
        Column("title", "Card", link=True),
        Column("link_label", "Links to"),
    ),
    order_field="sort_order",
    view_rank=roles.EDITOR,
    edit_rank=roles.EDITOR,
))


registry.register(Module(
    slug="home-page",
    model=HomePage,
    label="Home page",
    label_plural="Home page",
    group="Content",
    icon="page",
    blurb="The hero: its wording, and which video plays behind it.",
    singleton=True,
    can_create=False,
    can_delete=False,
    fields=(
        "title", "welcome_tag", "welcome_text", "lead", "meet_label",
        "scroll_label", "heading", "pause_label", "video_name",
    ),
    columns=(Column("title", "Headline", link=True),),
    view_rank=roles.EDITOR,
    edit_rank=roles.EDITOR,
))


registry.register(Module(
    slug="site-settings",
    model=SiteSettings,
    label="Site settings",
    label_plural="Site settings",
    group="Settings",
    icon="page",
    blurb="The site's name and the picture used when a page is shared.",
    singleton=True,
    can_create=False,
    can_delete=False,
    fields=("site_name", "legal_name", "abn", "default_og_image", "show_topbar"),
    columns=(Column("site_name", "Site name", link=True),),
    view_rank=roles.EDITOR,
    edit_rank=roles.PUBLISHER,
))


registry.register(Module(
    slug="contact",
    model=ContactDetails,
    label="Contact details",
    label_plural="Contact details",
    group="Settings",
    icon="inbox",
    blurb="The phone number, email and hours in the top bar and footer.",
    singleton=True,
    can_create=False,
    can_delete=False,
    fields=(
        "whatsapp_number", "phone_display", "email", "hours",
        "australia_address", "australia_map_url",
        "bangladesh_address", "bangladesh_map_url",
    ),
    columns=(Column("email", "Email", link=True),),
    view_rank=roles.EDITOR,
    edit_rank=roles.PUBLISHER,
))


registry.register(Module(
    slug="social",
    model=SocialLinks,
    label="Social links",
    label_plural="Social links",
    group="Settings",
    icon="people",
    blurb="Leave one empty and its icon disappears from the site.",
    singleton=True,
    can_create=False,
    can_delete=False,
    fields=("facebook", "youtube", "linkedin", "whatsapp", "x"),
    columns=(Column("id", "Social links", link=True),),
    view_rank=roles.EDITOR,
    edit_rank=roles.PUBLISHER,
))


registry.register(Module(
    slug="notice-bar",
    model=NoticeBar,
    label="Notice bar",
    label_plural="Notice bar",
    group="Settings",
    icon="warn",
    blurb="The strip above the header. It shows only between its two dates.",
    singleton=True,
    can_create=False,
    can_delete=False,
    fields=("enabled", "text", "link_label", "link_url", "starts_at", "ends_at"),
    columns=(Column("text", "Notice", link=True),),
    view_rank=roles.EDITOR,
    edit_rank=roles.PUBLISHER,
))


# --- Messages ---------------------------------------------------------------

registry.register(Module(
    slug="enquiries",
    model=Enquiry,
    label="Enquiry",
    label_plural="Enquiries",
    group="Messages",
    icon="inbox",
    blurb="Everything sent through the contact form. Nothing here is written by us.",

    # An enquiry is a visitor's own words: it is read, never edited. The one
    # thing staff change is whether it has been answered, which is the switch
    # below rather than a form.
    readonly=True,
    publish_field="handled",
    publish_text="Mark answered",
    unpublish_text="Reopen",
    publish_done="is marked answered",
    unpublish_done="is back in the queue",

    columns=(
        Column("created_at", "Received", kind="datetime"),
        Column("name", "From", link=True),
        Column("email", "Email", kind="email"),
        Column("subject", "About", kind="badge"),
        Column("enquiry_type", "They are", kind="muted"),
        Column("message", "Message", kind="muted", sortable=False, truncate=70),
        Column("emailed_at", "Emailed", kind="datetime"),
        Column("handled", "Answered", kind="bool", align="center"),
    ),
    search_fields=("name", "email", "phone", "message"),
    filters=(
        Filter("handled", "Answered", kind="bool"),
        Filter("subject", "About", choices=tuple(ENQUIRY_SUBJECTS)),
        Filter("enquiry_type", "They are", choices=tuple(ENQUIRY_TYPES)),
    ),
    ordering=("-created_at",),
    view_rank=roles.EDITOR,
    edit_rank=roles.EDITOR,
))


# --- Settings ---------------------------------------------------------------

registry.register(Module(
    slug="staff",
    model=User,
    label="Staff account",
    label_plural="Staff accounts",
    group="Settings",
    icon="people",
    blurb="Who can sign in to the console, and what each of them may do.",

    form_class=StaffForm,
    create_form_class=StaffCreateForm,
    columns=(
        Column("username", "Username", link=True),
        Column("email", "Email", kind="email"),
        Column("first_name", "First name"),
        Column("last_name", "Last name"),
        Column("is_active", "Active", kind="bool", align="center"),
        Column("last_login", "Last signed in", kind="datetime"),
    ),
    search_fields=("username", "email", "first_name", "last_name"),
    filters=(Filter("is_active", "Active", kind="bool"),),
    ordering=("username",),

    # Accounts are an administrator's business, and nobody else's.
    view_rank=roles.ADMINISTRATOR,
    edit_rank=roles.ADMINISTRATOR,
    delete_rank=roles.ADMINISTRATOR,
))


registry.register(Module(
    slug="activity",
    model=AuditEntry,
    label="Activity entry",
    label_plural="Activity",
    group="Settings",
    icon="history",
    blurb="Every change made in the console, who made it and when.",

    readonly=True,
    can_create=False,
    can_delete=False,
    columns=(
        Column("at", "When", kind="datetime", link=True),
        Column("actor_label", "Who"),
        Column("action", "Did", kind="badge"),
        Column("module", "In", kind="muted"),
        Column("object_label", "To", truncate=60),
        Column("note", "Note", kind="muted", sortable=False, truncate=50),
    ),
    search_fields=("actor_label", "object_label", "module", "note"),
    filters=(
        Filter("action", "Action", choices=tuple(AuditEntry.ACTIONS)),
    ),
    ordering=("-at",),
    select_related=("actor",),
    view_rank=roles.ADMINISTRATOR,
))
