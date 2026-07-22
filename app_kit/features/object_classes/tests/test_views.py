from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django_tenants.test.cases import TenantTestCase

from app_kit.features.object_classes.models import ObjectClass, ObjectClassTaxon
from app_kit.features.object_classes.tests.test_models import WithObjectClasses
from app_kit.features.object_classes.views import SetObjectClassLink
from app_kit.features.taxon_profiles.models import TaxonProfiles, TaxonProfile
from app_kit.models import MetaAppGenericContent
from app_kit.tests.common import test_settings
from app_kit.tests.mixins import (
	ViewTestMixin,
	WithAjaxAdminOnly,
	WithLoggedInUser,
	WithTenantClient,
	WithUser,
)

from taxonomy.lazy import LazyTaxon
from taxonomy.models import TaxonomyModelRouter


AJAX_KWARGS = {
	'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest',
}


class WithObjectClassesViewData(WithObjectClasses):

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


class TestGetObjectClasses(
	WithObjectClassesViewData,
	ViewTestMixin,
	WithAjaxAdminOnly,
	WithLoggedInUser,
	WithUser,
	WithTenantClient,
	TenantTestCase,
):

	url_name = 'get_object_classes'

	def get_url_kwargs(self):
		return {
			'meta_app_id': self.meta_app.id,
			'object_classes_id': self.object_classes.id,
		}

	@test_settings
	def test_get_contains_object_class_list(self):
		self.make_user_tenant_admin(self.user, self.tenant)
		self.create_object_class('Tree class')

		response = self.tenant_client.get(self.get_url(), **AJAX_KWARGS)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.context['object_classes'], self.object_classes)
		self.assertEqual(response.context['generic_content'], self.object_classes)
		self.assertEqual(response.context['object_class_list'].count(), 1)


class TestManageObjectClassCreate(
	WithObjectClassesViewData,
	ViewTestMixin,
	WithAjaxAdminOnly,
	WithLoggedInUser,
	WithUser,
	WithTenantClient,
	TenantTestCase,
):

	url_name = 'create_object_class'

	def get_url_kwargs(self):
		return {
			'meta_app_id': self.meta_app.id,
			'object_classes_id': self.object_classes.id,
		}

	@test_settings
	def test_post_creates_object_class(self):
		self.make_user_tenant_admin(self.user, self.tenant)

		post_data = {
			'name': 'Tree class',
			'scientific_name': 'tree_class',
			'description': 'A class for trees',
			'input_language': self.meta_app.primary_language,
		}

		response = self.tenant_client.post(self.get_url(), data=post_data, **AJAX_KWARGS)
		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.context['success'])

		object_class = ObjectClass.objects.get(
			object_classes=self.object_classes,
			scientific_name='tree_class',
		)
		self.assertEqual(object_class.name, 'Tree class')


class TestManageObjectClassEdit(
	WithObjectClassesViewData,
	ViewTestMixin,
	WithAjaxAdminOnly,
	WithLoggedInUser,
	WithUser,
	WithTenantClient,
	TenantTestCase,
):

	url_name = 'edit_object_class'

	def before_test_dispatch(self):
		self.object_class = self.create_object_class('Old class', description='Old description')

	def get_url_kwargs(self):
		return {
			'meta_app_id': self.meta_app.id,
			'object_classes_id': self.object_classes.id,
			'object_class_id': self.object_class.id,
		}

	@test_settings
	def test_post_updates_object_class(self):
		self.object_class = self.create_object_class('Old class', description='Old description')
		self.make_user_tenant_admin(self.user, self.tenant)

		post_data = {
			'name': 'Updated class',
			'scientific_name': self.object_class.scientific_name,
			'description': 'Updated description',
			'input_language': self.meta_app.primary_language,
		}

		response = self.tenant_client.post(self.get_url(), data=post_data, **AJAX_KWARGS)
		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.context['success'])

		self.object_class.refresh_from_db()
		self.assertEqual(self.object_class.name, 'Updated class')
		self.assertEqual(self.object_class.description, 'Updated description')


class TestDeleteObjectClass(
	WithObjectClassesViewData,
	ViewTestMixin,
	WithAjaxAdminOnly,
	WithLoggedInUser,
	WithUser,
	WithTenantClient,
	TenantTestCase,
):

	url_name = 'delete_object_class'

	def before_test_dispatch(self):
		self.object_class = self.create_object_class('Delete me')

	def get_url_kwargs(self):
		return {
			'pk': self.object_class.id,
		}

	@test_settings
	def test_post_deletes_object_class(self):
		self.object_class = self.create_object_class('Delete me')
		self.make_user_tenant_admin(self.user, self.tenant)

		response = self.tenant_client.post(self.get_url(), **AJAX_KWARGS)
		self.assertEqual(response.status_code, 200)
		self.assertFalse(ObjectClass.objects.filter(pk=self.object_class.pk).exists())


class TestAddObjectClassTaxon(
	WithObjectClassesViewData,
	ViewTestMixin,
	WithAjaxAdminOnly,
	WithLoggedInUser,
	WithUser,
	WithTenantClient,
	TenantTestCase,
):

	url_name = 'add_object_class_taxon'

	def before_test_dispatch(self):
		self.object_class = self.create_object_class('Tree class')

	def get_url_kwargs(self):
		return {
			'meta_app_id': self.meta_app.id,
			'object_classes_id': self.object_classes.id,
			'object_class_id': self.object_class.id,
		}

	@test_settings
	def test_post_creates_object_class_taxon(self):
		self.object_class = self.create_object_class('Tree class')
		self.make_user_tenant_admin(self.user, self.tenant)

		taxon = self.get_lazy_taxon('Quercus')
		post_data = self.build_taxon_post_data(taxon)

		response = self.tenant_client.post(self.get_url(), data=post_data, **AJAX_KWARGS)
		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.context['success'])

		taxon_mapping = ObjectClassTaxon.objects.get(object_class=self.object_class)
		self.assertEqual(taxon_mapping.name_uuid, taxon.name_uuid)


class TestDeleteObjectClassTaxon(
	WithObjectClassesViewData,
	ViewTestMixin,
	WithAjaxAdminOnly,
	WithLoggedInUser,
	WithUser,
	WithTenantClient,
	TenantTestCase,
):

	url_name = 'delete_object_class_taxon'

	def before_test_dispatch(self):
		object_class = self.create_object_class('Tree class')
		taxon = self.get_lazy_taxon('Quercus')
		self.taxon_mapping = ObjectClassTaxon(object_class=object_class)
		self.taxon_mapping.set_taxon(taxon)
		self.taxon_mapping.save()

	def get_url_kwargs(self):
		return {
			'pk': self.taxon_mapping.id,
		}

	@test_settings
	def test_post_deletes_object_class_taxon(self):
		object_class = self.create_object_class('Tree class')
		taxon = self.get_lazy_taxon('Quercus')
		self.taxon_mapping = ObjectClassTaxon(object_class=object_class)
		self.taxon_mapping.set_taxon(taxon)
		self.taxon_mapping.save()
		self.make_user_tenant_admin(self.user, self.tenant)

		response = self.tenant_client.post(self.get_url(), **AJAX_KWARGS)
		self.assertEqual(response.status_code, 200)
		self.assertFalse(ObjectClassTaxon.objects.filter(pk=self.taxon_mapping.pk).exists())


class TestSetObjectClassLink(
	WithObjectClassesViewData,
	ViewTestMixin,
	WithAjaxAdminOnly,
	WithLoggedInUser,
	WithUser,
	WithTenantClient,
	TenantTestCase,
):

	url_name = 'set_object_class_link'
	view_class = SetObjectClassLink

	def setUp(self):
		super().setUp()
		self.taxon = self.get_lazy_taxon('Quercus')
		self.object_class = self.create_object_class('Tree class')

		object_class_taxon = ObjectClassTaxon(object_class=self.object_class)
		object_class_taxon.set_taxon(self.taxon)
		object_class_taxon.save()

		taxon_profiles_content_type = ContentType.objects.get_for_model(TaxonProfiles)
		taxon_profiles_link = MetaAppGenericContent.objects.filter(
			meta_app=self.meta_app,
			content_type=taxon_profiles_content_type,
		).first()
		if taxon_profiles_link is None:
			self.create_generic_content(TaxonProfiles, self.meta_app)
			taxon_profiles_link = MetaAppGenericContent.objects.get(
				meta_app=self.meta_app,
				content_type=taxon_profiles_content_type,
			)

		self.taxon_profiles = taxon_profiles_link.generic_content
		self.taxon_profile = TaxonProfile(
			taxon_profiles=self.taxon_profiles,
			taxon=self.taxon,
		)
		self.taxon_profile.save()

	def get_url_kwargs(self):
		return {
			'meta_app_id': self.meta_app.id,
			'content_type_id': ContentType.objects.get_for_model(TaxonProfile).id,
			'object_id': self.taxon_profile.id,
		}

	@test_settings
	def test_post_sets_object_class_on_linked_instance(self):
		self.make_user_tenant_admin(self.user, self.tenant)

		response = self.tenant_client.post(
			self.get_url(),
			data={'object_class': self.object_class.id},
			**AJAX_KWARGS,
		)
		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.context['success'])

		self.taxon_profile.refresh_from_db()
		self.assertEqual(self.taxon_profile.object_class, self.object_class)

	@test_settings
	def test_set_linked_instance_raises_404_for_invalid_target_model(self):
		invalid_instance = self.create_object_class('Invalid target')
		content_type_id = ContentType.objects.get_for_model(ObjectClass).id

		view = self.get_view(ajax=True)
		invalid_kwargs = {
			'meta_app_id': self.meta_app.id,
			'content_type_id': content_type_id,
			'object_id': invalid_instance.id,
		}

		with self.assertRaises(Http404):
			view.set_linked_instance(**invalid_kwargs)
