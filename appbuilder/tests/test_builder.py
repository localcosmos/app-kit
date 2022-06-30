from django_tenants.test.cases import TenantTestCase

from app_kit.tests.common import test_settings

from app_kit.tests.mixins import (WithMetaApp,)

from app_kit.appbuilder.AppBuilderBase import AppBuilder, AppVersionExistsError

from django.conf import settings


import os

class TestAppBuilder(WithMetaApp, TenantTestCase):

    def setUp(self):
        super().setUp()


    @test_settings
    def test_init(self):
        appbuilder = AppBuilder(self.meta_app)

    @test_settings
    def test_create_app_version(self):
        
        expected_app_version_path = os.path.join(settings.APP_KIT_ROOT, str(self.meta_app.uuid), 'version',
            str(self.meta_app.current_version))

        self.assertFalse(os.path.exists(expected_app_version_path))

        appbuilder = AppBuilder(self.meta_app)

        appbuilder.create_app_version()

        print(expected_app_version_path)
        self.assertTrue(os.path.exists(expected_app_version_path))

        with self.assertRaises(AppVersionExistsError):
            appbuilder.create_app_version()


    @test_settings
    def test_delete_app_version(self):

        appbuilder = AppBuilder(self.meta_app)
        appbuilder.create_app_version()

        version_1_path = appbuilder._app_version_root_path
        self.assertTrue(version_1_path.endswith('/1'))

        self.assertTrue(os.path.exists(version_1_path))

        self.meta_app.current_version = self.meta_app.current_version + 1
        self.meta_app.save()

        appbuilder.create_app_version()

        version_2_path = appbuilder._app_version_root_path

        self.assertTrue(os.path.exists(version_2_path))
        self.assertTrue(os.path.exists(version_1_path))

        with self.assertRaises(AppVersionExistsError):
            appbuilder.create_app_version()

        appbuilder.delete_app_version(1)
        self.assertFalse(os.path.exists(version_1_path))

        with self.assertRaises(NotImplementedError):
            appbuilder.delete_app_version(2)


    @test_settings
    def test_delete_app(self):

        appbuilder = AppBuilder(self.meta_app)
        
        self.assertFalse(os.path.isdir(appbuilder._app_root_path))

        appbuilder.create_app_version()

        self.assertTrue(os.path.isdir(appbuilder._app_root_path))

        appbuilder.delete_app()
        self.assertFalse(os.path.isdir(appbuilder._app_root_path))