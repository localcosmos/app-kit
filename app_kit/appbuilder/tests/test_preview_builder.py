from django_tenants.test.cases import TenantTestCase

from app_kit.tests.common import test_settings

from app_kit.tests.mixins import (WithMetaApp, WithTenantClient, WithUser, WithLoggedInUser, WithAjaxAdminOnly,
                                  WithAdminOnly, WithImageStore, WithFormTest, ViewTestMixin,
                                  WithMedia)

from app_kit.appbuilder import AppBuilder, AppPreviewBuilder

import os

TEST_PRIVATE_API_URL = 'https://localhost/private-api-test/'

class TestAppPreviewBuilder(WithMetaApp, TenantTestCase):

    def setUp(self):
        super().setUp()


    @test_settings
    def test_build(self):

        app_builder = AppBuilder(self.meta_app)

        self.assertFalse(os.path.isdir(app_builder._app_root_path))

        app_builder.create_app_version()

        self.assertTrue(os.path.isdir(app_builder._app_root_path))
        self.assertTrue(os.path.isdir(app_builder._app_version_root_path))
        
        preview_builder = AppPreviewBuilder(self.meta_app)

        self.assertFalse(os.path.isdir(preview_builder._app_builder_path))

        print(preview_builder._app_builder_path)

        preview_builder.build()

        self.assertTrue(os.path.isdir(preview_builder._app_builder_path))

        # preview_dir should be empty
        preview_dir = os.listdir(preview_builder._app_builder_path)
        self.assertEqual(len(preview_dir), 2)

        subfolders = [f.path for f in os.scandir(preview_builder._app_builder_path) if f.is_dir()]
        self.assertIn(preview_builder._app_build_sources_path, subfolders)
        self.assertIn(preview_builder._cordova_build_path, subfolders)

        www_subfolders = [f.path for f in os.scandir(preview_builder._app_www_path) if f.is_dir()]

        self.assertIn(preview_builder._app_localcosmos_content_path, www_subfolders)

        self.assertTrue(os.path.isfile(preview_builder._app_settings_json_filepath))

        self.assertTrue(os.path.isdir(preview_builder._preview_browser_served_path))

        self.assertTrue(os.path.isfile(preview_builder._app_locale_filepath(self.meta_app.primary_language)))
        self.assertTrue(os.path.isfile(preview_builder._app_glossarized_locale_filepath(self.meta_app.primary_language)))

    
    ###############################################################################################################
    #   TEST LOCALIZATION
    ###############################################################################################################
    @test_settings
    def test_app_locales_path(self):

        appbuilder = AppPreviewBuilder(self.meta_app)
        locales_path = appbuilder._app_locales_path
        self.assertTrue(locales_path.endswith('locales'))


    @test_settings
    def test_app_locale_path(self):

        language_code = 'jp'

        appbuilder = AppPreviewBuilder(self.meta_app)
        locale_path = appbuilder._app_locale_path(language_code)
        self.assertTrue(locale_path.endswith('locales/jp'))


    @test_settings
    def test_app_locale_filepath(self):

        language_code = 'jp'

        appbuilder = AppPreviewBuilder(self.meta_app)
        locale_path = appbuilder._app_locale_filepath(language_code)
        self.assertTrue(locale_path.endswith('locales/jp/plain.json'))

    
    @test_settings
    def test_app_locale_filepath(self):

        language_code = 'jp'

        appbuilder = AppPreviewBuilder(self.meta_app)
        locale_path = appbuilder._app_glossarized_locale_filepath(language_code)
        self.assertTrue(locale_path.endswith('locales/jp/glossarized.json'))