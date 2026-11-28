"""
The module registry.

A console module is one model made editable: its list columns, its search
fields, its filters, who may change it and what inline rows hang off it. The
plan calls for roughly 38 content models, most of them short ordered lists of
icon / title / text, so they are described here as data and rendered by one set
of views and templates rather than 38 hand-written screens.

Register a module in modules.py and it gets a list with search, filters,
sorting and pagination, a create and an edit form, inline rows with drag
ordering, a delete confirmation, a publish switch, an entry in the navigation
and a line in the activity log on every write.

Nothing in here builds HTML. A column resolves to a ``Cell`` carrying a kind
and a value; the template decides the markup. That keeps the panel's markup in
templates, where the CSP tests can see it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from django.db import models
from django.urls import reverse
from django.utils import formats, timezone

from . import roles


# --- Cells ------------------------------------------------------------------

@dataclass(frozen=True)
class Cell:
    """One rendered table cell: a kind the template knows, and a value."""
    kind: str
    text: str = ""
    truthy: bool = False
    value: object = None


@dataclass(frozen=True)
class Column:
    """One column of a module's list."""
    name: str
    label: str = ""
    kind: str = "text"       # text | bool | date | datetime | number | badge | email | muted
    sortable: bool = True
    link: bool = False       # this cell links to the row's edit page
    align: str = ""          # "" | center | end
    truncate: int = 0        # characters before an ellipsis; 0 means no limit

    @property
    def heading(self) -> str:
        if self.label:
            return self.label
        return self.name.replace("_", " ").replace("__", " ").capitalize()

    @property
    def sort_key(self) -> str:
        return self.name.replace("__", "__")


# --- Filters ----------------------------------------------------------------

@dataclass(frozen=True)
class Filter:
    """A dropdown above a module's list."""
    name: str
    label: str = ""
    # ((value, label), …), or a callable returning that. A callable is how a
    # filter lists rows from the database: modules are built when the process
    # starts, long before a query is safe.
    choices: object = ()
    kind: str = "choice"     # choice | bool
    lookup: str = ""         # ORM lookup; defaults to name

    @property
    def heading(self) -> str:
        return self.label or self.name.replace("_", " ").capitalize()

    @property
    def orm(self) -> str:
        return self.lookup or self.name

    def resolved_choices(self) -> list[tuple[str, str]]:
        raw = self.choices() if callable(self.choices) else self.choices
        return [(str(value), str(label)) for value, label in raw]

    def options(self) -> list[tuple[str, str]]:
        if self.kind == "bool":
            return [("1", "Yes"), ("0", "No")]
        return self.resolved_choices()

    def condition(self, raw: str):
        """A Q-ready {lookup: value} dict, or None when the value is no good."""
        if self.kind == "bool":
            if raw not in {"0", "1"}:
                return None
            return {self.orm: raw == "1"}
        if raw not in {value for value, _ in self.resolved_choices()}:
            return None
        return {self.orm: raw}


# --- Inlines ----------------------------------------------------------------

@dataclass(frozen=True)
class Inline:
    """Child rows edited on the parent's form (project paragraphs, agenda items)."""
    model: type
    label: str = ""
    label_plural: str = ""
    fields: tuple[str, ...] = ()
    fk_name: str = ""
    extra: int = 1
    order_field: str = ""    # when set, rows can be dragged
    can_delete: bool = True

    @property
    def heading(self) -> str:
        return self.label_plural or self.label or self.model._meta.verbose_name_plural.capitalize()

    @property
    def prefix(self) -> str:
        return self.model._meta.model_name


# --- Modules ----------------------------------------------------------------

@dataclass
class Module:
    slug: str
    model: type
    label: str = ""
    label_plural: str = ""
    group: str = "Content"
    icon: str = "page"
    blurb: str = ""

    columns: tuple[Column, ...] = ()
    search_fields: tuple[str, ...] = ()
    filters: tuple[Filter, ...] = ()
    ordering: tuple[str, ...] = ("-pk",)
    select_related: tuple[str, ...] = ()

    form_class: type | None = None
    create_form_class: type | None = None   # when creating needs a different form
    # Either a flat tuple of field names, or the same names grouped into
    # headed blocks as ((heading, (field, …)), …). A module with twenty fields
    # on it -- a page singleton, typically -- declares the groups and gets both
    # the form's layout and its field list from them.
    fields: tuple[str, ...] | None = None
    fieldsets: tuple = ()
    inlines: tuple[Inline, ...] = ()

    readonly: bool = False    # list and read, never write (enquiries, activity)
    can_create: bool = True
    can_delete: bool = True
    # A record there is only ever one of: the sidebar opens its form directly
    # instead of a list with a single row in it.
    singleton: bool = False

    publish_field: str = ""   # a BooleanField; shows a publish switch
    publish_text: str = "Publish"
    unpublish_text: str = "Unpublish"
    publish_done: str = "is now published"
    unpublish_done: str = "is now hidden"
    order_field: str = ""     # an IntegerField; enables drag ordering
    per_page: int = 0

    view_rank: int = roles.VIEWER
    edit_rank: int = roles.EDITOR
    delete_rank: int = roles.PUBLISHER

    extra: dict = field(default_factory=dict)

    # --- names ---

    # Query-string names the list views already use for themselves.
    RESERVED_PARAMS = {"page", "q", "sort", "dir"}

    def __post_init__(self):
        meta = self.model._meta
        self.label = self.label or str(meta.verbose_name).capitalize()
        self.label_plural = self.label_plural or str(meta.verbose_name_plural).capitalize()

        clashes = sorted({f.name for f in self.filters} & self.RESERVED_PARAMS)
        if clashes:
            raise ValueError(
                f"console module {self.slug!r}: filter name(s) {clashes} are already "
                "used by the list itself (paging, search and sorting). "
                "Name the filter something else, e.g. 'on_page' instead of 'page'."
            )

    @property
    def model_label(self) -> str:
        return self.model._meta.label_lower

    @property
    def form_fields(self) -> tuple[str, ...]:
        """Every field the form edits, whether declared flat or in groups."""
        if self.fields:
            return tuple(self.fields)
        return tuple(name for _, group in self.fieldsets for name in group)

    # --- capability, given a user ---

    def may_view(self, user) -> bool:
        return roles.has_rank(user, self.view_rank)

    def may_edit(self, user) -> bool:
        return not self.readonly and roles.has_rank(user, self.edit_rank)

    def may_create(self, user) -> bool:
        return self.can_create and self.may_edit(user)

    def may_delete(self, user) -> bool:
        return (
            self.can_delete
            and not self.readonly
            and roles.has_rank(user, self.delete_rank)
        )

    def may_publish(self, user) -> bool:
        """
        The publish switch is not the edit form.

        A module can be read-only and still carry one switch — an enquiry is
        never edited, but it does get marked answered.
        """
        return bool(self.publish_field) and roles.has_rank(user, self.edit_rank)

    def publish_label(self, obj) -> str:
        """What the switch says for this row."""
        if not self.publish_field:
            return ""
        return self.unpublish_text if getattr(obj, self.publish_field, False) else self.publish_text

    # --- urls ---

    def url(self) -> str:
        return reverse("console:list", args=[self.slug])

    def create_url(self) -> str:
        return reverse("console:create", args=[self.slug])

    def edit_url(self, pk) -> str:
        return reverse("console:edit", args=[self.slug, pk])

    def view_url(self, pk) -> str:
        return reverse("console:detail", args=[self.slug, pk])

    def delete_url(self, pk) -> str:
        return reverse("console:delete", args=[self.slug, pk])

    def row_url(self, pk) -> str:
        """Where a row's own link goes: the form, or the read-only page."""
        return self.view_url(pk) if self.readonly else self.edit_url(pk)

    # --- data ---

    def queryset(self):
        qs = self.model._default_manager.all()
        if self.select_related:
            qs = qs.select_related(*self.select_related)
        return qs

    def sortable_names(self) -> set[str]:
        return {column.name for column in self.columns if column.sortable}

    def cell(self, obj, column: Column) -> Cell:
        value = resolve(obj, column.name)

        if column.kind == "bool":
            return Cell("bool", "Yes" if value else "No", bool(value), value)

        display = display_value(obj, column.name, value)
        if column.truncate and len(display) > column.truncate:
            display = display[: column.truncate].rstrip() + "…"
        return Cell(column.kind, display, bool(value), value)

    def row(self, obj) -> list[Cell]:
        return [self.cell(obj, column) for column in self.columns]


def resolve(obj, name: str):
    """
    Read ``name`` off ``obj``, following ``__`` across relations and calling
    anything callable. A missing or null link gives None rather than raising.
    """
    current = obj
    for part in name.split("__"):
        if current is None:
            return None
        current = getattr(current, part, None)
        if callable(current):
            current = current()
    return current


EMPTY = "—"


def display_value(obj, name: str, value) -> str:
    """
    The text a cell shows.

    Honours a field's ``choices``, renders dates the way the rest of the site
    does, and shows one em dash for anything empty, so a column never has a
    blank cell that could be read as a missing column.
    """
    if "__" not in name:
        getter = getattr(obj, f"get_{name}_display", None)
        if callable(getter):
            # A blank choice gives back the blank value; show the dash instead.
            return str(getter()) or EMPTY
    if value is None or value == "":
        return EMPTY
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, datetime):
        local = timezone.localtime(value) if timezone.is_aware(value) else value
        return formats.date_format(local, "j M Y, H:i")
    if isinstance(value, date):
        return formats.date_format(value, "j M Y")
    if isinstance(value, models.Model):
        return str(value)
    if isinstance(value, models.Manager):
        return str(value.count())
    return str(value)


# --- The registry itself ----------------------------------------------------

class Registry:
    """Every registered module, in registration order."""

    # The order groups appear in the sidebar. Anything else is appended.
    GROUP_ORDER = ("Content", "Programmes", "Projects", "Editorial", "Messages", "Settings")

    def __init__(self):
        self._modules: dict[str, Module] = {}

    def register(self, module: Module) -> Module:
        if module.slug in self._modules:
            raise ValueError(f"console module {module.slug!r} is already registered")
        self._modules[module.slug] = module
        return module

    def get(self, slug: str) -> Module | None:
        return self._modules.get(slug)

    def all(self) -> list[Module]:
        return list(self._modules.values())

    def slugs(self) -> list[str]:
        return list(self._modules)

    # The icon on each collapsible group in the sidebar. A group with no entry
    # here falls back to the first of its modules, so adding a group never
    # leaves a hole in the menu.
    GROUP_ICONS = {
        "Content": "page",
        "Projects": "layers",
        "Messages": "inbox",
        "Settings": "settings",
        "People": "people",
    }

    def nav(self, user, current=None) -> list[dict]:
        """
        The sidebar: groups in GROUP_ORDER, holding what this user may see.

        Each group carries its icon and whether it holds the page being looked
        at, so the template can open that one and leave the rest closed.
        """
        visible = [m for m in self._modules.values() if m.may_view(user)]
        groups: dict[str, list[Module]] = {}
        for module in visible:
            groups.setdefault(module.group, []).append(module)

        ordered = [name for name in self.GROUP_ORDER if name in groups]
        ordered += [name for name in groups if name not in self.GROUP_ORDER]
        return [
            {
                "name": name,
                "modules": groups[name],
                "icon": self.GROUP_ICONS.get(name) or groups[name][0].icon,
                "has_current": any(m.slug == getattr(current, "slug", None)
                                   for m in groups[name]),
            }
            for name in ordered
        ]


registry = Registry()
