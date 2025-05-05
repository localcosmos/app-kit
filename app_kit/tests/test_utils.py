from django_tenants.test.cases import TenantTestCase

from django.contrib.contenttypes.models import ContentType

from app_kit.tests.common import test_settings
from app_kit.tests.mixins import (WithMetaApp, WithUser)

from app_kit.utils import get_generic_content_meta_app, get_content_instance_meta_app

from app_kit.generic import AppContentTaxonomicRestriction
from app_kit.models import MetaAppGenericContent
from app_kit.features.backbonetaxonomy.models import BackboneTaxa
from app_kit.features.taxon_profiles.models import (TaxonProfiles, TaxonProfile, TaxonProfilesNavigation,
                                TaxonProfilesNavigationEntry, TaxonProfilesNavigationEntryTaxa)
from app_kit.features.nature_guides.models import NatureGuide, MetaNode
from app_kit.features.maps.models import Map, MapTaxonomicFilter, FilterTaxon
from app_kit.features.generic_forms.models import GenericForm, GenericField, GenericFieldToGenericForm
from app_kit.features.frontend.models import Frontend
from app_kit.features.glossary.models import Glossary

from taxonomy.models import TaxonomyModelRouter
from taxonomy.lazy import LazyTaxon

class TestGetGenericContentMetaApp(WithMetaApp, WithUser, TenantTestCase):
    
    @test_settings
    def test_backbone_taxonomy(self):
        
        bbt = self.meta_app.backbone()
        
        meta_app = get_generic_content_meta_app(bbt)
        self.assertEqual(meta_app, self.meta_app)
        

class TestGetContentInstanceMetaApp(WithMetaApp, WithUser, TenantTestCase):
    
    def setUp(self):
        super().setUp()
        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis_db = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        self.lacerta_agilis = LazyTaxon(instance=lacerta_agilis_db)
        
    
    @test_settings
    def test_app_content_taxonomic_restriction(self):
        
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
        
        meta_app = get_content_instance_meta_app(app_content_taxonomic_restriction)
        self.assertEqual(meta_app, self.meta_app)
        
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
        meta_app = get_content_instance_meta_app(generic_field_taxonomic_restriction)
        self.assertEqual(meta_app, self.meta_app)
    
    @test_settings
    def test_backbone_taxa(self):
        backbone_taxonomy = self.meta_app.backbone()
        backbone_taxon = BackboneTaxa(
            backbonetaxonomy = backbone_taxonomy,
        )
        
        backbone_taxon.set_taxon(self.lacerta_agilis)
        backbone_taxon.save()
        meta_app = get_content_instance_meta_app(backbone_taxon)
        self.assertEqual(meta_app, self.meta_app)
    
    @test_settings
    def test_filter_taxon(self):
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
        filter_taxon.set_taxon(self.lacerta_agilis)
        filter_taxon.save()
        meta_app = get_content_instance_meta_app(filter_taxon)
        self.assertEqual(meta_app, self.meta_app)
        
    @test_settings
    def test_taxon_profile(self):
        
        taxon_profiles_links = self.meta_app.get_generic_content_links(TaxonProfiles)
        taxon_profiles_link = taxon_profiles_links.first()
        taxon_profiles = taxon_profiles_link.generic_content
        
        taxon_profile = TaxonProfile(
            taxon_profiles=taxon_profiles,
        )
        taxon_profile.set_taxon(self.lacerta_agilis)
        taxon_profile.save()
        
        meta_app = get_content_instance_meta_app(taxon_profile)
        self.assertEqual(meta_app, self.meta_app)
        
    @test_settings
    def test_taxon_profiles_navigation_entry_taxa(self):
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
        tpne_taxa.set_taxon(self.lacerta_agilis)
        tpne_taxa.save()
        meta_app = get_content_instance_meta_app(tpne_taxa)
        self.assertEqual(meta_app, self.meta_app)
        
    @test_settings
    def test_meta_node(self):
        nature_guide = NatureGuide.objects.create(
            name='Test Nature Guide',
            primary_language=self.meta_app.primary_language,
        )
        ng_link = MetaAppGenericContent.objects.create(
            meta_app=self.meta_app,
            content_type=ContentType.objects.get_for_model(NatureGuide),
            object_id=nature_guide.id,
        )
        ng_link.save()
        
        meta_node = MetaNode(
            nature_guide=nature_guide,
        )
        meta_node.set_taxon(self.lacerta_agilis)
        meta_node.save()
        
        meta_app = get_content_instance_meta_app(meta_node)
        self.assertEqual(meta_app, self.meta_app)
    
    @test_settings
    def test_backbone_taxonomy(self):
        
        bbt = self.meta_app.backbone()
        
        meta_app = get_content_instance_meta_app(bbt)
        self.assertEqual(meta_app, self.meta_app)
        
    @test_settings
    def test_taxon_profiles(self):
        
        taxon_profiles_links = self.meta_app.get_generic_content_links(TaxonProfiles)
        taxon_profiles = taxon_profiles_links.first().generic_content
        
        meta_app = get_content_instance_meta_app(taxon_profiles)
        self.assertEqual(meta_app, self.meta_app)
        
    @test_settings
    def test_nature_guide(self):
        
        nature_guide = NatureGuide.objects.create(
            name='Test Nature Guide',
            primary_language=self.meta_app.primary_language,
        )
        
        ng_link = MetaAppGenericContent.objects.create(
            meta_app=self.meta_app,
            content_type=ContentType.objects.get_for_model(NatureGuide),
            object_id=nature_guide.id,
        )
        ng_link.save()
        
        meta_app = get_content_instance_meta_app(nature_guide)
        self.assertEqual(meta_app, self.meta_app)
        
    @test_settings
    def test_map(self):
        
        map = Map.objects.create(
            name='Test Map',
            primary_language=self.meta_app.primary_language,
        )
        
        map_link = MetaAppGenericContent.objects.create(
            meta_app=self.meta_app,
            content_type=ContentType.objects.get_for_model(Map),
            object_id=map.id,
        )
        map_link.save()
        
        meta_app = get_content_instance_meta_app(map)
        self.assertEqual(meta_app, self.meta_app)

    @test_settings
    def test_generic_form(self):
        
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
        
        meta_app = get_content_instance_meta_app(generic_form)
        self.assertEqual(meta_app, self.meta_app)
        
    @test_settings
    def test_frontend(self):
        frontend_links = self.meta_app.get_generic_content_links(Frontend)
        frontend = frontend_links.first().generic_content
        meta_app = get_content_instance_meta_app(frontend)
        self.assertEqual(meta_app, self.meta_app)
        
    @test_settings
    def test_glossary(self):
        
        glossary = Glossary.objects.create(
            name='Test Glossary',
            primary_language=self.meta_app.primary_language,
        )
        
        meta_app = get_content_instance_meta_app(glossary)
        self.assertEqual(meta_app, None)
        
        glossary_link = MetaAppGenericContent.objects.create(
            meta_app=self.meta_app,
            content_type=ContentType.objects.get_for_model(Glossary),
            object_id=glossary.id,
        )
        glossary_link.save()
        meta_app = get_content_instance_meta_app(glossary)
        self.assertEqual(meta_app, self.meta_app)