from django_tenants.test.cases import TenantTestCase
from django.contrib.contenttypes.models import ContentType
from app_kit.tests.common import test_settings
from app_kit.tests.mixins import (WithMetaApp, WithUser, WithImageStore, WithMedia)

from app_kit.features.backbonetaxonomy.models import BackboneTaxa
from app_kit.features.taxon_profiles.models import (TaxonProfiles, TaxonProfile, TaxonProfilesNavigation,
                                    TaxonProfilesNavigationEntry, TaxonProfilesNavigationEntryTaxa)
from app_kit.features.maps.models import FilterTaxon, Map, MapTaxonomicFilter
from app_kit.features.generic_forms.models import GenericForm, GenericField, GenericFieldToGenericForm
from app_kit.generic import AppContentTaxonomicRestriction
from app_kit.features.nature_guides.models import MetaNode, NatureGuide
from app_kit.models import ImageStore, MetaAppGenericContent

from localcosmos_server.models import TaxonomicRestriction
from localcosmos_server.datasets.models import Dataset, DatasetValidationRoutine
from localcosmos_server.models import ServerImageStore

from app_kit.features.backbonetaxonomy.utils import TaxonManager, TaxonReferencesUpdater

from taxonomy.models import TaxonomyModelRouter
from taxonomy.lazy import LazyTaxon

ALL_TAXON_MODELS = [
    BackboneTaxa,
    TaxonProfile,
    TaxonProfilesNavigationEntryTaxa,
    FilterTaxon,
    TaxonomicRestriction,
    AppContentTaxonomicRestriction,
    Dataset,
    DatasetValidationRoutine,
    MetaNode,
    ServerImageStore,
    ImageStore
]

class TestTaxonManager(WithImageStore, WithMedia, WithMetaApp, WithUser, TenantTestCase):
    
    def setUp(self):
        super().setUp()
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        lacerta_agilis_db = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        self.lacerta_agilis = LazyTaxon(instance=lacerta_agilis_db)
        
        picea_abies_db = models.TaxonTreeModel.objects.get(taxon_latname='Picea abies')
        self.picea_abies = LazyTaxon(instance=picea_abies_db)
        
        self.superuser = self.create_superuser()
        self.user = self.create_user()
    
    @test_settings
    def test_init(self):
        taxon_manager = TaxonManager(self.meta_app)
        
        self.assertEqual(taxon_manager.meta_app, self.meta_app)
        self.assertIsInstance(taxon_manager, TaxonManager)
        
    @test_settings
    def test_get_taxon_models(self):
        taxon_manager = TaxonManager(self.meta_app)
        
        taxon_models = taxon_manager.get_taxon_models()
        
        expected_models = set(ALL_TAXON_MODELS)
        self.assertEqual(set(taxon_models), expected_models)
    
    @test_settings
    def test_get_BackboneTaxa_occurrences(self):
        taxon_manager = TaxonManager(self.meta_app)
        
        occurrence_qry = taxon_manager.get_base_occurrence_query(BackboneTaxa, self.picea_abies)
        occurrences = taxon_manager._get_BackboneTaxa_occurrences(occurrence_qry)
        
        self.assertEqual(list(occurrences), [])
        
        backbonetaxnomy = self.meta_app.backbone()
        
        backbone_taxon = BackboneTaxa(
            backbonetaxonomy=backbonetaxnomy,
        )
        
        backbone_taxon.set_taxon(self.picea_abies)
        backbone_taxon.save()
        
        occurrences = taxon_manager._get_BackboneTaxa_occurrences(occurrence_qry)
        
        expected_occurrences = [backbone_taxon]
        
        self.assertEqual(list(occurrences), expected_occurrences)
        
    
    @test_settings
    def test_get_TaxonProfile_occurrences(self):
        taxon_manager = TaxonManager(self.meta_app)
        
        occurrence_qry = taxon_manager.get_base_occurrence_query(TaxonProfile, self.picea_abies)
        occurrences = taxon_manager._get_TaxonProfile_occurrences(occurrence_qry)
        self.assertEqual(list(occurrences), [])
        
        taxon_profiles_links = self.meta_app.get_generic_content_links(TaxonProfiles)
        taxon_profiles_link = taxon_profiles_links.first()
        taxon_profiles = taxon_profiles_link.generic_content
        taxon_profile = TaxonProfile(
            taxon_profiles=taxon_profiles,
        )
        taxon_profile.set_taxon(self.picea_abies)
        taxon_profile.save()
        occurrences = taxon_manager._get_TaxonProfile_occurrences(occurrence_qry)
        expected_occurrences = [taxon_profile]
        self.assertEqual(list(occurrences), expected_occurrences)
        
    @test_settings
    def test_get_TaxonProfilesNavigationEntryTaxa_occurrences(self):
        taxon_manager = TaxonManager(self.meta_app)
        
        occurrence_qry = taxon_manager.get_base_occurrence_query(TaxonProfilesNavigationEntryTaxa, self.picea_abies)
        occurrences = taxon_manager._get_TaxonProfilesNavigationEntryTaxa_occurrences(occurrence_qry)
        self.assertEqual(list(occurrences), [])
        
        taxon_profiles_links = self.meta_app.get_generic_content_links(TaxonProfiles)
        taxon_profiles_link = taxon_profiles_links.first()
        taxon_profiles = taxon_profiles_link.generic_content
        taxon_profiles_navigation = TaxonProfilesNavigation(
            taxon_profiles = taxon_profiles,
        )
        taxon_profiles_navigation.save()
        
        tpn_entry = TaxonProfilesNavigationEntry(
            navigation=taxon_profiles_navigation,
        )
        tpn_entry.save()
        
        tpne_taxa = TaxonProfilesNavigationEntryTaxa(
            navigation_entry=tpn_entry,
        )
        tpne_taxa.set_taxon(self.picea_abies)
        tpne_taxa.save()
        occurrences = taxon_manager._get_TaxonProfilesNavigationEntryTaxa_occurrences(occurrence_qry)
        expected_occurrences = [tpne_taxa]
        self.assertEqual(list(occurrences), expected_occurrences)
        
    @test_settings
    def test_get_FilterTaxon_occurrences(self):
        taxon_manager = TaxonManager(self.meta_app)
        
        occurrence_qry = taxon_manager.get_base_occurrence_query(FilterTaxon, self.picea_abies)
        occurrences = taxon_manager._get_FilterTaxon_occurrences(occurrence_qry)
        self.assertEqual(list(occurrences), [])
        
        map = Map.objects.create(name='Map', primary_language=self.meta_app.primary_language)
        map_link = MetaAppGenericContent.objects.create(
            meta_app=self.meta_app,
            content_type=ContentType.objects.get_for_model(Map),
            object_id=map.id,
        )
        
        map_filter = MapTaxonomicFilter(
            map=map,
            name='Filter',
        )
        map_filter.save()
        
        filter_taxon = FilterTaxon(
            taxonomic_filter=map_filter,
        )
        filter_taxon.set_taxon(self.picea_abies)
        filter_taxon.save()
        occurrences = taxon_manager._get_FilterTaxon_occurrences(occurrence_qry)
        expected_occurrences = [filter_taxon]
        self.assertEqual(list(occurrences), expected_occurrences)
        
    @test_settings
    def test_get_MetaNode_occurrences(self):
        taxon_manager = TaxonManager(self.meta_app)
        
        occurrence_qry = taxon_manager.get_base_occurrence_query(MetaNode, self.picea_abies)
        occurrences = taxon_manager._get_MetaNode_occurrences(occurrence_qry)
        self.assertEqual(list(occurrences), [])
        
        nature_guide = NatureGuide.objects.create(name='Nature Guide', primary_language=self.meta_app.primary_language)
        
        ng_link = MetaAppGenericContent.objects.create(
            meta_app=self.meta_app,
            content_type=ContentType.objects.get_for_model(NatureGuide),
            object_id=nature_guide.id,
        )
        
        meta_node = MetaNode(
            nature_guide=nature_guide,
        )
        meta_node.set_taxon(self.picea_abies)
        meta_node.save()

        occurrences = taxon_manager._get_MetaNode_occurrences(occurrence_qry)
        expected_occurrences = [meta_node]
        self.assertEqual(list(occurrences), expected_occurrences)
        
    @test_settings
    def test_get_AppContentTaxonomicRestriction_occurrences(self):
        taxon_manager = TaxonManager(self.meta_app)
        
        occurrence_qry = taxon_manager.get_base_occurrence_query(AppContentTaxonomicRestriction, self.lacerta_agilis)
        occurrences = taxon_manager._get_AppContentTaxonomicRestriction_occurrences(occurrence_qry)
        self.assertEqual(list(occurrences), [])
        
        generic_form = GenericForm.objects.create(
            name='Test Generic Form',
            primary_language=self.meta_app.primary_language,
        )
        form_link = MetaAppGenericContent.objects.create(
            meta_app=self.meta_app,
            content_type=ContentType.objects.get_for_model(GenericForm),
            object_id=generic_form.id,
        )
        form_link.save()

        
        app_content_taxonomic_restriction = AppContentTaxonomicRestriction(
            content_type=ContentType.objects.get_for_model(GenericForm),
            object_id=generic_form.id,
        )
        app_content_taxonomic_restriction.set_taxon(self.lacerta_agilis)
        app_content_taxonomic_restriction.save()
        
        
        occurrence_qry = taxon_manager.get_base_occurrence_query(AppContentTaxonomicRestriction, self.lacerta_agilis)        
        occurrences = taxon_manager._get_AppContentTaxonomicRestriction_occurrences(occurrence_qry)
        expected_occurrences = [app_content_taxonomic_restriction]
        self.assertEqual(list(occurrences), expected_occurrences)
        
        
        # field restriction
        
        generic_field = GenericField(
            field_class='CharField',
            render_as='TextInput',
            label='Test Field',
        )
        generic_field.save(generic_form)
        field_link = GenericFieldToGenericForm(
            generic_form=generic_form,
            generic_field=generic_field,
        )
        field_link.save()
        generic_field_taxonomic_restriction = AppContentTaxonomicRestriction(
            content_type=ContentType.objects.get_for_model(GenericField),
            object_id=generic_field.id,
        )
        generic_field_taxonomic_restriction.set_taxon(self.lacerta_agilis)
        generic_field_taxonomic_restriction.save()
        
        occurrence_qry = taxon_manager.get_base_occurrence_query(AppContentTaxonomicRestriction, self.lacerta_agilis)
        occurrences = taxon_manager._get_AppContentTaxonomicRestriction_occurrences(occurrence_qry)
        expected_occurrences = [app_content_taxonomic_restriction, generic_field_taxonomic_restriction]

        self.assertEqual(list(occurrences), expected_occurrences)
        
        
    @test_settings
    def test_get_ImageStore_occurrences(self):
        taxon_manager = TaxonManager(self.meta_app)
        
        occurrence_qry = taxon_manager.get_base_occurrence_query(ImageStore, self.picea_abies)
        occurrences = taxon_manager._get_ImageStore_occurrences(occurrence_qry)
        self.assertEqual(list(occurrences), [])
        
        
        # create image stores
        # taxon image
        lacerta_agilis_image_store = self.create_image_store_with_taxon(lazy_taxon=self.lacerta_agilis)
        picea_abies_image_store = self.create_image_store_with_taxon(lazy_taxon=self.picea_abies)


        # add image to nature guide meta node
        nature_guide = NatureGuide.objects.create(name='Nature Guide', primary_language=self.meta_app.primary_language)
        
        ng_link = MetaAppGenericContent.objects.create(
            meta_app=self.meta_app,
            content_type=ContentType.objects.get_for_model(NatureGuide),
            object_id=nature_guide.id,
        )
        
        meta_node = MetaNode(
            nature_guide=nature_guide,
        )
        meta_node.save()
        
        meta_node_image = self.create_content_image(meta_node, self.user, image_store=lacerta_agilis_image_store)
        
        lacerta_agilis_occurrence_qry = taxon_manager.get_base_occurrence_query(ImageStore, self.lacerta_agilis)
        occurrences = taxon_manager._get_ImageStore_occurrences(lacerta_agilis_occurrence_qry)

        expected_occurrences = [lacerta_agilis_image_store]
        self.assertEqual(list(occurrences), expected_occurrences)
        
        
        taxon_profiles_links = self.meta_app.get_generic_content_links(TaxonProfiles)
        taxon_profiles_link = taxon_profiles_links.first()
        taxon_profiles = taxon_profiles_link.generic_content
        taxon_profile = TaxonProfile(
            taxon_profiles=taxon_profiles,
        )
        taxon_profile.set_taxon(self.picea_abies)
        taxon_profile.save()
        
        taxon_profile_image = self.create_content_image(taxon_profile, self.user, image_store=picea_abies_image_store)

        occurrence_qry = taxon_manager.get_base_occurrence_query(ImageStore, self.picea_abies)
        occurrences = taxon_manager._get_ImageStore_occurrences(occurrence_qry)
        self.assertEqual(list(occurrences), [picea_abies_image_store])
        
    
    def create_all_contents(self):
        backbonetaxnomy = self.meta_app.backbone()
        
        backbone_taxon = BackboneTaxa(
            backbonetaxonomy=backbonetaxnomy,
        )
        
        backbone_taxon.set_taxon(self.picea_abies)
        backbone_taxon.save()
        
        taxon_profiles_links = self.meta_app.get_generic_content_links(TaxonProfiles)
        taxon_profiles_link = taxon_profiles_links.first()
        taxon_profiles = taxon_profiles_link.generic_content
        taxon_profile = TaxonProfile(
            taxon_profiles=taxon_profiles,
        )
        taxon_profile.set_taxon(self.picea_abies)
        taxon_profile.save()
        
        taxon_profiles_navigation = TaxonProfilesNavigation(
            taxon_profiles = taxon_profiles,
        )
        taxon_profiles_navigation.save()
        tpn_entry = TaxonProfilesNavigationEntry(
            navigation=taxon_profiles_navigation,
        )
        tpn_entry.save()
        tpne_taxa = TaxonProfilesNavigationEntryTaxa(
            navigation_entry=tpn_entry,
        )
        tpne_taxa.set_taxon(self.picea_abies)
        tpne_taxa.save()
        
        map = Map.objects.create(name='Map', primary_language=self.meta_app.primary_language)
        map_link = MetaAppGenericContent.objects.create(
            meta_app=self.meta_app,
            content_type=ContentType.objects.get_for_model(Map),
            object_id=map.id,
        )
        map_link.save()
        map_filter = MapTaxonomicFilter(
            map=map,
            name='Filter',
        )
        map_filter.save()
        filter_taxon = FilterTaxon(
            taxonomic_filter=map_filter,
        )
        filter_taxon.set_taxon(self.picea_abies)
        filter_taxon.save()
        
        nature_guide = NatureGuide.objects.create(name='Nature Guide', primary_language=self.meta_app.primary_language)
        ng_link = MetaAppGenericContent.objects.create(
            meta_app=self.meta_app,
            content_type=ContentType.objects.get_for_model(NatureGuide),
            object_id=nature_guide.id,
        )
        ng_link.save()
        meta_node = MetaNode(
            nature_guide=nature_guide,
        )
        meta_node.set_taxon(self.picea_abies)
        meta_node.save()
        
        generic_form = GenericForm.objects.create(
            name='Test Generic Form',
            primary_language=self.meta_app.primary_language,
        )
        form_link = MetaAppGenericContent.objects.create(
            meta_app=self.meta_app,
            content_type=ContentType.objects.get_for_model(GenericForm),
            object_id=generic_form.id,
        )
        form_link.save()
        app_content_taxonomic_restriction = AppContentTaxonomicRestriction(
            content_type=ContentType.objects.get_for_model(GenericForm),
            object_id=generic_form.id,
        )
        app_content_taxonomic_restriction.set_taxon(self.picea_abies)
        app_content_taxonomic_restriction.save()
        generic_field = GenericField(
            field_class='CharField',
            render_as='TextInput',
            label='Test Field',
        )
        generic_field.save(generic_form)
        field_link = GenericFieldToGenericForm(
            generic_form=generic_form,
            generic_field=generic_field,
        )
        field_link.save()
        generic_field_taxonomic_restriction = AppContentTaxonomicRestriction(
            content_type=ContentType.objects.get_for_model(GenericField),
            object_id=generic_field.id,
        )
        generic_field_taxonomic_restriction.set_taxon(self.picea_abies)
        generic_field_taxonomic_restriction.save()
        
        # create image stores
        # taxon image
        picea_abies_image_store = self.create_image_store_with_taxon(lazy_taxon=self.picea_abies)
        meta_node_image = self.create_content_image(meta_node, self.user, image_store=picea_abies_image_store)
        
        return backbone_taxon, taxon_profile, tpne_taxa, filter_taxon, meta_node, app_content_taxonomic_restriction, generic_field_taxonomic_restriction, picea_abies_image_store
        
    
    @test_settings
    def test_get_taxon_occurrences(self):
                
        backbone_taxon, taxon_profile, tpne_taxa, filter_taxon, meta_node, app_content_taxonomic_restriction, generic_field_taxonomic_restriction, picea_abies_image_store = self.create_all_contents()

        taxon_manager = TaxonManager(self.meta_app)
        occurrences = taxon_manager.get_taxon_occurrences(self.picea_abies)
        
        for occurrence_entry in occurrences:
            occurrence_entry['occurrences'] = list(occurrence_entry['occurrences'])
        
        expected_occurrences = [
            {
                'model': BackboneTaxa,
                'occurrences': [backbone_taxon]
            },
            {
                'model': TaxonProfile,
                'occurrences': [taxon_profile]
            },
            {
                'model': TaxonProfilesNavigationEntryTaxa,
                'occurrences': [tpne_taxa]
            },
            {
                'model': FilterTaxon,
                'occurrences': [filter_taxon]
            },
            {
                'model': AppContentTaxonomicRestriction,
                'occurrences': [
                    app_content_taxonomic_restriction,
                    generic_field_taxonomic_restriction
                ],
            },
            {
                'model': MetaNode,
                'occurrences': [meta_node]
            },
            {
                'model': ImageStore,
                'occurrences': [picea_abies_image_store]
            }
        ]
        
        self.assertEqual(occurrences, expected_occurrences)
    
    @test_settings
    def test_swap(self):
        
        backbone_taxon, taxon_profile, tpne_taxa, filter_taxon, meta_node, app_content_taxonomic_restriction, generic_field_taxonomic_restriction, picea_abies_image_store = self.create_all_contents()

        
        taxon_manager = TaxonManager(self.meta_app)
        
        taxon_manager.swap_taxon(self.picea_abies, self.lacerta_agilis)

        backbone_taxon = BackboneTaxa.objects.get(id=backbone_taxon.id)
        taxon_profile = TaxonProfile.objects.get(id=taxon_profile.id)
        tpne_taxa = TaxonProfilesNavigationEntryTaxa.objects.get(id=tpne_taxa.id)
        filter_taxon = FilterTaxon.objects.get(id=filter_taxon.id)
        meta_node = MetaNode.objects.get(id=meta_node.id)
        app_content_taxonomic_restriction = AppContentTaxonomicRestriction.objects.get(id=app_content_taxonomic_restriction.id)
        generic_field_taxonomic_restriction = AppContentTaxonomicRestriction.objects.get(id=generic_field_taxonomic_restriction.id)
        picea_abies_image_store = ImageStore.objects.get(id=picea_abies_image_store.id)

        self.assertEqual(backbone_taxon.taxon, self.lacerta_agilis)
        self.assertEqual(taxon_profile.taxon, self.lacerta_agilis)
        self.assertEqual(tpne_taxa.taxon, self.lacerta_agilis)
        self.assertEqual(filter_taxon.taxon, self.lacerta_agilis)
        self.assertEqual(meta_node.taxon, self.lacerta_agilis)
        self.assertEqual(app_content_taxonomic_restriction.taxon, self.lacerta_agilis)
        self.assertEqual(generic_field_taxonomic_restriction.taxon, self.lacerta_agilis)
        self.assertEqual(picea_abies_image_store.taxon, self.lacerta_agilis)
        
    @test_settings
    def test_get_BackboneTaxa_occurrences_verbose(self):        
        backbonetaxnomy = self.meta_app.backbone()
        
        backbone_taxon = BackboneTaxa(
            backbonetaxonomy=backbonetaxnomy,
        )
        
        backbone_taxon.set_taxon(self.picea_abies)
        backbone_taxon.save()
        
        taxon_manager = TaxonManager(self.meta_app)
        occurrences = taxon_manager.get_taxon_occurrences(self.picea_abies)
        occurrences_verbose = taxon_manager._get_BackboneTaxa_occurrences_verbose(occurrences[0])
        
        occurrences_verbose[0]['occurrences'] = list(occurrences_verbose[0]['occurrences'])
        
        expected_occurrences = [{
            'model': BackboneTaxa,
            'occurrences': [backbone_taxon],
            'verbose_model_name': 'Backbone Taxon',
            'verbose_occurrences': ['has been manually added to the Backbone Taxonomy'],
        }]
        
        self.assertEqual(occurrences_verbose, expected_occurrences)
        
    @test_settings
    def test_get_AppContentTaxonomicRestriction_occurrences_verbose(self):
        generic_form = GenericForm.objects.create(
            name='Test Generic Form',
            primary_language=self.meta_app.primary_language,
        )
        form_link = MetaAppGenericContent.objects.create(
            meta_app=self.meta_app,
            content_type=ContentType.objects.get_for_model(GenericForm),
            object_id=generic_form.id,
        )
        form_link.save()
        
        app_content_taxonomic_restriction = AppContentTaxonomicRestriction(
            content_type=ContentType.objects.get_for_model(GenericForm),
            object_id=generic_form.id,
        )
        app_content_taxonomic_restriction.set_taxon(self.picea_abies)
        app_content_taxonomic_restriction.save()
        
        generic_field = GenericField(
            field_class='CharField',
            render_as='TextInput',
            label='Test Field',
        )
        generic_field.save(generic_form)
        field_link = GenericFieldToGenericForm(
            generic_form=generic_form,
            generic_field=generic_field,
        )
        field_link.save()
        generic_field_taxonomic_restriction = AppContentTaxonomicRestriction(
            content_type=ContentType.objects.get_for_model(GenericField),
            object_id=generic_field.id,
        )
        generic_field_taxonomic_restriction.set_taxon(self.picea_abies)
        generic_field_taxonomic_restriction.save()
        
        taxon_manager = TaxonManager(self.meta_app)
        occurrences = taxon_manager.get_taxon_occurrences(self.picea_abies)
        occurrences_verbose = taxon_manager._get_AppContentTaxonomicRestriction_occurrences_verbose(
            occurrences[0])
        
        occurrences_verbose[0]['occurrences'] = list(occurrences_verbose[0]['occurrences'])
        occurrences_verbose[1]['occurrences'] = list(occurrences_verbose[1]['occurrences'])
        
        expected_occurrences = [
            {
                'model': AppContentTaxonomicRestriction,
                'occurrences': [app_content_taxonomic_restriction],
                'verbose_model_name': 'Observation form',
                'verbose_occurrences': [
                    'acts as a taxonomic restriction of Test Generic Form'
                ]
             },
            {
                'model': AppContentTaxonomicRestriction,
                'occurrences': [generic_field_taxonomic_restriction],
                'verbose_model_name': 'Observation Form Field',
                'verbose_occurrences': ['acts as a taxonomic restriction of Test Field']
            }
        ]
        
        self.assertEqual(occurrences_verbose, expected_occurrences)
        
    @test_settings
    def test_get_TaxonProfile_occurrences_verbose(self):
        taxon_profiles_links = self.meta_app.get_generic_content_links(TaxonProfiles)
        taxon_profiles_link = taxon_profiles_links.first()
        taxon_profiles = taxon_profiles_link.generic_content
        taxon_profile = TaxonProfile(
            taxon_profiles=taxon_profiles,
        )
        taxon_profile.set_taxon(self.picea_abies)
        taxon_profile.save()
        
        taxon_manager = TaxonManager(self.meta_app)
        occurrences = taxon_manager.get_taxon_occurrences(self.picea_abies)
        occurrences_verbose = taxon_manager._get_TaxonProfile_occurrences_verbose(occurrences[0])
        
        occurrences_verbose[0]['occurrences'] = list(occurrences_verbose[0]['occurrences'])
        
        expected_occurrences = [{
            'model': TaxonProfile,
            'occurrences': [taxon_profile],
            'verbose_model_name': 'Taxon Profile',
            'verbose_occurrences': ['exists as a Taxon Profile'],
        }]
        
        self.assertEqual(occurrences_verbose, expected_occurrences)
        
    @test_settings
    def test_get_TaxonProfilesNavigationEntryTaxa_occurrences_verbose(self):
        taxon_profiles_links = self.meta_app.get_generic_content_links(TaxonProfiles)
        taxon_profiles_link = taxon_profiles_links.first()
        taxon_profiles = taxon_profiles_link.generic_content
        taxon_profiles_navigation = TaxonProfilesNavigation(
            taxon_profiles = taxon_profiles,
        )
        taxon_profiles_navigation.save()
        tpn_entry = TaxonProfilesNavigationEntry(
            navigation=taxon_profiles_navigation,
        )
        tpn_entry.save()
        tpne_taxa = TaxonProfilesNavigationEntryTaxa(
            navigation_entry=tpn_entry,
        )
        tpne_taxa.set_taxon(self.picea_abies)
        tpne_taxa.save()
        
        taxon_manager = TaxonManager(self.meta_app)
        occurrences = taxon_manager.get_taxon_occurrences(self.picea_abies)
        occurrences_verbose = taxon_manager._get_TaxonProfilesNavigationEntryTaxa_occurrences_verbose(
            occurrences[0])
        
        occurrences_verbose[0]['occurrences'] = list(occurrences_verbose[0]['occurrences'])

        expected_occurrences = [{
            'model': TaxonProfilesNavigationEntryTaxa,
            'occurrences': [tpne_taxa],
            'verbose_model_name': 'Taxon Profiles Navigation Entry Taxon',
            'verbose_occurrences': ['occurs in 1 navigation entries'],
        }]
        
        self.assertEqual(occurrences_verbose, expected_occurrences)
        
    @test_settings
    def test_get_FilterTaxon_occurrences_verbose(self):
        map = Map.objects.create(name='Map', primary_language=self.meta_app.primary_language)
        map_link = MetaAppGenericContent.objects.create(
            meta_app=self.meta_app,
            content_type=ContentType.objects.get_for_model(Map),
            object_id=map.id,
        )
        map_link.save()
        map_filter = MapTaxonomicFilter(
            map=map,
            name='Filter',
        )
        map_filter.save()
        filter_taxon = FilterTaxon(
            taxonomic_filter=map_filter,
        )
        filter_taxon.set_taxon(self.picea_abies)
        filter_taxon.save()
        
        taxon_manager = TaxonManager(self.meta_app)
        occurrences = taxon_manager.get_taxon_occurrences(self.picea_abies)
        occurrences_verbose = taxon_manager._get_FilterTaxon_occurrences_verbose(occurrences[0])
        
        occurrences_verbose[0]['occurrences'] = list(occurrences_verbose[0]['occurrences'])
        
        expected_occurrences = [{
            'model': FilterTaxon,
            'occurrences': [filter_taxon],
            'verbose_model_name': 'Map Filter Taxon',
            'verbose_occurrences': ['is a taxonomic filter of Map'],
        }]
        
        self.assertEqual(occurrences_verbose, expected_occurrences)
        
    
    @test_settings
    def test_get_MetaNode_occurrences_verbose(self):
        nature_guide = NatureGuide.objects.create(name='Nature Guide', primary_language=self.meta_app.primary_language)
        
        ng_link = MetaAppGenericContent.objects.create(
            meta_app=self.meta_app,
            content_type=ContentType.objects.get_for_model(NatureGuide),
            object_id=nature_guide.id,
        )
        
        meta_node = MetaNode(
            nature_guide=nature_guide,
        )
        meta_node.set_taxon(self.picea_abies)
        meta_node.save()
        
        taxon_manager = TaxonManager(self.meta_app)
        occurrences = taxon_manager.get_taxon_occurrences(self.picea_abies)
        occurrences_verbose = taxon_manager._get_MetaNode_occurrences_verbose(occurrences[0])
        
        occurrences_verbose[0]['occurrences'] = list(occurrences_verbose[0]['occurrences'])
        
        expected_occurrences = [{
            'model': MetaNode,
            'occurrences': [meta_node],
            'verbose_model_name': 'Nature Guide',
            'verbose_occurrences': ['occurs in Nature Guide Nature Guide'],
        }]
        
        self.assertEqual(occurrences_verbose, expected_occurrences)
        
        
class TestTaxonReferencesUpdater(WithImageStore, WithMedia, WithMetaApp, WithUser, TenantTestCase):
    
    def setUp(self):
        super().setUp()
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        
        picea_abies_db = models.TaxonTreeModel.objects.get(taxon_latname='Picea abies')
        self.picea_abies = LazyTaxon(instance=picea_abies_db)
        
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        
        taxon_profiles_links = self.meta_app.get_generic_content_links(TaxonProfiles)
        taxon_profiles_link = taxon_profiles_links.first()
        taxon_profiles = taxon_profiles_link.generic_content
        
        self.taxon_profile = TaxonProfile(
            taxon_profiles=taxon_profiles,
        )
        self.taxon_profile.set_taxon(self.picea_abies)
        self.taxon_profile.save()
        
        
    @test_settings
    def test_init(self):
        
        updater = TaxonReferencesUpdater(self.meta_app)
        self.assertEqual(updater.meta_app, self.meta_app)
        self.assertIsInstance(updater.taxon_manager, TaxonManager)
        
        
    @test_settings 
    def test_check_and_update(self):
        
        updater = TaxonReferencesUpdater(self.meta_app)
        errors = updater.check_taxa()
        self.assertEqual(errors, [])
        
        reference_lazy_taxon = LazyTaxon(instance=self.taxon_profile)
        
        outdated_taxon_kwargs = {
            'taxon_source': self.picea_abies.taxon_source,
            'taxon_latname': self.picea_abies.taxon_latname,
            'taxon_author': self.picea_abies.taxon_author,
            'taxon_nuid': '001002003',
            'name_uuid': 'aaaaaaaa-47ac-4ad4-bd6a-4158c78165be', # a uuid v4
        }
        
        outdated_lazy_taxon = LazyTaxon(**outdated_taxon_kwargs)
        self.taxon_profile.set_taxon(outdated_lazy_taxon)
        self.taxon_profile.save()
        
        taxon_profile = TaxonProfile.objects.get(id=self.taxon_profile.id)
        self.assertEqual(taxon_profile.taxon_nuid, '001002003')
        self.assertEqual(taxon_profile.name_uuid, 'aaaaaaaa-47ac-4ad4-bd6a-4158c78165be')
        
        
        errors = updater.check_taxa()
        
        expected_errors = [
            {
                'instance': self.taxon_profile,
                'taxon': outdated_lazy_taxon,
                'errors': [
                    'Taxon Picea abies (L.) H. Karst. has changed its position in Catalogue Of Life 2019',
                    'Taxon Picea abies (L.) H. Karst. has changed its identifier in Catalogue Of Life 2019'
                ],
                'updated': False
            }
        ]
        
        # check_taxa called without update=True should preserve the old taxon
        self.assertEqual(errors, expected_errors)
        
        # update = True switches from old_taxon_nuid to new
        errors = updater.check_taxa(update=True)
        
        expected_errors[0].update({
            'taxon': reference_lazy_taxon,
            'updated':True,
        })
        
        self.assertEqual(errors, expected_errors)
        
        updated_taxon_profile = TaxonProfile.objects.get(id=self.taxon_profile.id)
        self.assertEqual(updated_taxon_profile.taxon_nuid, reference_lazy_taxon.taxon_nuid)
        self.assertEqual(updated_taxon_profile.taxon_latname, reference_lazy_taxon.taxon_latname)
        self.assertEqual(updated_taxon_profile.taxon_author, reference_lazy_taxon.taxon_author)
        self.assertEqual(updated_taxon_profile.taxon_source, reference_lazy_taxon.taxon_source)
        self.assertEqual(updated_taxon_profile.name_uuid, str(reference_lazy_taxon.name_uuid))
