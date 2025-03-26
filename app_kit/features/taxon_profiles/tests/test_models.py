from django_tenants.test.cases import TenantTestCase

from django.contrib.contenttypes.models import ContentType

from app_kit.tests.common import test_settings
from app_kit.features.taxon_profiles.models import (TaxonProfiles, TaxonProfile, TaxonTextType,
        TaxonText, TaxonProfilesNavigation, TaxonProfilesNavigationEntry, TaxonProfilesNavigationEntryTaxa,
        TaxonTextTypeCategory)
        
from app_kit.models import MetaAppGenericContent

from app_kit.features.taxon_profiles.zip_import import TaxonProfilesZipImporter

from app_kit.features.nature_guides.tests.test_models import WithNatureGuide

from app_kit.tests.mixins import WithMetaApp

from taxonomy.lazy import LazyTaxonList, LazyTaxon
from taxonomy.models import TaxonomyModelRouter

from .common import WithTaxonProfilesNavigation


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
        
        # add a nav
        nav = TaxonProfilesNavigation(
            taxon_profiles=taxon_profiles,
        )
        
        nav.save()
        
        naventry_name = 'naventry name'
        naventry_description = 'naventry description'
        nav_entry_1 = TaxonProfilesNavigationEntry(
            navigation=nav,
            name=naventry_name,
            description = naventry_description,
        )
        
        nav_entry_1.save()
        
        locale = taxon_profiles.get_primary_localization()
        
        self.assertEqual(locale[naventry_name], naventry_name)
        self.assertEqual(locale[naventry_description], naventry_description)
        

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
    def test_categorized_texts(self):
        
        taxon_profiles = self.get_taxon_profiles()

        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)

        text_type_name = 'Test Text Type'
        taxon_profile, text_type, taxon_text = self.create_taxon_profile_with_text(lacerta_agilis,
                                            text_type_name, self.short_text_content, self.long_text_content)


        category_name = 'test cat'
        category = TaxonTextTypeCategory(
            taxon_profiles=taxon_profiles,
            name=category_name, 
        )
        category.save()
        
        cat_type_name = 'cat type'
        # create a text type with text and add it to the category
        cat_text_type, created = TaxonTextType.objects.get_or_create(taxon_profiles=taxon_profiles,
                                                                 text_type=cat_type_name)
        
        cat_text_type.category = category
        cat_text_type.save()

        cat_taxon_text = TaxonText(
            taxon_profile=taxon_profile,
            taxon_text_type=cat_text_type,
            text='cat text',
        )

        cat_taxon_text.save()
        
        categorized_texts = taxon_profile.categorized_texts()       
        
        self.assertIn('uncategorized', categorized_texts)
        self.assertEqual(list(categorized_texts['uncategorized']), [taxon_text])
        
        self.assertIn(category_name, categorized_texts)
        self.assertEqual(list(categorized_texts[category_name]), [cat_taxon_text])
        

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

        
class TestTaxonProfilesNavigation(WithTaxonProfilesNavigation, WithMetaApp, TenantTestCase):
    
    @test_settings
    def test_save(self):
        
        last_modified = self.navigation.last_modified_at
        
        self.navigation.save(prerendered=True)
        self.navigation.refresh_from_db()
        self.assertEqual(last_modified, self.navigation.last_modified_at)
        
        self.navigation.save()
        self.navigation.refresh_from_db()
        self.assertTrue(last_modified != self.navigation.last_modified_at)
        
    
    
    @test_settings
    def test_prerender(self):
        
        self.navigation.delete()
        
        navigation = TaxonProfilesNavigation(
            taxon_profiles = self.taxon_profiles,
        )
        
        navigation.save()
        
        self.assertEqual(navigation.prerendered, None)
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        chordata_db = models.TaxonTreeModel.objects.get(taxon_latname='Chordata')
        chordata = LazyTaxon(instance=chordata_db)
        
        n1 = self.create_navigation_entry(navigation, taxon=chordata)
        
        n2 = self.create_navigation_entry(navigation, parent=n1)
        
        navigation.refresh_from_db()
        
        last_modified = navigation.last_modified_at
        navigation.prerender()

        self.assertEqual(last_modified, navigation.last_modified_at)
        
        self.assertIn('tree', navigation.prerendered)
        self.assertEqual(len(navigation.prerendered['tree']), 1)
        self.assertEqual(len(navigation.prerendered['tree'][0]['children']), 1)
        
        
class TestTaxonProfilesNavigationEntry(WithTaxonProfilesNavigation, WithTaxonProfiles, WithMetaApp,
                                       TenantTestCase):
    
    @test_settings
    def test_key(self):
        
        entry = self.create_navigation_entry()
        
        self.assertEqual(entry.key, 'tpne-{0}'.format(entry.id))
    
    @test_settings
    def test_as_dict(self):
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        chordata_db = models.TaxonTreeModel.objects.get(taxon_latname='Chordata')
        chordata = LazyTaxon(instance=chordata_db)
        
        entry = self.create_navigation_entry()
        
        navigation_entry_content_type = ContentType.objects.get_for_model(TaxonProfilesNavigationEntry)
        
        dic = entry.as_dict()
        
        expected_dic = {
            'id': entry.id,
            'content_type_id': navigation_entry_content_type.id,
            'key': 'tpne-{0}'.format(entry.id),
            'parent_id': None,
            'parent_key': None,
            'taxa': [],
            'verbose_name': 'Unconfigured navigation entry',
            'name' : None,
            'description': None,
            'children': [],
            'images': [],
        }
        
        self.assertEqual(dic, expected_dic)
        
        entry_2_kwargs = {
            'name': 'Name',
            'description': 'Description',
        }
        entry_2 = self.create_navigation_entry(parent=entry, taxon=chordata, **entry_2_kwargs)
        
        entry_3 = self.create_navigation_entry(parent=entry_2)
        
        expected_dic = {
            'id': entry_2.id,
            'content_type_id': navigation_entry_content_type.id,
            'key': 'tpne-{0}'.format(entry_2.id),
            'parent_id': entry.id,
            'parent_key': 'tpne-{0}'.format(entry.id),
            'taxa': [
                {
                    'label': 'Chordata ',
                    'taxon_latname': 'Chordata',
                    'taxon_author': None,
                    'taxon_nuid': '001008',
                    'taxon_source': 'taxonomy.sources.col',
                    'name_uuid': '8f269294-09c9-4856-9347-0daf8a2fd80b'
                }
            ],
            'verbose_name': 'Name',
            'name': 'Name',
            'description':'Description',
            'children': [
                {
                    'id': entry_3.id,
                    'content_type_id': navigation_entry_content_type.id,
                    'key': 'tpne-{0}'.format(entry_3.id),
                    'parent_id': entry_2.id,
                    'parent_key': 'tpne-{0}'.format(entry_2.id),
                    'taxa': [],
                    'verbose_name': 'Unconfigured navigation entry',
                    'name': None,
                    'description': None,
                    'children': [],
                    'images': []
                }
            ], 
            'images': []
        }
    
    
    @test_settings
    def test_save(self):
        entry = self.create_navigation_entry()
        
        self.navigation.refresh_from_db()
        
        last_modified = self.navigation.last_modified_at
        
        entry.save()
        
        self.navigation.refresh_from_db()
        
        self.assertTrue(last_modified != self.navigation.last_modified_at)
    
    
    @test_settings
    def test_children(self):
        entry = self.create_navigation_entry()
        
        c1 = self.create_navigation_entry(parent=entry)
        c2 = self.create_navigation_entry(parent=entry)
        
        children = entry.children
        
        self.assertTrue(c1 in children)
        self.assertTrue(c2 in children)
        
        self.assertEqual(len(children), 2)
    
    
    @test_settings
    def test_str(self):
        entry = self.create_navigation_entry()
        
        self.assertEqual(str(entry), 'Unconfigured navigation entry')
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        chordata_db = models.TaxonTreeModel.objects.get(taxon_latname='Chordata')
        chordata = LazyTaxon(instance=chordata_db)
        
        taxon_link = TaxonProfilesNavigationEntryTaxa(
            navigation_entry=entry,
        )
        
        taxon_link.set_taxon(chordata)
        taxon_link.save()
        
        self.assertEqual(str(entry), 'Chordata')
        
        name = 'Test entry'
        
        entry.name = name
        entry.save()
        
        self.assertEqual(str(entry), name)
    
    
    @test_settings
    def test_taxa(self):
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        chordata_db = models.TaxonTreeModel.objects.get(taxon_latname='Chordata')
        chordata = LazyTaxon(instance=chordata_db)
        
        entry = self.create_navigation_entry(taxon=chordata)
        
        taxa = entry.taxa
        
        names = [str(t) for t in taxa.values_list('name_uuid', flat=True)]
        
        self.assertIn(chordata.name_uuid, names)
        self.assertEqual(len(taxa), 1)
        
        
    @test_settings
    def test_matching_custom_taxa(self):
        ct_models = TaxonomyModelRouter('taxonomy.sources.custom')
        animalia_ct = ct_models.TaxonTreeModel.objects.create(
            'Animalia',
            '',
            **{
                'is_root_taxon':True
            }
        )
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        animalia_db = models.TaxonTreeModel.objects.get(taxon_latname='Animalia')
        animalia = LazyTaxon(instance=animalia_db)
        
        entry = self.create_navigation_entry(taxon=animalia)
        
        self.assertEqual(entry.matching_custom_taxa, [animalia_ct])
    
    @test_settings
    def test_combined_taxa(self):
        ct_models = TaxonomyModelRouter('taxonomy.sources.custom')
        animalia_ct = ct_models.TaxonTreeModel.objects.create(
            'Animalia',
            '',
            **{
                'is_root_taxon':True
            }
        )
        
        lazy_animalia_ct = LazyTaxon(instance=animalia_ct)
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        animalia_db = models.TaxonTreeModel.objects.get(taxon_latname='Animalia')
        animalia = LazyTaxon(instance=animalia_db)
        
        entry = self.create_navigation_entry(taxon=animalia)
        
        self.assertEqual(entry.combined_taxa, [animalia, lazy_animalia_ct])
    
    
    @test_settings
    def test_attached_taxon_profiles(self):
        models = TaxonomyModelRouter('taxonomy.sources.col')
        aves_db = models.TaxonTreeModel.objects.get(taxon_latname='Aves')
        aves = LazyTaxon(instance=aves_db)
        
        # 3 types: col by nuid, custom by nuid and custom by name
        
        entry = self.create_navigation_entry()
        
        c1 = self.create_navigation_entry(parent=entry)
        
        # add aves
        aves_link = TaxonProfilesNavigationEntryTaxa(
            navigation_entry=c1,
        )
            
        aves_link.set_taxon(aves)
        aves_link.save()
        
        # add lacerta
        lacerta = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta')
        lacerta_link = TaxonProfilesNavigationEntryTaxa(
            navigation_entry=c1,
        )
            
        lacerta_link.set_taxon(LazyTaxon(instance=lacerta))
        lacerta_link.save()
        
        
        # create a custom taxon with lacerta
        custom_taxa = TaxonomyModelRouter('taxonomy.sources.custom')
        
        
        root_taxon = custom_taxa.TaxonTreeModel.objects.create(
            'Lacerta',
            '',
            **{
                'is_root_taxon':True
            }
        )
        
        lacerta_agilis_custom = custom_taxa.TaxonTreeModel.objects.create(
            'Lacerta agilis custom',
            '',
            **{
                'parent':root_taxon,
            }
        )

        lacerta_agilis_custom.save()
        
        
        # create 2 Taxon Profiles: one aves an one lacerta agilis custom
        taxon_profiles = self.get_taxon_profiles()

        pica_pica = models.TaxonTreeModel.objects.get(taxon_latname='Pica pica')
        aves_profile = TaxonProfile(
            taxon_profiles=taxon_profiles,
            taxon=LazyTaxon(instance=pica_pica),
        )

        aves_profile.save()
        
        custom_lacerta_profile = TaxonProfile(
            taxon_profiles=taxon_profiles,
            taxon=LazyTaxon(instance=lacerta_agilis_custom),
        )

        custom_lacerta_profile.save()
        
        self.assertEqual(list(c1.attached_taxon_profiles), [aves_profile, custom_lacerta_profile])
    
    # test a mix: a node has both groups and attached taxon profile    
    @test_settings
    def test_attached_taxon_profiles_mixed(self):
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        chordata_db = models.TaxonTreeModel.objects.get(taxon_latname='Chordata')
        chordata = LazyTaxon(instance=chordata_db)
        
        plantae_db = models.TaxonTreeModel.objects.get(taxon_latname='Plantae')
        plantae = LazyTaxon(instance=plantae_db)
        
        aves_db = models.TaxonTreeModel.objects.get(taxon_latname='Aves')
        aves = LazyTaxon(instance=aves_db)
        
        pinus_db = models.TaxonTreeModel.objects.get(taxon_latname='Pinus')
        pinus = LazyTaxon(instance=pinus_db)
        
        # 3 types: col by nuid, custom by nuid and custom by name
        
        entry = self.create_navigation_entry(taxon=chordata)
        
        plantae_link = TaxonProfilesNavigationEntryTaxa(
            navigation_entry=entry,
        )
            
        plantae_link.set_taxon(plantae)
        plantae_link.save()
        
        c1 = self.create_navigation_entry(parent=entry, taxon=aves)
        c2 = self.create_navigation_entry(parent=c1, taxon=pinus)        
        
        # add three taxon profiles: one aves, one col lactera, one custom lacerta
        taxon_profiles = self.get_taxon_profiles()
        pica_pica = models.TaxonTreeModel.objects.get(taxon_latname='Pica pica')
        aves_profile = TaxonProfile(
            taxon_profiles=taxon_profiles,
            taxon=LazyTaxon(instance=pica_pica),
        )

        aves_profile.save()
        
        # turdus merula profile
        pinus_sylvestris = models.TaxonTreeModel.objects.get(taxon_latname='Pinus sylvestris')
        pinus_sylvestris_profile = TaxonProfile(
            taxon_profiles=taxon_profiles,
            taxon=LazyTaxon(instance=pinus_sylvestris),
        )

        pinus_sylvestris_profile.save()
                
        # col chordate
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        chordate_col_profile = TaxonProfile(
            taxon_profiles=taxon_profiles,
            taxon=LazyTaxon(instance=lacerta_agilis),
        )

        chordate_col_profile.save()
        
        # custom chordata
        custom_taxa = TaxonomyModelRouter('taxonomy.sources.custom')
        root_taxon = custom_taxa.TaxonTreeModel.objects.create(
            'Chordata',
            '',
            **{
                'is_root_taxon':True
            }
        )
        
        lacerta_agilis_custom = custom_taxa.TaxonTreeModel.objects.create(
            'Lacerta agilis custom',
            '',
            **{
                'parent':root_taxon,
            }
        )

        lacerta_agilis_custom.save()
        
        custom_lacerta_profile = TaxonProfile(
            taxon_profiles=taxon_profiles,
            taxon=LazyTaxon(instance=lacerta_agilis_custom),
        )

        custom_lacerta_profile.save()
        
        attached_profiles = entry.attached_taxon_profiles
        
        self.assertEqual(attached_profiles, [chordate_col_profile, custom_lacerta_profile])
    
    @test_settings
    def test_branch(self):
        
        entry = self.create_navigation_entry(name='root')
        
        d1 = self.create_navigation_entry(parent=entry, name='d1')
        d2 = self.create_navigation_entry(parent=d1, name='d2')
        d3 = self.create_navigation_entry(parent=d2, name='d3')
        
        branch = d3.branch
        
        self.assertEqual(branch, [entry, d1, d2, d3])
        
    @test_settings
    def test_descendants(self):
        entry = self.create_navigation_entry(name='root')
        
        entry_2 = self.create_navigation_entry(name='root2')
        d11 = self.create_navigation_entry(parent=entry_2, name='d1')
        
        d1 = self.create_navigation_entry(parent=entry, name='d1')
        d2 = self.create_navigation_entry(parent=d1, name='d2')
        d3 = self.create_navigation_entry(parent=d2, name='d3')
        d4 = self.create_navigation_entry(parent=d2, name='d4')
        d5 = self.create_navigation_entry(parent=d3, name='d5')
        
        descendants = entry.get_descendants()
        
        self.assertEqual(list(descendants), [d1, d2, d3, d4, d5])
        
    
    @test_settings
    def test_change_publication_status(self):
        
        entry = self.create_navigation_entry(name='root')
        
        d1 = self.create_navigation_entry(parent=entry, name='d1')
        d2 = self.create_navigation_entry(parent=d1, name='d2')
        d3 = self.create_navigation_entry(parent=d2, name='d3')
        
        nodes = [entry, d1, d2, d3]
        
        for node in nodes:
            self.assertEqual(node.publication_status, 'publish')
        
        entry.change_publication_status('draft')
        
        for node in nodes:
            node.refresh_from_db()
            self.assertEqual(node.publication_status, ('draft'))
            
            
    @test_settings
    def test_unpublish_publish(self):
        
        entry = self.create_navigation_entry(name='root')
        
        d1 = self.create_navigation_entry(parent=entry, name='d1')
        d2 = self.create_navigation_entry(parent=d1, name='d2')
        d3 = self.create_navigation_entry(parent=d2, name='d3')
        
        nodes = [entry, d1, d2, d3]
        
        for node in nodes:
            self.assertEqual(node.publication_status, 'publish')
        
        entry.unpublish()
        
        for node in nodes:
            node.refresh_from_db()
            self.assertEqual(node.publication_status, ('draft'))
            
            
        entry.publish()
        
        for node in nodes:
            node.refresh_from_db()
            self.assertEqual(node.publication_status, ('publish'))


class TestTaxonTextTypeCategory(WithTaxonProfiles, WithMetaApp, TenantTestCase):
    
    @test_settings
    def test_str(self):
        
        taxon_profiles = self.get_taxon_profiles()
        
        name = 'Test category'
        
        category = TaxonTextTypeCategory(
            taxon_profiles=taxon_profiles,
            name=name,
        )
        
        category.save()
        
        self.assertEqual(str(category), name)
    
    
    @test_settings
    def test_taxon_text_type(self):
        
        taxon_profiles = self.get_taxon_profiles()
        
        category = TaxonTextTypeCategory(
            taxon_profiles=taxon_profiles,
            name='category name',
        )
        
        category.save()
        
        
        text_type = TaxonTextType(
            taxon_profiles=taxon_profiles,
            text_type='Test text type',
            category=category,
        )
        
        text_type.save()
        
        self.assertEqual(text_type.category, category)