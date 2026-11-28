"""
The content models.

Split by area so the file never becomes the 2,000-line module every Django
project grows. Phase 2 lands the site map, the hideable sections and the four
settings records; the rest arrive with their phases (see CMS-PLAN.md §6).
"""

from .about import (
    AboutPage, AboutStat, Audience, CareerArea, JobOpening, VisionAttribute,
)
from .carousel import CarouselSlide, SlideBadge, SlideFact
from .faq import FaqGroup, FaqItem, FaqPage
from .home import ApproachItem, Counter, District, HomePage
from .pages import Page, Section, SectionVisibility
from .programmes import Programme, ProgrammeAttribute, ProgrammeStep
from .projects import Project, ProjectAttribute, ProjectImage, ProjectParagraph
from .site import ContactDetails, NoticeBar, SiteSettings, SocialLinks
from .team import TeamGroup, TeamLeader, TeamPage
from .why import WhyGsslPage, WhyItem

__all__ = [
    "AboutPage",
    "AboutStat",
    "ApproachItem",
    "Audience",
    "CareerArea",
    "ContactDetails",
    "Counter",
    "District",
    "FaqGroup",
    "FaqItem",
    "FaqPage",
    "CarouselSlide",
    "HomePage",
    "JobOpening",
    "SlideBadge",
    "SlideFact",
    "NoticeBar",
    "Page",
    "Programme",
    "ProgrammeAttribute",
    "ProgrammeStep",
    "Project",
    "ProjectAttribute",
    "ProjectImage",
    "ProjectParagraph",
    "Section",
    "SectionVisibility",
    "SiteSettings",
    "SocialLinks",
    "TeamGroup",
    "TeamLeader",
    "TeamPage",
    "VisionAttribute",
    "WhyGsslPage",
    "WhyItem",
]
