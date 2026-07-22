from django_tenants.test.cases import TenantTestCase

from app_kit.features.object_classes.forms import (
	ObjectClassForm,
	AddObjectClassTaxonForm,
	AddObjectClassLinkForm,
)
from app_kit.features.object_classes.models import ObjectClass, ObjectClassTaxon
from app_kit.features.object_classes.tests.test_models import WithObjectClasses
from app_kit.tests.common import test_settings

from taxonomy.lazy import LazyTaxon
from taxonomy.models import TaxonomyModelRouter


class TestObjectClassForm(WithObjectClasses, TenantTestCase):

	def build_post_data(self, name, description=None, scientific_name=None):
		post_data = {
			'name': name,
			'scientific_name': scientific_name or name.lower().replace(' ', '_'),
			'input_language': 'en',
		}

		if description is not None:
			post_data['description'] = description

		return post_data

	@test_settings
	def test_form(self):
		post_data = self.build_post_data('Tree', 'Test object class description')

		form = ObjectClassForm(data=post_data, object_classes=self.object_classes)
		self.assertTrue(form.is_valid(), form.errors)

		invalid_without_name = post_data.copy()
		del invalid_without_name['name']

		form_without_name = ObjectClassForm(
			data=invalid_without_name,
			object_classes=self.object_classes,
		)
		self.assertFalse(form_without_name.is_valid())
		self.assertIn('name', form_without_name.errors)

	@test_settings
	def test_save(self):
		post_data = self.build_post_data('Tree', 'Test object class description')

		form = ObjectClassForm(data=post_data, object_classes=self.object_classes)

		self.assertTrue(form.is_valid(), form.errors)

		object_class = form.save()

		self.assertEqual(object_class.object_classes, self.object_classes)
		self.assertEqual(object_class.name, post_data['name'])
		self.assertEqual(object_class.scientific_name, post_data['scientific_name'])
		self.assertEqual(object_class.description, post_data['description'])

	@test_settings
	def test_update(self):
		object_class = self.create_object_class('Tree')
		original_scientific_name = object_class.scientific_name

		post_data = self.build_post_data('Shrub', 'Updated description', scientific_name=original_scientific_name)

		form = ObjectClassForm(
			data=post_data,
			instance=object_class,
			object_classes=self.object_classes,
		)

		self.assertTrue(form.is_valid(), form.errors)

		updated_object_class = form.save()

		self.assertEqual(updated_object_class.pk, object_class.pk)
		self.assertEqual(updated_object_class.object_classes, self.object_classes)
		self.assertEqual(updated_object_class.name, post_data['name'])
		self.assertEqual(updated_object_class.scientific_name, original_scientific_name)
		self.assertEqual(updated_object_class.description, post_data['description'])


	@test_settings
	def test_clean_scientific_name_existing_entry(self):
		self.create_object_class('Tree')

		post_data = self.build_post_data('Shrub', scientific_name='tree')

		form = ObjectClassForm(data=post_data, object_classes=self.object_classes)

		self.assertFalse(form.is_valid())
		self.assertIn('scientific_name', form.errors)
		self.assertEqual(ObjectClass.objects.filter(object_classes=self.object_classes).count(), 1)

	@test_settings
	def test_clean_name_allows_existing_instance_name(self):
		object_class = self.create_object_class('Tree')

		form = ObjectClassForm(
			data=self.build_post_data('Tree', 'Updated description', scientific_name=object_class.scientific_name),
			instance=object_class,
			object_classes=self.object_classes,
		)

		self.assertTrue(form.is_valid(), form.errors)


class TestAddObjectClassTaxonForm(WithObjectClasses, TenantTestCase):

	def get_lazy_taxon(self, taxon_latname):
		models = TaxonomyModelRouter('taxonomy.sources.col')
		taxon_db = models.TaxonTreeModel.objects.get(taxon_latname=taxon_latname)
		return LazyTaxon(instance=taxon_db)

	def build_taxon_post_data(self, taxon):
		return {
			'taxon_0': taxon.taxon_source,
			'taxon_1': taxon.taxon_latname,
			'taxon_2': taxon.taxon_author or '',
			'taxon_3': str(taxon.name_uuid),
			'taxon_4': taxon.taxon_nuid or '',
		}

	@test_settings
	def test_valid_new_taxon(self):
		object_class = self.create_object_class('Trees')
		taxon = self.get_lazy_taxon('Quercus')

		form = AddObjectClassTaxonForm(
			data=self.build_taxon_post_data(taxon),
			object_class=object_class,
			taxon_search_url='/search_taxon/',
		)

		self.assertTrue(form.is_valid(), form.errors)

	@test_settings
	def test_duplicate_taxon_invalid(self):
		object_class = self.create_object_class('Lizards')
		taxon = self.get_lazy_taxon('Lacerta agilis')

		taxon_mapping = ObjectClassTaxon(object_class=object_class)
		taxon_mapping.set_taxon(taxon)
		taxon_mapping.save()

		form = AddObjectClassTaxonForm(
			data=self.build_taxon_post_data(taxon),
			object_class=object_class,
			taxon_search_url='/search_taxon/',
		)

		self.assertFalse(form.is_valid())
		self.assertIn('taxon', form.errors)


class TestAddObjectClassLinkForm(WithObjectClasses, TenantTestCase):

	def get_lazy_taxon(self, taxon_latname):
		models = TaxonomyModelRouter('taxonomy.sources.col')
		taxon_db = models.TaxonTreeModel.objects.get(taxon_latname=taxon_latname)
		return LazyTaxon(instance=taxon_db)

	@test_settings
	def test_queryset_filters_object_classes_by_matching_taxon(self):
		target_taxon = self.get_lazy_taxon('Quercus')
		non_matching_taxon = self.get_lazy_taxon('Lacerta agilis')

		matching_object_class = self.create_object_class('Tree class')
		non_matching_object_class = self.create_object_class('Lizard class')

		matching_mapping = ObjectClassTaxon(object_class=matching_object_class)
		matching_mapping.set_taxon(target_taxon)
		matching_mapping.save()

		non_matching_mapping = ObjectClassTaxon(object_class=non_matching_object_class)
		non_matching_mapping.set_taxon(non_matching_taxon)
		non_matching_mapping.save()

		form = AddObjectClassLinkForm(
			data={'object_class': matching_object_class.pk},
			object_classes=self.object_classes,
			taxon=target_taxon,
		)

		queryset = form.fields['object_class'].queryset
		self.assertIn(matching_object_class, queryset)
		self.assertNotIn(non_matching_object_class, queryset)
		self.assertTrue(form.is_valid(), form.errors)
