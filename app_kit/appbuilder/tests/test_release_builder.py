import pstats
from django_tenants.test.cases import TenantTestCase
from django.test import RequestFactory
from django.urls import reverse

from django.contrib.contenttypes.models import ContentType

from app_kit.tests.common import test_settings, TESTS_ROOT

from app_kit.tests.mixins import WithMetaApp, WithMedia, WithUser, WithPublicDomain

from app_kit.appbuilder import AppReleaseBuilder
from app_kit.app_kit_api.models import AppKitJobs

from localcosmos_cordova_builder.CordovaAppBuilder import CordovaAppBuilder

from app_kit.models import MetaAppGenericContent
from localcosmos_server.models import SecondaryAppLanguages

from localcosmos_cordova_builder.MetaAppDefinition import MetaAppDefinition

from app_kit.features.glossary.models import Glossary
from app_kit.features.nature_guides.models import NatureGuide, MatrixFilterSpace
from app_kit.features.nature_guides.tests.common import WithNatureGuide
from app_kit.features.generic_forms.models import GenericForm
from app_kit.features.frontend.models import FrontendText
from app_kit.features.backbonetaxonomy.models import BackboneTaxonomy, BackboneTaxa
from app_kit.features.taxon_profiles.models import TaxonProfiles
from app_kit.features.maps.models import Map

from taxonomy.models import TaxonomyModelRouter
from taxonomy.lazy import LazyTaxon


from django.conf import settings

import os

TEST_PRIVATE_API_URL = 'http://localhost/private-api-test/'

class TestReleaseBuilder(WithPublicDomain, WithMetaApp, WithUser, WithMedia, WithNatureGuide, TenantTestCase):

    def setUp(self):
        super().setUp()

        self.release_builder = AppReleaseBuilder(self.meta_app)


    def get_generic_content_link(self, model):

        content_type = ContentType.objects.get_for_model(model)
        link = MetaAppGenericContent.objects.get(meta_app=self.meta_app, content_type=content_type)
        return link


    def get_lazy_taxon(self, taxon_latname):

        models = TaxonomyModelRouter('taxonomy.sources.col')
        taxon = models.TaxonTreeModel.objects.get(taxon_latname=taxon_latname)
        lazy_taxon = LazyTaxon(instance=taxon)

        return lazy_taxon

    
    def get_request(self):
        factory = RequestFactory()
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'action' : 'build',
        }
        url = reverse('build_app', kwargs=url_kwargs)
        
        request = factory.get(url)
        request.session = self.client.session
        request.tenant = self.tenant

        return request


    def general_path_check(self, path):
        self.assertTrue(path.startswith(TESTS_ROOT))
        self.assertTrue(path.startswith(settings.APP_KIT_ROOT))


    @test_settings
    def test_get_cordova_builder(self):

        cordova_builder = self.release_builder.get_cordova_builder()
        self.assertTrue(isinstance(cordova_builder, CordovaAppBuilder))

    
    @test_settings
    def test_app_relative_generic_content_path(self):

        self.create_all_generic_contents(self.meta_app)

        generic_content_links = MetaAppGenericContent.objects.filter(meta_app=self.meta_app)

        for link in generic_content_links:

            generic_content = link.generic_content

            path = self.release_builder._app_relative_generic_content_path(generic_content)

            self.assertFalse(path.startswith(TESTS_ROOT))
            self.assertFalse(path.startswith(settings.APP_KIT_ROOT))
            
            self.assertTrue(path.startswith('localcosmos/features/'))
            self.assertTrue(path.endswith(str(generic_content.uuid)))


    @test_settings
    def test_app_absolute_generic_content_path(self):

        self.create_all_generic_contents(self.meta_app)

        generic_content_links = MetaAppGenericContent.objects.filter(meta_app=self.meta_app)

        for link in generic_content_links:

            generic_content = link.generic_content

            path = self.release_builder._app_absolute_generic_content_path(generic_content)

            self.general_path_check(path)
            self.assertTrue('localcosmos/features' in path)
            self.assertTrue(path.endswith(str(generic_content.uuid)))


    @test_settings
    def test_app_relative_content_images_path(self):

        path = self.release_builder._app_relative_content_images_path

        self.assertFalse(path.startswith(TESTS_ROOT))
        self.assertFalse(path.startswith(settings.APP_KIT_ROOT))
        self.assertEqual(path, 'localcosmos/user_content/content_images')


    @test_settings
    def test_app_absolute_content_images_path(self):

        path = self.release_builder._app_absolute_content_images_path

        self.general_path_check(path)
        self.assertTrue(path.endswith('localcosmos/user_content/content_images'))


    ###############################################################################################
    # tests for product urls 
    ###############################################################################################

    @test_settings
    def test_aab_review_url(self):
        request = self.get_request()
        url = self.release_builder.aab_review_url(request)
        self.assertIn('/packages/review/android', url)
        self.assertTrue(url.startswith('http'))


    @test_settings
    def test_aab_published_url(self):
        url = self.release_builder.aab_published_url()
        self.assertIn('/packages/published/android', url)
        self.assertFalse(url.startswith('http'))


    @test_settings
    def test_browser_review_url(self):

        self.create_public_domain()
        
        request = self.get_request()
        url = self.release_builder.browser_review_url(request)
        self.assertIn('.review.', url)
        self.assertTrue(url.startswith('http'))


    @test_settings
    def test_browser_zip_review_url(self):
        request = self.get_request()
        url = self.release_builder.browser_zip_review_url(request)
        self.assertIn('/packages/review/browser', url)
        self.assertTrue(url.startswith('http'))

    @test_settings
    def test_browser_zip_published_url(self):
        url = self.release_builder.browser_zip_published_url()
        self.assertIn('/packages/published/browser', url)
        self.assertFalse(url.startswith('http'))


    def create_successful_app_kit_api_job(self, platform):

        meta_app_definition = MetaAppDefinition.meta_app_to_dict(self.meta_app)

        app_kit_job = AppKitJobs(
            meta_app_uuid=self.meta_app.uuid,
            meta_app_definition = meta_app_definition,
            app_version=self.meta_app.current_version,
            platform=platform,
            job_type='build',
            job_result={'success':True},
        )

        app_kit_job.save()
        

    @test_settings
    def test_ipa_review_url(self):
        request = self.get_request()
        url = self.release_builder.ipa_review_url(request)

        self.assertEqual(url, None)

        self.create_successful_app_kit_api_job('ios')

        url_2 = self.release_builder.ipa_review_url(request)
        self.assertTrue(url_2.startswith('http'))
        self.assertIn('/packages/review/ios', url_2)


    @test_settings
    def test_ipa_published_url(self):
        
        url = self.release_builder.ipa_published_url()

        self.assertEqual(url, None)

        self.create_successful_app_kit_api_job('ios')

        url_2 = self.release_builder.ipa_published_url()
        self.assertFalse(url_2.startswith('http'))
        self.assertIn('/packages/published/ios', url_2)

    ##########################################################################################
    # tests for glossary paths
    ##########################################################################################
    def get_glossary(self):

        glossary_content_type = ContentType.objects.get_for_model(Glossary)

        glossary_link = MetaAppGenericContent.objects.get(meta_app=self.meta_app, content_type=glossary_content_type)

        return glossary_link.generic_content

    @test_settings
    def test_app_glossarized_locale_filepath(self):

        language_code = 'en'
        
        path = self.release_builder._app_glossarized_locale_filepath(language_code)

        self.general_path_check(path)
        self.assertTrue(path.endswith('en/glossarized.json'))


    @test_settings
    def test_app_localized_glossaries_path(self):

        self.create_all_generic_contents(self.meta_app)
        
        language_code = 'en'

        glossary = self.get_glossary()

        path = self.release_builder._app_localized_glossaries_path(glossary, language_code)

        self.general_path_check(path)
        #print(path)
        path_end = 'localcosmos/features/Glossary/{0}/en'.format(str(glossary.uuid))
        self.assertTrue(path.endswith(path_end))


    @test_settings
    def test_app_localized_glossary_filepath(self):
        
        self.create_all_generic_contents(self.meta_app)

        language_code = 'en'

        glossary = self.get_glossary()

        path = self.release_builder._app_localized_glossary_filepath(glossary, language_code)

        self.general_path_check(path)
        #print(path)
        path_end = 'localcosmos/features/Glossary/{0}/en/glossary.json'.format(str(glossary.uuid))
        self.assertTrue(path.endswith(path_end))


    @test_settings
    def test_app_localized_glossary_csv_filepath(self):
        
        self.create_all_generic_contents(self.meta_app)

        language_code = 'en'

        glossary = self.get_glossary()

        path = self.release_builder._app_localized_glossary_csv_filepath(glossary, language_code)

        self.general_path_check(path)
        #print(path)
        path_end = 'localcosmos/features/Glossary/{0}/en/glossary.csv'.format(str(glossary.uuid))
        self.assertTrue(path.endswith(path_end))


    @test_settings
    def test_app_used_terms_glossary_filepath(self):
        
        self.create_all_generic_contents(self.meta_app)

        language_code = 'en'

        glossary = self.get_glossary()

        path = self.release_builder._app_used_terms_glossary_filepath(glossary, language_code)

        self.general_path_check(path)
        #print(path)
        path_end = 'localcosmos/features/Glossary/{0}/en/used_terms_glossary.json'.format(str(glossary.uuid))
        self.assertTrue(path.endswith(path_end))


    @test_settings
    def test_app_used_terms_glossary_csv_filepath(self):
        
        self.create_all_generic_contents(self.meta_app)

        language_code = 'en'

        glossary = self.get_glossary()

        path = self.release_builder._app_used_terms_glossary_csv_filepath(glossary, language_code)

        self.general_path_check(path)
        #print(path)
        path_end = 'localcosmos/features/Glossary/{0}/en/used_terms_glossary.csv'.format(str(glossary.uuid))
        self.assertTrue(path.endswith(path_end))


    # relative paths
    @test_settings
    def test_app_relative_localized_glossaries_path(self):
        
        self.create_all_generic_contents(self.meta_app)

        language_code = 'en'

        glossary = self.get_glossary()

        path = self.release_builder._app_relative_localized_glossaries_path(glossary, language_code)

        expected_path = 'localcosmos/features/Glossary/{0}/en'.format(str(glossary.uuid))
        
        self.assertEqual(path, expected_path)


    @test_settings
    def test_app_relative_localized_glossary_filepath(self):
        
        self.create_all_generic_contents(self.meta_app)

        language_code = 'en'

        glossary = self.get_glossary()

        path = self.release_builder._app_relative_localized_glossary_filepath(glossary, language_code)

        expected_path = 'localcosmos/features/Glossary/{0}/en/glossary.json'.format(str(glossary.uuid))
        

        self.assertEqual(path, expected_path)


    @test_settings
    def test_app_relative_localized_glossary_csv_filepath(self):
        
        self.create_all_generic_contents(self.meta_app)

        language_code = 'en'

        glossary = self.get_glossary()

        path = self.release_builder._app_relative_localized_glossary_csv_filepath(glossary, language_code)

        expected_path = 'localcosmos/features/Glossary/{0}/en/glossary.csv'.format(str(glossary.uuid))
        

        self.assertEqual(path, expected_path)


    @test_settings
    def test_app_relative_used_terms_glossary_filepath(self):
        
        self.create_all_generic_contents(self.meta_app)

        language_code = 'en'

        glossary = self.get_glossary()

        path = self.release_builder._app_relative_used_terms_glossary_filepath(glossary, language_code)

        expected_path = 'localcosmos/features/Glossary/{0}/en/used_terms_glossary.json'.format(str(glossary.uuid))
        

        self.assertEqual(path, expected_path)


    @test_settings
    def test_app_relative_used_terms_glossary_csv_filepath(self):
        
        self.create_all_generic_contents(self.meta_app)

        language_code = 'en'

        glossary = self.get_glossary()

        path = self.release_builder._app_relative_used_terms_glossary_csv_filepath(glossary, language_code)

        expected_path = 'localcosmos/features/Glossary/{0}/en/used_terms_glossary.csv'.format(str(glossary.uuid))
        

        self.assertEqual(path, expected_path)


    ##########################################################################################
    # tests for validation
    ##########################################################################################

    @test_settings
    def test_validate(self):
        pass

    @test_settings
    def test_validate_app(self):
        
        # no NatureGuide OR GenericForm
        result = self.release_builder.validate_app()

        self.assertEqual(result['warnings'], [])
        self.assertTrue('at least one' in result['errors'][0].messages[0])
        self.assertEqual(len(result['errors']), 1)

        # localcosmos_private requires an API url
        self.meta_app.global_options['localcosmos_private'] = True
        self.meta_app.save()

        result = self.release_builder.validate_app()

        self.assertEqual(result['warnings'], [])
        self.assertTrue('at least one' in result['errors'][0].messages[0])
        self.assertTrue('You have to provide an API URL' in result['errors'][1].messages[0])
        self.assertEqual(len(result['errors']), 2)

        # set the api url to something wrong
        self.meta_app.global_options['localcosmos_private_api_url'] = 'http://something.wrong'
        self.meta_app.save()

        result = self.release_builder.validate_app()

        self.assertEqual(result['warnings'], [])
        self.assertTrue('at least one' in result['errors'][0].messages[0])
        self.assertTrue('API URL Error' in result['errors'][1].messages[0])
        self.assertEqual(len(result['errors']), 2)

        # set the api url to a real server, but 404
        self.meta_app.global_options['localcosmos_private_api_url'] = 'https://localcosmos.org/api/'
        self.meta_app.save()

        result = self.release_builder.validate_app()

        self.assertEqual(result['warnings'], [])
        self.assertIn('at least one', result['errors'][0].messages[0])
        self.assertIn('API HTTP Error', result['errors'][1].messages[0])
        self.assertEqual(len(result['errors']), 2)


        self.meta_app.global_options['localcosmos_private_api_url'] = 'https://localcosmos.org/'
        self.meta_app.save()

        result = self.release_builder.validate_app()

        self.assertEqual(result['warnings'], [])
        self.assertIn('at least one', result['errors'][0].messages[0])
        #print(result['errors'][1].messages[0])
        self.assertEqual(len(result['errors']), 1)


        # create ng, public lx
        self.meta_app.global_options['localcosmos_private'] = False
        self.meta_app.save()

        ng_link = self.create_generic_content(NatureGuide, self.meta_app)

        result = self.release_builder.validate_app()
        self.assertEqual(result['warnings'], [])
        self.assertEqual(result['errors'], [])

        ng_link.delete()

        result = self.release_builder.validate_app()

        self.assertEqual(result['warnings'], [])
        self.assertTrue('at least one' in result['errors'][0].messages[0])
        self.assertEqual(len(result['errors']), 1)

        form_link = self.create_generic_content(GenericForm, self.meta_app)

        result = self.release_builder.validate_app()
        self.assertEqual(result['warnings'], [])
        self.assertEqual(result['errors'], [])


    @test_settings
    def test_validate_translations(self):
        
        # no secondary language, nor errors
        result = self.release_builder.validate_translations()
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['warnings'], [])

        # add a secondary language
        fr = SecondaryAppLanguages(
            app=self.meta_app.app,
            language_code='fr',
        )
        fr.save()

        result = self.release_builder.validate_translations()

        self.assertEqual(result['warnings'], [])
        self.assertIn('translation for the language fr is incomplete', result['errors'][0].messages[0])

        localization_fr = {}

        for text_type, text in self.meta_app.localizations[self.meta_app.primary_language].items():

            if text_type == '_meta':
                continue

            localization_fr[text_type] = text

        self.meta_app.localizations['fr'] = localization_fr

        self.meta_app.save()

        result = self.release_builder.validate_translations()
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['warnings'], [])


    @test_settings
    def test_validate_options(self):
        
        ng_link = self.create_generic_content(NatureGuide, self.meta_app)
        nature_guide = ng_link.generic_content

        result = self.release_builder.validate_options(nature_guide)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['warnings'], [])

        gf_link = self.create_generic_content(GenericForm, self.meta_app)
        generic_form = gf_link.generic_content

        option = generic_form.make_option_from_instance(generic_form)

        ng_options = {
            'result_action' : option,
        }

        # option on the link
        ng_link.options = ng_options
        ng_link.save()

        result = self.release_builder.validate_options(nature_guide)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['warnings'], [])

        generic_form.delete()

        result = self.release_builder.validate_options(nature_guide)
        self.assertIn('does not exist', result['errors'][0].messages[0])
        self.assertEqual(result['warnings'], [])


    ##########################################################################################
    # tests for validation of generic contents
    ##########################################################################################
    @test_settings
    def test_validate_frontend(self):
        
        frontend = self.release_builder._get_frontend()

        result = self.release_builder.validate_Frontend(frontend)
        self.assertEqual(result['warnings'], [])
        self.assertTrue('legal notice' in result['errors'][0].messages[0])

        # check settings for requirements
        frontend_settings = self.release_builder._get_frontend_settings()

        required_image_types = []
        required_text_types = ['legal_notice']
        required_configuration_types = []

        for image_type, image_definition in frontend_settings['userContent']['images'].items():
            
            image_is_required = image_definition['required']

            if image_is_required == True:
                required_image_types.append(image_type)

        for text_type, text_definition in frontend_settings['userContent']['texts'].items():

            text_is_required = text_definition.get('required', False)

            if text_is_required == True:
                required_text_types.append(text_type)

        
        for configuration_type, configuration_definition in frontend_settings['userContent']['configuration'].items():

            configuration_is_required = configuration_definition.get('required', False)

            if configuration_is_required == True:
                required_configuration_types.append(configuration_type)


        required_count = len(required_text_types) + len (required_image_types) + len(required_configuration_types)

        self.assertEqual(len(result['errors']), required_count)


        # create all texts
        for text_type in required_text_types:

            frontend_text = FrontendText(
                frontend=frontend,
                frontend_name=frontend.frontend_name,
                identifier=text_type,
                text=text_type,
            )

            frontend_text.save()

        
        # create all confs
        frontend.configuration = {}
        for configuration_type in required_configuration_types:
            frontend.configuration[configuration_type] = 'test conf'
        
        frontend.save()
        
        result = self.release_builder.validate_Frontend(frontend)
        required_count = len(required_image_types)
        self.assertEqual(len(result['errors']), required_count)

        # create all images
        user = self.create_user()
        for image_type in required_image_types:

            namespaced_image_type = frontend.get_namespaced_image_type(image_type)
            self.create_content_image(frontend, user, taxon=None, image_type=namespaced_image_type)

        
        result = self.release_builder.validate_Frontend(frontend)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['warnings'], [])


    @test_settings
    def test_validate_BackboneTaxonomy(self):

        link = self.get_generic_content_link(BackboneTaxonomy)

        backbone_taxonomy = link.generic_content
        
        result = self.release_builder.validate_BackboneTaxonomy(backbone_taxonomy)
        self.assertIn('no taxa', result['errors'][0].messages[0])
        self.assertEqual(result['warnings'], [])

        lacerta_agilis = self.get_lazy_taxon(taxon_latname='Lacerta agilis')

        backbone_taxon = BackboneTaxa(
            backbonetaxonomy = backbone_taxonomy,
            taxon=lacerta_agilis,
        )

        backbone_taxon.save()

        result = self.release_builder.validate_BackboneTaxonomy(backbone_taxonomy)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['warnings'], [])


    @test_settings
    def test_validate_NatureGuide(self):
        
        self.create_all_generic_contents(self.meta_app)

        link = self.get_generic_content_link(NatureGuide)

        nature_guide = link.generic_content

        result = self.release_builder.validate_NatureGuide(nature_guide)

        self.assertIn('no setting for what happens', result['errors'][0].messages[0])
        self.assertEqual(result['warnings'], [])

        # add setting
        generic_form_link = self.get_generic_content_link(GenericForm)
        generic_form = generic_form_link.generic_content
        option = self.meta_app.make_option_from_instance(generic_form)

        link.options = {
            'result_action' : option
        }

        link.save()

        result = self.release_builder.validate_NatureGuide(nature_guide)

        self.assertIn('The nature guide is empty', result['errors'][0].messages[0])
        self.assertEqual(result['warnings'], [])

        # add one node
        child_node_name = 'Child node'
        child_node = self.create_node(nature_guide.root_node, child_node_name)

        result = self.release_builder.validate_NatureGuide(nature_guide)

        self.assertIn('The group Child node is empty', result['errors'][0].messages[0])
        self.assertIn('Image is missing', result['warnings'][0].messages[0])

        # add result
        result_name = 'result'
        identification_result = self.create_node(child_node, result_name, **{'node_type':'result'})

        result = self.release_builder.validate_NatureGuide(nature_guide)
        self.assertEqual(result['errors'], [])
        self.assertIn('Image is missing', result['warnings'][0].messages[0])
        self.assertIn('Image is missing', result['warnings'][1].messages[0])

        # add an empty matrix filter
        filter_type = 'DescriptiveTextAndImagesFilter'
        matrix_filter = self.create_matrix_filter('DTAI', child_node.meta_node, filter_type)

        result = self.release_builder.validate_NatureGuide(nature_guide)
        self.assertIn('This filter is empty', result['errors'][0].messages[0])
        self.assertIn('Image is missing', result['warnings'][0].messages[0])
        self.assertIn('Image is missing', result['warnings'][1].messages[0])

        space = MatrixFilterSpace(
            matrix_filter=matrix_filter,
            encoded_space='test filter', 
        )

        space.save()

        
        result = self.release_builder.validate_NatureGuide(nature_guide)
        self.assertEqual(result['errors'], [])
        self.assertIn('Image is missing', result['warnings'][0].messages[0])
        self.assertIn('Image is missing', result['warnings'][1].messages[0])


    @test_settings
    def test_validate_TaxonProfiles(self):
        
        link = self.get_generic_content_link(TaxonProfiles)
        taxon_profiles = link.generic_content

        result = self.release_builder.validate_TaxonProfiles(taxon_profiles)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['warnings'], [])

        lacerta_agilis = self.get_lazy_taxon(taxon_latname='Lacerta agilis')

        self.create_all_generic_contents(self.meta_app)

        link = self.get_generic_content_link(NatureGuide)

        nature_guide = link.generic_content
        result_name = 'result'
        identification_result = self.create_node(nature_guide.root_node, result_name,
            **{'node_type':'result'})

        identification_result.meta_node.taxon = lacerta_agilis
        identification_result.meta_node.save()

        result = self.release_builder.validate_TaxonProfiles(taxon_profiles)
        self.assertEqual(result['errors'], [])
        self.assertIn('taxa missing. A generic', result['warnings'][0].messages[0])


    @test_settings
    def test_validate_GenericForm(self):
        
        self.create_all_generic_contents(self.meta_app)

        link = self.get_generic_content_link(GenericForm)

        generic_form = link.generic_content

        result = self.release_builder.validate_GenericForm(generic_form)

        for error in result['errors']:
            print(error.messages)

        self.assertEqual(result['errors'], [])
        self.assertEqual(result['warnings'], [])

    @test_settings
    def test_validate_Glossary(self):
        
        self.create_all_generic_contents(self.meta_app)

        link = self.get_generic_content_link(Glossary)

        glossary = link.generic_content

        result = self.release_builder.validate_Glossary(glossary)

        self.assertEqual(result['errors'], [])
        self.assertEqual(result['warnings'], [])


    @test_settings
    def test_validate_Map(self):
        
        self.create_all_generic_contents(self.meta_app)

        link = self.get_generic_content_link(Map)

        map = link.generic_content

        result = self.release_builder.validate_Map(map)

        self.assertEqual(result['errors'], [])
        self.assertEqual(result['warnings'], [])


    ##########################################################################################
    # tests for build processes
    ##########################################################################################

    @test_settings
    def test_build(self):

        pass


