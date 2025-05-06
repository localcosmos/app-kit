from django_tenants.test.cases import TenantTestCase

from taxonomy.lazy import LazyTaxon
from taxonomy.models import TaxonomyModelRouter

from taxonomy.forms import ManageMetaVernacularNameForm
from taxonomy.models import MetaVernacularNames

from app_kit.tests.common import test_settings
from app_kit.tests.mixins import (WithMetaApp, )


class TestManageMetaVernacularNameForm(WithMetaApp, TenantTestCase):
    
    @test_settings
    def test__init__(self):
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        natrix_natrix = models.TaxonTreeModel.objects.get(taxon_latname='Natrix natrix')
        
        lazy_taxon = LazyTaxon(instance=natrix_natrix)
        
        form = ManageMetaVernacularNameForm(lazy_taxon, language='en')
        
        self.assertEqual(form.lazy_taxon, lazy_taxon)
        self.assertEqual(form.fields['input_language'].initial, 'en')
    
    
    @test_settings
    def test_clean_name(self):
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        natrix_natrix = models.TaxonTreeModel.objects.get(taxon_latname='Natrix natrix')
        
        lazy_taxon = LazyTaxon(instance=natrix_natrix)
        
        post_data = {
            'input_language': 'en',
            'name': '  Snake  ',
        }
        
        form = ManageMetaVernacularNameForm(lazy_taxon, data=post_data, language='en')
        
        form.is_valid()
        
        self.assertEqual(form.errors, {})  
        
        self.assertEqual(form.cleaned_data['name'], 'Snake') 
    
    
    @test_settings
    def test_clean(self):
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        natrix_natrix = models.TaxonTreeModel.objects.get(taxon_latname='Natrix natrix')
        
        lazy_taxon = LazyTaxon(instance=natrix_natrix)
        
        post_data = {
            'input_language': 'en',
            'name': 'Snake',
        }
        
        form = ManageMetaVernacularNameForm(lazy_taxon, data=post_data, language='en')
        
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        existing_name = MetaVernacularNames(
            taxon_latname=lazy_taxon.taxon_latname,
            taxon_author=lazy_taxon.taxon_author,
            taxon_source=lazy_taxon.taxon_source,
            taxon_nuid=lazy_taxon.taxon_nuid,
            name_uuid=lazy_taxon.name_uuid,
            name='Snake',
            language='en',
        )
        
        existing_name.save()
        
        form = ManageMetaVernacularNameForm(lazy_taxon, data=post_data)
        
        form.is_valid()
        
        self.assertEqual(form.errors, {'name': ['This name already exists']})
        
        
        form = ManageMetaVernacularNameForm(lazy_taxon, meta_vernacular_name=existing_name,
                                            data=post_data, language='en')
        
        form.is_valid()
        # existing name is the one we are editing
        self.assertEqual(form.errors, {})