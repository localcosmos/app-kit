from django_tenants.test.cases import TenantTestCase

from app_kit.features.object_classes.forms import ObjectClassForm
from app_kit.features.object_classes.models import ObjectClass
from app_kit.features.object_classes.tests.test_models import WithObjectClasses
from app_kit.tests.common import test_settings


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
