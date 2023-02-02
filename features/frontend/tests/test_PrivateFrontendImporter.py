from django.conf import settings
from django.db import connection
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile

from django_tenants.test.cases import TenantTestCase

from django.contrib.contenttypes.models import ContentType

from app_kit.tests.common import test_settings, TESTS_ROOT

from app_kit.features.frontend.PrivateFrontendImporter import PrivateFrontendImporter

from app_kit.tests.mixins import (WithTenantClient, WithUser, WithLoggedInUser, WithMetaApp)

from app_kit.models import MetaAppGenericContent

from app_kit.features.frontend.models import Frontend

from .mixins import WithFrontendZip, CleanFrontendTestFolders

import os, shutil

TEST_FRONTEND_NAME = 'Mountain'

class TestPrivateFrontendImporter(CleanFrontendTestFolders, WithFrontendZip, WithMetaApp, WithUser, WithLoggedInUser,
                                    WithTenantClient, TenantTestCase):


    def setUp(self):
        super().setUp()

        frontend_content_type = ContentType.objects.get_for_model(Frontend)
        frontend_link = MetaAppGenericContent.objects.get(content_type=frontend_content_type)
        self.frontend = frontend_link.generic_content


    def get_fake_zip_file(self):        
        file = ContentFile(b'content', name='Mountain.zip')
        return file


    def get_frontend_importer(self):
        return PrivateFrontendImporter(self.meta_app)

    @test_settings
    def test__init__(self):
        frontend_importer = self.get_frontend_importer()
        self.assertTrue(hasattr(frontend_importer, 'preview_builder'))
        self.assertFalse(frontend_importer.is_valid)
        self.assertIsNone(frontend_importer.temporary_frontend_folder)

    @test_settings
    def test_zip_destination_dir(self):

        frontend_importer = self.get_frontend_importer()

        self.assertTrue(frontend_importer.zip_destination_dir.startswith(TESTS_ROOT))
        self.assertTrue(frontend_importer.zip_destination_dir.startswith(settings.APP_KIT_TEMPORARY_FOLDER))
        self.assertIn(connection.schema_name, frontend_importer.zip_destination_dir)

    @test_settings
    def test_unzip_path(self):

        frontend_importer = self.get_frontend_importer()
        
        self.assertTrue(frontend_importer.unzip_path.startswith(TESTS_ROOT))
        self.assertTrue(frontend_importer.unzip_path.startswith(settings.APP_KIT_TEMPORARY_FOLDER))
        self.assertIn(connection.schema_name, frontend_importer.unzip_path)

    @test_settings
    def test_unzip_to_temporary_folder(self):
        valid_zip_file = self.get_valid_zip_file()
        frontend_importer = self.get_frontend_importer()
        frontend_importer.unzip_to_temporary_folder(valid_zip_file)

        self.assertTrue(os.path.isdir(frontend_importer.zip_destination_dir))

        frontend_zip_filepath = os.path.join(frontend_importer.zip_destination_dir, 'Frontend.zip')
        self.assertTrue(os.path.isfile(frontend_zip_filepath))

        frontend_dir = os.path.join(frontend_importer.unzip_path, TEST_FRONTEND_NAME)
        self.assertTrue(os.path.isdir(frontend_dir))

    @test_settings
    def test_validate_temporary_frontend_folder(self):
        valid_zip_file = self.get_valid_zip_file()
        frontend_importer = self.get_frontend_importer()
        frontend_importer.unzip_to_temporary_folder(valid_zip_file)

        self.assertIsNone(frontend_importer.temporary_frontend_folder)

        frontend_importer.validate_temporary_frontend_folder()
        frontend_dir = os.path.join(frontend_importer.unzip_path, TEST_FRONTEND_NAME)

        self.assertEqual(frontend_importer.errors, [])
        self.assertEqual(frontend_importer.temporary_frontend_folder, frontend_dir)

        # add bogus file to unzip path
        bogus_file_path = os.path.join(frontend_importer.unzip_path, 'test.txt')

        with open(bogus_file_path, 'w') as bogus_file:
            bogus_file.write('test')

        frontend_importer.validate_temporary_frontend_folder()
        self.assertIsNone(frontend_importer.temporary_frontend_folder)

        self.assertTrue(len(frontend_importer.errors), 1)
        

    @test_settings
    def test_get_frontend_settings(self):
        
        valid_zip_file = self.get_valid_zip_file()
        frontend_importer = self.get_frontend_importer()
        frontend_importer.unzip_to_temporary_folder(valid_zip_file)

        frontend_importer.validate_temporary_frontend_folder()

        frontend_settings = frontend_importer.get_frontend_settings()
        self.assertEqual(frontend_importer.errors, [])
        self.assertEqual(frontend_settings['frontend'], TEST_FRONTEND_NAME)
        self.assertEqual(frontend_settings['version'], '1.0')

        settings_path = os.path.join(frontend_importer.temporary_frontend_folder, 'settings.json')
        os.remove(settings_path)

        frontend_settings = frontend_importer.get_frontend_settings()
        self.assertEqual(frontend_settings, {})
        self.assertEqual(len(frontend_importer.errors), 1)        

    
    @test_settings
    def test_validate_settings_json(self):
        
        valid_zip_file = self.get_valid_zip_file()
        frontend_importer = self.get_frontend_importer()
        frontend_importer.unzip_to_temporary_folder(valid_zip_file)

        frontend_importer.validate_temporary_frontend_folder()

        frontend_settings = {}

        frontend_importer.validate_settings_json(frontend_settings)
        self.assertEqual(len(frontend_importer.errors), 3)

        frontend_importer.errors = []

        frontend_settings = {
            'frontend' : 'something'
        }

        frontend_importer.validate_settings_json(frontend_settings)
        self.assertEqual(len(frontend_importer.errors), 3)

        frontend_importer.errors = []
        frontend_settings = {
            'frontend' : TEST_FRONTEND_NAME
        }

        frontend_importer.validate_settings_json(frontend_settings)
        self.assertEqual(len(frontend_importer.errors), 2)

        frontend_importer.errors = []
        frontend_settings = {
            'frontend' : TEST_FRONTEND_NAME,
            'version' : '1.0',
        }

        frontend_importer.validate_settings_json(frontend_settings)
        self.assertEqual(len(frontend_importer.errors), 1)

        frontend_importer.errors = []
        frontend_settings = {
            'frontend' : TEST_FRONTEND_NAME,
            'version' : '1.0',
            'userContent' : {},
        }

        frontend_importer.validate_settings_json(frontend_settings)
        self.assertEqual(len(frontend_importer.errors), 1)

        frontend_importer.errors = []
        frontend_settings = {
            'frontend' : TEST_FRONTEND_NAME,
            'version' : '1.0',
            'userContent' : {
                'images' : {}
            },
        }

        frontend_importer.validate_settings_json(frontend_settings)
        self.assertEqual(len(frontend_importer.errors), 2)

        frontend_importer.errors = []
        frontend_settings = {
            'frontend' : TEST_FRONTEND_NAME,
            'version' : '1.0',
            'userContent' : {
                'images' : {
                    'appLauncherIcon' : {},
                    'appSplashscreen' : {},
                }
            },
        }

        frontend_importer.validate_settings_json(frontend_settings)
        self.assertEqual(len(frontend_importer.errors), 6)

        frontend_importer.errors = []
        frontend_settings = {
            'frontend' : TEST_FRONTEND_NAME,
            'version' : '1.0',
            'userContent' : {
                'images' : {
                    'appLauncherIcon' : {
                        'restrictions': {
                            'fileType': ['svg'],
                            'ratio': '1:1'
                        },
                        'required': True
                    },
                    'appSplashscreen' : {},
                },
            },
        }

        frontend_importer.validate_settings_json(frontend_settings)
        print(frontend_importer.errors)
        self.assertEqual(len(frontend_importer.errors), 3)


        frontend_importer.errors = []
        frontend_settings = {
            'frontend' : TEST_FRONTEND_NAME,
            'version' : '1.0',
            'userContent' : {
                'images' : {
                    'appLauncherIcon' : {
                        'restrictions': {
                            'fileType': ['svg'],
                            'ratio': '1:1'
                        },
                        'required': True
                    },
                    'appSplashscreen' : {
                        'restrictions': {
                            'ratio': '2:1'
                        },
                    },
                },
            },
        }

        frontend_importer.validate_settings_json(frontend_settings)
        self.assertEqual(len(frontend_importer.errors), 3)


        frontend_importer.errors = []
        frontend_settings = {
            'frontend' : TEST_FRONTEND_NAME,
            'version' : '1.0',
            'userContent' : {
                'images' : {
                    'appLauncherIcon' : {
                        'restrictions': {
                            'fileType': ['svg'],
                            'ratio': '1:1'
                        },
                        'required': True
                    },
                    'appSplashscreen' : {
                        'restrictions': {
                            'ratio': '1:1'
                        },
                    },
                },
            },
        }

        frontend_importer.validate_settings_json(frontend_settings)
        self.assertEqual(len(frontend_importer.errors), 2)

        frontend_importer.errors = []
        frontend_settings = {
            'frontend' : TEST_FRONTEND_NAME,
            'version' : '1.0',
            'userContent' : {
                'images' : {
                    'appLauncherIcon' : {
                        'restrictions': {
                            'fileType': ['svg'],
                            'ratio': '1:1'
                        },
                        'required': True
                    },
                    'appSplashscreen' : {
                        'restrictions': {
                            'fileType': ['svg'],
                            'ratio': '1:1'
                        },
                    },
                },
            },
        }

        frontend_importer.validate_settings_json(frontend_settings)
        self.assertEqual(len(frontend_importer.errors), 1)

        frontend_importer.errors = []
        frontend_settings = {
            'frontend' : TEST_FRONTEND_NAME,
            'version' : '1.0',
            'userContent' : {
                'images' : {
                    'appLauncherIcon' : {
                        'restrictions': {
                            'fileType': ['svg'],
                            'ratio': '1:1'
                        },
                        'required': True
                    },
                    'appSplashscreen' : {
                        'restrictions': {
                            'fileType': ['svg'],
                            'ratio': '1:1'
                        },
                        'required' : True
                    },
                },
            },
        }

        frontend_importer.validate_settings_json(frontend_settings)
        self.assertEqual(len(frontend_importer.errors), 0)


    @test_settings
    def test_validate_frontend_files(self):
        
        valid_zip_file = self.get_valid_zip_file()
        frontend_importer = self.get_frontend_importer()
        frontend_importer.unzip_to_temporary_folder(valid_zip_file)

        frontend_importer.validate_temporary_frontend_folder()

        self.assertEqual(frontend_importer.errors, [])

        frontend_importer.validate_frontend_files()

        self.assertEqual(frontend_importer.errors, [])
        www_folder_path = os.path.join(frontend_importer.temporary_frontend_folder, 'www')
        shutil.rmtree(www_folder_path)

        self.assertFalse(os.path.isdir(www_folder_path))

        frontend_importer.validate_frontend_files()

        self.assertEqual(len(frontend_importer.errors), 1)

        os.makedirs(www_folder_path)

        settings_json_path = os.path.join(frontend_importer.temporary_frontend_folder, 'settings.json')
        os.remove(settings_json_path)
        frontend_importer.errors = []

        frontend_importer.validate_frontend_files()

        self.assertEqual(len(frontend_importer.errors), 1)


    @test_settings
    def test_get_frontend_name(self):
        
        valid_zip_file = self.get_valid_zip_file()
        frontend_importer = self.get_frontend_importer()
        frontend_importer.unzip_to_temporary_folder(valid_zip_file)

        with self.assertRaises(ValueError):
            name = frontend_importer.get_frontend_name()

        frontend_importer.validate()

        self.assertTrue(frontend_importer.is_valid)
        name = frontend_importer.get_frontend_name()
        self.assertEqual(name, TEST_FRONTEND_NAME)


    @test_settings
    def test_validate(self):
        
        valid_zip_file = self.get_valid_zip_file()
        frontend_importer = self.get_frontend_importer()
        frontend_importer.unzip_to_temporary_folder(valid_zip_file)

        is_valid = frontend_importer.validate()

        self.assertTrue(is_valid)

    @test_settings
    def test_invalidate(self):

        invalid_zip_file = self.get_invalid_zip_file()
        frontend_importer = self.get_frontend_importer()
        frontend_importer.unzip_to_temporary_folder(invalid_zip_file)

        is_valid = frontend_importer.validate()

        self.assertFalse(is_valid)

        self.assertFalse(os.path.isdir(frontend_importer.zip_destination_dir))

    @test_settings
    def test_install_frontend(self):
        
        valid_zip_file = self.get_valid_zip_file()
        frontend_importer = self.get_frontend_importer()
        frontend_importer.unzip_to_temporary_folder(valid_zip_file)

        is_valid = frontend_importer.validate()

        self.assertTrue(is_valid)

        preview_builder = self.meta_app.get_preview_builder()

        frontend_temporary_path = os.path.join(frontend_importer.unzip_path, TEST_FRONTEND_NAME)
        frontend_path = preview_builder.get_private_frontend_path(TEST_FRONTEND_NAME)

        self.assertTrue(os.path.isdir(frontend_temporary_path))
        self.assertFalse(os.path.isdir(frontend_path))

        frontend_importer.install_frontend()

        self.assertFalse(os.path.isdir(frontend_temporary_path))
        self.assertTrue(os.path.isdir(frontend_path))
        self.assertFalse(os.path.isdir(frontend_importer.zip_destination_dir))

    @test_settings
    def test_install_invalid_frontend(self):
        
        frontend_importer = self.get_frontend_importer()

        self.assertFalse(frontend_importer.is_valid)
        with self.assertRaises(ValueError):
            frontend_importer.install_frontend()


