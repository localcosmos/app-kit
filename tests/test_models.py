from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile

# django-tentants
from django_tenants.test.cases import TenantTestCase

from app_kit.AppThemeText import AppThemeText

from app_kit.models import (ContentImageMixin, UpdateContentImageTaxonMixin, MetaAppManager, MetaApp,
                            MetaAppGenericContent, ImageStore, ContentImage, MetaCache)


from app_kit.tests.common import test_settings, TESTS_ROOT, TEST_IMAGE_PATH
from app_kit.tests.mixins import WithMetaApp, WithUser, WithMedia, WithImageStore
from app_kit.tests.cases import TransactionTenantTestCase

from localcosmos_appkit_utils.AppTheme import AppTheme

from localcosmos_server.models import App, SecondaryAppLanguages
from django_tenants.utils import get_tenant_domain_model
Domain = get_tenant_domain_model()

from app_kit.app_kit_api.models import AppKitJobs

from app_kit.appbuilders.AppBuilderBase import AppBuilderBase

from app_kit.features.backbonetaxonomy.models import BackboneTaxonomy, BackboneTaxa
from app_kit.features.taxon_profiles.models import TaxonProfiles
from app_kit.features.generic_forms.models import GenericForm, GenericField, GenericFieldToGenericForm
from app_kit.features.glossary. models import Glossary
from app_kit.features.maps.models import Map
from app_kit.features.nature_guides.models import NatureGuide, MetaNode, NatureGuidesTaxonTree
from app_kit.features.fact_sheets.models import FactSheets

from app_kit.generic import AppContentTaxonomicRestriction, LocalizeableImage

from app_kit.tests.common import (TEST_MEDIA_ROOT, TEST_IMAGE_PATH)

feature_models = [BackboneTaxonomy, TaxonProfiles, GenericForm, Glossary, Map, NatureGuide, FactSheets]

from taxonomy.lazy import LazyTaxon, LazyTaxonList
from taxonomy.models import TaxonomyModelRouter

from django.utils import timezone
from datetime import datetime
from PIL import Image

import os, shutil, inspect, time, hashlib, json
                

# for some reason, decorating TenantTestCase with @test_settings does not work
class TestCreateMetaApp(WithMedia, TenantTestCase):

    subdomain = 'testmetaapp'


    @test_settings
    def setUp(self):

        if not settings.APP_KIT_ROOT.startswith(TESTS_ROOT):
            raise ValueError('Invalid APP_KIT_ROOT setting: {1}. Does not start with: {2}'.format(
                settings.APP_KIT_ROOT, TESTS_ROOT))
        

    @test_settings
    def tearDown(self):
        if not settings.APP_KIT_ROOT.startswith(TESTS_ROOT):
            raise ValueError('Invalid APP_KIT_ROOT setting: {1}. Does not start with: {2}'.format(
                settings.APP_KIT_ROOT, TESTS_ROOT))

        if not settings.LOCALCOSMOS_APPS_ROOT.startswith(TESTS_ROOT):
            raise ValueError('Invalid LOCALCOSMOS_APPS_ROOT setting: {1}. Does not start with: {2}'.format(
                settings.LOCALCOSMOS_APPS_ROOT, TESTS_ROOT))
        
        for entry in os.scandir(settings.APP_KIT_ROOT):
            if os.path.isdir(entry.path):
                shutil.rmtree(entry.path)

        for www_entry in os.scandir(settings.LOCALCOSMOS_APPS_ROOT):
            if os.path.isdir(www_entry.path):
                shutil.rmtree(www_entry.path)


    # from TenantTestCase
    @staticmethod
    def get_test_tenant_domain():
        return 'tenant.my_domain.com'

    # from TenantTestCase
    @staticmethod
    def get_test_schema_name():
        return 'tester'

    @test_settings
    def test_create(self):

        # make sure to use the tes folders
        self.assertTrue(settings.APP_KIT_ROOT.startswith(TESTS_ROOT))

        domain_name = 'testmetaapp.my-domain.com'
        name = 'Test Meta App'
        primary_language = 'en'

        # creates App and MetaApp
        meta_app = MetaApp.objects.create(name, primary_language, domain_name, self.tenant, self.subdomain)

        app_dir = os.path.join(TESTS_ROOT, settings.APP_KIT_ROOT, str(meta_app.uuid))

        # check if App has been  created
        self.assertTrue(os.path.isdir(app_dir))

        # check app params
        self.assertEqual(meta_app.published_version, None)
        self.assertEqual(meta_app.current_version, 1)
        self.assertFalse(meta_app.is_locked)
        self.assertEqual(meta_app.global_options, {})
        self.assertEqual(meta_app.package_name, 'org.localcosmos.testmetaapp')
        self.assertEqual(meta_app.build_settings, None)
        self.assertEqual(meta_app.theme, 'Flat')
        self.assertEqual(meta_app.store_links, None)
        self.assertEqual(meta_app.appbuilder_version, '1') # CharField
        self.assertEqual(meta_app.build_status, None)
        self.assertEqual(meta_app.last_build_report, None)
        self.assertEqual(meta_app.validation_status, None)
        self.assertEqual(meta_app.last_validation_report, None)
        self.assertEqual(meta_app.last_release_report, None)
        self.assertFalse(meta_app.last_modified_at == None)

        self.assertEqual(meta_app.last_published_at, None)

        # check App
        app = meta_app.app
        self.assertEqual(meta_app.uuid, app.uuid)
        self.assertEqual(app.uid, self.subdomain)
        self.assertEqual(app.primary_language, primary_language)
        self.assertEqual(app.name, name)
        self.assertEqual(app.url, None)
        self.assertEqual(app.apk_url, None)
        self.assertEqual(app.ipa_url, None)
        self.assertEqual(app.pwa_zip_url, None)
        self.assertEqual(app.published_version, None)
        self.assertEqual(app.published_version_path, None)

        preview_path_head = os.path.join(TESTS_ROOT, settings.LOCALCOSMOS_APPS_ROOT, app.uid)
        self.assertTrue(app.preview_version_path.startswith(preview_path_head))
        self.assertTrue(app.preview_version_path.endswith('www'))
        self.assertEqual(app.review_version_path, None)

        # check Domain
        domain = Domain.objects.get(app=app)
        self.assertEqual(domain.tenant, self.tenant)
        self.assertEqual(domain.domain, domain_name)

        # it is the tenants second domain
        self.assertFalse(domain.is_primary)


        # test required generic contents for appbuilder version 1
        backbone_taxonomy_content_type = ContentType.objects.get_for_model(BackboneTaxonomy)
        bbt_link = MetaAppGenericContent.objects.get(meta_app=meta_app, content_type=backbone_taxonomy_content_type)

        backbone_taxonomy = BackboneTaxonomy.objects.get(pk=bbt_link.object_id)
        self.assertTrue(isinstance(bbt_link.generic_content, BackboneTaxonomy))

        taxon_profiles_content_type = ContentType.objects.get_for_model(TaxonProfiles)
        tp_link = MetaAppGenericContent.objects.get(meta_app=meta_app, content_type=taxon_profiles_content_type)

        taxon_profiles = TaxonProfiles.objects.get(pk=tp_link.object_id)
        self.assertTrue(isinstance(tp_link.generic_content, TaxonProfiles))
        

    @test_settings
    def test_create_with_secondary_languages(self):

        self.assertTrue(settings.APP_KIT_ROOT.startswith(TESTS_ROOT))

        domain_name = 'testmetaapp.my-domain.com'
        name = 'Test Meta App'
        primary_language = 'en'
        secondary_languages = ['de', 'fr', 'jp']

        # creates App and MetaApp
        meta_app = MetaApp.objects.create(name, primary_language, domain_name, self.tenant, self.subdomain,
                                          secondary_languages=secondary_languages)


        meta_app_secondary_languages = meta_app.secondary_languages()
        
        for language_code in secondary_languages:
            self.assertTrue(meta_app_secondary_languages.filter(language_code=language_code).exists())

        self.assertEqual(len(secondary_languages), meta_app_secondary_languages.count())
        

    @test_settings
    def test_create_with_passed_appbuilder_version(self):
        self.assertTrue(settings.APP_KIT_ROOT.startswith(TESTS_ROOT))

        domain_name = 'testmetaapp.my-domain.com'
        name = 'Test Meta App'
        primary_language = 'en'
        secondary_languages = ['de', 'fr', 'jp']

        # creates App and MetaApp
        meta_app = MetaApp.objects.create(name, primary_language, domain_name, self.tenant, self.subdomain,
                                          appbuilder_version='1')

        self.assertEqual(meta_app.appbuilder_version, '1')
        

    @test_settings
    def test_create_with_passed_global_options(self):

        self.assertTrue(settings.APP_KIT_ROOT.startswith(TESTS_ROOT))

        domain_name = 'testmetaapp.my-domain.com'
        name = 'Test Meta App'
        primary_language = 'en'
        secondary_languages = ['de', 'fr', 'jp']

        global_options = {
            'option_1' : 1,
            'option_2' : 'two',
        }

        # creates App and MetaApp
        meta_app = MetaApp.objects.create(name, primary_language, domain_name, self.tenant, self.subdomain,
                                          global_options=global_options)

        self.assertEqual(meta_app.global_options, global_options)
        
        
class TestMetaApp(WithMetaApp, WithMedia, TenantTestCase):

    def get_app_generic_content(self, ModelClass):
        content_type = ContentType.objects.get_for_model(ModelClass)
        link = MetaAppGenericContent.objects.get(meta_app=self.meta_app, content_type=content_type)
        return link.generic_content
        

    # this is a more complex method: we need to test each generic content's taxa()
    # BackboneTaxonomy, GenericForm, NatureGuide, taxon_profiles: can contain taxa
    # Glossary and Maps can not contain taxa
    def add_set_of_taxa(self):
        collected_taxa = []
        
        self.create_all_generic_contents(self.meta_app)
        
        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)

        # first, add a single backbone taxon
        backbone_taxonomy = self.get_app_generic_content(BackboneTaxonomy)
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)
        backbone_taxon = BackboneTaxa.objects.filter(taxon_latname='Lacerta agilis').first()
        if not backbone_taxon:
            backbone_taxon = BackboneTaxa(
                backbonetaxonomy = backbone_taxonomy,
                taxon=lacerta_agilis,
            )
            backbone_taxon.save()

        collected_taxa.append(lacerta_agilis)

        # second, add a generic form restriction
        generic_form = self.get_app_generic_content(GenericForm)
        # check if there is a checkbox field, if not create one
        generic_field_link = GenericFieldToGenericForm.objects.filter(generic_form=generic_form,
                                    generic_field__field_class='BooleanField').first()
        if generic_field_link:
            generic_field = generic_field_link.generic_field
        else:
            # create the field
            generic_field = GenericField(
                field_class='BooleanField',
                render_as='CheckboxInput',
                label='Oak processionary moth',
            )

            generic_field.save(generic_form)
            
            generic_field_link = GenericFieldToGenericForm(
                generic_form=generic_form,
                generic_field=generic_field,
            )
            generic_field_link.save()

        # generic_field is present. Now add the taxonomic restriction
        generic_field_type = ContentType.objects.get_for_model(GenericField)
        quercus = models.TaxonTreeModel.objects.get(taxon_latname='Quercus')
        quercus = LazyTaxon(instance=quercus)
        quercus.taxon_include_descendants = True
        taxonomic_restriction = AppContentTaxonomicRestriction(
            content_type=generic_field_type,
            object_id=generic_field.id,
            taxon=quercus,
        )

        taxonomic_restriction.save()

        collected_taxa.append(quercus)

        # nature guide: just add one node as a result
        nature_guide = self.get_app_generic_content(NatureGuide)

        turdus_merula = models.TaxonTreeModel.objects.get(taxon_latname='Turdus merula')
        turdus_merula = LazyTaxon(instance=turdus_merula)

        root_node = NatureGuidesTaxonTree.objects.get(nature_guide=nature_guide, is_root_taxon=True)

        node = NatureGuidesTaxonTree.objects.filter(
            parent=root_node, taxon_latname=turdus_merula.taxon_latname).first()
        
        if not node:
            meta_node = MetaNode(
                nature_guide = nature_guide,
                name = 'Common Blackbird',
                taxon=turdus_merula,
                node_type='result',
            )
            meta_node.save()
            
            node = NatureGuidesTaxonTree(
                nature_guide = nature_guide,
                meta_node=meta_node,
            )

            node.save(root_node)

        collected_taxa.append(turdus_merula)

        return collected_taxa

    @test_settings
    def test_uuid(self):
        self.assertEqual(self.meta_app.uuid, self.meta_app.app.uuid)

    @test_settings
    def test_name(self):
        self.assertEqual(self.meta_app.name, self.meta_app.app.name)

    @test_settings
    def test_primary_language(self):
        self.assertEqual(self.meta_app.primary_language, self.primary_language)

    @test_settings
    def test_tenant(self):
        self.assertEqual(self.meta_app.tenant, self.tenant)

    @test_settings
    def test_global_build_status(self):

        meta_app = self.meta_app

        self.assertEqual(meta_app.global_build_status, None)

        meta_app.build_status = 'in_progress'
        meta_app.save()

        self.assertEqual(meta_app.global_build_status, 'in_progress')

        meta_app.build_status = 'passing'
        meta_app.save()

        # create one in_progress job
        job = AppKitJobs(
            meta_app_uuid=meta_app.uuid,
            meta_app_definition={'test':1},
            app_version=1,
            platform='android',
            job_type='build',
        )
        job.save()

        self.assertEqual(meta_app.global_build_status, 'in_progress')
        
        job.job_result = {
            'success' : False
        }
        job.finished_at = timezone.now()
        job.save()

        self.assertEqual(meta_app.global_build_status, 'failing')

        job.job_result = 'passing'
        job.save()

        self.assertEqual(meta_app.global_build_status, 'passing')

        job.delete()

        meta_app.build_status = 'failing'
        meta_app.save()

        self.assertEqual(meta_app.global_build_status, 'failing')
        

    @test_settings
    def test_languages(self):

        meta_app = self.meta_app
        app = meta_app.app

        secondary_languages = ['de', 'fr']

        for language_code in secondary_languages:
            secondary_language = SecondaryAppLanguages(
                app=app,
                language_code=language_code,
            )
            secondary_language.save()


        languages = set(meta_app.languages())
        expected_languages = set([meta_app.primary_language] + secondary_languages)


    @test_settings
    def test_secondary_languages(self):

        meta_app = self.meta_app
        app = meta_app.app

        secondary_languages = ['de', 'fr']

        for language_code in secondary_languages:
            secondary_language = SecondaryAppLanguages(
                app=app,
                language_code=language_code,
            )
            secondary_language.save()


        languages = set(meta_app.secondary_languages())
        expected_languages = set(secondary_languages)


    @test_settings
    def test_get_theme(self):

        theme = self.meta_app.get_theme()
        self.assertEqual(theme.__class__, AppTheme)

        self. assertEqual(theme.name, 'Flat')


    @test_settings
    def test_get_preview_builder(self):

        preview_builder = self.meta_app.get_preview_builder()
        self.assertTrue(isinstance(preview_builder, AppBuilderBase))
        self.assertEqual(preview_builder.__class__.__name__, 'AppPreviewBuilder')


    @test_settings
    def test_get_release_builder(self):

        release_builder = self.meta_app.get_release_builder()
        self.assertTrue(isinstance(release_builder, AppBuilderBase))
        self.assertEqual(release_builder.__class__.__name__, 'AppReleaseBuilder')


    @test_settings
    def test_lock_and_unlock_generic_contents(self):
        
        self.create_all_generic_contents(self.meta_app)

        content_links = MetaAppGenericContent.objects.filter(meta_app=self.meta_app)
        for link in content_links:
            generic_content = link.generic_content
            self.assertFalse(generic_content.is_locked)
            
        self.meta_app.lock_generic_contents()

        for link in content_links:
            generic_content = link.generic_content
            generic_content.refresh_from_db()
            self.assertTrue(generic_content.is_locked)

        self.meta_app.unlock_generic_contents()

        for link in content_links:
            generic_content = link.generic_content
            generic_content.refresh_from_db()
            self.assertFalse(generic_content.is_locked)


    @test_settings
    def test_get_primary_localization(self):
        
        primary_localization = self.meta_app.get_primary_localization()

        self.assertIn(self.meta_app.name, primary_localization)
        self.assertEqual(primary_localization[self.meta_app.name], self.meta_app.name)

        theme = self.meta_app.get_theme()
        theme_text_types = theme.user_content['texts']

        for key, definition in theme_text_types.items():
            self.assertFalse(key in primary_localization)

        # add some texts
        for key, definition in theme_text_types.items():
            text = '{0} text'.format(key)
            app_text = AppThemeText(self.meta_app, key, text=text)
            app_text.save()


        primary_localization = self.meta_app.get_primary_localization()
        for key, definition in theme_text_types.items():
            text = '{0} text'.format(key)
            self.assertEqual(primary_localization[key], text)


    @test_settings
    def test_media_path(self):
        media_path = self.meta_app.media_path()
        expected_media_path = '/'.join(['apps', str(self.meta_app.uuid)])
        self.assertEqual(media_path, expected_media_path)


    @test_settings
    def test_features(self):
        self.create_all_generic_contents(self.meta_app)

        content_links = MetaAppGenericContent.objects.filter(meta_app=self.meta_app)

        features = self.meta_app.features()
        self.assertEqual(content_links.count(), features.count())

        link_ids = content_links.values_list('id', flat=True)
        expected_link_ids = features.values_list('id', flat=True)
        self.assertEqual(set(link_ids), set(expected_link_ids))


    @test_settings
    def test_addable_features(self):

        addable_features = self.meta_app.addable_features()
        release_builder = self.meta_app.get_release_builder()

        for feature in addable_features:
            models_path = feature.__module__.replace('.models', '')
            self.assertIn(models_path, release_builder.addable_features)
            self.assertIn(feature, feature_models)


    @test_settings
    def test_get_generic_content_link(self):

        self.create_all_generic_contents(self.meta_app)

        for link in MetaAppGenericContent.objects.filter(meta_app=self.meta_app):
            generic_content = link.generic_content
            link_ = self.meta_app.get_generic_content_link(generic_content)
            self.assertEqual(link.__class__, link_.__class__)
            self.assertEqual(link.id, link_.id)


    @test_settings
    def test_backbone(self):
        backbone = self.meta_app.backbone()
        self.assertEqual(backbone.__class__, BackboneTaxonomy)

        content_type = ContentType.objects.get_for_model(BackboneTaxonomy)
        link = MetaAppGenericContent.objects.filter(content_type=content_type).first()

        self.assertEqual(link.meta_app, self.meta_app)
        

    @test_settings
    def test_get_source_nuid_map(self):
        # a taxonlist is required
        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        queryset = models.TaxonTreeModel.objects.all()[:3]

        taxonlist = LazyTaxonList(queryset=queryset)

        source_nuid_map = self.meta_app._get_source_nuid_map(taxonlist)
        self.assertIn(taxon_source, source_nuid_map)

        for taxon in queryset:
            self.assertIn(taxon.taxon_nuid, source_nuid_map[taxon_source])


    @test_settings
    def test_taxon_count(self):
        
        taxa = self.add_set_of_taxa()
        count = 0
        for taxon in taxa:
            if taxon.taxon_include_descendants == True:
                models = TaxonomyModelRouter(taxon.taxon_source)
                descendant_count = models.TaxonTreeModel.objects.filter(
                    taxon_nuid__startswith=taxon.taxon_nuid).count()
                count += descendant_count
            else:
                count += 1

        taxon_count = self.meta_app.taxon_count()

        self.assertEqual(taxon_count, count)
        

    @test_settings
    def test_higher_taxa(self):

        taxa = self.add_set_of_taxa()

        higher_taxa = self.meta_app.higher_taxa()

        expected_taxa_uuids = set([expected_taxon.name_uuid for expected_taxon in taxa])
        
        taxa_uuids = set([taxon.name_uuid for taxon in higher_taxa])
            

    @test_settings
    def test_taxa(self):

        expected_taxa = self.add_set_of_taxa()

        taxa = self.meta_app.taxa()

        expected_taxa_uuids = set([expected_taxon.name_uuid for expected_taxon in expected_taxa])
        taxa_uuids = set([taxon.name_uuid for taxon in taxa])

        self.assertEqual(expected_taxa_uuids, taxa_uuids)


    @test_settings
    def test_name_uuids(self):

        expected_taxa = self.add_set_of_taxa()

        name_uuids = self.meta_app.name_uuids()

        expected_name_uuids = set([expected_taxon.name_uuid for expected_taxon in expected_taxa])

        self.assertEqual(expected_name_uuids, set(name_uuids))


    @test_settings
    def test_has_taxon(self):

        taxa = self.add_set_of_taxa()
        for taxon in taxa:
            exists = self.meta_app.has_taxon(taxon)
            self.assertTrue(exists)

        # test a subtaxon of Quercus
        models = TaxonomyModelRouter('taxonomy.sources.col')
        quercus_robur = models.TaxonTreeModel.objects.get(taxon_latname='Quercus robur')
        exists = self.meta_app.has_taxon(quercus_robur)
        self.assertTrue(exists)


    @test_settings
    def test_all_taxa(self):
        expected_taxa = self.add_set_of_taxa()

        taxa = self.meta_app.all_taxa()

        expected_name_uuids = set([expected_taxon.name_uuid for expected_taxon in expected_taxa])

        name_uuids = set([taxon.name_uuid for taxon in taxa])

        self.assertEqual(expected_name_uuids, name_uuids)


    @test_settings
    def test_search_taxon(self):

        taxa = self.add_set_of_taxa()

        searchtext_1 = 'laCerta'
        results = self.meta_app.search_taxon(searchtext_1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['taxon_latname'], 'Lacerta agilis')

        searchtext_2 = 'common blackbir'
        results = self.meta_app.search_taxon(searchtext_2)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['taxon_latname'], 'Turdus merula')

        searchtext_3 = 'quercus '
        results = self.meta_app.search_taxon(searchtext_3)
        self.assertEqual(len(results), 9)


    @test_settings
    def test_create_version(self):
        current_version = self.meta_app.current_version

        appbuilder = self.meta_app.get_release_builder()
        version_folder = appbuilder._app_version_root_folder(self.meta_app, current_version)
        self.assertTrue(os.path.isdir(version_folder))
        self.assertIn(str(current_version), version_folder)

        feature_versions = {}

        for feature in self.meta_app.features():
            generic_content = feature.generic_content
            feature_versions[feature.content_type.id] = {}
            feature_versions[feature.content_type.id][generic_content.id] = generic_content.current_version

            generic_content.published_version = generic_content.current_version
            generic_content.save()


        # next version
        next_version = current_version + 1
        self.meta_app.create_version(next_version)

        self.meta_app.refresh_from_db()
        self.assertEqual(self.meta_app.current_version, current_version+1)
        self.assertEqual(self.meta_app.validation_status, None)
        self.assertEqual(self.meta_app.build_status, None)
        self.assertEqual(self.meta_app.build_number, None)

        for feature in self.meta_app.features():
            generic_content = feature.generic_content
            old_version = feature_versions[feature.content_type.id][generic_content.id]
            self.assertEqual(old_version+1, generic_content.current_version)
            self.assertEqual(old_version, generic_content.published_version)

        new_version_folder = appbuilder._app_version_root_folder(self.meta_app, next_version)
        self.assertTrue(os.path.isdir(new_version_folder))

        with self.assertRaises(ValueError):
            self.meta_app.create_version(1)
            

    @test_settings
    def test_save(self):
        
        self.assertEqual(self.meta_app.app.published_version, None)
        self.assertEqual(self.meta_app.published_version, None)

        # simple save does nothing special
        feature_versions = {}

        for feature in self.meta_app.features():
            generic_content = feature.generic_content
            feature_versions[feature.content_type.id] = {}
            feature_versions[feature.content_type.id][generic_content.id] = generic_content.current_version

        self.meta_app.save()

        for feature in self.meta_app.features():
            generic_content = feature.generic_content
            old_version = feature_versions[feature.content_type.id][generic_content.id]
            self.assertEqual(old_version, generic_content.current_version)
            self.assertEqual(None, generic_content.published_version)

        self.assertEqual(self.meta_app.app.published_version, None)
    

    @test_settings
    def test_save_publish(self):

        feature_versions = {}

        self.assertEqual(self.meta_app.app.published_version, None)
        
        for feature in self.meta_app.features():
            generic_content = feature.generic_content
            feature_versions[feature.content_type.id] = {}
            feature_versions[feature.content_type.id][generic_content.id] = generic_content.current_version

        self.meta_app.save(publish=True)

        self.assertTrue(self.meta_app.published_version != None)
        self.assertTrue(self.meta_app.app.published_version != None)
        self.assertTrue(self.meta_app.app.apk_url != None)
        #self.assertTrue(self.meta_app.app.ipa_url != None)
        self.assertTrue(self.meta_app.app.pwa_zip_url != None)

        for feature in self.meta_app.features():
            generic_content = feature.generic_content
            old_version = feature_versions[feature.content_type.id][generic_content.id]
            # version bump is done when a new version is created
            self.assertEqual(old_version, generic_content.current_version)
            self.assertEqual(old_version, generic_content.published_version)

        self.assertEqual(self.meta_app.app.published_version, 1)
        self.assertEqual(self.meta_app.current_version, 1)

        
    @test_settings
    def test_remove_old_version_from_disk(self):

        release_builder = self.meta_app.get_release_builder()
        
        current_version = self.meta_app.current_version
        current_version_folder = release_builder._app_version_root_folder(self.meta_app, current_version)
        self.assertTrue(os.path.isdir(current_version_folder))

        next_version = current_version + 1
        self.meta_app.create_version(next_version)
        next_version_folder = release_builder._app_version_root_folder(self.meta_app, next_version)
        self.assertTrue(os.path.isdir(next_version_folder))

        next_next_version = next_version + 1
        self.meta_app.create_version(next_next_version)
        next_next_version_folder = release_builder._app_version_root_folder(self.meta_app, next_next_version)
        self.assertTrue(os.path.isdir(next_next_version_folder))

        # REMOVE app version
        self.meta_app.remove_old_version_from_disk(2)

        self.assertTrue(os.path.isdir(current_version_folder))
        self.assertTrue(os.path.isdir(next_version_folder))
        self.assertTrue(os.path.isdir(next_next_version_folder))


        self.meta_app.remove_old_version_from_disk(1)

        self.assertFalse(os.path.isdir(current_version_folder))
        self.assertTrue(os.path.isdir(next_version_folder))
        self.assertTrue(os.path.isdir(next_next_version_folder))
        

    @test_settings
    def test_is_localcosmos_private(self):
        is_private = self.meta_app.is_localcosmos_private
        self.assertFalse(is_private)

        self.meta_app.global_options['localcosmos_private'] = True
        self.meta_app.save()

        is_private = self.meta_app.is_localcosmos_private
        self.assertTrue(is_private)


    @test_settings
    def test_str(self):
        meta_app_name = str(self.meta_app)
        self.assertEqual(self.meta_app.app.name, meta_app_name)    


    @test_settings
    def test_delete(self):

        appbuilder = self.meta_app.get_preview_builder()
        app_root_folder = appbuilder._app_root_folder(self.meta_app)

        self.assertTrue(os.path.isdir(app_root_folder))

        self.meta_app.delete()
        self.assertFalse(os.path.isdir(app_root_folder))


    # TEST GenericContentMethodsMixin methods
    @test_settings
    def test_get_global_option(self):
        testoption = 'testglobaloption'
        testvalue = 'testglobalvalue'
        self.meta_app.global_options[testoption] = testvalue
        self.meta_app.save()

        self.meta_app.refresh_from_db()

        option = self.meta_app.get_global_option(testoption)
        self.assertEqual(option, testvalue)

        nonexistant = self.meta_app.get_global_option('doesnotexist')
        self.assertEqual(nonexistant, None)


    @test_settings
    def test_get_option(self):

        testoption = 'testoption'
        testvalue = 'testvalue'
        
        self.create_all_generic_contents(self.meta_app)

        feature = self.meta_app.features()[0]
        self.assertEqual(feature.options, None)
        
        generic_content = feature.generic_content

        nonexistant = generic_content.get_option(self.meta_app, 'doesnotexist')
        self.assertEqual(nonexistant, None)

        feature.options = {}
        feature.options[testoption] = testvalue
        feature.save()
        feature.refresh_from_db()

        option = generic_content.get_option(self.meta_app, testoption)
        self.assertEqual(option, testvalue)

        nonexistant = generic_content.get_option(self.meta_app, 'doesnotexist')
        self.assertEqual(nonexistant, None)


    @test_settings
    def test_options(self):

        testoption = 'testoption'
        testvalue = 'testvalue'

        testoption_2 = 'testoption'
        testvalue_2 = 'testvalue'
        
        self.create_all_generic_contents(self.meta_app)

        feature = self.meta_app.features()[0]

        self.assertEqual(feature.options, None)

        generic_content = feature.generic_content
        empty_options = generic_content.options(self.meta_app)
        self.assertEqual(empty_options, {})

        feature.options = {}
        feature.options[testoption] = testvalue
        feature.options[testoption_2] = testvalue_2
        feature.save()
        feature.refresh_from_db()

        options = generic_content.options(self.meta_app)
        self.assertIn(testoption, options)
        self.assertIn(testoption_2, options)

        self.assertEqual(options[testoption], testvalue)
        self.assertEqual(options[testoption_2], testvalue_2)
        

    @test_settings
    def test_make_option_from_instance(self):

        self.create_all_generic_contents(self.meta_app)

        feature = self.meta_app.features()[0]
        generic_content = feature.generic_content

        option = self.meta_app.make_option_from_instance(generic_content)

        self.assertEqual(option['app_label'], generic_content._meta.app_label)
        self.assertEqual(option['model'], generic_content.__class__.__name__)
        self.assertEqual(option['uuid'], str(generic_content.uuid))
        self.assertEqual(option['id'], generic_content.id)
        self.assertEqual(option['action'], generic_content.__class__.__name__)


    @test_settings
    def test_manage_url(self):
        manage_url = self.meta_app.manage_url()
        self.assertEqual(manage_url, 'manage_metaapp')


    @test_settings
    def test_verbose_name(self):
        verbose_name = self.meta_app.verbose_name()
        self.assertEqual(verbose_name, 'App')


    @test_settings
    def test_feature_type(self):
        self.create_all_generic_contents(self.meta_app)

        feature = self.meta_app.features()[0]
        generic_content = feature.generic_content
        
        feature_type = generic_content.feature_type()
        self.assertEqual(feature_type, 'app_kit.features.backbonetaxonomy')


    @test_settings
    def test_media_path(self):
        self.create_all_generic_contents(self.meta_app)

        feature = self.meta_app.features()[0]
        generic_content = feature.generic_content
        
        media_path = generic_content.media_path()
        
        self.assertEqual(media_path, 'app_kit.features.backbonetaxonomy/{0}'.format(str(generic_content.uuid)))
        

    @test_settings
    def test_lock_unlock(self):

        self.create_all_generic_contents(self.meta_app)

        for feature in self.meta_app.features():
            generic_content = feature.generic_content
            generic_content.lock(str(generic_content.uuid))

        for feature in self.meta_app.features():
            generic_content = feature.generic_content
            self.assertTrue(generic_content.is_locked)
            self.assertTrue('lock_reason' in generic_content.messages)
            self.assertEqual(generic_content.messages['lock_reason'], str(generic_content.uuid))
            
        for feature in self.meta_app.features():
            generic_content = feature.generic_content
            generic_content.unlock()


        for feature in self.meta_app.features():
            generic_content = feature.generic_content
            self.assertFalse(generic_content.is_locked)
            self.assertFalse('lock_reason' in generic_content.messages)


# this test uses TransactionTenantTestCase to make django_cleanup work
class TestMetaAppContentImageMixin(WithMetaApp, WithUser, WithMedia, TransactionTenantTestCase):
    
    # TEST ContentImageMixin methods
    @test_settings
    def test_content_images(self):
        user = self.create_user()
        content_image = self.create_content_image(self.meta_app, user)

        images = self.meta_app._content_images()
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0], content_image)


    @test_settings
    def test_images(self):
        user = self.create_user()
        content_image = self.create_content_image(self.meta_app, user)

        images = self.meta_app.images()
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0], content_image)


    @test_settings
    def test_image(self):

        user = self.create_user()
        content_image = self.create_content_image(self.meta_app, user)

        image = self.meta_app.image()

        self.assertEqual(content_image, image)


    @test_settings
    def test_image_url(self):

        user = self.create_user()
        content_image = self.create_content_image(self.meta_app, user)

        image = self.meta_app.image()

        image_url = self.meta_app.image_url()
        self.assertTrue('thumbnails' in image_url)
        self.assertFalse(image_url.startswith('http'))


    @test_settings
    def test_delete_images(self):

        user = self.create_user()
        content_image = self.create_content_image(self.meta_app, user)
        image_path = content_image.image_store.source_image.path
        
        self.assertTrue(os.path.isfile(image_path))

        self.meta_app.delete_images()
        
        self.assertFalse(os.path.isfile(image_path))

        image = self.meta_app.image()
        self.assertEqual(image, None)    
    
    
class TestMetaAppGenericContent(WithMetaApp, WithMedia, TenantTestCase):

    @test_settings
    def test_feature_type(self):

        self.create_all_generic_contents(self.meta_app)

        content_type = ContentType.objects.get_for_model(BackboneTaxonomy)
        feature = self.meta_app.features().filter(content_type=content_type).first()

        feature_type = feature.feature_type()
        self.assertEqual(feature_type, 'app_kit.features.backbonetaxonomy')


    @test_settings
    def test_manage_url(self):

        self.create_all_generic_contents(self.meta_app)

        content_type = ContentType.objects.get_for_model(BackboneTaxonomy)
        feature = self.meta_app.features().filter(content_type=content_type).first()

        manage_url = feature.manage_url()
        self.assertEqual(manage_url, 'manage_backbonetaxonomy')


    @test_settings
    def test_str(self):

        self.create_all_generic_contents(self.meta_app)

        content_type = ContentType.objects.get_for_model(BackboneTaxonomy)
        feature = self.meta_app.features().filter(content_type=content_type).first()

        name = str(feature)
        self.assertEqual(name, 'Backbone taxonomy')



class TestImageStore(WithMedia, WithUser, TenantTestCase):

    @test_settings
    def test_create(self):

        user = self.create_user()
        md5 = hashlib.md5(Image.open(TEST_IMAGE_PATH).tobytes()).hexdigest()

        image = SimpleUploadedFile(name='test_image.jpg', content=open(TEST_IMAGE_PATH, 'rb').read(),
                                        content_type='image/jpeg')

        image_store = ImageStore(
            source_image=image,
            uploaded_by=user,
            md5=md5,
            taxon=None,
        )

        image_store.save()

        image_store.refresh_from_db()
        filename = '{0}.jpg'.format(md5)
        self.assertTrue(image_store.source_image.name.endswith(filename))
        self.assertEqual(image_store.uploaded_by, user)
        self.assertEqual(image_store.md5, md5)
        

    @test_settings
    def test_create_with_taxon(self):

        user = self.create_user()
        md5 = hashlib.md5(Image.open(TEST_IMAGE_PATH).tobytes()).hexdigest()

        image = SimpleUploadedFile(name='test_image.jpg', content=open(TEST_IMAGE_PATH, 'rb').read(),
                                        content_type='image/jpeg')

        models = TaxonomyModelRouter('taxonomy.sources.col')

        # first, add a single backbone taxon
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lazy_taxon = LazyTaxon(instance=lacerta_agilis)

        image_store = ImageStore(
            source_image=image,
            uploaded_by=user,
            md5=md5,
            taxon=lazy_taxon,
        )

        image_store.save()

        image_store.refresh_from_db()
        self.assertEqual(image_store.uploaded_by, user)
        self.assertEqual(image_store.md5, md5)
        self.assertEqual(image_store.taxon.name_uuid, lazy_taxon.name_uuid)
        

class TestContentImage(WithMedia, WithImageStore, WithMetaApp, WithUser, TenantTestCase):


    def create_content_image(self):

        image_store = self.create_image_store()

        content_type = ContentType.objects.get_for_model(self.meta_app)

        content_image = ContentImage(
            image_store=image_store,
            content_type=content_type,
            object_id=self.meta_app.id,
        )

        content_image.save()

        return content_image
        

    @test_settings
    def test_create(self):
        image_store = self.create_image_store()

        content_type = ContentType.objects.get_for_model(self.meta_app)

        content_image = ContentImage(
            image_store=image_store,
            content_type=content_type,
            object_id=self.meta_app.id,
        )

        content_image.save()

        self.assertEqual(content_image.content, self.meta_app)


    @test_settings
    def test_get_thumb_filename(self):
        content_image = self.create_content_image()
        crop_parameters = {
            'x' : 0,
            'y' : 0,
            'width' : 10,
            'height' : 10,
        }

        text_parameters = json.dumps(crop_parameters)
        content_image.crop_parameters = text_parameters

        content_image.save()

        thumb_filename = content_image.get_thumb_filename()

        filename_parts = thumb_filename.split('.')
        self.assertEqual(filename_parts[-1], 'jpg')
        self.assertTrue(len(filename_parts[0]) > 0)
        self.assertFalse('uncropped' in thumb_filename)
        
        

    @test_settings
    def test_get_thumb_filename_uncropped(self):
        content_image = self.create_content_image()
        thumb_filename = content_image.get_thumb_filename()

        filename_parts = thumb_filename.split('.')
        self.assertEqual(filename_parts[-1], 'jpg')
        self.assertTrue(len(filename_parts[0]) > 0)
        self.assertIn('uncropped', thumb_filename)

    @test_settings
    def test_image_url_uncropped(self):

        content_image = self.create_content_image()

        url = content_image.image_url()
        self.assertIn(settings.MEDIA_URL, url)
        self.assertTrue(url.endswith('.jpg'))

        filename = url.split('/')[-1]
        filename_parts = filename.split('.')
        self.assertEqual(filename_parts[-1], 'jpg')
        self.assertTrue(len(filename_parts[0]) > 0)


    @test_settings
    def test_image_url(self):

        content_image = self.create_content_image()

        crop_parameters = {
            'x' : 0,
            'y' : 0,
            'width' : 500,
            'height' : 500,
        }

        text_parameters = json.dumps(crop_parameters)
        content_image.crop_parameters = text_parameters

        content_image.save()

        url = content_image.image_url()
        self.assertIn(settings.MEDIA_URL, url)
        self.assertTrue(url.endswith('.jpg'))

        filename = url.split('/')[-1]
        filename_parts = filename.split('.')
        self.assertEqual(filename_parts[-1], 'jpg')
        self.assertTrue(len(filename_parts[0]) > 0)

        # validate image size
        image_path = content_image.image_store.source_image.path
        folder_path = os.path.dirname(image_path)

        thumbpath = os.path.join(folder_path, 'thumbnails', filename)
        self.assertTrue(os.path.isfile(thumbpath))

        image = Image.open(thumbpath)
        self.assertEqual(image.width, 400)
        self.assertEqual(image.height, 400)


        url = content_image.image_url(size=450)
        filename = url.split('/')[-1]
        thumbpath = os.path.join(folder_path, 'thumbnails', filename)
        self.assertTrue(os.path.isfile(thumbpath))

        image = Image.open(thumbpath)
        self.assertEqual(image.width, 450)
        self.assertEqual(image.height, 450)


class TestUpdateContentImageTaxonMixin(WithImageStore, WithMedia, WithUser, TenantTestCase):

    def create_nodes(self):
        nature_guide = NatureGuide.objects.create('Test Nature Guide', 'en')

        root_node = NatureGuidesTaxonTree.objects.get(nature_guide=nature_guide, is_root_taxon=True)
        meta_node = MetaNode(
            name='Test Node',
            nature_guide=nature_guide,
            node_type='node',
        )
        meta_node.save()

        node = NatureGuidesTaxonTree(
            nature_guide=nature_guide,
            meta_node=meta_node,
        )
        node.save(root_node)
        
        return root_node, node


    @test_settings
    def test_get_content_image_taxon(self):
        root_node, node = self.create_nodes()

        meta_node = node.meta_node

        taxon = meta_node.get_content_image_taxon()
        self.assertEqual(taxon, None)

        models = TaxonomyModelRouter('taxonomy.sources.col')

        # add taxon
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lazy_taxon = LazyTaxon(instance=lacerta_agilis)
        
        meta_node.taxon = lazy_taxon
        meta_node.save()

        taxon = meta_node.get_content_image_taxon()
        self.assertEqual(taxon.name_uuid, lazy_taxon.name_uuid)


    @test_settings
    def test_save_with_taxon(self):

        root_node, node = self.create_nodes()

        meta_node = node.meta_node

        image_store = self.create_image_store()

        content_type = ContentType.objects.get_for_model(meta_node)

        content_image = ContentImage(
            image_store=image_store,
            content_type=content_type,
            object_id=meta_node.id,
        )

        content_image.save()

        self.assertEqual(image_store.taxon, None)

        # add the taxon
        models = TaxonomyModelRouter('taxonomy.sources.col')

        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lazy_taxon = LazyTaxon(instance=lacerta_agilis)
        
        meta_node.set_taxon(lazy_taxon)

        # trigger updatecontentimagetaxonmixin.save
        meta_node.save()

        meta_node.refresh_from_db()

        taxon = meta_node.get_content_image_taxon()
        self.assertEqual(taxon.name_uuid, lazy_taxon.name_uuid)

        content_images = ContentImage.objects.filter(content_type=content_type, object_id=meta_node.pk)
        meta_node_content_image = content_images[0]
        self.assertEqual(meta_node_content_image, content_image)
        
        image_store = meta_node_content_image.image_store
        self.assertTrue(image_store.taxon != None)
        self.assertEqual(image_store.taxon.name_uuid, lazy_taxon.name_uuid)

        

class TestLocalizeableImage(WithImageStore, WithMedia, WithMetaApp, WithUser, TenantTestCase):


    def setUp(self):
        super().setUp()

        self.content_type = ContentType.objects.get_for_model(ContentImage)


    def create_content_image(self):

        image_store = self.create_image_store()

        content_type = ContentType.objects.get_for_model(self.meta_app)

        content_image = ContentImage(
            image_store=image_store,
            content_type=content_type,
            object_id=self.meta_app.id,
        )

        content_image.save()

        return content_image
    

    @test_settings
    def test_init(self):

        content_image = self.create_content_image()

        localizeable_image = LocalizeableImage(content_image, model_field='image_store.source_image')

        self.assertEqual(localizeable_image.image_instance, content_image)
        self.assertEqual(localizeable_image.image_file, content_image.image_store.source_image)
        

    @test_settings
    def test_get_relative_localized_image_folder(self):

        language_code = 'en'

        folder = LocalizeableImage.get_relative_localized_image_folder(language_code)
        self.assertEqual(folder, 'locales/en/images/')


    @test_settings
    def test_get_localized_filename(self):

        content_image = self.create_content_image()

        localizeable_image = LocalizeableImage(content_image, model_field='image_store.source_image')

        filename = localizeable_image.get_localized_filename('en')

        # localized_image_46_1_en.jpg
        self.assertEqual(filename, 'localized_image_{0}_{1}_en.jpg'.format(self.content_type.id,
                                                                              content_image.id))


    @test_settings
    def test_localize_language_independant_filename(self):

        content_image = self.create_content_image()

        filename = 'localized_image_{0}_{1}.jpg'.format(self.content_type.id, content_image.id)
        language_code = 'en'
        
        localized_filename = LocalizeableImage.localize_language_independant_filename(filename, language_code)


        expected_filename = 'localized_image_{0}_{1}_en.jpg'.format(self.content_type.id, content_image.id)

        self.assertEqual(localized_filename, expected_filename)


    @test_settings
    def test_get_language_independant_filename(self):
        
        content_image = self.create_content_image()

        localizeable_image = LocalizeableImage(content_image, model_field='image_store.source_image')

        filename = localizeable_image.get_language_independant_filename()

        # localized_image_46_1_en.jpg
        self.assertEqual(filename, 'localized_image_{0}_{1}.jpg'.format(self.content_type.id,
                                                                              content_image.id))
        
    
    @test_settings
    def test_get_relative_localized_image_path(self):

        content_image = self.create_content_image()

        localizeable_image = LocalizeableImage(content_image, model_field='image_store.source_image')

        language_code = 'en'
        relative_image_path = localizeable_image.get_relative_localized_image_path(language_code)

        # locales/en/images/localized_image_46_2_en.jpg
        expected_path = 'locales/en/images/localized_image_{0}_{1}_en.jpg'.format(self.content_type.id,
                                                                                  content_image.id)
        self.assertEqual(relative_image_path, expected_path)

    
    @test_settings
    def test_get_locale(self):

        # the media root is not uses in the real, for testing purposes this is irrelevant
        app_www_folder = TEST_MEDIA_ROOT

        language_code = 'en'

        content_image = self.create_content_image()

        localizeable_image = LocalizeableImage(content_image, model_field='image_store.source_image')

        locale = localizeable_image.get_locale(app_www_folder, language_code)
        self.assertEqual(locale, None)

        # store the locale
        relative_locale_folder = localizeable_image.get_relative_localized_image_folder(language_code)
        absolute_locale_folder = os.path.join(app_www_folder, relative_locale_folder) 
        
        if not os.path.isdir(absolute_locale_folder):
            os.makedirs(absolute_locale_folder)


        relative_image_path = localizeable_image.get_relative_localized_image_path(language_code)
        full_localized_image_path = os.path.join(app_www_folder, relative_image_path)

        img = Image.new("RGB", (800, 1280), (255, 255, 255))
        img.save(full_localized_image_path, "PNG")

        

        locale = localizeable_image.get_locale(app_www_folder, language_code)
        self.assertEqual(locale, full_localized_image_path)


    @test_settings
    def test_save_locale(self):

        # the media root is not uses in the real, for testing purposes this is irrelevant
        app_www_folder = TEST_MEDIA_ROOT

        language_code = 'en'

        image = SimpleUploadedFile(name='test_image.jpg', content=open(TEST_IMAGE_PATH, 'rb').read(),
                                        content_type='image/jpeg')

        content_image = self.create_content_image()

        localizeable_image = LocalizeableImage(content_image, model_field='image_store.source_image')

        localizeable_image.save_locale(app_www_folder, image, language_code)

        relative_image_path = localizeable_image.get_relative_localized_image_path(language_code)
        full_localized_image_path = os.path.join(app_www_folder, relative_image_path)

        self.assertTrue(os.path.isfile(full_localized_image_path))
        

    @test_settings
    def test_url(self):

        content_image = self.create_content_image()
        language_code = 'en'

        localizeable_image = LocalizeableImage(content_image, model_field='image_store.source_image')

        url = localizeable_image.url(language_code)

        expected_path = 'locales/en/images/localized_image_{0}_{1}_en.jpg'.format(self.content_type.id,
                                                                                  content_image.id)
        self.assertEqual(url, expected_path)


    @test_settings
    def test_preview_url(self):

        language_code = 'en'
        localized_filename = 'localized_image.jpg'

        preview_url = LocalizeableImage.preview_url(localized_filename, language_code)

        self.assertEqual('locales/en/images/localized_image.jpg', preview_url)
