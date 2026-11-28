"""
Console forms.

Every widget is given a class here rather than a ``style`` attribute, because
the console runs under the site's own Content-Security-Policy: no inline
styles, no inline scripts. A test enforces it.
"""

from __future__ import annotations

from django import forms

from apps.content.richtext import validate as validate_inline
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, SetPasswordForm

from . import roles

# Widget class -> the console class that styles it.
WIDGET_CLASSES = {
    forms.CheckboxInput: "cns-check",
    forms.CheckboxSelectMultiple: "cns-checklist",
    forms.RadioSelect: "cns-radiolist",
    forms.Select: "cns-select",
    forms.SelectMultiple: "cns-select cns-select--multi",
    forms.Textarea: "cns-textarea",
    forms.ClearableFileInput: "cns-file",
    forms.FileInput: "cns-file",
}
DEFAULT_WIDGET_CLASS = "cns-input"


def theme(form: forms.BaseForm) -> None:
    """Add the console's classes to every widget on a form, in place."""
    for name, field in form.fields.items():
        widget = field.widget
        css = DEFAULT_WIDGET_CLASS
        for widget_type, class_name in WIDGET_CLASSES.items():
            if isinstance(widget, widget_type):
                css = class_name
                break
        existing = widget.attrs.get("class", "")
        widget.attrs["class"] = f"{existing} {css}".strip()

        if isinstance(widget, forms.Textarea):
            widget.attrs.setdefault("rows", 4)
            # A field that runs the limited-HTML validator is the one an editor
            # should get a rich-text box for. Marked here rather than listed by
            # name in JavaScript, so a new one is picked up by having the
            # validator, not by somebody remembering to add it to a list.
            if any(v is validate_inline for v in field.validators):
                widget.attrs["data-richtext"] = "true"
        # Select2 attaches to these. A plain <select> still works without it.
        if isinstance(widget, forms.Select) and not isinstance(
            widget, (forms.RadioSelect, forms.CheckboxSelectMultiple)
        ):
            widget.attrs.setdefault("data-enhance", "select")
        if field.required and not isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
            widget.attrs.setdefault("required", "required")
        if form.errors.get(name):
            widget.attrs["aria-invalid"] = "true"


class ConsoleFormMixin:
    """Themes the form and exposes the fieldsets the template groups by."""

    fieldsets: tuple = ()

    @property
    def has_richtext(self) -> bool:
        """
        Whether any field wants the editor. The editor is a megabyte and a
        half, so a form without one of these fields never asks for it.
        """
        return any(
            f.widget.attrs.get("data-richtext") for f in self.fields.values()
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        theme(self)

    def grouped_fields(self):
        """
        [(heading, [BoundField, …]), …].

        With no fieldsets declared, everything lands in one unnamed group, so
        the template has a single code path.
        """
        if not self.fieldsets:
            return [("", list(self))]
        seen: set[str] = set()
        groups = []
        for heading, names in self.fieldsets:
            fields = [self[name] for name in names if name in self.fields]
            seen.update(name for name in names if name in self.fields)
            if fields:
                groups.append((heading, fields))
        rest = [bound for bound in self if bound.name not in seen]
        if rest:
            groups.append(("", rest))
        return groups


class ConsoleModelForm(ConsoleFormMixin, forms.ModelForm):
    """The base every module form uses."""


class ConsoleAuthenticationForm(ConsoleFormMixin, AuthenticationForm):
    """
    Sign-in for the console.

    A non-staff account is refused with the same message as a wrong password,
    so the form never reveals which addresses have accounts.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"autocomplete": "username", "autocapitalize": "none", "autofocus": "autofocus"}
        )
        self.fields["password"].widget.attrs["autocomplete"] = "current-password"

    def confirm_login_allowed(self, user):
        if not user.is_active or not user.is_staff:
            raise forms.ValidationError(
                self.error_messages["invalid_login"],
                code="invalid_login",
                params={"username": self.username_field.verbose_name},
            )


class ConsoleSetPasswordForm(ConsoleFormMixin, SetPasswordForm):
    """Used by an administrator to set someone else's password."""


class ConsolePasswordChangeForm(ConsoleFormMixin, PasswordChangeForm):
    """Changing your own password, which asks for the current one first."""


# --- Content ----------------------------------------------------------------

class ProjectForm(ConsoleModelForm):
    """
    A project is a long form, so it is grouped.

    The slug is not offered: it is the project's web address, and changing it
    silently breaks every link anyone has already shared.
    """

    class Meta:
        from apps.content.models import Project

        model = Project
        fields = (
            "title", "summary", "card_summary", "location", "stage",
            "programme", "gs_id", "standard", "tags",
            "photo", "photo_has_large", "stock_photo",
            "proponent", "status_label", "status_note", "card_badge",
            "stove_detail",
            "sort_order", "grid_order", "reveal_delay", "card_links_to_programme",
        )

    fieldsets = (
        ("The project", ("title", "summary", "card_summary", "location", "stage")),
        ("Programme and standard", ("programme", "gs_id", "standard", "tags")),
        ("Photo", ("photo", "photo_has_large", "stock_photo")),
        ("Key details", ("proponent", "status_label", "status_note", "card_badge", "stove_detail")),
        ("Order and presentation", ("sort_order", "grid_order", "reveal_delay", "card_links_to_programme")),
    )


class ProgrammeForm(ConsoleModelForm):
    class Meta:
        from apps.content.models import Programme

        model = Programme
        fields = ("label", "stage", "summary", "priority", "show_on_website", "sort_order")

    fieldsets = (
        ("The programme", ("label", "stage", "summary")),
        ("On the website", ("priority", "show_on_website", "sort_order")),
    )


# --- Staff accounts ---------------------------------------------------------

User = get_user_model()

STAFF_FIELDS = ("username", "first_name", "last_name", "email", "is_active")


class StaffForm(ConsoleModelForm):
    """
    Edit a staff account.

    Role is a single choice rather than a free pick of groups: the console has
    exactly three roles and showing the raw group list invites a half-assigned
    account. ``is_staff`` is not offered either — every account the console
    creates is staff, which is what makes it able to sign in here.
    """

    role = forms.TypedChoiceField(
        label="Role",
        coerce=int,
        choices=[
            (roles.VIEWER, "Read only — can sign in and read, change nothing"),
            (roles.EDITOR, "Editor — change content, but not publish it"),
            (roles.PUBLISHER, "Publisher — change, publish and delete content"),
            (roles.ADMINISTRATOR, "Administrator — everything, plus staff accounts"),
        ],
        help_text="A new account starts read-only until someone gives it a role.",
    )

    class Meta:
        model = User
        fields = STAFF_FIELDS

    fieldsets = (
        ("Account", ("username", "email", "first_name", "last_name")),
        ("Access", ("role", "is_active")),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Django's own wording here is written for developers.
        self.fields["is_active"].label = "Can sign in"
        self.fields["is_active"].help_text = (
            "Turn this off when someone leaves. Keep the account rather than "
            "deleting it, so the activity log still shows who did what."
        )
        self.fields["username"].help_text = "What they type to sign in. Letters, digits and @ . + - _ only."
        self.fields["email"].label = "Email address"

        if self.instance.pk:
            self.fields["role"].initial = roles.rank_of(self.instance)
        else:
            self.fields["role"].initial = roles.VIEWER
        if self.instance.pk and self.instance.is_superuser:
            # A superuser's access is not ours to change from here.
            self.fields["role"].disabled = True
            self.fields["role"].help_text = (
                "This is a superuser account. Its access is set outside the console."
            )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True
        if commit:
            user.save()
            self.save_role(user)
        return user

    def save_role(self, user) -> None:
        """Put the account in exactly the group its role names, and no other."""
        if user.is_superuser:
            return
        from django.contrib.auth.models import Group

        wanted = self.cleaned_data.get("role", roles.VIEWER)
        names = [name for name, rank in roles.GROUP_RANKS.items() if rank == wanted]
        user.groups.remove(*Group.objects.filter(name__in=roles.GROUP_RANKS))
        if names:
            group, _ = Group.objects.get_or_create(name=names[0])
            user.groups.add(group)


class StaffCreateForm(StaffForm):
    """Creating an account, with its first password."""

    password1 = forms.CharField(
        label="Password", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=password_validation.password_validators_help_text_html,
    )
    password2 = forms.CharField(
        label="Password again", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    fieldsets = (
        ("Account", ("username", "email", "first_name", "last_name")),
        ("Password", ("password1", "password2")),
        ("Access", ("role", "is_active")),
    )

    def clean_password2(self):
        first = self.cleaned_data.get("password1")
        second = self.cleaned_data.get("password2")
        if first and second and first != second:
            raise forms.ValidationError("The two passwords do not match.")
        password_validation.validate_password(second, self.instance)
        return second

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password2"])
        user.is_staff = True
        if commit:
            user.save()
            self.save_role(user)
        return user
