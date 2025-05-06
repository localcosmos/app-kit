'''
    These tests work only with an installed Local Cosmos App Kit
'''
from django_tenants.test.cases import TenantTestCase
from app_kit.tests.mixins import (WithMetaApp, WithTenantClient, WithUser, WithLoggedInUser, WithAjaxAdminOnly,
                                  ViewTestMixin)

from django.contrib.contenttypes.models import ContentType

from app_kit.tests.common import test_settings

from app_kit.features.taxon_profiles.models import TaxonProfiles, TaxonProfile
from app_kit.models import MetaAppGenericContent

from taxonomy.models import TaxonomyModelRouter
from taxonomy.lazy import LazyTaxon

from taxonomy.sources.custom.views import MoveCustomTaxonTreeEntry


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