"""
The small amount of HTML an editor may type.

Phase 4 left this question open. The home page's intro paragraph contains a
``<mark>`` element, and rather than decide there and then how much markup a
content field may carry, Phase 4 left that paragraph in the template and called
it Phase 9's problem.

Phase 5 cannot leave it. A privacy policy is prose with emphasis and lists, and
six of the twenty FAQ answers contain a link. A policy field that cannot hold
``<strong>`` or ``<ul>`` is not a policy field.

So the question is answered here, and narrowly:

* **A whitelist, checked when the record is saved.** ``validate`` is attached to
  the field, so a console form refuses anything outside ``ALLOWED`` before it
  reaches the database, and names the tag or attribute that was the problem.
* **``render`` re-emits rather than passes through.** Content written straight
  into the database, or written before the whitelist was tightened, still
  cannot put a script, a style or an event handler on a page.
* **Internal links are route names, not paths.** ``href="route:enquire"``
  resolves through ``reverse()`` when the page renders. Routes stay in code —
  the rule this project settled on — so a page that moves does not leave a dead
  link buried in a paragraph in the database. It is the same idea as
  ``ApproachItem.link_route``, and it degrades the same way: a link to a route
  that no longer exists renders as its own words rather than raising
  ``NoReverseMatch`` and taking the page down with it.

What is deliberately *not* allowed: ``<script>``, ``<style>``, ``style=``, any
``on*`` handler, ``<iframe>``, ``<img>``, and anything else that loads or runs.
The site's CSP forbids all of it and the console's own tests assert that no
page carries an inline script or an inline style.
"""

from __future__ import annotations

from html.parser import HTMLParser

from django.core.exceptions import ValidationError
from django.urls import NoReverseMatch, reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe

# tag -> the attributes it may carry. Everything else is dropped.
ALLOWED: dict[str, tuple[str, ...]] = {
    "a": ("href", "target", "rel"),
    "br": (),
    "em": (),
    "li": (),
    "mark": (),
    "ol": (),
    "p": (),
    "span": ("class",),
    "strong": (),
    "ul": (),
}

# Tags with no closing tag.
VOID = {"br"}

# The only class a span may carry. The site uses exactly one -- the words that
# tell a screen reader a link opens in a new tab -- and a free-text class
# attribute in a content field is an invitation to restyle the page from the
# console.
SPAN_CLASSES = {"visually-hidden"}

# Where a link may point. Everything else, javascript: and data: included, is
# refused.
SCHEMES = ("https://", "http://", "mailto:", "tel:", "/", "#")

# An internal link: route:<url name>[#fragment].
ROUTE_PREFIX = "route:"


def _resolve(href: str) -> str | None:
    """
    The URL a stored href points at, or None when it points nowhere.

    None is the signal to render the link as plain words: an editor's paragraph
    must not be able to 500 the page it sits on.
    """
    if not href.startswith(ROUTE_PREFIX):
        return href
    name, _, fragment = href[len(ROUTE_PREFIX):].partition("#")
    try:
        url = reverse(f"website:{name}")
    except NoReverseMatch:
        return None
    return f"{url}#{fragment}" if fragment else url


class _Rewriter(HTMLParser):
    """
    Re-emits whitelisted markup and resolves ``route:`` links.

    ``convert_charrefs`` is on, so ``&amp;`` arrives as ``&`` and goes back out
    as ``&amp;`` through ``escape()`` -- the same escaping Django applies to a
    plain text field, so a rich field and a plain one cannot disagree about an
    ampersand.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.problems: list[str] = []
        # One entry per open tag: its name, or None for a tag that was dropped,
        # so its closing tag is dropped with it.
        self.stack: list[str | None] = []

    def _refuse(self, problem: str) -> None:
        self.problems.append(problem)

    # --- parsing ---

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED:
            self._refuse(f"<{tag}> is not allowed here")
            if tag not in VOID:
                self.stack.append(None)
            return

        kept: list[tuple[str, str]] = []
        for name, value in attrs:
            if name not in ALLOWED[tag]:
                self._refuse(f"<{tag}> may not carry {name}=")
                continue
            kept.append((name, value or ""))

        if tag == "a":
            href = dict(kept).get("href", "")
            if not href:
                self._refuse("a link needs an href")
            elif not href.startswith(ROUTE_PREFIX) and not href.startswith(SCHEMES):
                self._refuse(f"a link may not point at {href!r}")
                href = ""
            resolved = _resolve(href) if href else None
            if resolved is None:
                # Points nowhere: keep the words, drop the link.
                self.stack.append(None)
                return
            kept = [(n, resolved if n == "href" else v) for n, v in kept]

        if tag == "span":
            classes = dict(kept).get("class", "")
            if classes not in SPAN_CLASSES:
                self._refuse(f"a span may not carry class={classes!r}")
                self.stack.append(None)
                return

        rendered = "".join(f' {n}="{escape(v)}"' for n, v in kept)
        self.out.append(f"<{tag}{rendered}>")
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self._refuse(f"</{tag}> closes nothing")
            return
        open_tag = self.stack.pop()
        if open_tag is not None:
            self.out.append(f"</{open_tag}>")

    def handle_startendtag(self, tag, attrs):
        depth = len(self.stack)
        self.handle_starttag(tag, attrs)
        if tag not in VOID and len(self.stack) > depth:
            self.handle_endtag(tag)

    def handle_data(self, data):
        self.out.append(escape(data))

    def handle_comment(self, data):
        self._refuse("an HTML comment is not allowed here")

    def handle_decl(self, decl):
        self._refuse("a doctype is not allowed here")

    def handle_pi(self, data):
        self._refuse("a processing instruction is not allowed here")

    def unknown_decl(self, data):
        self._refuse("a CDATA section is not allowed here")

    # --- result ---

    def result(self) -> str:
        while self.stack:
            open_tag = self.stack.pop()
            if open_tag is not None:
                self._refuse(f"<{open_tag}> is never closed")
                self.out.append(f"</{open_tag}>")
        return "".join(self.out)


def _parse(value: str) -> _Rewriter:
    parser = _Rewriter()
    parser.feed(value)
    parser.close()
    return parser


def render(value: str):
    """Stored markup, ready for a template."""
    if not value:
        return mark_safe("")
    parser = _parse(value)
    return mark_safe(parser.result())


def validate(value: str) -> None:
    """A field validator: refuse markup a page may not carry."""
    if not value:
        return
    parser = _parse(value)
    parser.result()
    if parser.problems:
        raise ValidationError([f"{problem}." for problem in dict.fromkeys(parser.problems)])


class _Words(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data):
        self.parts.append(data)


def to_text(value: str) -> str:
    """The words without the markup, for a console list column."""
    words = _Words()
    words.feed(value or "")
    words.close()
    return " ".join("".join(words.parts).split())


# For a field's help text: the tags an editor may use, written out.
ALLOWED_TAGS_HELP = ", ".join(f"&lt;{tag}&gt;" for tag in sorted(ALLOWED))
