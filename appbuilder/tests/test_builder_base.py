from xml.dom import NotFoundErr
from django_tenants.test.cases import TenantTestCase

from django.contrib.contenttypes.models import ContentType

from app_kit.tests.common import test_settings, TESTS_ROOT

from app_kit.tests.mixins import (WithMetaApp,)

from app_kit.appbuilder.AppBuilderBase import AppBuilderBase

from app_kit.models import MetaAppGenericContent
from app_kit.features.frontend.models import Frontend, FrontendText

TEST_PRIVATE_API_URL = 'https://localhost/private-api-test/'

from django.conf import settings

import shutil


import os

class TestAppBuilderBase(WithMetaApp, TenantTestCase):

    def setUp(self):
        super().setUp()
        self.test_dir = os.path.join(TESTS_ROOT, 'deletecreate_test')

    def tearDown(self):
        if os.path.isdir(self.test_dir):
            shutil.rmtree(self.test_dir)


    def get_frontend(self):

        frontend_content_type = ContentType.objects.get_for_model(Frontend)
        frontend_link = MetaAppGenericContent.objects.get(content_type=frontend_content_type,
            meta_app=self.meta_app)

        frontend = frontend_link.generic_content

        return frontend


    @test_settings
    def test_init(self):
        appbuilder = AppBuilderBase(self.meta_app)

        self.assertEqual(appbuilder.meta_app, self.meta_app)
        self.assertTrue(hasattr(appbuilder, '_builder_root_path'))
        self.assertTrue(hasattr(appbuilder, '_certificates_path'))

    @test_settings
    def test_validate(self):
        appbuilder = AppBuilderBase(self.meta_app)
        with self.assertRaises(NotImplementedError):
            appbuilder.validate()


    @test_settings
    def test_build(self):
        appbuilder = AppBuilderBase(self.meta_app)
        with self.assertRaises(NotImplementedError):
            appbuilder.build()


    @test_settings
    def test_deletecreate_folder(self):

        appbuilder = AppBuilderBase(self.meta_app)

        self.assertFalse(os.path.exists(self.test_dir))

        appbuilder.deletecreate_folder(self.test_dir)
        self.assertTrue(os.path.isdir(self.test_dir))

        appbuilder.deletecreate_folder(self.test_dir)

        self.assertTrue(os.path.isdir(self.test_dir))


    @test_settings
    def test_localcosmos_server_api_url(self):
        appbuilder = AppBuilderBase(self.meta_app)
        url = appbuilder._localcosmos_server_api_url()

        # set localcosmos_private
        self.meta_app.global_options['localcosmos_private'] = True
        self.meta_app.global_options['localcosmos_private_api_url'] = TEST_PRIVATE_API_URL

        url_2 = appbuilder._localcosmos_server_api_url()

        self.assertEqual(url, url_2)


    @test_settings
    def test_localcosmos_road_remotedb_api_url(self):
        appbuilder = AppBuilderBase(self.meta_app)
        url = appbuilder._localcosmos_road_remotedb_api_url()

        # set localcosmos_private
        self.meta_app.global_options['localcosmos_private'] = True
        self.meta_app.global_options['localcosmos_private_api_url'] = TEST_PRIVATE_API_URL

        url_2 = appbuilder._localcosmos_road_remotedb_api_url()

        self.assertEqual(url, url_2)


    @test_settings
    def test_app_api_url(self):
        appbuilder = AppBuilderBase(self.meta_app)

        url = appbuilder._app_api_url()

        # set localcosmos_private
        self.meta_app.global_options['localcosmos_private'] = True
        self.meta_app.global_options['localcosmos_private_api_url'] = TEST_PRIVATE_API_URL

        url_2 = appbuilder._app_api_url()

        self.assertEqual(TEST_PRIVATE_API_URL, url_2)


    @test_settings
    def test_app_road_remotedb_api_url(self):

        appbuilder = AppBuilderBase(self.meta_app)

        url = appbuilder._app_road_remotedb_api_url()

        # set localcosmos_private
        self.meta_app.global_options['localcosmos_private'] = True
        self.meta_app.global_options['localcosmos_private_api_url'] = TEST_PRIVATE_API_URL

        url_2 = appbuilder._app_road_remotedb_api_url()

        self.assertEqual(TEST_PRIVATE_API_URL + 'road-remotedb-api/', url_2)

    
    @test_settings
    def test_public_frontends_path(self):
        appbuilder = AppBuilderBase(self.meta_app)

        self.assertTrue('app_kit/appbuilder/app/frontends' in appbuilder.public_frontends_path)

    @test_settings
    def test_private_frontends_path(self):
        appbuilder = AppBuilderBase(self.meta_app)
        print(appbuilder.private_frontends_path)

    
    @test_settings
    def test_get_frontend(self):
        appbuilder = AppBuilderBase(self.meta_app)

        frontend = appbuilder._get_frontend()

        self.assertEqual(frontend.__class__.__name__, 'Frontend')


    @test_settings
    def test_frontend_root_path(self):

        appbuilder = AppBuilderBase(self.meta_app)

        self.assertEqual(appbuilder._frontend_root_path, os.path.join(appbuilder.public_frontends_path,
            settings.APP_KIT_DEFAULT_FRONTEND))


        frontend = self.get_frontend()

        frontend.frontend_name = 'nonexistant'
        frontend.save()

        with self.assertRaises(NotFoundErr):
            frontend_root_path = appbuilder._frontend_root_path


    @test_settings
    def test_frontend_www_path(self):

        appbuilder = AppBuilderBase(self.meta_app)

        self.assertEqual(appbuilder._frontend_www_path, os.path.join(appbuilder.public_frontends_path,
            settings.APP_KIT_DEFAULT_FRONTEND, 'www'))


    @test_settings
    def test_frontend_www_path(self):
        appbuilder = AppBuilderBase(self.meta_app)
        path = appbuilder._frontend_www_path
        self.assertTrue(path.endswith('Flat/www'))

    
    @test_settings
    def test_frontend_webapp_assets_www_path(self):

        appbuilder = AppBuilderBase(self.meta_app)

        self.assertTrue(appbuilder._frontend_webapp_assets_www_path.endswith('webapp/www'))
    

    ###############################################################################################################
    #   TEST PATHS
    ###############################################################################################################
    @test_settings
    def test_app_root_path(self):
        appbuilder = AppBuilderBase(self.meta_app)
        path = appbuilder._app_root_path


    @test_settings
    def test_app_version_root_path(self):
        appbuilder = AppBuilderBase(self.meta_app)
        path = appbuilder._app_version_root_path

    @test_settings
    def test_app_preview_path(self):
        appbuilder = AppBuilderBase(self.meta_app)
        path = appbuilder._app_preview_path
        self.assertTrue(path.endswith('preview'))

    @test_settings
    def test_app_www_path(self):
        appbuilder = AppBuilderBase(self.meta_app)

        with self.assertRaises(NotImplementedError):
            path = appbuilder._app_www_path


    @test_settings
    def test_app_release_path(self):
        appbuilder = AppBuilderBase(self.meta_app)
        path = appbuilder._app_release_path
        self.assertTrue(path.endswith('release'))


    ###############################################################################################################
    #   TEST LOCALIZATION
    ###############################################################################################################
    @test_settings
    def test_app_locales_path(self):

        appbuilder = AppBuilderBase(self.meta_app)
        with self.assertRaises(NotImplementedError):
            locales_path = appbuilder._app_locales_path


    @test_settings
    def test_app_locale_path(self):

        language_code = 'jp'

        appbuilder = AppBuilderBase(self.meta_app)

        with self.assertRaises(NotImplementedError):
            locale_path = appbuilder._app_locale_path(language_code)


    @test_settings
    def test_app_locale_filepath(self):

        language_code = 'jp'

        appbuilder = AppBuilderBase(self.meta_app)

        with self.assertRaises(NotImplementedError):
            locale_path = appbuilder._app_locale_filepath(language_code)

    
    @test_settings
    def test_app_locale_filepath(self):

        language_code = 'jp'

        appbuilder = AppBuilderBase(self.meta_app)

        with self.assertRaises(NotImplementedError):
            locale_path = appbuilder._app_glossarized_locale_filepath(language_code)

    
    @test_settings
    def test_fill_primary_localization(self):

        self.create_all_generic_contents(self.meta_app)

        self.assertEqual(self.meta_app.localizations, None)

        appbuilder = AppBuilderBase(self.meta_app)
        appbuilder.fill_primary_localization()

        self.assertIn(self.meta_app.primary_language, self.meta_app.localizations)

        generic_content_links = MetaAppGenericContent.objects.filter(meta_app=self.meta_app)

        for link in generic_content_links:
            generic_content = link.generic_content
            self.assertIn(generic_content.name, self.meta_app.localizations[self.meta_app.primary_language])

        # create a few FrontendTexts
        frontend = appbuilder._get_frontend()
        frontend_settings = appbuilder._get_frontend_settings()
        for text_type, text_definition in frontend_settings['user_content']['texts'].items():

            frontend_text = FrontendText(
                frontend=frontend,
                frontend_name=frontend.frontend_name,
                identifier=text_type,
                text=text_type,
            )

            frontend_text.save()

        appbuilder.fill_primary_localization()

        for link in generic_content_links:
            generic_content = link.generic_content
            self.assertIn(generic_content.name, self.meta_app.localizations[self.meta_app.primary_language])

        for text_type, text_definition in frontend_settings['user_content']['texts'].items():
            self.assertIn(text_type, self.meta_app.localizations[self.meta_app.primary_language])

    
    @test_settings
    def test_get_localized(self):

        # empty test
        appbuilder = AppBuilderBase(self.meta_app)

        test_key = 'test text'
        test_value = 'test value'

        loc = appbuilder.get_localized(test_key, 'jp')
        self.assertEqual(loc, None)

        self.meta_app.localizations = {}
        self.meta_app.save()

        loc = appbuilder.get_localized(test_key, 'jp')
        self.assertEqual(loc, None)

        self.meta_app.localizations = {
            'jp' : {
                'test text' : test_value
            }
        }

        self.meta_app.save()

        loc = appbuilder.get_localized(test_key, 'jp')
        self.assertEqual(loc, test_value)


    ###############################################################################################################
    #   TEST settings.json file creation
    ###############################################################################################################
    @test_settings
    def test_get_localcosmos_settings(self):
        appbuilder = AppBuilderBase(self.meta_app)

        localcosmos_settings = appbuilder._get_localcosmos_settings()
        self.assertFalse(localcosmos_settings['PREVIEW'])

        localcosmos_preview_settings = appbuilder._get_localcosmos_settings(preview=True)
        self.assertTrue(localcosmos_preview_settings['PREVIEW'])


    @test_settings
    def test_get_frontend_settings(self):
        appbuilder = AppBuilderBase(self.meta_app)
        frontend_settings = appbuilder._get_frontend_settings()


    @test_settings
    def test_get_app_settings(self):
        appbuilder = AppBuilderBase(self.meta_app)
        app_settings = appbuilder._get_app_settings()
