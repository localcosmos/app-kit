from django_tenants.test.cases import TenantTestCase

from taxonomy.lazy import LazyTaxon
from taxonomy.models import TaxonomyModelRouter

from taxonomy.models import MetaVernacularNames

from app_kit.tests.common import test_settings

from django.db.utils import IntegrityError

import uuid

class TestMetaVernacularNames(TenantTestCase):
    
    @test_settings
    def test_save(self):
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        natrix_natrix = models.TaxonTreeModel.objects.get(taxon_latname='Natrix natrix')
        
        lazy_taxon = LazyTaxon(instance=natrix_natrix)
        
        name = MetaVernacularNames(
            taxon_latname=lazy_taxon.taxon_latname,
            taxon_author=lazy_taxon.taxon_author,
            taxon_source=lazy_taxon.taxon_source,
            taxon_nuid=lazy_taxon.taxon_nuid,
            name_uuid=lazy_taxon.name_uuid,
            name='Snake',
            language='en',
        )
        
        name.save()
        
        
        name_duplicate = MetaVernacularNames(
            taxon_latname=lazy_taxon.taxon_latname,
            taxon_author=lazy_taxon.taxon_author,
            taxon_source=lazy_taxon.taxon_source,
            taxon_nuid='001002003004005006',
            name_uuid=uuid.uuid4(),
            name='Snake',
            language='en',
        )
        
        with self.assertRaises(IntegrityError):
            name_duplicate.save()
            
    @test_settings
    def test_update_preferred(self):
        
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        natrix_natrix = models.TaxonTreeModel.objects.get(taxon_latname='Natrix natrix')
        
        lazy_taxon = LazyTaxon(instance=natrix_natrix)
        
        name = MetaVernacularNames(
            taxon_latname=lazy_taxon.taxon_latname,
            taxon_author=lazy_taxon.taxon_author,
            taxon_source=lazy_taxon.taxon_source,
            taxon_nuid=lazy_taxon.taxon_nuid,
            name_uuid=lazy_taxon.name_uuid,
            name='Snake',
            language='en',
            preferred=True,
        )
        
        name.save()
        
        self.assertTrue(name.preferred)
        
        name_2 = MetaVernacularNames(
            taxon_latname=lazy_taxon.taxon_latname,
            taxon_author=lazy_taxon.taxon_author,
            taxon_source=lazy_taxon.taxon_source,
            taxon_nuid=lazy_taxon.taxon_nuid,
            name_uuid=lazy_taxon.name_uuid,
            name='Snake 2',
            language='en',
            preferred=True,
        )
        
        name_2.save()
        
        name.refresh_from_db()
        
        self.assertFalse(name.preferred)
        
        name_2.refresh_from_db()
        self.assertTrue(name_2.preferred)