from django_tenants.test.cases import TenantTestCase

from django.contrib.contenttypes.models import ContentType

from app_kit.tests.common import test_settings
from app_kit.features.taxon_profiles.models import TaxonProfiles, TaxonProfile, TaxonTextType, TaxonText
from app_kit.models import MetaAppGenericContent

from app_kit.features.taxon_profiles.zip_import import TaxonProfilesZipImporter

from app_kit.features.nature_guides.tests.test_models import WithNatureGuide

from app_kit.tests.mixins import WithMetaApp

from taxonomy.lazy import LazyTaxonList, LazyTaxon
from taxonomy.models import TaxonomyModelRouter


class WithTaxonProfiles:

    short_text_content = 'Lacerta agilis test text'
    long_text_content = 'Lacerta agilis test text long text'

    def get_taxon_profiles(self):
        taxon_profiles_ctype = ContentType.objects.get_for_model(TaxonProfiles)
        taxon_profiles_link = MetaAppGenericContent.objects.get(meta_app=self.meta_app,
                                        content_type=taxon_profiles_ctype)
        
        return taxon_profiles_link.generic_content


    def create_taxon_profile_with_text(self, taxon, text_type, text, long_text):

        taxon_profiles = self.get_taxon_profiles()

        profile = TaxonProfile(
            taxon_profiles=taxon_profiles,
            taxon=taxon,
        )

        profile.save()

        text_type, created = TaxonTextType.objects.get_or_create(taxon_profiles=taxon_profiles,
                                                                 text_type=text_type)

        taxon_text = TaxonText(
            taxon_profile=profile,
            taxon_text_type=text_type,
            text=text,
            long_text=long_text,
        )

        taxon_text.save()

        return profile, text_type, taxon_text


class TestTaxonProfiles(WithTaxonProfiles, WithMetaApp, WithNatureGuide, TenantTestCase):

    @test_settings
    def test_zip_import_class(self):
        taxon_profiles = self.get_taxon_profiles()

        ZipImportClass = taxon_profiles.zip_import_class

        self.assertEqual(ZipImportClass, TaxonProfilesZipImporter)
        

    @test_settings
    def test_taxa(self):
        taxon_profiles = self.get_taxon_profiles()

        taxa = taxon_profiles.taxa()
        
        self.assertTrue(isinstance(taxa, LazyTaxonList))
        self.assertEqual(taxa.count(), 0)
        

    @test_settings
    def test_higher_taxa(self):
        taxon_profiles = self.get_taxon_profiles()

        higher_taxa = taxon_profiles.higher_taxa()
        
        self.assertTrue(isinstance(higher_taxa, LazyTaxonList))
        self.assertEqual(higher_taxa.count(), 0)
        

    @test_settings
    def test_collected_taxa(self):

        taxon_profiles = self.get_taxon_profiles()

        collected_taxa = taxon_profiles.collected_taxa()
        
        self.assertTrue(isinstance(collected_taxa, LazyTaxonList))
        self.assertEqual(collected_taxa.count(), 0)

        # add some taxa
        nature_guide = self.create_nature_guide()
        nature_guide_content_type = ContentType.objects.get_for_model(nature_guide)
        nature_guide_link = MetaAppGenericContent(
            meta_app=self.meta_app,
            content_type=nature_guide_content_type,
            object_id=nature_guide.id,
        )
        nature_guide_link.save()

        # add a node with taxon
        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)
        
        parent_node = nature_guide.root_node
        node = self.create_node(parent_node, 'First', **{'node_type':'result'})
        node.meta_node.taxon = lacerta_agilis
        node.meta_node.save()
        
        collected_taxa = taxon_profiles.collected_taxa()
        self.assertTrue(isinstance(collected_taxa, LazyTaxonList))
        self.assertEqual(collected_taxa.count(), 1)
        self.assertEqual(collected_taxa[0].name_uuid, lacerta_agilis.name_uuid)


    @test_settings
    def test_get_primary_localization(self):
        
        taxon_profiles = self.get_taxon_profiles()

        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)

        text_type_name = 'Test Text Type'
        taxon_profile, text_type, taxon_text = self.create_taxon_profile_with_text(lacerta_agilis,
                                            text_type_name, self.short_text_content, self.long_text_content)

        locale = taxon_profiles.get_primary_localization()
        self.assertEqual(locale[taxon_profiles.name], taxon_profiles.name)
        self.assertEqual(locale[text_type_name], text_type_name)

        short_text_key = taxon_profiles.get_short_text_key(taxon_text)
        self.assertEqual(locale[short_text_key], self.short_text_content)

        long_text_key = taxon_profiles.get_long_text_key(taxon_text)
        self.assertEqual(locale[long_text_key], self.long_text_content)
        

    @test_settings
    def test_get_text_keys(self):

        taxon_profiles = self.get_taxon_profiles()

        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)

        text_type_name = 'Test Text Type'
        taxon_profile, text_type, taxon_text = self.create_taxon_profile_with_text(lacerta_agilis,
                                            text_type_name, self.short_text_content, self.long_text_content)

        short_text_key = taxon_profiles.get_short_text_key(taxon_text)
        self.assertEqual(short_text_key, 'taxon_text_{0}_{1}'.format(text_type.id, taxon_text.id))

        long_text_key = taxon_profiles.get_long_text_key(taxon_text)
        self.assertEqual(long_text_key, 'taxon_text_{0}_{1}_long'.format(text_type.id, taxon_text.id))


class TestTaxonProfile(WithTaxonProfiles, WithMetaApp, TenantTestCase):

    @test_settings
    def test_texts(self):

        taxon_profiles = self.get_taxon_profiles()

        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)

        text_type_name = 'Test Text Type'
        taxon_profile, text_type, taxon_text = self.create_taxon_profile_with_text(lacerta_agilis,
                                            text_type_name, self.short_text_content, self.long_text_content)


        texts = taxon_profile.texts()

        self.assertEqual(texts.count(), 1)
        self.assertEqual(texts[0], taxon_text)
        

    @test_settings
    def test_profile_complete(self):

        taxon_profiles = self.get_taxon_profiles()

        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)

        text_type_name = 'Test Text Type'
        taxon_profile, text_type, taxon_text = self.create_taxon_profile_with_text(lacerta_agilis,
                                            text_type_name, self.short_text_content, self.long_text_content)


        texts = taxon_profile.texts()

        self.assertEqual(texts.count(), 1)
        self.assertEqual(texts[0], taxon_text)

        complete = taxon_profile.profile_complete()
        self.assertTrue(complete)

        # add second taxon_text
        text_type, created = TaxonTextType.objects.get_or_create(taxon_profiles=taxon_profiles,
                                                                 text_type='Second type')


        complete_2 = taxon_profile.profile_complete()
        self.assertFalse(complete_2)
        


class TestTaxonTextType(WithTaxonProfiles, WithMetaApp, TenantTestCase):

    @test_settings
    def test_str(self):

        taxon_profiles = self.get_taxon_profiles()

        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)

        text_type_name = 'Test Text Type'
        taxon_profile, text_type, taxon_text = self.create_taxon_profile_with_text(lacerta_agilis,
                                            text_type_name, self.short_text_content, self.long_text_content)

        self.assertEqual(str(text_type), text_type_name)


class TestTaxonText(WithTaxonProfiles, WithMetaApp, TenantTestCase):

    @test_settings
    def test_create(self):

        taxon_profiles = self.get_taxon_profiles()

        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)

        profile = TaxonProfile(
            taxon_profiles=taxon_profiles,
            taxon=lacerta_agilis,
        )

        profile.save()

        text_type, created = TaxonTextType.objects.get_or_create(taxon_profiles=taxon_profiles,
                                                                 text_type='Test text type')

        taxon_text = TaxonText(
            taxon_profile=profile,
            taxon_text_type=text_type,
            text='Test Lacerta agilis text',
        )

        taxon_text.save()

        taxon_text.delete()

        taxon_text_only_long = TaxonText(
            taxon_profile=profile,
            taxon_text_type=text_type,
            long_text='Test Lacerta agilis text',
        )

        taxon_text_only_long.save()

        taxon_text_only_long.delete()

        taxon_text_full = TaxonText(
            taxon_profile=profile,
            taxon_text_type=text_type,
            text='Text Lacerta agilis short',
            long_text='Test Lacerta agilis text',
        )

        taxon_text_full.save()

        
