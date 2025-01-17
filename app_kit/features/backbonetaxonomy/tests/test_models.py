from django_tenants.test.cases import TenantTestCase
from app_kit.tests.common import test_settings

from app_kit.features.backbonetaxonomy.models import BackboneTaxonomy, BackboneTaxa

from taxonomy.lazy import LazyTaxon, LazyTaxonList
from taxonomy.models import TaxonomyModelRouter


class TestBackboneTaxonomy(TenantTestCase):

    def create_backbonetaxonomy(self):

        backbonetaxonomy = BackboneTaxonomy.objects.create('Test Backbone Taxonomy', 'en')
        return backbonetaxonomy


    def add_single_taxon(self, backbonetaxonomy):
        
        # add one taxon
        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)

        backbone_taxon = BackboneTaxa(
            backbonetaxonomy = backbonetaxonomy,
            taxon=lacerta_agilis,
        )
        backbone_taxon.save()

        return lacerta_agilis, backbone_taxon


    def add_higher_taxon(self, backbonetaxonomy):

        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)

        # add one higher taxon
        quercus = models.TaxonTreeModel.objects.get(taxon_latname='Quercus')
        quercus = LazyTaxon(instance=quercus)
        quercus.taxon_include_descendants = True

        higher_backbone_taxon = BackboneTaxa(
            backbonetaxonomy = backbonetaxonomy,
            taxon=quercus,
        )
        higher_backbone_taxon.save()

        return quercus, higher_backbone_taxon
    

    @test_settings
    def test_include_full_tree(self):
        backbonetaxonomy = self.create_backbonetaxonomy()

        include_full_tree = backbonetaxonomy.include_full_tree()
        self.assertFalse(include_full_tree)

        self.assertEqual(backbonetaxonomy.global_options, None)
        backbonetaxonomy.global_options = {
            'include_full_tree' : True,
        }
        backbonetaxonomy.save()

        backbonetaxonomy.refresh_from_db()

        include_full_tree = backbonetaxonomy.include_full_tree()
        self.assertTrue(include_full_tree)
        

    @test_settings
    def test_taxa(self):

        backbonetaxonomy = self.create_backbonetaxonomy()

        taxa = backbonetaxonomy.taxa()

        self.assertTrue(isinstance(taxa, LazyTaxonList))
        self.assertEqual(taxa.count(), 0)

        lazy_taxon, backbone_taxon = self.add_single_taxon(backbonetaxonomy)

        taxa = backbonetaxonomy.taxa()

        self.assertTrue(isinstance(taxa, LazyTaxonList))
        self.assertEqual(taxa.count(), 1)
        self.assertEqual(taxa[0].name_uuid, lazy_taxon.name_uuid)
        

    @test_settings
    def test_higher_taxa(self):

        backbonetaxonomy = self.create_backbonetaxonomy()

        higher_taxa = backbonetaxonomy.higher_taxa()

        self.assertTrue(isinstance(higher_taxa, LazyTaxonList))
        self.assertEqual(higher_taxa.count(), 0)

        # add one taxon
        lazy_taxon, backbone_taxon = self.add_single_taxon(backbonetaxonomy)

        # add one hgher taxon
        higher_lazy_taxon, higher_backbone_taxon = self.add_higher_taxon(backbonetaxonomy)

        higher_taxa = backbonetaxonomy.higher_taxa()

        self.assertTrue(isinstance(higher_taxa, LazyTaxonList))
        self.assertEqual(higher_taxa.count(), 1)
        self.assertEqual(higher_taxa[0].name_uuid, higher_lazy_taxon.name_uuid)
        

    @test_settings
    def test_descendant_taxa(self):

        backbonetaxonomy = self.create_backbonetaxonomy()

        descendant_taxa = backbonetaxonomy.descendant_taxa()

        self.assertTrue(isinstance(descendant_taxa, LazyTaxonList))
        self.assertEqual(descendant_taxa.count(), 0)

        # add one taxon
        lazy_taxon, backbone_taxon = self.add_single_taxon(backbonetaxonomy)

        # add one hgher taxon
        higher_lazy_taxon, higher_backbone_taxon = self.add_higher_taxon(backbonetaxonomy)

        descendant_taxa = backbonetaxonomy.descendant_taxa()

        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        expected_count = models.TaxonTreeModel.objects.filter(
            taxon_nuid__startswith=higher_lazy_taxon.taxon_nuid).count()
        
        self.assertEqual(descendant_taxa.count(), expected_count)
        

    @test_settings
    def test_get_primary_localization(self):

        # create a custom taxon
        models = TaxonomyModelRouter('taxonomy.sources.custom')

        root_taxon = models.TaxonTreeModel.objects.create(
            'Test root taxon',
            '',
            **{
                'is_root_taxon':True
            }
        )
        
        taxon = models.TaxonTreeModel.objects.create(
            'Test taxon',
            '',
            **{
                'parent':root_taxon,
            }
        )

        taxon.save()

        locale_name = 'Test taxon locale en'
        language = 'en'

        taxon_locale = models.TaxonLocaleModel.objects.create(taxon, locale_name, language)

        backbonetaxonomy = self.create_backbonetaxonomy()

        backbone_taxon = BackboneTaxa(
            backbonetaxonomy = backbonetaxonomy,
            taxon=LazyTaxon(instance=taxon),
        )
        backbone_taxon.save()

        translation = backbonetaxonomy.get_primary_localization()

        self.assertIn(backbonetaxonomy.name, translation)
        self.assertEqual(backbonetaxonomy.name, translation[backbonetaxonomy.name])
        self.assertIn(taxon.taxon_latname, translation)
        self.assertEqual(taxon_locale.name, translation[taxon.taxon_latname])

        taxon_locale.delete()

        translation = backbonetaxonomy.get_primary_localization()
        self.assertIn(taxon.taxon_latname, translation)
        self.assertEqual(translation[taxon.taxon_latname], None)


class TestBackboneTaxa(TenantTestCase):

    @test_settings
    def test_create(self):

        backbonetaxonomy = BackboneTaxonomy.objects.create('Test Backbone Taxonomy', 'en')

        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)

        backbone_taxon = BackboneTaxa(
            backbonetaxonomy = backbonetaxonomy,
            taxon=lacerta_agilis,
        )
        backbone_taxon.save()
