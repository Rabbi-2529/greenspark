"""
Views for the website.

Every static page is the same shape: render a template, tell the chrome which
nav item is current. One generic view covers all of them, driven by
pages.PAGES. The contact page adds a POST handler; projects are slug-driven
from the Project table. robots.txt and sitemap.xml are built from the same
two tables, so a page taken offline drops out of both automatically.
"""

import hashlib

from django.conf import settings
from django.core.cache import cache
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView

from apps.content.models import Page as PageRecord
from apps.content.models import (
    AboutPage, AboutStat, ApproachItem, Audience, CareerArea, CarouselSlide,
    Counter, District, FaqGroup, FaqItem, FaqPage, HomePage, JobOpening,
    Project, TeamGroup, TeamLeader, TeamPage, VisionAttribute, WhyGsslPage,
    WhyItem,
)
from apps.content.models.faq import number_questions

from .forms import EnquiryForm
from .mail import notify_enquiry
from .models import ENQUIRY_SUBJECTS, ENQUIRY_TYPES
from .pages import PAGES, Page


class StaticPageView(TemplateView):
    """
    Render one row of pages.PAGES.

    The route, the template and the nav key come from the code map; whether the
    page is published, what it is called and which of its bands are shown come
    from the database, so Green Spark can change them without a deploy. With no
    row yet — a fresh install, before the seed migration — the code map's own
    values stand in, so the site renders either way.
    """

    # Set per URL by as_view(page=…); must exist on the class for Django to
    # accept it as a keyword there.
    page: Page | None = None

    def dispatch(self, request, *args, **kwargs):
        self.record = PageRecord.by_name(self.page.name)
        published = self.record.is_published if self.record else self.page.is_published
        if not published:
            raise Http404("This page is not published.")
        return super().dispatch(request, *args, **kwargs)

    def get_template_names(self) -> list[str]:
        return [f"pages/{self.page.template}"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        listed = self.record.in_sitemap if self.record else self.page.in_sitemap
        context["nav_active"] = self.page.nav
        context["page_name"] = self.page.name
        context["noindex"] = not listed
        context["page"] = self.record
        context["sections"] = (
            self.record.visibility() if self.record else PageRecord.visibility_for(self.page.name)
        )
        return context


class ImpactBandMixin:
    """
    The "where we work" band -- impact figures and the district map -- is on
    the home page and the cookstove programme page, so both views need it.

    Only approved figures are listed. The design build's README has every
    current number down as sample data awaiting Green Spark's sign-off, and a
    figure on that page is a claim about their impact, so it appears when
    someone has ticked it and not before.
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["counters"] = Counter.objects.filter(published=True)
        context["districts"] = District.objects.all()
        return context


class HomeView(ImpactBandMixin, StaticPageView):
    """The home page. Its hero and approach cards come from the database."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # filter().first() rather than load(): rendering a page must not write
        # a row, and an unsaved instance carries the same defaults.
        context["home"] = HomePage.objects.filter(pk=1).first() or HomePage()
        context["carousel_slides"] = CarouselSlide.objects.prefetch_related(
            "badges", "facts"
        ).select_related("project", "programme")
        context["approach_highlights"] = ApproachItem.objects.filter(
            kind=ApproachItem.HIGHLIGHT
        )
        context["approach_attributes"] = ApproachItem.objects.filter(
            kind=ApproachItem.ATTRIBUTE
        )
        return context


class AboutView(StaticPageView):
    """About Us, including the Careers band at the foot of it."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # filter().first() rather than load(): rendering a page must not write
        # a row, and an unsaved instance carries the same defaults.
        context["about"] = AboutPage.objects.filter(pk=1).first() or AboutPage()
        context["about_stats"] = AboutStat.objects.all()
        context["vision_attributes"] = VisionAttribute.objects.all()
        context["approach_attributes"] = ApproachItem.objects.filter(
            kind=ApproachItem.ABOUT
        )
        context["audiences"] = Audience.objects.all()
        context["career_areas"] = CareerArea.objects.all()
        # Most of the time this is empty, and the band is written for that.
        context["openings"] = JobOpening.objects.filter(published=True)
        return context


class FaqView(StaticPageView):
    """
    The FAQ page.

    The accordions' ids run faq-0 to faq-19 across all five topics, so the
    numbering is worked out once over the whole page rather than per topic --
    see FaqGroup.with_questions.
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["faq"] = FaqPage.objects.filter(pk=1).first() or FaqPage()
        context["faq_groups"] = FaqGroup.with_questions()
        return context


class TeamView(StaticPageView):
    """Our team: the leadership band and the five teams."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["team"] = TeamPage.objects.filter(pk=1).first() or TeamPage()
        context["team_leaders"] = TeamLeader.objects.all()
        context["team_groups"] = TeamGroup.objects.all()
        return context


class WhyGsslView(StaticPageView):
    """Why GSSL. Unlisted, but its words are still Green Spark's to change."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["why"] = WhyGsslPage.objects.filter(pk=1).first() or WhyGsslPage()
        context["why_reasons"] = WhyItem.objects.filter(kind=WhyItem.REASON)
        context["why_expectations"] = WhyItem.objects.filter(kind=WhyItem.EXPECTATION)
        context["why_steps"] = WhyItem.objects.filter(kind=WhyItem.STEP)
        return context


class ImprovedCookstoveView(ImpactBandMixin, StaticPageView):
    """
    The cookstove programme page, which repeats the impact band.

    Its FAQ band is six questions of its own -- shorter answers than the FAQ
    page gives, and one question the FAQ page does not ask at all -- so they
    are rows against this programme rather than a filtered view of the FAQ
    page's twenty. The programme is found by the route it points at, so the
    other five programme pages pick theirs up the same way when their turn
    comes.
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["programme_faq"] = number_questions(
            FaqItem.objects.filter(programme__url_name=self.page.name)
        )
        return context


class ProjectsView(StaticPageView):
    """
    The Projects page.

    The grid has its own order, arranged by hand when the page was built and
    kept on the Project row as ``grid_order``, so it is not the order used
    anywhere else.
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["projects"] = (
            Project.objects.select_related("programme").order_by("grid_order", "pk")
        )
        return context


# --- Contact form -----------------------------------------------------------

def _client_key(request) -> str:
    """A hashed per-visitor key for throttling. The raw IP is never stored."""
    ip = request.META.get("REMOTE_ADDR", "")
    if settings.BEHIND_PROXY:
        # The reverse proxy appends the address it saw; the last entry is the
        # one a visitor cannot forge.
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            ip = forwarded.split(",")[-1].strip()
    return "enquiry-throttle:" + hashlib.sha256(ip.encode()).hexdigest()[:32]


def _throttled(request) -> bool:
    key = _client_key(request)
    window = settings.ENQUIRY_THROTTLE_SECONDS
    if cache.add(key, 1, timeout=window):
        return False
    try:
        count = cache.incr(key)
    except ValueError:  # expired between add() and incr()
        cache.add(key, 1, timeout=window)
        return False
    return count > settings.ENQUIRY_THROTTLE_COUNT


class EnquireView(StaticPageView):
    """The contact page. GET shows the form; POST stores and emails it."""

    http_method_names = ["get", "post", "head", "options"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", EnquiryForm())
        context["subject_choices"] = ENQUIRY_SUBJECTS
        context["enquiry_type_choices"] = ENQUIRY_TYPES
        context["sent"] = self.request.GET.get("sent") == "1"
        return context

    def post(self, request, *args, **kwargs):
        wants_json = (
            request.headers.get("x-requested-with") == "XMLHttpRequest"
            or "application/json" in request.headers.get("accept", "")
        )
        form = EnquiryForm(request.POST)

        if form.is_bot():
            # Pretend it worked; store and send nothing.
            return JsonResponse({"ok": True}) if wants_json else self._sent()

        if _throttled(request):
            message = (
                "You have sent several messages in a short time. Please wait a few "
                "minutes, or email info@greensparksolutions.com."
            )
            if wants_json:
                return JsonResponse({"ok": False, "errors": {}, "message": message}, status=429)
            context = self.get_context_data(form=form, throttle_message=message)
            return self.render_to_response(context, status=429)

        if not form.is_valid():
            if wants_json:
                errors = {field: msgs[0] for field, msgs in form.errors.items()}
                return JsonResponse({"ok": False, "errors": errors}, status=400)
            return self.render_to_response(self.get_context_data(form=form), status=400)

        enquiry = form.save()
        notify_enquiry(enquiry)
        return JsonResponse({"ok": True}) if wants_json else self._sent()

    def _sent(self):
        # Post/Redirect/Get, so a refresh never resubmits.
        return redirect(f"{reverse('website:enquire')}?sent=1#contact-form")


# --- Projects ---------------------------------------------------------------

class ProjectDetailView(TemplateView):
    """One page per project, from the database."""

    template_name = "pages/project_detail.html"

    def get_context_data(self, **kwargs):
        project = (
            Project.objects.select_related("programme")
            .filter(slug=kwargs.get("slug"))
            .first()
        )
        if project is None:
            raise Http404("No such project")
        context = super().get_context_data(**kwargs)
        context["project"] = project
        context["related"] = project.related()
        context["nav_active"] = "projects"
        context["page_name"] = "project_detail"
        # Every project page shares one template, so they share one set of
        # section switches.
        context["sections"] = PageRecord.visibility_for("project_detail")
        return context


# --- robots.txt and sitemap.xml ---------------------------------------------

@require_GET
@cache_control(max_age=60 * 60 * 24, public=True)
def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow:",
        "",
        f"Sitemap: {settings.SITE_URL}{reverse('website:sitemap')}",
        "",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


@require_GET
@cache_control(max_age=60 * 60, public=True)
def sitemap_xml(request):
    # A page taken offline or unlisted in the console drops out of the sitemap
    # on the next request, with no deploy.
    records = {record.name: record for record in PageRecord.objects.all()}
    urls = [
        reverse(f"website:{page.name}")
        for page in PAGES
        if (records[page.name].in_sitemap if page.name in records else page.in_sitemap)
    ]
    urls += [
        reverse("website:project_detail", args=[slug])
        for slug in Project.objects.values_list("slug", flat=True)
    ]
    body = render_to_string("sitemap.xml", {"urls": urls, "site_url": settings.SITE_URL})
    return HttpResponse(body, content_type="application/xml; charset=utf-8")


# --- Errors -----------------------------------------------------------------

def page_not_found(request, exception=None, template_name="pages/404.html"):
    return render(request, template_name, {"nav_active": "", "noindex": True}, status=404)


def server_error(request, template_name="pages/500.html"):
    return render(request, template_name, {"nav_active": "", "noindex": True}, status=500)
