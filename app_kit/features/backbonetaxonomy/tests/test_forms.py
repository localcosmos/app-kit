from django.test import TestCase
from django_tenants.test.cases import TenantTestCase

from app_kit.tests.common import test_settings, powersetdic
from app_kit.tests.mixins import WithMetaApp, WithFormTest

from app_kit.features.backbonetaxonomy.forms import (SearchTaxonomicBackboneForm, AddMultipleTaxaForm,
    ManageFulltreeForm, SwapTaxonForm, TaxonRelationshipTypeForm, TaxonRelationshipForm)

from app_kit.features.backbonetaxonomy.models import BackboneTaxonomy, TaxonRelationshipType


from taxonomy.models import TaxonomyModelRouter


class TestSearchTaxonomicBackboneForm(TenantTestCase):

    @test_settings
    def test_init(self):

        form = SearchTaxonomicBackboneForm(taxon_search_url='/')
        self.assertEqual(str(form.fields['taxon'].label), 'Search app taxa')


class TestAddMultipleTaxaForm(WithFormTest, TenantTestCase):

    @test_settings
    def test_form(self):

        form = AddMultipleTaxaForm()

        post_data = {
            'source' : 'taxonomy.sources.col',
            'taxa' : 'Lacerta agilis, Turdus merula, Something',
        }

        self.perform_form_test(AddMultipleTaxaForm, post_data)


class TestManageFulltreeForm(WithMetaApp, WithFormTest, TenantTestCase):

    @test_settings
    def test_init(self):

        form = ManageFulltreeForm()
        self.assertEqual(form.fields['include_full_tree'].initial, None)

        generic_content_link = self.get_generic_content_link(BackboneTaxonomy)
        generic_content = generic_content_link.generic_content
        generic_content.global_options = {
            'include_full_tree' : 'taxonomy.sources.col',
        }
        generic_content.save()
        
        form = ManageFulltreeForm(instance=generic_content)
        self.assertEqual(form.fields['include_full_tree'].initial, 'taxonomy.sources.col')
        
    
class TestSwapTaxonForm(WithMetaApp, WithFormTest, TenantTestCase):
    
    @test_settings
    def test_init(self):

        form = SwapTaxonForm()
        self.assertIn('from_taxon', form.fields)
        self.assertIn('to_taxon', form.fields)
        
        
class TestTaxonRelationshipTypeForm(WithMetaApp, WithFormTest, TenantTestCase):

    @test_settings
    def test_form(self):

        post_data = {
            'relationship_name' : 'Predation',
            'taxon_role' : 'Predator',
            'related_taxon_role' : 'Prey',
        }

        self.perform_form_test(TaxonRelationshipTypeForm, post_data)



class TestTaxonRelationshipForm(WithMetaApp, WithFormTest, TenantTestCase):
    
    
    def create_relationship_type(self):
        
        backbonetaxonomy = self.meta_app.backbone()
        
        relationship_type = TaxonRelationshipType.objects.create(
            backbonetaxonomy = backbonetaxonomy,
            relationship_name = 'Pollination',
            taxon_role = 'Pollinator',
            related_taxon_role = 'Plant',
        )
        return relationship_type
    
    
    @test_settings
    def test_init(self):
        
        relationship_type = self.create_relationship_type()
        
        form = TaxonRelationshipForm(relationship_type)
        self.assertIn('taxon', form.fields)
        self.assertIn('related_taxon', form.fields)
        self.assertIn('description', form.fields)
        

    @test_settings
    def test_form(self):

        relationship_type = self.create_relationship_type()
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.filter(taxon_latname='Lacerta agilis').first()
        pica_pica = models.TaxonTreeModel.objects.filter(taxon_latname='Pica pica').first()
        
        post_data = {
            'taxon_0' : 'taxonomy.sources.col', # taxon_source
            'taxon_1' : lacerta_agilis.taxon_latname, # taxon_latname
            'taxon_2' : lacerta_agilis.taxon_author, # taxon_author
            'taxon_3' : str(lacerta_agilis.name_uuid), # name_uuid
            'taxon_4' : lacerta_agilis.taxon_nuid, # taxon_nuid
            'related_taxon_0' : 'taxonomy.sources.col', # related_taxon_source
            'related_taxon_1' : pica_pica.taxon_latname, # related_taxon_latname
            'related_taxon_2' : pica_pica.taxon_author, # related_taxon_author
            'related_taxon_3' : str(pica_pica.name_uuid), # related_taxon_name_uuid
            'related_taxon_4' : pica_pica.taxon_nuid, # related_taxon_nuid
            'description' : 'A relationship description',
        }

        form = TaxonRelationshipForm(relationship_type, data=post_data)
        self.assertTrue(form.is_valid())
