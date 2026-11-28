"""
Tests for the console.

The ones that matter most are the access tests: a panel that edits the live
site must never be reachable without a staff account and the right role, and
"we remembered the mixin on every view" is not something to take on trust. The
walk over the registry checks every registered module, so a content module
added in a later phase is covered the day it is registered.
"""

from __future__ import annotations

import json
import re
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from apps.content.models import Page

from apps.website.models import Enquiry

from . import roles
from .mixins import SEEN_KEY
from .models import AuditEntry
from .registry import registry

User = get_user_model()

CONSOLE = "/" + settings.CONSOLE_URL


def make_user(username, rank=roles.EDITOR, *, staff=True, active=True, password="Pw-console-7781"):
    user = User.objects.create_user(
        username=username, email=f"{username}@example.test", password=password,
    )
    user.is_staff = staff
    user.is_active = active
    user.save()
    for name, group_rank in roles.GROUP_RANKS.items():
        if group_rank == rank:
            group, _ = Group.objects.get_or_create(name=name)
            user.groups.add(group)
    return user


class ConsoleUrls:
    """Every console URL, built from the registry rather than written twice."""

    @staticmethod
    def read_only() -> list[str]:
        urls = [reverse("console:dashboard"), reverse("console:password_change")]
        for module in registry.all():
            urls.append(module.url())
            urls.append(reverse("console:data", args=[module.slug]))
            if module.can_create and not module.readonly:
                urls.append(module.create_url())
        return urls


# --- Access -----------------------------------------------------------------

class AccessTests(TestCase):
    """Nothing in the console opens without a staff account."""

    @classmethod
    def setUpTestData(cls):
        cls.editor = make_user("editor")

    def test_every_console_page_redirects_an_anonymous_visitor(self):
        for url in ConsoleUrls.read_only():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302, url)
                self.assertIn(reverse("console:login"), response["Location"])

    def test_the_sign_in_page_itself_is_open(self):
        self.assertEqual(self.client.get(reverse("console:login")).status_code, 200)

    def test_a_non_staff_account_is_refused_exactly_like_a_wrong_password(self):
        """
        The form must not reveal which addresses have accounts, so a real
        account without staff access and a wrong password have to come back
        saying the same thing.
        """
        make_user("visitor", staff=False)
        url = reverse("console:login")

        non_staff = self.client.post(url, {"username": "visitor", "password": "Pw-console-7781"})
        self.assertEqual(non_staff.status_code, 200)
        self.assertFalse(non_staff.context["user"].is_authenticated)

        wrong_password = Client().post(url, {"username": "editor", "password": "not-the-password"})
        self.assertEqual(
            list(non_staff.context["form"].non_field_errors()),
            list(wrong_password.context["form"].non_field_errors()),
        )

    def test_an_inactive_staff_account_cannot_sign_in(self):
        make_user("retired", active=False)
        response = self.client.post(
            reverse("console:login"),
            {"username": "retired", "password": "Pw-console-7781"},
        )
        self.assertFalse(response.context["user"].is_authenticated)

    def test_a_staff_account_signs_in_and_reaches_the_overview(self):
        ok = self.client.login(username="editor", password="Pw-console-7781")
        self.assertTrue(ok)
        response = self.client.get(reverse("console:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Overview")

    def test_an_unknown_module_is_404(self):
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(f"{CONSOLE}not-a-module/").status_code, 404)

    def test_signing_in_is_logged_and_so_is_failing(self):
        url = reverse("console:login")
        # Separate clients: once signed in, the sign-in page redirects away
        # rather than taking another attempt.
        Client().post(url, {"username": "editor", "password": "Pw-console-7781"})
        Client().post(url, {"username": "editor", "password": "wrong"})

        self.assertTrue(AuditEntry.objects.filter(action=AuditEntry.LOGIN).exists())
        failed = AuditEntry.objects.filter(action=AuditEntry.LOGIN_FAILED).first()
        self.assertIsNotNone(failed)
        self.assertIn("editor", failed.note)

    def test_a_signed_in_account_is_sent_on_from_the_sign_in_page(self):
        self.client.force_login(self.editor)
        response = self.client.get(reverse("console:login"))
        self.assertRedirects(response, reverse("console:dashboard"))


class RoleTests(TestCase):
    """A role opens exactly what it should and nothing more."""

    @classmethod
    def setUpTestData(cls):
        cls.reader = make_user("reader", roles.VIEWER)
        cls.editor = make_user("editor", roles.EDITOR)
        cls.publisher = make_user("publisher", roles.PUBLISHER)
        cls.admin = make_user("boss", roles.ADMINISTRATOR)
        cls.enquiry = Enquiry.objects.create(
            name="Rahim", email="rahim@example.test", subject="general",
            message="Please tell me about the cookstove programme.",
        )

    def test_ranks_come_from_groups(self):
        self.assertEqual(roles.rank_of(self.reader), roles.VIEWER)
        self.assertEqual(roles.rank_of(self.editor), roles.EDITOR)
        self.assertEqual(roles.rank_of(self.publisher), roles.PUBLISHER)
        self.assertEqual(roles.rank_of(self.admin), roles.ADMINISTRATOR)

    def test_a_new_staff_account_with_no_group_can_change_nothing(self):
        self.assertEqual(roles.rank_of(make_user("fresh", rank=None)), roles.VIEWER)

    def test_a_superuser_ranks_as_an_administrator(self):
        root = User.objects.create_superuser("root", "root@example.test", "Pw-console-7781")
        self.assertEqual(roles.rank_of(root), roles.ADMINISTRATOR)

    def test_an_editor_cannot_open_staff_accounts(self):
        self.client.force_login(self.editor)
        response = self.client.get(registry.get("staff").url())
        self.assertEqual(response.status_code, 403)

    def test_an_administrator_can_open_staff_accounts(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(registry.get("staff").url()).status_code, 200)

    def test_an_editor_cannot_open_the_activity_log(self):
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(registry.get("activity").url()).status_code, 403)

    def test_a_reader_sees_no_sections(self):
        self.client.force_login(self.reader)
        response = self.client.get(reverse("console:dashboard"))
        self.assertContains(response, "needs to give it a role")

    def test_the_sidebar_only_lists_what_the_account_may_open(self):
        self.client.force_login(self.editor)
        body = self.client.get(reverse("console:dashboard")).content.decode()
        self.assertIn(registry.get("enquiries").url(), body)
        self.assertNotIn(registry.get("staff").url(), body)

    def test_an_enquiry_is_never_editable_through_a_form(self):
        self.client.force_login(self.publisher)
        response = self.client.get(
            reverse("console:edit", args=["enquiries", self.enquiry.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_an_enquiry_cannot_be_created_or_deleted_in_the_console(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(registry.get("enquiries").create_url()).status_code, 403)
        self.assertEqual(
            self.client.get(reverse("console:delete", args=["enquiries", self.enquiry.pk])).status_code,
            403,
        )


class SessionTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.editor = make_user("editor")

    def test_an_idle_session_is_signed_out(self):
        self.client.force_login(self.editor)
        session = self.client.session
        session[SEEN_KEY] = int(time.time()) - settings.CONSOLE_IDLE_SECONDS - 10
        session.save()

        response = self.client.get(reverse("console:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("timeout=1", response["Location"])
        self.assertTrue(
            AuditEntry.objects.filter(action=AuditEntry.LOGOUT, note="idle timeout").exists()
        )

    def test_a_session_in_use_is_not_signed_out(self):
        self.client.force_login(self.editor)
        session = self.client.session
        session[SEEN_KEY] = int(time.time()) - 30
        session.save()
        self.assertEqual(self.client.get(reverse("console:dashboard")).status_code, 200)

    def test_the_timeout_page_says_so(self):
        response = self.client.get(reverse("console:login") + "?timeout=1")
        self.assertContains(response, "sat idle")


@override_settings(CONSOLE_LOGIN_MAX_ATTEMPTS=3)
class LoginThrottleTests(TestCase):

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        make_user("editor")

    def test_repeated_failures_stop_being_answered(self):
        url = reverse("console:login")
        for _ in range(3):
            self.client.post(url, {"username": "editor", "password": "wrong"})

        response = self.client.post(url, {"username": "editor", "password": "wrong"})
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "Too many sign-in attempts", status_code=429)

    def test_the_lockout_holds_even_with_the_right_password(self):
        url = reverse("console:login")
        for _ in range(3):
            self.client.post(url, {"username": "editor", "password": "wrong"})

        response = self.client.post(url, {"username": "editor", "password": "Pw-console-7781"})
        self.assertEqual(response.status_code, 429)
        self.assertFalse(response.context["user"].is_authenticated)

    def test_a_different_address_is_not_locked_out(self):
        url = reverse("console:login")
        for _ in range(3):
            self.client.post(url, {"username": "editor", "password": "wrong"})

        make_user("other")
        response = self.client.post(url, {"username": "other", "password": "Pw-console-7781"})
        self.assertEqual(response.status_code, 302)


# --- The generic list -------------------------------------------------------

class ListTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.editor = make_user("editor")
        for index in range(7):
            Enquiry.objects.create(
                name=f"Person {index}",
                email=f"p{index}@example.test",
                subject="partnership" if index % 2 else "general",
                enquiry_type="partner" if index % 2 else "community",
                message=f"Message number {index}",
                handled=index < 2,
            )
        Enquiry.objects.create(
            name="Unmistakable Name", email="unique@example.test",
            subject="press", message="A press question.",
        )

    def setUp(self):
        self.client.force_login(self.editor)
        self.url = registry.get("enquiries").url()

    def test_the_list_renders_with_its_rows(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unmistakable Name")

    def test_search_narrows_the_list(self):
        response = self.client.get(self.url, {"q": "Unmistakable"})
        self.assertEqual(len(response.context["rows"]), 1)

    def test_search_in_the_message_body_works(self):
        response = self.client.get(self.url, {"q": "press question"})
        self.assertEqual(len(response.context["rows"]), 1)

    def test_a_boolean_filter_narrows_the_list(self):
        response = self.client.get(self.url, {"handled": "1"})
        self.assertEqual(len(response.context["rows"]), 2)

    def test_a_choice_filter_narrows_the_list(self):
        response = self.client.get(self.url, {"subject": "press"})
        self.assertEqual(len(response.context["rows"]), 1)

    def test_a_filter_value_that_is_not_a_choice_is_ignored(self):
        response = self.client.get(self.url, {"subject": "../etc/passwd"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["rows"]), Enquiry.objects.count())

    def test_sorting_by_a_listed_column_works(self):
        response = self.client.get(self.url, {"sort": "name", "dir": "asc"})
        names = [row["object"].name for row in response.context["rows"]]
        self.assertEqual(names, sorted(names))

    def test_sorting_by_anything_else_is_ignored(self):
        response = self.client.get(self.url, {"sort": "password", "dir": "asc"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["sort"], "")

    @override_settings(CONSOLE_PER_PAGE=3)
    def test_the_list_pages(self):
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["rows"]), 3)
        self.assertTrue(response.context["page_obj"].has_next())

    @override_settings(CONSOLE_PER_PAGE=3)
    def test_the_search_is_carried_across_pages(self):
        response = self.client.get(self.url, {"q": "Person", "sort": "name", "dir": "desc"})
        carried = response.context["carried"]
        self.assertIn("q=Person", carried)
        self.assertIn("sort=name", carried)
        self.assertNotIn("page=", carried)

    def test_an_empty_search_says_so(self):
        response = self.client.get(self.url, {"q": "nothing matches this"})
        self.assertContains(response, "Nothing matches that search")


class DataFeedTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.editor = make_user("editor")
        Enquiry.objects.create(
            name="Feed Person", email="feed@example.test", subject="general",
            message="A question.",
        )

    def setUp(self):
        self.client.force_login(self.editor)

    def test_the_feed_answers_json_in_the_expected_shape(self):
        response = self.client.get(reverse("console:data", args=["enquiries"]), {"draw": "3"})
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(payload["draw"], "3")
        self.assertEqual(payload["recordsTotal"], 1)
        self.assertEqual(payload["recordsFiltered"], 1)
        self.assertEqual(len(payload["data"]), 1)
        self.assertIn("cells", payload["data"][0])

    def test_the_feed_respects_a_search(self):
        payload = json.loads(
            self.client.get(
                reverse("console:data", args=["enquiries"]), {"search[value]": "nope"}
            ).content
        )
        self.assertEqual(payload["recordsTotal"], 1)
        self.assertEqual(payload["recordsFiltered"], 0)

    def test_the_feed_caps_how_much_it_will_hand_over(self):
        payload = json.loads(
            self.client.get(
                reverse("console:data", args=["enquiries"]), {"length": "100000"}
            ).content
        )
        self.assertLessEqual(len(payload["data"]), 200)

    def test_bad_paging_is_rejected(self):
        response = self.client.get(
            reverse("console:data", args=["enquiries"]), {"start": "abc"}
        )
        self.assertEqual(response.status_code, 400)


# --- Writing ----------------------------------------------------------------

class PublishSwitchTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.editor = make_user("editor")
        cls.enquiry = Enquiry.objects.create(
            name="Nasrin", email="nasrin@example.test", subject="general",
            message="A question about stoves.",
        )

    def test_the_switch_marks_an_enquiry_answered_and_logs_it(self):
        self.client.force_login(self.editor)
        response = self.client.post(
            reverse("console:publish", args=["enquiries", self.enquiry.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.enquiry.refresh_from_db()
        self.assertTrue(self.enquiry.handled)

        entry = AuditEntry.objects.filter(action=AuditEntry.PUBLISH).first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.module, "enquiries")
        self.assertEqual(entry.changes["handled"], {"from": False, "to": True})

    def test_the_switch_flips_back(self):
        self.enquiry.handled = True
        self.enquiry.save()
        self.client.force_login(self.editor)
        self.client.post(reverse("console:publish", args=["enquiries", self.enquiry.pk]))
        self.enquiry.refresh_from_db()
        self.assertFalse(self.enquiry.handled)
        self.assertTrue(AuditEntry.objects.filter(action=AuditEntry.UNPUBLISH).exists())

    def test_the_switch_is_post_only(self):
        self.client.force_login(self.editor)
        response = self.client.get(
            reverse("console:publish", args=["enquiries", self.enquiry.pk])
        )
        self.assertEqual(response.status_code, 405)

    def test_a_reader_cannot_use_the_switch(self):
        self.client.force_login(make_user("reader", roles.VIEWER))
        response = self.client.post(
            reverse("console:publish", args=["enquiries", self.enquiry.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.enquiry.refresh_from_db()
        self.assertFalse(self.enquiry.handled)

    def test_a_module_with_nothing_to_publish_answers_404(self):
        self.client.force_login(make_user("boss", roles.ADMINISTRATOR))
        response = self.client.post(
            reverse("console:publish", args=["staff", self.editor.pk])
        )
        self.assertEqual(response.status_code, 403)


class StaffModuleTests(TestCase):
    """The one module Phase 1 can write, so it is where the form stack is proved."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = make_user("boss", roles.ADMINISTRATOR)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_the_create_form_renders(self):
        response = self.client.get(registry.get("staff").create_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Password again")

    def test_creating_an_account_sets_its_role_and_logs_it(self):
        response = self.client.post(registry.get("staff").create_url(), {
            "username": "shamima",
            "email": "shamima@example.test",
            "first_name": "Shamima",
            "last_name": "Akter",
            "password1": "Console-pw-4417",
            "password2": "Console-pw-4417",
            "role": str(roles.PUBLISHER),
            "is_active": "on",
        })
        self.assertEqual(response.status_code, 302)

        made = User.objects.get(username="shamima")
        self.assertTrue(made.is_staff)
        self.assertEqual(roles.rank_of(made), roles.PUBLISHER)
        self.assertTrue(made.check_password("Console-pw-4417"))

        entry = AuditEntry.objects.filter(action=AuditEntry.CREATE).first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.module, "staff")

    def test_a_weak_password_is_refused(self):
        response = self.client.post(registry.get("staff").create_url(), {
            "username": "weak", "email": "weak@example.test",
            "password1": "password", "password2": "password",
            "role": str(roles.EDITOR), "is_active": "on",
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username="weak").exists())

    def test_mismatched_passwords_are_refused(self):
        response = self.client.post(registry.get("staff").create_url(), {
            "username": "mismatch", "email": "m@example.test",
            "password1": "Console-pw-4417", "password2": "Console-pw-4418",
            "role": str(roles.EDITOR), "is_active": "on",
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username="mismatch").exists())

    def test_changing_a_role_moves_the_account_between_groups(self):
        target = make_user("mover", roles.EDITOR)
        response = self.client.post(registry.get("staff").edit_url(target.pk), {
            "username": "mover", "email": "mover@example.test",
            "first_name": "", "last_name": "",
            "role": str(roles.PUBLISHER), "is_active": "on",
        })
        self.assertEqual(response.status_code, 302)
        target.refresh_from_db()
        self.assertEqual(roles.rank_of(target), roles.PUBLISHER)
        self.assertEqual(
            target.groups.filter(name__in=roles.GROUP_RANKS).count(), 1,
            "an account must hold exactly one role group",
        )

    def test_the_change_is_logged_with_a_diff(self):
        target = make_user("tracked", roles.EDITOR)
        self.client.post(registry.get("staff").edit_url(target.pk), {
            "username": "tracked", "email": "new@example.test",
            "first_name": "New", "last_name": "",
            "role": str(roles.EDITOR), "is_active": "on",
        })
        entry = AuditEntry.objects.filter(action=AuditEntry.UPDATE).first()
        self.assertIsNotNone(entry)
        self.assertIn("email", entry.changes)
        self.assertEqual(entry.changes["email"]["to"], "new@example.test")

    def test_an_administrator_can_set_someone_elses_password(self):
        target = make_user("forgetful", roles.EDITOR)
        response = self.client.post(
            reverse("console:staff_password", args=[target.pk]),
            {"new_password1": "Console-pw-9931", "new_password2": "Console-pw-9931"},
        )
        self.assertEqual(response.status_code, 302)
        target.refresh_from_db()
        self.assertTrue(target.check_password("Console-pw-9931"))

    def test_an_editor_cannot_set_anyone_elses_password(self):
        target = make_user("target", roles.EDITOR)
        self.client.force_login(make_user("editor", roles.EDITOR))
        response = self.client.post(
            reverse("console:staff_password", args=[target.pk]),
            {"new_password1": "Console-pw-9931", "new_password2": "Console-pw-9931"},
        )
        self.assertEqual(response.status_code, 403)
        target.refresh_from_db()
        self.assertFalse(target.check_password("Console-pw-9931"))

    def test_deleting_an_account_asks_first(self):
        target = make_user("goner", roles.EDITOR)
        response = self.client.get(registry.get("staff").delete_url(target.pk))
        self.assertContains(response, "cannot be undone")
        self.assertTrue(User.objects.filter(pk=target.pk).exists())

    def test_deleting_an_account_on_post_removes_it_and_logs_it(self):
        target = make_user("goner", roles.EDITOR)
        response = self.client.post(registry.get("staff").delete_url(target.pk))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(pk=target.pk).exists())
        self.assertTrue(AuditEntry.objects.filter(action=AuditEntry.DELETE).exists())

    def test_the_activity_log_survives_the_account_that_made_it(self):
        target = make_user("ghost", roles.EDITOR)
        self.client.force_login(target)
        self.client.post(reverse("console:logout"))
        self.client.force_login(self.admin)
        self.client.post(registry.get("staff").delete_url(target.pk))

        entry = AuditEntry.objects.filter(actor_label="ghost").first()
        self.assertIsNotNone(entry)
        self.assertIsNone(entry.actor)
        self.assertEqual(entry.actor_label, "ghost")


class ReorderTests(TestCase):
    """
    No module is drag-ordered yet — the first ones arrive with the content
    models in Phase 3 — so these pin down the refusals, which is where the
    endpoint can do harm.
    """

    def setUp(self):
        self.admin = make_user("boss", roles.ADMINISTRATOR)
        self.client.force_login(self.admin)

    def post_order(self, slug, payload):
        return self.client.post(
            reverse("console:reorder", args=[slug]),
            data=payload, content_type="application/json",
        )

    def test_a_module_without_an_order_field_refuses_to_reorder(self):
        response = self.post_order("staff", json.dumps({"ids": [self.admin.pk]}))
        self.assertEqual(response.status_code, 404)

    def test_a_read_only_module_cannot_be_reordered(self):
        response = self.post_order("enquiries", json.dumps({"ids": [1]}))
        self.assertEqual(response.status_code, 403)

    def test_a_body_that_is_not_json_is_rejected(self):
        from unittest import mock
        with mock.patch.object(registry.get("staff"), "order_field", "id"):
            response = self.post_order("staff", "not json at all")
        self.assertEqual(response.status_code, 400)

    def test_an_order_naming_rows_that_do_not_exist_is_rejected(self):
        from unittest import mock
        with mock.patch.object(registry.get("staff"), "order_field", "id"):
            response = self.post_order("staff", json.dumps({"ids": [self.admin.pk, 999999]}))
        self.assertEqual(response.status_code, 400)

    def test_reordering_is_post_only(self):
        response = self.client.get(reverse("console:reorder", args=["staff"]))
        self.assertEqual(response.status_code, 405)


# --- The audit log ----------------------------------------------------------

class AuditTests(TestCase):

    def test_a_password_value_is_never_written_to_the_log(self):
        self.client.force_login(make_user("boss", roles.ADMINISTRATOR))
        secret = "Console-pw-7788"
        self.client.post(registry.get("staff").create_url(), {
            "username": "logged", "email": "logged@example.test",
            "password1": secret, "password2": secret,
            "role": str(roles.EDITOR), "is_active": "on",
        })
        for entry in AuditEntry.objects.all():
            self.assertNotIn(secret, json.dumps(entry.changes))
            self.assertNotIn(secret, entry.note)

    def test_a_failed_log_write_never_loses_the_edit(self):
        from unittest import mock
        from . import audit

        self.client.force_login(make_user("boss", roles.ADMINISTRATOR))
        with mock.patch.object(
            audit.AuditEntry.objects, "create", side_effect=RuntimeError("database gone")
        ):
            response = self.client.post(registry.get("staff").create_url(), {
                "username": "saved-anyway", "email": "s@example.test",
                "password1": "Console-pw-5512", "password2": "Console-pw-5512",
                "role": str(roles.EDITOR), "is_active": "on",
            })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="saved-anyway").exists())


# --- Security headers and template hygiene ---------------------------------

class ConsoleSecurityTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.editor = make_user("editor")

    def test_console_pages_carry_the_console_policy(self):
        self.client.force_login(self.editor)
        response = self.client.get(reverse("console:dashboard"))
        header = response.headers.get(
            "Content-Security-Policy", response.headers.get("Content-Security-Policy-Report-Only", "")
        )
        self.assertEqual(header, settings.CONTENT_SECURITY_POLICY_CONSOLE)
        self.assertIn("blob:", header)

    def test_the_console_policy_still_forbids_inline_script(self):
        self.assertIn("script-src 'self'", settings.CONTENT_SECURITY_POLICY_CONSOLE)
        self.assertNotIn("unsafe-inline", settings.CONTENT_SECURITY_POLICY_CONSOLE.split("style-src")[0])

    def test_the_website_policy_is_unchanged_by_the_console(self):
        response = self.client.get("/")
        header = response.headers.get(
            "Content-Security-Policy", response.headers.get("Content-Security-Policy-Report-Only", "")
        )
        self.assertEqual(header, settings.CONTENT_SECURITY_POLICY)

    def test_the_sign_in_page_is_never_indexed(self):
        self.assertContains(self.client.get(reverse("console:login")), 'name="robots" content="noindex')

    def test_console_pages_are_never_indexed(self):
        self.client.force_login(self.editor)
        for url in (reverse("console:dashboard"), registry.get("enquiries").url()):
            with self.subTest(url=url):
                self.assertContains(self.client.get(url), 'name="robots" content="noindex')


class ConsoleTemplateTests(TestCase):
    """The console holds itself to the same rules as the public templates."""

    def templates(self):
        return sorted((settings.BASE_DIR / "templates" / "console").rglob("*.html"))

    def test_there_are_console_templates_to_check(self):
        self.assertGreater(len(self.templates()), 5)

    def test_no_console_template_has_an_inline_style_attribute(self):
        culprits = [
            path.name for path in self.templates()
            if re.search(r"\sstyle\s*=\s*[\"']", path.read_text(encoding="utf-8"))
        ]
        self.assertEqual(culprits, [], "inline style attributes break the console CSP")

    def test_no_console_template_has_an_inline_script_or_handler(self):
        bad = []
        for path in self.templates():
            text = path.read_text(encoding="utf-8")
            if re.search(r"<script(?![^>]*\ssrc=)", text):
                bad.append(f"{path.name}: inline <script>")
            if re.search(r"\son[a-z]+\s*=\s*[\"']", text):
                bad.append(f"{path.name}: on*= handler")
        self.assertEqual(bad, [])

    def test_no_console_template_has_a_byte_order_mark(self):
        import codecs
        culprits = [p.name for p in self.templates() if p.read_bytes()[:3] == codecs.BOM_UTF8]
        self.assertEqual(culprits, [])

    def test_every_static_file_the_console_asks_for_exists(self):
        editor = make_user("editor", roles.ADMINISTRATOR)
        self.client.force_login(editor)
        static_dir = settings.STATICFILES_DIRS[0]
        missing = set()
        urls = [reverse("console:login"), reverse("console:dashboard")]
        urls += [module.url() for module in registry.all()]

        for url in urls:
            body = self.client.get(url).content.decode()
            for ref in re.findall(r'(?:src|href)="([^"]+)"', body):
                if ref.startswith(settings.STATIC_URL):
                    rel = ref[len(settings.STATIC_URL):]
                    if not (static_dir / rel).is_file():
                        missing.add(rel)
        self.assertEqual(missing, set())


# --- The registry itself ----------------------------------------------------

class RegistryTests(TestCase):

    def test_every_module_can_build_its_own_urls(self):
        for module in registry.all():
            with self.subTest(module=module.slug):
                self.assertTrue(module.url().startswith(CONSOLE))
                self.assertIn(str(module.slug), module.url())

    def test_every_writable_module_declares_a_form_or_its_fields(self):
        """A console form never falls back to every field on the model."""
        for module in registry.all():
            if module.readonly:
                continue
            with self.subTest(module=module.slug):
                self.assertTrue(
                    module.form_class or module.form_fields,
                    f"{module.slug} would expose every model field",
                )

    def test_every_column_can_be_read_off_a_row(self):
        enquiry = Enquiry.objects.create(
            name="Column Test", email="c@example.test", subject="general", message="Hello.",
        )
        module = registry.get("enquiries")
        cells = module.row(enquiry)
        self.assertEqual(len(cells), len(module.columns))
        self.assertTrue(all(isinstance(cell.text, str) for cell in cells))

    def test_a_blank_choice_shows_a_dash_rather_than_an_empty_cell(self):
        enquiry = Enquiry.objects.create(
            name="No Type", email="n@example.test", subject="general",
            enquiry_type="", message="Hello.",
        )
        module = registry.get("enquiries")
        cell = module.cell(enquiry, next(c for c in module.columns if c.name == "enquiry_type"))
        self.assertEqual(cell.text, "—")

    def test_a_long_value_is_truncated(self):
        enquiry = Enquiry.objects.create(
            name="Chatty", email="long@example.test", subject="general",
            message="x" * 500,
        )
        module = registry.get("enquiries")
        column = next(c for c in module.columns if c.name == "message")
        self.assertLessEqual(len(module.cell(enquiry, column).text), column.truncate + 1)

    def test_registering_the_same_slug_twice_is_refused(self):
        from .registry import Module
        with self.assertRaises(ValueError):
            registry.register(Module(slug="enquiries", model=Enquiry))

    def test_the_nav_groups_in_a_fixed_order(self):
        admin = make_user("boss", roles.ADMINISTRATOR)
        names = [group["name"] for group in registry.nav(admin)]
        self.assertEqual(names, sorted(names, key=lambda n: registry.GROUP_ORDER.index(n)))


class SidebarPagesTests(TestCase):
    """
    Green Spark asked for the menu to mirror the website: a page, and its
    bands under it. The list is built from the Page table, so a page added or
    taken offline changes the menu without anyone editing a template.
    """

    def setUp(self):
        self.client.force_login(make_user("nav-admin", rank=roles.ADMINISTRATOR))

    def body(self):
        return self.client.get(reverse("console:dashboard")).content.decode()

    def test_live_pages_are_listed(self):
        body = self.body()
        page = Page.objects.exclude(status="offline").filter(sections__isnull=False).first()
        self.assertIsNotNone(page)
        self.assertIn(page.label, body)
        self.assertIn(f"on_page={page.name}", body)

    def test_offline_pages_are_not_listed(self):
        """An offline page answers 404; there is nothing to go and look at."""
        page = Page.objects.filter(status="offline").first()
        if page is None:
            self.skipTest("nothing offline to check")
        self.assertNotIn(f"on_page={page.name}", self.body())

    def test_a_page_with_no_sections_is_not_a_dead_end(self):
        page = Page.objects.exclude(status="offline").first()
        page.sections.all().delete()
        self.assertNotIn(f"on_page={page.name}", self.body())

    def test_the_menu_carries_no_inline_style_or_handler(self):
        """The console runs under the site's CSP, like every other screen."""
        body = self.body()
        self.assertNotIn(" style=", body)
        self.assertNotIn("onclick=", body)
