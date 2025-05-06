from django_tenants.test.cases import TenantTestCase

from taxonomy.sources.custom.models import CustomTaxonTree

class TestCustomTaxonTreeManager(TenantTestCase):
    
    def test_create(self):
        taxon_latname = 'Root taxon'
        taxon_author = None
        
        root_taxon = CustomTaxonTree.objects.create(taxon_latname, taxon_author, is_root_taxon=True)
        
        self.assertEqual(root_taxon.taxon_latname, 'Root taxon')
        self.assertEqual(root_taxon.taxon_author, None)
        self.assertEqual(root_taxon.taxon_nuid, '001')
        self.assertEqual(root_taxon.is_root_taxon, True)
        
        l2_taxon_latname = 'L2 taxon'
        level_2_taxon = CustomTaxonTree.objects.create(l2_taxon_latname, taxon_author, parent=root_taxon)
        self.assertEqual(level_2_taxon.taxon_latname, l2_taxon_latname)
        self.assertEqual(level_2_taxon.taxon_author, None)
        self.assertEqual(level_2_taxon.taxon_nuid, '001001')
        self.assertEqual(level_2_taxon.parent, root_taxon)
        
        l2_2_taxon_latname = 'L2 taxon 2'
        level_2_taxon_2 = CustomTaxonTree.objects.create(l2_2_taxon_latname, taxon_author, parent=root_taxon)
        self.assertEqual(level_2_taxon_2.taxon_latname, l2_2_taxon_latname)
        self.assertEqual(level_2_taxon_2.taxon_author, None)
        self.assertEqual(level_2_taxon_2.taxon_nuid, '001002')
        self.assertEqual(level_2_taxon_2.parent, root_taxon)
        
        
        species_latname = 'Species'
        species_author = 'Tester 2024'
        species = CustomTaxonTree.objects.create(species_latname, species_author, parent=level_2_taxon_2,
                                                 rank='species')
        self.assertEqual(species.taxon_latname, species_latname)
        self.assertEqual(species.taxon_author, species_author)
        self.assertEqual(species.taxon_nuid, '001002001')
        self.assertEqual(species.parent, level_2_taxon_2)
        self.assertEqual(species.rank, 'species')
        