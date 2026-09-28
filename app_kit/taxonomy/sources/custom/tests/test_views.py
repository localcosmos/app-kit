'''
    These tests work only with an installed Local Cosmos App Kit
'''
from django.urls import reverse
from django.test import RequestFactory

from django_tenants.test.cases import TenantTestCase
from app_kit.tests.mixins import (WithMetaApp, WithTenantClient, WithUser, WithLoggedInUser, WithAjaxAdminOnly,
                                  ViewTestMixin)

from django.contrib.contenttypes.models import ContentType

from app_kit.tests.common import test_settings

from app_kit.features.taxon_profiles.models import TaxonProfiles, TaxonProfile
from app_kit.models import MetaAppGenericContent

from taxonomy.models import TaxonomyModelRouter
from taxonomy.lazy import LazyTaxon

from taxonomy.sources.custom.views import MoveCustomTaxonTreeEntry, AddCustomTaxonLocale, ManageCustomTaxon

import uuid as uuid_module

AJAX_KWARGS = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}


class TestMoveCustomTaxonTreeEntry(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser,
                                WithMetaApp, WithTenantClient, TenantTestCase):    
    
    url_name = 'move_custom_taxon'
    view_class = MoveCustomTaxonTreeEntry

    def get_url_kwargs(self):
        url_kwargs = {
            'name_uuid' : str(self.taxon_2_1.name_uuid),
        }
        return url_kwargs
    
    def setUp(self):
        extra_fields = {
            'is_root_taxon': True,
        }
        self.root_taxon = self.create_custom_taxon('Root Taxon', parent=None)
        self.taxon_1 = self.create_custom_taxon('Taxon 1', parent=self.root_taxon)
        self.taxon_2 = self.create_custom_taxon('Taxon 2', parent=self.root_taxon)
        self.taxon_2_1 = self.create_custom_taxon('Taxon 2 1', parent=self.taxon_2)
        self.taxon_2_1_1 = self.create_custom_taxon('Taxon 2 1 1', parent=self.taxon_2_1)
        self.taxon_3 = self.create_custom_taxon('Taxon 3', parent=self.root_taxon)
        self.taxon_3_1 = self.create_custom_taxon('Taxon 3 1', parent=self.taxon_3)
        self.taxon_3_2 = self.create_custom_taxon('Taxon 3 2', parent=self.taxon_3)
        self.taxon_3_3 = self.create_custom_taxon('Taxon 3 3', parent=self.taxon_3)
        
        self.taxon_3_2.delete()

        
        super().setUp()


class TestAddCustomTaxonLocale(WithLoggedInUser, WithUser, WithTenantClient, TenantTestCase):

    def setUp(self):
        super().setUp()
        self.taxon = self.create_custom_taxon('Testus taxonus')
        self.language = 'de'

    def create_custom_taxon(self, taxon_latname, parent=None, rank=None):
        extra_fields = {'parent': parent}
        if not parent:
            extra_fields['is_root_taxon'] = True
        if rank:
            extra_fields['rank'] = rank
        models = TaxonomyModelRouter('taxonomy.sources.custom')
        return models.TaxonTreeModel.objects.create(taxon_latname, taxon_latname, **extra_fields)

    def get_url(self):
        return reverse('add_custom_taxon_locale', kwargs={'name_uuid': self.taxon.name_uuid})

    @test_settings
    def test_dispatch_requires_ajax(self):
        url = self.get_url()
        self.make_user_tenant_admin(self.user, self.tenant)

        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 400)

    @test_settings
    def test_dispatch_unknown_taxon_raises_404(self):
        url = reverse('add_custom_taxon_locale', kwargs={
            'name_uuid': uuid_module.uuid4(),
        })
        self.make_user_tenant_admin(self.user, self.tenant)

        with self.assertRaises(Exception):
            self.tenant_client.get(url, **AJAX_KWARGS)

    @test_settings
    def test_get(self):
        url = self.get_url()
        self.make_user_tenant_admin(self.user, self.tenant)

        response = self.tenant_client.get(url, **AJAX_KWARGS)
        self.assertEqual(response.status_code, 200)

    @test_settings
    def test_form_valid_creates_locale(self):
        url = self.get_url()
        self.make_user_tenant_admin(self.user, self.tenant)

        post_data = {
            'name_uuid': str(self.taxon.name_uuid),
            'name': 'Testname',
            'language': self.language,
        }

        response = self.tenant_client.post(url, data=post_data, **AJAX_KWARGS)
        self.assertEqual(response.status_code, 200)

        models = TaxonomyModelRouter('taxonomy.sources.custom')
        locale = models.TaxonLocaleModel.objects.filter(
            taxon=self.taxon, language=self.language,
        ).first()
        self.assertIsNotNone(locale)
        self.assertEqual(locale.name, 'Testname')
        self.assertTrue(locale.preferred)
        self.assertIn('success', response.context)
        self.assertTrue(response.context['success'])

    @test_settings
    def test_form_invalid_missing_name(self):
        url = self.get_url()
        self.make_user_tenant_admin(self.user, self.tenant)

        post_data = {
            'name_uuid': str(self.taxon.name_uuid),
            'language': self.language,
        }

        response = self.tenant_client.post(url, data=post_data, **AJAX_KWARGS)
        self.assertEqual(response.status_code, 200)

        models = TaxonomyModelRouter('taxonomy.sources.custom')
        self.assertFalse(
            models.TaxonLocaleModel.objects.filter(
                taxon_id=str(self.taxon.name_uuid), language=self.language,
            ).exists()
        )
        self.assertFalse(response.context.get('success', False))


class TestManageCustomTaxon(ViewTestMixin, WithLoggedInUser, WithUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'manage_custom_taxon'
    view_class = ManageCustomTaxon

    def setUp(self):
        super().setUp()
        self.root_taxon = self.create_custom_taxon('Root Taxon')
        self.language = 'en'

    def create_custom_taxon(self, taxon_latname, parent=None, rank=None):
        extra_fields = {'parent': parent}
        if not parent:
            extra_fields['is_root_taxon'] = True
        if rank:
            extra_fields['rank'] = rank
        models = TaxonomyModelRouter('taxonomy.sources.custom')
        return models.TaxonTreeModel.objects.create(taxon_latname, taxon_latname, **extra_fields)

    def get_url_kwargs(self):
        return {
            'meta_app_id': self.meta_app.id,
            'name_uuid': self.root_taxon.name_uuid,
            'language': self.language,
        }

    @test_settings
    def test_create_taxon_with_primary_locale(self):
        url = reverse('create_new_custom_root_taxon', kwargs={'meta_app_id': self.meta_app.id, 'language': self.language})
        self.make_user_tenant_admin(self.user, self.tenant)

        post_data = {
            'taxon_latname': 'Animalia',
            'taxon_author': 'Linnaeus',
            'name': 'Animals',
            'input_language': self.language,
            'rank': 'kingdom',
        }

        response = self.tenant_client.post(url, data=post_data, **AJAX_KWARGS)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['success'])
        self.assertTrue(response.context['created'])

        models = TaxonomyModelRouter('taxonomy.sources.custom')
        taxon = models.TaxonTreeModel.objects.get(taxon_latname='Animalia')
        self.assertEqual(taxon.rank, 'kingdom')

        locale = models.TaxonLocaleModel.objects.get(taxon=taxon, language=self.language)
        self.assertEqual(locale.name, 'Animals')
        self.assertTrue(locale.preferred)

    @test_settings
    def test_update_taxon_primary_locale(self):
        models = TaxonomyModelRouter('taxonomy.sources.custom')
        original_locale = models.TaxonLocaleModel.objects.create(
            self.root_taxon, 'Original Name', self.language, preferred=True
        )

        url = self.get_url()
        self.make_user_tenant_admin(self.user, self.tenant)

        post_data = {
            'name_uuid': str(self.root_taxon.name_uuid),
            'taxon_latname': 'Root Taxon Updated',
            'taxon_author': 'Author',
            'name': 'Updated Name',
            'input_language': self.language,
            'rank': 'kingdom',
        }

        response = self.tenant_client.post(url, data=post_data, **AJAX_KWARGS)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['success'])
        self.assertFalse(response.context.get('created', False))

        self.root_taxon.refresh_from_db()
        self.assertEqual(self.root_taxon.taxon_latname, 'Root Taxon Updated')

        locale = models.TaxonLocaleModel.objects.get(id=original_locale.id)
        self.assertEqual(locale.name, 'Updated Name')

    @test_settings
    def test_update_secondary_locale(self):
        models = TaxonomyModelRouter('taxonomy.sources.custom')
        secondary_locale = models.TaxonLocaleModel.objects.create(
            self.root_taxon, 'German Name', 'de', preferred=False
        )
        primary_locale = models.TaxonLocaleModel.objects.create(
            self.root_taxon, 'English Name', self.language, preferred=True
        )

        url = self.get_url()
        self.make_user_tenant_admin(self.user, self.tenant)

        post_data = {
            'name_uuid': str(self.root_taxon.name_uuid),
            'taxon_latname': self.root_taxon.taxon_latname,
            'name': 'English Name',
            'input_language': self.language,
            f'name_de_{secondary_locale.id}': 'Updated German Name',
        }

        response = self.tenant_client.post(url, data=post_data, **AJAX_KWARGS)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['success'])

        secondary_locale.refresh_from_db()
        self.assertEqual(secondary_locale.name, 'Updated German Name')

    @test_settings
    def test_delete_secondary_locale(self):
        models = TaxonomyModelRouter('taxonomy.sources.custom')
        secondary_locale = models.TaxonLocaleModel.objects.create(
            self.root_taxon, 'German Name', 'de', preferred=False
        )
        primary_locale = models.TaxonLocaleModel.objects.create(
            self.root_taxon, 'English Name', self.language, preferred=True
        )

        url = self.get_url()
        self.make_user_tenant_admin(self.user, self.tenant)

        post_data = {
            'name_uuid': str(self.root_taxon.name_uuid),
            'taxon_latname': self.root_taxon.taxon_latname,
            'name': 'English Name',
            'input_language': self.language,
            f'name_de_{secondary_locale.id}': '',
        }

        response = self.tenant_client.post(url, data=post_data, **AJAX_KWARGS)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['success'])

        self.assertFalse(
            models.TaxonLocaleModel.objects.filter(id=secondary_locale.id).exists()
        )
        self.assertTrue(
            models.TaxonLocaleModel.objects.filter(id=primary_locale.id).exists()
        )

    @test_settings
    def test_update_multiple_secondary_locales(self):
        models = TaxonomyModelRouter('taxonomy.sources.custom')
        de_locale = models.TaxonLocaleModel.objects.create(
            self.root_taxon, 'German Name', 'de', preferred=False
        )
        fr_locale = models.TaxonLocaleModel.objects.create(
            self.root_taxon, 'French Name', 'fr', preferred=False
        )
        primary_locale = models.TaxonLocaleModel.objects.create(
            self.root_taxon, 'English Name', self.language, preferred=True
        )

        url = self.get_url()
        self.make_user_tenant_admin(self.user, self.tenant)

        post_data = {
            'name_uuid': str(self.root_taxon.name_uuid),
            'taxon_latname': self.root_taxon.taxon_latname,
            'name': 'English Name',
            'input_language': self.language,
            f'name_de_{de_locale.id}': 'Aktualisierter deutscher Name',
            f'name_fr_{fr_locale.id}': '',
        }

        response = self.tenant_client.post(url, data=post_data, **AJAX_KWARGS)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['success'])

        de_locale.refresh_from_db()
        self.assertEqual(de_locale.name, 'Aktualisierter deutscher Name')
        self.assertFalse(models.TaxonLocaleModel.objects.filter(id=fr_locale.id).exists())

    # -- helpers --

    def get_taxon_profiles_link(self):
        taxon_profiles_ctype = ContentType.objects.get_for_model(TaxonProfiles)
        return MetaAppGenericContent.objects.get(meta_app=self.meta_app, content_type=taxon_profiles_ctype)

    def set_include_vernacular_names_languages(self, languages):
        link = self.get_taxon_profiles_link()
        if link.options is None:
            link.options = {}
        link.options['include_vernacular_names_languages'] = ','.join(languages)
        link.save()

    # -- _get_include_vernacular_names_languages --

    @test_settings
    def test_get_include_vernacular_names_languages_no_option(self):
        view = self.get_view(ajax=True)
        view.meta_app = self.meta_app

        result = view._get_include_vernacular_names_languages()
        self.assertEqual(result, [])

    @test_settings
    def test_get_include_vernacular_names_languages_with_option(self):
        self.set_include_vernacular_names_languages(['de', 'fr'])

        view = self.get_view(ajax=True)
        view.meta_app = self.meta_app

        result = view._get_include_vernacular_names_languages()
        self.assertCountEqual(result, ['de', 'fr'])

    @test_settings
    def test_get_include_vernacular_names_languages_includes_secondary_languages(self):
        self.create_secondary_languages(['de'])

        view = self.get_view(ajax=True)
        view.meta_app = self.meta_app

        result = view._get_include_vernacular_names_languages()
        self.assertIn('de', result)

    @test_settings
    def test_get_include_vernacular_names_languages_merges_option_and_secondary(self):
        self.create_secondary_languages(['de'])
        self.set_include_vernacular_names_languages(['fr'])

        view = self.get_view(ajax=True)
        view.meta_app = self.meta_app

        result = view._get_include_vernacular_names_languages()
        self.assertCountEqual(result, ['de', 'fr'])

    # -- set_taxa --

    @test_settings
    def test_set_taxa_new_root_taxon(self):
        view = self.get_view(ajax=True)
        view.meta_app = self.meta_app
        view.include_vernacular_names_languages = []

        view.set_taxa(meta_app_id=self.meta_app.id, language=self.language)

        self.assertIsNone(view.taxon)
        self.assertIsNone(view.parent_taxon)
        self.assertIsNone(view.locale)
        self.assertEqual(view.language, self.language)

    @test_settings
    def test_set_taxa_existing_taxon_with_locale(self):
        models = TaxonomyModelRouter('taxonomy.sources.custom')
        locale = models.TaxonLocaleModel.objects.create(
            self.root_taxon, 'English Name', self.language, preferred=True
        )

        view = self.get_view(ajax=True)
        view.meta_app = self.meta_app
        view.include_vernacular_names_languages = []

        view.set_taxa(meta_app_id=self.meta_app.id, name_uuid=self.root_taxon.name_uuid, language=self.language)

        self.assertEqual(view.taxon, self.root_taxon)
        self.assertEqual(view.locale, locale)
        self.assertIsNone(view.parent_taxon)

    @test_settings
    def test_set_taxa_sets_parent_from_tree(self):
        child_taxon = self.create_custom_taxon('Child Taxon', parent=self.root_taxon)

        view = self.get_view(ajax=True)
        view.meta_app = self.meta_app
        view.include_vernacular_names_languages = []

        view.set_taxa(meta_app_id=self.meta_app.id, name_uuid=child_taxon.name_uuid, language=self.language)

        self.assertEqual(view.taxon, child_taxon)
        self.assertEqual(view.parent_taxon, self.root_taxon)

    @test_settings
    def test_set_taxa_sets_parent_from_parent_name_uuid(self):
        view = self.get_view(ajax=True)
        view.meta_app = self.meta_app
        view.include_vernacular_names_languages = []

        view.set_taxa(
            meta_app_id=self.meta_app.id,
            parent_name_uuid=self.root_taxon.name_uuid,
            language=self.language,
        )

        self.assertIsNone(view.taxon)
        self.assertEqual(view.parent_taxon, self.root_taxon)

    # -- include_vernacular_names_languages form integration --

    @test_settings
    def test_form_shows_included_language_fields(self):
        self.set_include_vernacular_names_languages(['de', 'fr'])
        models = TaxonomyModelRouter('taxonomy.sources.custom')
        models.TaxonLocaleModel.objects.create(
            self.root_taxon, 'English Name', self.language, preferred=True
        )

        url = self.get_url()
        self.make_user_tenant_admin(self.user, self.tenant)

        response = self.tenant_client.get(url, **AJAX_KWARGS)
        self.assertEqual(response.status_code, 200)

        form = response.context['form']
        self.assertIn('name_de', form.fields)
        self.assertIn('name_fr', form.fields)

    @test_settings
    def test_form_uses_existing_locale_field_when_language_already_has_locale(self):
        self.set_include_vernacular_names_languages(['de', 'fr'])
        models = TaxonomyModelRouter('taxonomy.sources.custom')
        models.TaxonLocaleModel.objects.create(
            self.root_taxon, 'English Name', self.language, preferred=True
        )
        de_locale = models.TaxonLocaleModel.objects.create(
            self.root_taxon, 'German Name', 'de', preferred=False
        )

        url = self.get_url()
        self.make_user_tenant_admin(self.user, self.tenant)

        response = self.tenant_client.get(url, **AJAX_KWARGS)
        form = response.context['form']

        self.assertNotIn('name_de', form.fields)
        self.assertIn(f'name_de_{de_locale.id}', form.fields)
        self.assertIn('name_fr', form.fields)

    @test_settings
    def test_form_valid_creates_included_language_locale(self):
        self.set_include_vernacular_names_languages(['de'])
        models = TaxonomyModelRouter('taxonomy.sources.custom')
        models.TaxonLocaleModel.objects.create(
            self.root_taxon, 'English Name', self.language, preferred=True
        )

        url = self.get_url()
        self.make_user_tenant_admin(self.user, self.tenant)

        post_data = {
            'name_uuid': str(self.root_taxon.name_uuid),
            'taxon_latname': self.root_taxon.taxon_latname,
            'name': 'English Name',
            'input_language': self.language,
            'name_de': 'Deutscher Name',
        }

        response = self.tenant_client.post(url, data=post_data, **AJAX_KWARGS)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['success'])

        de_locale = models.TaxonLocaleModel.objects.filter(
            taxon=self.root_taxon, language='de'
        ).first()
        self.assertIsNotNone(de_locale)
        self.assertEqual(de_locale.name, 'Deutscher Name')
        self.assertTrue(de_locale.preferred)  # first locale for a language is always preferred

    @test_settings
    def test_form_valid_skips_empty_included_language_field(self):
        self.set_include_vernacular_names_languages(['de'])
        models = TaxonomyModelRouter('taxonomy.sources.custom')
        models.TaxonLocaleModel.objects.create(
            self.root_taxon, 'English Name', self.language, preferred=True
        )

        url = self.get_url()
        self.make_user_tenant_admin(self.user, self.tenant)

        post_data = {
            'name_uuid': str(self.root_taxon.name_uuid),
            'taxon_latname': self.root_taxon.taxon_latname,
            'name': 'English Name',
            'input_language': self.language,
            'name_de': '',
        }

        response = self.tenant_client.post(url, data=post_data, **AJAX_KWARGS)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['success'])

        self.assertFalse(
            models.TaxonLocaleModel.objects.filter(taxon=self.root_taxon, language='de').exists()
        )


class TestMoveCustomTaxonTreeEntry(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser,
                                WithMetaApp, WithTenantClient, TenantTestCase):    
    
    url_name = 'move_custom_taxon'
    view_class = MoveCustomTaxonTreeEntry

    def get_url_kwargs(self):
        url_kwargs = {
            'name_uuid' : str(self.taxon_2_1.name_uuid),
        }
        return url_kwargs
    
    def setUp(self):
        extra_fields = {
            'is_root_taxon': True,
        }
        self.root_taxon = self.create_custom_taxon('Root Taxon', parent=None)
        self.taxon_1 = self.create_custom_taxon('Taxon 1', parent=self.root_taxon)
        self.taxon_2 = self.create_custom_taxon('Taxon 2', parent=self.root_taxon)
        self.taxon_2_1 = self.create_custom_taxon('Taxon 2 1', parent=self.taxon_2)
        self.taxon_2_1_1 = self.create_custom_taxon('Taxon 2 1 1', parent=self.taxon_2_1)
        self.taxon_3 = self.create_custom_taxon('Taxon 3', parent=self.root_taxon)
        self.taxon_3_1 = self.create_custom_taxon('Taxon 3 1', parent=self.taxon_3)
        self.taxon_3_2 = self.create_custom_taxon('Taxon 3 2', parent=self.taxon_3)
        self.taxon_3_3 = self.create_custom_taxon('Taxon 3 3', parent=self.taxon_3)
        
        self.taxon_3_2.delete()

        
        super().setUp()
        
        taxon_profiles_ctype = ContentType.objects.get_for_model(TaxonProfiles)
        link = MetaAppGenericContent.objects.get(meta_app=self.meta_app, content_type=taxon_profiles_ctype)
        
        self.taxon_profiles = link.generic_content
    
    def create_taxon_profile(self, custom_taxon):
        lazy_taxon = LazyTaxon(instance=custom_taxon)

        taxon_profile = TaxonProfile(
            taxon_profiles=self.taxon_profiles,
            taxon=lazy_taxon,
        )

        taxon_profile.save()
        
        return taxon_profile
    
    
    def create_custom_taxon(self, taxon_latname, parent=None, rank=None):
        
        extra_fields = {
            'parent': parent,
        }
        
        if not parent:
            extra_fields['is_root_taxon'] = True
            
        if rank:
            extra_fields['rank'] = rank
        
        models = TaxonomyModelRouter('taxonomy.sources.custom')
        taxon = models.TaxonTreeModel.objects.create(taxon_latname, taxon_latname, **extra_fields)
        
        return taxon
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        view.taxon = self.taxon_2_1
        
        context_data = view.get_context_data(**view.kwargs)
        self.assertEqual(context_data['taxon'], self.taxon_2_1)
        
    
    @test_settings
    def test_get_form(self):
        
        view = self.get_view()
        view.taxon = self.taxon_2_1
        
        form = view.get_form()
        
        self.assertEqual(form.__class__.__name__, 'MoveCustomTaxonForm')
        self.assertEqual(form.taxon, self.taxon_2_1)
        
    
    @test_settings
    def test_update_nuids(self):
        
        taxon_profile = self.create_taxon_profile(self.taxon_2_1_1)
        self.assertEqual(taxon_profile.taxon_nuid, '001002001001')
        
        altered_taxon = self.taxon_2_1_1
        altered_taxon.taxon_nuid = '001001001001'
        altered_taxon.save()
        
        taxon_profile.refresh_from_db()
        self.assertEqual(taxon_profile.taxon_nuid, '001002001001')
        
        view = self.get_view()
        view.taxon = self.taxon_2_1
        
        view.update_nuids(altered_taxon, TaxonProfile)
        
        taxon_profile.refresh_from_db()
        self.assertEqual(taxon_profile.taxon_nuid, '001001001001')
        
    
    @test_settings
    def test_update_lazy_taxa(self):
        
        taxon_profile = self.create_taxon_profile(self.taxon_2_1_1)
        self.assertEqual(taxon_profile.taxon_nuid, '001002001001')
        
        altered_taxon = self.taxon_2_1_1
        altered_taxon.taxon_nuid = '001001001001'
        altered_taxon.save()
        
        view = self.get_view()
        view.taxon = self.taxon_2_1
        
        view.update_lazy_taxa(altered_taxon)
        
        taxon_profile.refresh_from_db()
        self.assertEqual(taxon_profile.taxon_nuid, '001001001001')
        
    
    @test_settings
    def test_form_valid(self):
        
        taxon_profile = self.create_taxon_profile(self.taxon_2_1_1)
        self.assertEqual(taxon_profile.taxon_nuid, '001002001001')
        
        view = self.get_view()
        view.taxon = self.taxon_2_1
        
        old_nuid = self.taxon_2_1.taxon_nuid
        
        post_data = {
            'new_parent_taxon_0': 'taxonomy.sources.custom',
            'new_parent_taxon_1': self.taxon_3.taxon_latname,
            'new_parent_taxon_2': self.taxon_3.taxon_author,
            'new_parent_taxon_3': self.taxon_3.name_uuid,
            'new_parent_taxon_4': self.taxon_3.taxon_nuid,
        }
        
        form = view.form_class(self.taxon_2_1, data=post_data)
        
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)
        
        self.assertEqual(response.status_code, 200)
        
        
        self.taxon_2_1.refresh_from_db()
        
        self.assertEqual(self.taxon_2_1.parent, self.taxon_3)
        self.assertEqual(self.taxon_2_1.taxon_nuid, '001003004')
        
        self.taxon_2_1_1.refresh_from_db()
        
        self.assertEqual(self.taxon_2_1_1.parent, self.taxon_2_1)
        self.assertEqual(self.taxon_2_1_1.taxon_nuid, '001003004001')
        
        taxon_profile.refresh_from_db()
        self.assertEqual(taxon_profile.taxon_nuid, '001003004001')
        
        models = TaxonomyModelRouter('taxonomy.sources.custom')
        qry = models.TaxonTreeModel.objects.filter(taxon_nuid__startswith=old_nuid)
        
        self.assertFalse(qry.exists())

    @test_settings
    def test_form_valid_move_to_root(self):

        taxon_profile = self.create_taxon_profile(self.taxon_2_1_1)
        self.assertEqual(taxon_profile.taxon_nuid, '001002001001')

        view = self.get_view()
        view.taxon = self.taxon_2_1

        old_nuid = self.taxon_2_1.taxon_nuid

        post_data = {
            'move_to_root': True,
        }

        form = view.form_class(self.taxon_2_1, data=post_data)
        form.is_valid()

        self.assertEqual(form.errors, {})

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)

        self.taxon_2_1.refresh_from_db()
        self.assertIsNone(self.taxon_2_1.parent)
        self.assertEqual(self.taxon_2_1.taxon_nuid, '002')

        self.taxon_2_1_1.refresh_from_db()
        self.assertEqual(self.taxon_2_1_1.parent, self.taxon_2_1)
        self.assertEqual(self.taxon_2_1_1.taxon_nuid, '002001')

        taxon_profile.refresh_from_db()
        self.assertEqual(taxon_profile.taxon_nuid, '002001')

        models = TaxonomyModelRouter('taxonomy.sources.custom')
        qry = models.TaxonTreeModel.objects.filter(taxon_nuid__startswith=old_nuid)
        self.assertFalse(qry.exists())