from django import forms
from django.conf import settings
from django_tenants.test.cases import TenantTestCase

from taxonomy.models import TaxonomyModelRouter
from taxonomy.sources.custom.forms import (
    AddCustomTaxonLocaleForm,
    ManageCustomTaxonForm,
    MoveCustomTaxonForm,
)


class WithCustomTaxa:

    def create_custom_taxon(self, taxon_latname, taxon_author=None, parent=None, rank=None):
        extra_fields = {"parent": parent}
        if not parent:
            extra_fields["is_root_taxon"] = True
        if rank:
            extra_fields["rank"] = rank
        return self.models.TaxonTreeModel.objects.create(taxon_latname, taxon_author, **extra_fields)


class TestManageCustomTaxonForm(WithCustomTaxa, TenantTestCase):

    def setUp(self):
        super().setUp()
        self.models = TaxonomyModelRouter("taxonomy.sources.custom")
        self.root_taxon = self.create_custom_taxon("Root Taxon", "Linnaeus")

    def test_init_adds_other_locale_fields_and_orders_them_after_primary_name(self):
        de_locale = self.models.TaxonLocaleModel.objects.create(
            self.root_taxon, "Deutscher Name", "de", preferred=False
        )
        fr_locale = self.models.TaxonLocaleModel.objects.create(
            self.root_taxon, "Nom francais", "fr", preferred=False
        )
        self.models.TaxonLocaleModel.objects.create(
            self.root_taxon, "English Name", "en", preferred=True
        )

        form = ManageCustomTaxonForm(initial={"name_uuid": self.root_taxon.name_uuid, "input_language": "en"})

        de_field = f"name_de_{de_locale.id}"
        fr_field = f"name_fr_{fr_locale.id}"

        self.assertIn(de_field, form.fields)
        self.assertIn(fr_field, form.fields)
        self.assertNotIn("name_en", form.fields)

        self.assertEqual(form.fields[de_field].initial, "Deutscher Name")
        self.assertEqual(form.fields[fr_field].initial, "Nom francais")

        self.assertIn(de_field, form.localizeable_fields)
        self.assertIn(fr_field, form.localizeable_fields)

        field_order = list(form.fields.keys())
        name_index = field_order.index("name")
        self.assertIn(field_order[name_index + 1], [de_field, fr_field])
        self.assertIn(field_order[name_index + 2], [de_field, fr_field])

    def test_init_without_initial_taxon_keeps_only_default_localizeable_field(self):
        form = ManageCustomTaxonForm()

        self.assertEqual(form.localizeable_fields, ["name"])

    def test_clean_raises_on_existing_language_independent_taxon(self):
        self.create_custom_taxon("Duplicate Taxon", "Miller")

        form = ManageCustomTaxonForm()
        form.cleaned_data = {
            "latname": "duplicate taxon",
            "author": "miller",
            "name_uuid": None,
        }

        with self.assertRaises(forms.ValidationError):
            form.clean()

    def test_clean_allows_unique_language_independent_taxon(self):
        form = ManageCustomTaxonForm()
        form.cleaned_data = {
            "latname": "Unique Taxon",
            "author": "Tester",
            "name_uuid": None,
        }

        cleaned_data = form.clean()
        self.assertEqual(cleaned_data, form.cleaned_data)


class TestAddCustomTaxonLocaleForm(TenantTestCase):

    def test_valid_data(self):
        language = settings.LANGUAGES[0][0]
        form = AddCustomTaxonLocaleForm(
            data={
                "name_uuid": "b795d838-7388-4a8b-b38b-ef8a6875ec11",
                "language": language,
                "name": "Common Name",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_name_is_invalid(self):
        language = settings.LANGUAGES[0][0]
        form = AddCustomTaxonLocaleForm(
            data={
                "name_uuid": "b795d838-7388-4a8b-b38b-ef8a6875ec11",
                "language": language,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_missing_name_uuid_is_invalid(self):
        language = settings.LANGUAGES[0][0]
        form = AddCustomTaxonLocaleForm(
            data={
                "language": language,
                "name": "Common Name",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("name_uuid", form.errors)


class TestMoveCustomTaxonForm(WithCustomTaxa, TenantTestCase):

    def setUp(self):
        super().setUp()
        self.models = TaxonomyModelRouter("taxonomy.sources.custom")

        self.root_taxon = self.create_custom_taxon("Root")
        self.taxon_to_move = self.create_custom_taxon("Taxon To Move", parent=self.root_taxon)
        self.descendant = self.create_custom_taxon("Descendant", parent=self.taxon_to_move)
        self.safe_parent = self.create_custom_taxon("Safe Parent", parent=self.root_taxon)

    def test_clean_disallows_moving_into_descendant(self):
        form = MoveCustomTaxonForm(self.taxon_to_move)
        form.cleaned_data = {
            "new_parent_taxon": self.descendant,
            "move_to_root": False,
        }

        with self.assertRaises(forms.ValidationError):
            form.clean()

    def test_clean_disallows_selecting_parent_and_move_to_root(self):
        form = MoveCustomTaxonForm(self.taxon_to_move)
        form.cleaned_data = {
            "new_parent_taxon": self.safe_parent,
            "move_to_root": True,
        }

        with self.assertRaises(forms.ValidationError):
            form.clean()

    def test_clean_allows_move_to_root_only(self):
        form = MoveCustomTaxonForm(self.taxon_to_move)
        form.cleaned_data = {
            "new_parent_taxon": None,
            "move_to_root": True,
        }

        cleaned_data = form.clean()

        self.assertTrue(cleaned_data["move_to_root"])
        self.assertIsNone(cleaned_data["new_parent_taxon"])

    def test_clean_allows_safe_new_parent(self):
        form = MoveCustomTaxonForm(self.taxon_to_move)
        form.cleaned_data = {
            "new_parent_taxon": self.safe_parent,
            "move_to_root": False,
        }

        cleaned_data = form.clean()

        self.assertEqual(cleaned_data["new_parent_taxon"], self.safe_parent)
        self.assertFalse(cleaned_data["move_to_root"])
