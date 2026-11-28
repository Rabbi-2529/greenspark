"""
Every console screen opens, for every module.

The registry tests check that a module *could* build its URLs and that it does
not expose every field on its model. Nothing checked that the page it produces
actually renders -- which matters more with every module added, and Phase 5
added thirteen of them, including six page singletons whose forms are grouped
into fieldsets and one list whose columns are model properties rather than
fields.

So: sign in as an administrator, open every list, every create form and the
edit form of a real row, and insist on 200 with no exception. A column that
cannot be read, a fieldset naming a field that is not on the form, a list
ordering by a lookup that does not exist -- all of those are a 500 here and a
green test suite otherwise.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from . import roles
from .registry import registry

User = get_user_model()
CONSOLE = "/" + settings.CONSOLE_URL


class EveryScreenTests(TestCase):
    """An administrator can open every screen the console offers."""

    @classmethod
    def setUpTestData(cls):
        cls.password = "Pw-console-7781"
        cls.admin = User.objects.create_superuser(
            username="screens", email="screens@example.test", password=cls.password,
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_the_dashboard_opens(self):
        self.assertEqual(
            self.client.get(reverse("console:dashboard")).status_code, 200,
        )

    def test_every_list_opens(self):
        for module in registry.all():
            with self.subTest(module=module.slug):
                response = self.client.get(module.url())
                # A singleton's "list" is its form, which redirects to the row.
                self.assertIn(response.status_code, (200, 302), module.slug)
                if response.status_code == 302:
                    self.assertEqual(
                        self.client.get(response["Location"]).status_code, 200,
                    )

    def test_every_create_form_opens(self):
        for module in registry.all():
            if module.readonly or not module.can_create:
                continue
            with self.subTest(module=module.slug):
                self.assertEqual(
                    self.client.get(module.create_url()).status_code, 200, module.slug,
                )

    def test_every_edit_form_opens_on_a_real_row(self):
        for module in registry.all():
            row = module.model.objects.first()
            if row is None:
                # Nothing shipped in this table; the create form above covers it.
                continue
            with self.subTest(module=module.slug):
                self.assertEqual(
                    self.client.get(module.edit_url(row.pk)).status_code, 200, module.slug,
                )

    def test_every_list_can_be_searched_sorted_and_filtered(self):
        for module in registry.all():
            with self.subTest(module=module.slug):
                url = module.url()
                if module.search_fields:
                    self.assertIn(
                        self.client.get(url, {"q": "green"}).status_code, (200, 302),
                    )
                for column in module.columns:
                    if not column.sortable:
                        continue
                    self.assertIn(
                        self.client.get(
                            url, {"sort": column.sort_key, "dir": "desc"}
                        ).status_code,
                        (200, 302),
                        f"{module.slug} sorted by {column.name}",
                    )
                for filt in module.filters:
                    for value, _label in filt.options():
                        self.assertIn(
                            self.client.get(url, {filt.name: value}).status_code,
                            (200, 302),
                            f"{module.slug} filtered by {filt.name}={value}",
                        )

    def test_every_column_can_be_read_off_a_real_row(self):
        for module in registry.all():
            row = module.model.objects.first()
            if row is None:
                continue
            with self.subTest(module=module.slug):
                cells = module.row(row)
                self.assertEqual(len(cells), len(module.columns), module.slug)
                for cell in cells:
                    self.assertIsInstance(cell.text, str)


class EditorRankTests(TestCase):
    """An editor sees what an editor should see, and no more."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth.models import Group

        cls.password = "Pw-console-7781"
        cls.editor = User.objects.create_user(
            username="ed", email="ed@example.test", password=cls.password,
        )
        cls.editor.is_staff = True
        cls.editor.save()
        group, _ = Group.objects.get_or_create(name=roles.EDITOR_GROUP)
        cls.editor.groups.add(group)

    def setUp(self):
        self.client.force_login(self.editor)

    def test_an_editor_can_read_the_policy_but_not_change_it(self):
        """
        A privacy policy is a legal statement about what Green Spark does with
        people's information, so it ranks with the impact figures: a publisher
        changes it, an editor only reads it.

        The list opens; the form answers 403. That is how the console has
        behaved since Phase 1 for every module whose edit rank is above its
        view rank -- the impact figures and all four settings records -- so
        this test documents it rather than asking Phase 5 to change it. It is
        a rough edge: an editor clicking a row in a list they are allowed to
        see gets a refusal instead of a read-only view of it. Noted in
        CMS-PLAN.md for Phase 9, which is where editorial safety lives.
        """
        module = registry.get("policy-sections")
        row = module.model.objects.first()
        self.assertEqual(self.client.get(module.url()).status_code, 200)
        self.assertEqual(self.client.get(module.edit_url(row.pk)).status_code, 403)

    def test_the_impact_figures_behave_the_same_way(self):
        module = registry.get("counters")
        row = module.model.objects.first()
        self.assertEqual(self.client.get(module.url()).status_code, 200)
        self.assertEqual(self.client.get(module.edit_url(row.pk)).status_code, 403)

    def test_an_editor_can_open_an_ordinary_content_form(self):
        module = registry.get("faq-topics")
        row = module.model.objects.first()
        response = self.client.get(module.edit_url(row.pk))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["may_edit"])
