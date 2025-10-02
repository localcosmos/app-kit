from django_tenants.test.cases import TenantTestCase
from app_kit.tests.common import test_settings

from app_kit.features.backbonetaxonomy.models import (BackboneTaxonomy, BackboneTaxa,
                                TaxonRelationshipType, TaxonRelationship)

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



class TestTaxonRelationshipType(TenantTestCase):

    @test_settings
    def test_create(self):
        backbonetaxonomy = BackboneTaxonomy.objects.create('Test Backbone Taxonomy', 'en')
                
        relationship_type = TaxonRelationshipType.objects.create(
            backbonetaxonomy = backbonetaxonomy,
            relationship_name = 'Predation',
            taxon_role = 'Predator',
            related_taxon_role = 'Prey',
        )

        self.assertTrue(isinstance(relationship_type, TaxonRelationshipType))
        self.assertEqual(relationship_type.relationship_name, 'Predation')
        self.assertEqual(relationship_type.taxon_role, 'Predator')
        self.assertEqual(relationship_type.related_taxon_role, 'Prey')
        
    @test_settings
    def test_string_representation(self):
        backbonetaxonomy = BackboneTaxonomy.objects.create('Test Backbone Taxonomy', 'en')
        relationship_type = TaxonRelationshipType.objects.create(
            backbonetaxonomy = backbonetaxonomy,
            relationship_name = 'Predation',
            taxon_role = 'Predator',
            related_taxon_role = 'Prey',
        )

        self.assertEqual(str(relationship_type), 'Predation')


class TestTaxonRelationships(TenantTestCase):
    
    
    def create_relationship_type(self, backbonetaxonomy):
        relationship_type = TaxonRelationshipType.objects.create(
            backbonetaxonomy = backbonetaxonomy,
            relationship_name = 'Predation',
            taxon_role = 'Predator',
            related_taxon_role = 'Prey',
        )
        return relationship_type
    
    
    def create_relationship(self, backbonetaxonomy, taxon, related_taxon, relationship_type):
        relationship = TaxonRelationship.objects.create(
            backbonetaxonomy = backbonetaxonomy,
            taxon = taxon,
            related_taxon_source = 'taxonomy.sources.col',
            related_taxon_name_uuid = related_taxon.name_uuid,
            related_taxon_latname = related_taxon.taxon_latname,
            related_taxon_author = related_taxon.taxon_author,
            related_taxon_nuid = related_taxon.taxon_nuid,
            related_taxon_include_descendants = False,
            relationship_type = relationship_type,
            description = 'Pica pica preys on Lacerta agilis',
        )
        return relationship


    @test_settings
    def test_create_relationship(self):
        backbonetaxonomy = BackboneTaxonomy.objects.create('Test Backbone Taxonomy', 'en')
        relationship_type = self.create_relationship_type(backbonetaxonomy)
        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        lacerta_agilis_db = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis_db)
        
        pica_pica_db = models.TaxonTreeModel.objects.get(taxon_latname='Pica pica')
        pica_pica = LazyTaxon(instance=pica_pica_db)
        
        relationship = TaxonRelationship.objects.create(
            backbonetaxonomy = backbonetaxonomy,
            taxon = lacerta_agilis,
            related_taxon_source = taxon_source,
            related_taxon_name_uuid = pica_pica.name_uuid,
            related_taxon_latname = pica_pica.taxon_latname,
            related_taxon_author = pica_pica.taxon_author,
            related_taxon_nuid = pica_pica.taxon_nuid,
            related_taxon_include_descendants = False,
            relationship_type = relationship_type,
            description = 'Pica pica preys on Lacerta agilis',
        )
        
        self.assertTrue(isinstance(relationship, TaxonRelationship))
        self.assertEqual(relationship.taxon.name_uuid, lacerta_agilis.name_uuid)
        self.assertEqual(relationship.related_taxon_source, taxon_source)
        self.assertEqual(relationship.related_taxon_name_uuid, pica_pica.name_uuid)
        self.assertEqual(relationship.related_taxon_latname, pica_pica.taxon_latname)
        self.assertEqual(relationship.related_taxon_author, pica_pica.taxon_author)
        self.assertEqual(relationship.related_taxon_nuid, pica_pica.taxon_nuid)
        self.assertFalse(relationship.related_taxon_include_descendants)
        self.assertEqual(relationship.relationship_type.relationship_name, 'Predation')
        self.assertEqual(relationship.description, 'Pica pica preys on Lacerta agilis')
        
    @test_settings
    def test_string_representation(self):
        backbonetaxonomy = BackboneTaxonomy.objects.create('Test Backbone Taxonomy', 'en')
        relationship_type = self.create_relationship_type(backbonetaxonomy)
        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        lacerta_agilis_db = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis_db)
        
        pica_pica_db = models.TaxonTreeModel.objects.get(taxon_latname='Pica pica')
        pica_pica = LazyTaxon(instance=pica_pica_db)
        
        relationship = self.create_relationship(
            backbonetaxonomy, 
            lacerta_agilis, 
            pica_pica, 
            relationship_type
        )
        
        self.assertEqual(str(relationship), 'Predation: Lacerta agilis - Pica pica')
        
    @test_settings
    def test_related_taxon_property(self):
        backbonetaxonomy = BackboneTaxonomy.objects.create('Test Backbone Taxonomy', 'en')
        relationship_type = self.create_relationship_type(backbonetaxonomy)
        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        lacerta_agilis_db = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis_db)
        
        pica_pica_db = models.TaxonTreeModel.objects.get(taxon_latname='Pica pica')
        pica_pica = LazyTaxon(instance=pica_pica_db)
        
        relationship = self.create_relationship(
            backbonetaxonomy, 
            lacerta_agilis, 
            pica_pica, 
            relationship_type
        )
        
        related_taxon = relationship.related_taxon
        
        self.assertTrue(isinstance(related_taxon, LazyTaxon))
        self.assertEqual(related_taxon.name_uuid, pica_pica.name_uuid)
        self.assertEqual(related_taxon.taxon_latname, pica_pica.taxon_latname)
        self.assertEqual(related_taxon.taxon_author, pica_pica.taxon_author)
        self.assertEqual(related_taxon.taxon_nuid, pica_pica.taxon_nuid)
        
    @test_settings
    def test_set_related_taxon_method(self):
        backbonetaxonomy = BackboneTaxonomy.objects.create('Test Backbone Taxonomy', 'en')
        relationship_type = self.create_relationship_type(backbonetaxonomy)
        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        lacerta_agilis_db = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis_db)
        
        pica_pica_db = models.TaxonTreeModel.objects.get(taxon_latname='Pica pica')
        pica_pica = LazyTaxon(instance=pica_pica_db)
        
        relationship = self.create_relationship(
            backbonetaxonomy, 
            lacerta_agilis, 
            pica_pica, 
            relationship_type
        )
        
        # create a new related taxon
        corvus_corax_db = models.TaxonTreeModel.objects.get(taxon_latname='Corvus corax')
        corvus_corax = LazyTaxon(instance=corvus_corax_db)
        
        relationship.set_related_taxon(corvus_corax)
        relationship.save()
        
        self.assertEqual(relationship.related_taxon_source, 'taxonomy.sources.col')
        self.assertEqual(relationship.related_taxon_name_uuid, corvus_corax.name_uuid)
        self.assertEqual(relationship.related_taxon_latname, corvus_corax.taxon_latname)
        self.assertEqual(relationship.related_taxon_author, corvus_corax.taxon_author)
        self.assertEqual(relationship.related_taxon_nuid, corvus_corax.taxon_nuid)
        self.assertFalse(relationship.related_taxon_include_descendants)