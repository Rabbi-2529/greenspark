"""
The content models.

Split by area so the file never becomes the 2,000-line module every Django
project grows. Phase 2 lands the site map, the hideable sections and the four
settings records; the rest arrive with their phases (see CMS-PLAN.md §6).
"""

from .carousel import CarouselSlide, SlideBadge, SlideFact
from .home import ApproachItem, Counter, District, HomePage
from .pages import Page, Section, SectionVisibility
from .programmes import Programme, ProgrammeAttribute, ProgrammeStep
from .projects import Project, ProjectAttribute, ProjectImage, ProjectParagraph
from .site import ContactDetails, NoticeBar, SiteSettings, SocialLinks

__all__ = [
    "ApproachItem",
    "ContactDetails",
    "Counter",
    "District",
    "CarouselSlide",
    "HomePage",
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
]
