"""
The generic screens every console module gets.

One list, one form, one delete confirmation, one read-only detail, plus the
publish switch, the reorder endpoint and the JSON feed a server-side table
reads. A module describes itself in registry.py; nothing here knows what a
project or an event is.

Everything a template needs is computed here — sort links, filter options,
pagination query strings, cells — so the templates hold markup and no logic.
"""

from __future__ import annotations

import json

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models import Q
from django.forms import inlineformset_factory, modelform_factory
from django.http import Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views import View
from django.views.generic import ListView

from .. import audit
from ..forms import ConsoleModelForm
from ..mixins import ConsoleAccessMixin
from ..models import AuditEntry
from ..registry import Column, registry


class ModuleMixin(ConsoleAccessMixin):
    """Resolves ``<slug>`` to a module and asks it who may do this."""

    action = "view"          # view | edit | delete

    def dispatch(self, request, *args, **kwargs):
        self.module = registry.get(kwargs.get("slug", ""))
        return super().dispatch(request, *args, **kwargs)

    def check_access(self, request):
        if self.module is None:
            raise Http404("No such console module")
        allowed = {
            "view": self.module.may_view,
            "edit": self.module.may_edit,
            "delete": self.module.may_delete,
        }[self.action]
        if not allowed(request.user):
            return self.refuse(request)
        return None

    def get_object_or_404(self):
        try:
            return self.module.queryset().get(pk=self.kwargs["pk"])
        except self.module.model.DoesNotExist as exc:
            raise Http404("No such row") from exc

    def module_context(self, **kwargs) -> dict:
        """The shell's context plus what every module screen shows."""
        user = self.request.user
        context = self.console_base_context(
            module=self.module,
            may_create=self.module.may_create(user),
            may_edit=self.module.may_edit(user),
            may_delete=self.module.may_delete(user),
            may_publish=self.module.may_publish(user),
        )
        context.update(kwargs)
        return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for key, value in self.module_context().items():
            context.setdefault(key, value)
        return context

    def breadcrumbs(self):
        return [(self.module.label_plural, self.module.url())]


# --- Query building, shared by the list and the JSON feed -------------------

class ModuleQueryMixin(ModuleMixin):

    def apply_search(self, qs, term: str):
        if not term or not self.module.search_fields:
            return qs
        query = Q()
        for name in self.module.search_fields:
            query |= Q(**{f"{name}__icontains": term})
        return qs.filter(query)

    def apply_filters(self, qs):
        """Returns (queryset, {filter name: raw value}) for valid values only."""
        active: dict[str, str] = {}
        for item in self.module.filters:
            raw = self.request.GET.get(item.name, "").strip()
            if not raw:
                continue
            condition = item.condition(raw)
            if condition is None:
                continue
            active[item.name] = raw
            qs = qs.filter(**condition)
        return qs, active

    def apply_sort(self, qs, name: str, direction: str):
        if name in self.module.sortable_names():
            prefix = "-" if direction == "desc" else ""
            return qs.order_by(f"{prefix}{name}", "-pk")
        return qs.order_by(*self.module.ordering)


class ModuleListView(ModuleQueryMixin, ListView):
    template_name = "console/list.html"
    action = "view"
    context_object_name = "page_rows"

    def get(self, request, *args, **kwargs):
        # There is no list worth showing for a record there is only one of:
        # open its form instead, creating the row from its defaults if this is
        # the first time anyone has looked.
        if self.module.singleton:
            return redirect(self.module.edit_url(self.module.model.load().pk))
        return super().get(request, *args, **kwargs)

    def get_paginate_by(self, queryset):
        return self.module.per_page or settings.CONSOLE_PER_PAGE

    def get_queryset(self):
        self.search = self.request.GET.get("q", "").strip()[:200]
        self.sort = self.request.GET.get("sort", "").strip()
        self.direction = "desc" if self.request.GET.get("dir") == "desc" else "asc"
        if self.sort not in self.module.sortable_names():
            self.sort = ""

        qs = self.apply_search(self.module.queryset(), self.search)
        qs, self.active_filters = self.apply_filters(qs)
        return self.apply_sort(qs, self.sort, self.direction)

    # --- the bits the template needs ---

    def carried_params(self, **overrides) -> str:
        """The current query string with ``page`` dropped and overrides applied."""
        params: dict[str, str] = {}
        if self.search:
            params["q"] = self.search
        params.update(self.active_filters)
        if self.sort:
            params["sort"] = self.sort
            params["dir"] = self.direction
        params.update({k: v for k, v in overrides.items() if v not in (None, "")})
        for key, value in list(params.items()):
            if value in (None, ""):
                params.pop(key)
        return urlencode(params)

    def heading_links(self) -> list[dict]:
        out = []
        for column in self.module.columns:
            item = {"column": column, "state": "", "url": ""}
            if column.sortable:
                flip = "desc" if (self.sort == column.name and self.direction == "asc") else "asc"
                item["url"] = "?" + self.carried_params(sort=column.name, dir=flip)
                if self.sort == column.name:
                    item["state"] = self.direction
            out.append(item)
        return out

    def describe(self, obj) -> dict:
        """
        One row, with everything the template needs already resolved.

        Cells are paired with their column so the template can read an
        alignment without indexing two parallel lists, and the per-row URLs are
        built here because a Django template cannot call a method with
        arguments.
        """
        module = self.module
        return {
            "object": obj,
            "cells": [
                {"cell": cell, "column": column}
                for column, cell in zip(module.columns, module.row(obj))
            ],
            "url": module.row_url(obj.pk),
            "delete_url": module.delete_url(obj.pk),
            "publish_url": reverse("console:publish", args=[module.slug, obj.pk]),
            "publish_label": module.publish_label(obj),
        }

    def filter_controls(self) -> list[dict]:
        return [
            {
                "filter": item,
                "options": item.options(),
                "value": self.active_filters.get(item.name, ""),
            }
            for item in self.module.filters
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        module = self.module
        context["rows"] = [self.describe(obj) for obj in context["page_rows"]]
        context["headings"] = self.heading_links()
        context["filter_controls"] = self.filter_controls()
        context["search"] = self.search
        context["sort"] = self.sort
        context["direction"] = self.direction
        context["carried"] = self.carried_params()
        context["total"] = context["paginator"].count if context.get("paginator") else len(context["rows"])
        context["is_filtered"] = bool(self.search or self.active_filters)
        context["data_url"] = reverse("console:data", args=[module.slug])
        context["may_reorder"] = bool(module.order_field) and context["may_edit"]
        return context

    def breadcrumbs(self):
        return [(self.module.label_plural, "")]


class ModuleDataView(ModuleQueryMixin, View):
    """
    The JSON a server-side table reads.

    Answers DataTables' parameter names so the list can be upgraded to a
    server-side table without touching this view, and stays useful on its own
    as a plain paged feed.
    """

    action = "view"
    MAX_LENGTH = 200

    def get(self, request, *args, **kwargs):
        module = self.module
        columns = module.columns

        term = request.GET.get("search[value]", request.GET.get("q", "")).strip()[:200]
        try:
            start = max(0, int(request.GET.get("start", 0)))
            length = int(request.GET.get("length", settings.CONSOLE_PER_PAGE))
        except (TypeError, ValueError):
            return HttpResponseBadRequest("bad paging")
        length = min(max(1, length), self.MAX_LENGTH)

        sort_name, direction = "", "asc"
        try:
            index = int(request.GET.get("order[0][column]", -1))
            if 0 <= index < len(columns):
                sort_name = columns[index].name
                direction = "desc" if request.GET.get("order[0][dir]") == "desc" else "asc"
        except (TypeError, ValueError):
            pass

        base = module.queryset()
        total = base.count()
        qs = self.apply_search(base, term)
        qs, _active = self.apply_filters(qs)
        filtered = qs.count()
        qs = self.apply_sort(qs, sort_name, direction)

        rows = []
        for obj in qs[start:start + length]:
            rows.append({
                "pk": obj.pk,
                "url": module.row_url(obj.pk),
                "cells": [
                    {"kind": cell.kind, "text": cell.text, "truthy": cell.truthy}
                    for cell in module.row(obj)
                ],
            })

        return JsonResponse({
            "draw": request.GET.get("draw", ""),
            "recordsTotal": total,
            "recordsFiltered": filtered,
            "data": rows,
        })


# --- Writing ----------------------------------------------------------------

class ModuleEditView(ModuleMixin, View):
    """Create or change one row, with its inline rows."""

    action = "edit"
    template_name = "console/form.html"

    @property
    def is_create(self) -> bool:
        return "pk" not in self.kwargs

    def check_access(self, request):
        refused = super().check_access(request)
        if refused is not None:
            return refused
        if self.is_create and not self.module.may_create(request.user):
            return self.refuse(request)
        return None

    def form_class(self):
        module = self.module
        if self.is_create and module.create_form_class is not None:
            return module.create_form_class
        if module.form_class is not None:
            return module.form_class
        if not module.fields:
            raise ImproperlyConfigured(
                f"console module {module.slug!r} needs either form_class or fields; "
                "a console form never falls back to every field on the model."
            )
        return modelform_factory(module.model, form=ConsoleModelForm, fields=module.fields)

    def formsets(self, instance, data=None, files=None):
        out = []
        for inline in self.module.inlines:
            factory = inlineformset_factory(
                self.module.model,
                inline.model,
                form=ConsoleModelForm,
                fields=inline.fields,
                extra=inline.extra,
                can_delete=inline.can_delete,
                fk_name=inline.fk_name or None,
            )
            out.append({
                "inline": inline,
                "formset": factory(data, files, instance=instance, prefix=inline.prefix),
            })
        return out

    def get(self, request, *args, **kwargs):
        instance = None if self.is_create else self.get_object_or_404()
        form = self.form_class()(instance=instance)
        return self.render(form, self.formsets(instance), instance)

    def post(self, request, *args, **kwargs):
        instance = None if self.is_create else self.get_object_or_404()
        form = self.form_class()(request.POST, request.FILES, instance=instance)

        if not form.is_valid():
            return self.render(form, self.formsets(instance, request.POST, request.FILES), instance, status=400)

        obj = form.save()
        blocks = self.formsets(obj, request.POST, request.FILES)
        if any(not block["formset"].is_valid() for block in blocks):
            # The parent is saved but a child is not: show the errors rather
            # than silently dropping the child rows.
            return self.render(form, blocks, obj, status=400)
        for block in blocks:
            block["formset"].save()

        audit.record(
            request,
            AuditEntry.CREATE if self.is_create else AuditEntry.UPDATE,
            obj=obj,
            module=self.module.slug,
            changes=audit.changes_from_form(form),
        )
        messages.success(
            request,
            f"{self.module.label} “{obj}” was {'created' if self.is_create else 'saved'}.",
        )
        return redirect(self.module.url())

    def render(self, form, blocks, instance, status=200):
        context = self.module_context(
            form=form,
            groups=form.grouped_fields() if hasattr(form, "grouped_fields") else [("", list(form))],
            inline_blocks=blocks,
            object=instance,
            is_create=self.is_create,
            cancel_url=self.module.url(),
        )
        return render(self.request, self.template_name, context, status=status)

    def breadcrumbs(self):
        label = f"New {self.module.label.lower()}" if self.is_create else "Edit"
        return [(self.module.label_plural, self.module.url()), (label, "")]


class ModuleDetailView(ModuleMixin, View):
    """Read-only view of one row, for modules that are never edited here."""

    action = "view"
    template_name = "console/detail.html"

    def get(self, request, *args, **kwargs):
        obj = self.get_object_or_404()
        self.object = obj
        # The primary key is bookkeeping, not content: staff reading an
        # enquiry have no use for a row id.
        fields = [
            {"label": field.verbose_name, "cell": self.module.cell(obj, Column(name=field.name))}
            for field in self.module.model._meta.fields
            if not field.primary_key
        ]
        context = self.module_context(
            object=obj,
            fields=fields,
            publish_label=self.module.publish_label(obj),
            history=AuditEntry.objects.filter(
                module=self.module.slug, object_id=str(obj.pk)
            )[:10],
        )
        return render(request, self.template_name, context)

    def breadcrumbs(self):
        label = str(getattr(self, "object", "")) or "Details"
        return [(self.module.label_plural, self.module.url()), (label, "")]


class ModuleDeleteView(ModuleMixin, View):
    action = "delete"
    template_name = "console/confirm_delete.html"

    def get(self, request, *args, **kwargs):
        obj = self.get_object_or_404()
        context = self.module_context(
            object=obj,
            related=self.related_counts(obj),
            cancel_url=self.module.url(),
        )
        return render(request, self.template_name, context)

    def breadcrumbs(self):
        return [(self.module.label_plural, self.module.url()), ("Delete", "")]

    def post(self, request, *args, **kwargs):
        obj = self.get_object_or_404()
        label = str(obj)
        audit.record(
            request, AuditEntry.DELETE, obj=obj, module=self.module.slug,
            changes=audit.snapshot(obj, self.module.fields or ()),
        )
        obj.delete()
        messages.success(request, f"{self.module.label} “{label}” was deleted.")
        return redirect(self.module.url())

    def related_counts(self, obj) -> list[str]:
        """
        What a delete takes with it, so the confirmation can name it.

        Only cascading relations are listed: those are the rows that actually
        disappear. A relation that nulls out or protects is not a loss to warn
        about, and a PROTECT will refuse the delete anyway.
        """
        out = []
        for rel in self.module.model._meta.related_objects:
            if getattr(rel, "on_delete", None) is not models.CASCADE:
                continue
            manager = getattr(obj, rel.get_accessor_name(), None)
            if manager is None or not hasattr(manager, "count"):
                continue
            count = manager.count()
            if count:
                out.append(f"{count} {rel.related_model._meta.verbose_name_plural}")
        return out


class ModulePublishView(ModuleMixin, View):
    """Flip a module's publish flag. POST only."""

    action = "edit"

    def check_access(self, request):
        if self.module is None:
            raise Http404("No such console module")
        if not self.module.may_publish(request.user):
            return self.refuse(request)
        return None

    def post(self, request, *args, **kwargs):
        module = self.module
        if not module.publish_field:
            raise Http404("This module has nothing to publish")
        obj = self.get_object_or_404()
        current = bool(getattr(obj, module.publish_field))
        setattr(obj, module.publish_field, not current)
        obj.save(update_fields=[module.publish_field])

        audit.record(
            request,
            AuditEntry.UNPUBLISH if current else AuditEntry.PUBLISH,
            obj=obj, module=module.slug,
            changes={module.publish_field: {"from": current, "to": not current}},
        )
        said = module.unpublish_done if current else module.publish_done
        messages.success(request, f"{module.label} “{obj}” {said}.")
        return redirect(request.POST.get("back") or module.url())


class ModuleReorderView(ModuleMixin, View):
    """Save a new order for a module's rows. POST of {"ids": [pk, …]}."""

    action = "edit"

    def post(self, request, *args, **kwargs):
        module = self.module
        if not module.order_field:
            raise Http404("This module is not ordered")
        try:
            payload = json.loads(request.body.decode() or "{}")
            ids = [int(value) for value in payload.get("ids", [])]
        except (ValueError, AttributeError, TypeError):
            return HttpResponseBadRequest("bad order")

        rows = {obj.pk: obj for obj in module.queryset().filter(pk__in=ids)}
        if len(rows) != len(ids):
            return HttpResponseBadRequest("unknown rows in the order")

        for position, pk in enumerate(ids, start=1):
            obj = rows[pk]
            if getattr(obj, module.order_field) != position:
                setattr(obj, module.order_field, position)
                obj.save(update_fields=[module.order_field])

        audit.record(
            request, AuditEntry.REORDER, module=module.slug,
            note=f"{len(ids)} {module.label_plural.lower()}",
        )
        return JsonResponse({"ok": True, "count": len(ids)})
