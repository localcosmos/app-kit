from django_tenants.test.cases import TenantTestCase

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

import os

from unittest.mock import patch

from app_kit.tests.common import test_settings

from app_kit.features.frontend.forms import FrontendSettingsForm
from app_kit.features.frontend.models import FrontendResourceFile

from app_kit.appbuilder import AppBuilder

from .test_models import WithFrontend


MOCK_RESOURCE_FILES = {
    'firebaseAndroid': {
        'platform': 'android',
        'fileType': ['json'],
        'fileName': 'google-services.json',
        'cordovaTarget': 'app/google-services.json',
        'helpText': 'Firebase configuration file for Android.',
        'required': True,
    },
    'firebaseIOS': {
        'platform': 'ios',
        'fileType': ['plist'],
        'fileName': 'GoogleService-Info.plist',
        'cordovaTarget': '',
        'helpText': 'Firebase configuration file for iOS.',
        'required': True,
    },
}


def add_resource_files_to_settings(original_get_settings):
    def patched(self_inner):
        settings = original_get_settings(self_inner)
        settings['userContent']['resourceFiles'] = MOCK_RESOURCE_FILES
        return settings
    return patched

class TestFrontendSettingsForm(WithFrontend, TenantTestCase):

    @test_settings
    def test_init(self):
        
        form = FrontendSettingsForm(self.meta_app, self.frontend)

        self.assertEqual(form.meta_app, self.meta_app)
        self.assertEqual(form.frontend, self.frontend)
        self.assertEqual(type(form.frontend_settings), dict)

        for field in form:
            self.assertFalse(field.field.required)

    @test_settings
    def test_get_frontend_settings_fields(self):
        
        form = FrontendSettingsForm(self.meta_app, self.frontend)

        self.assertIn('legal_notice', form.fields)
        self.assertIn('privacy_policy', form.fields)
        self.assertIn('termsOfUse', form.fields)
        self.assertIn('appLauncherIcon', form.fields)
        #self.assertIn('appBackground', form.fields)

    @test_settings
    def test_validate(self):
        
        # only texts get data. images are using TwoStepFileInout with a separate dialogue

        app_builder = AppBuilder(self.meta_app)
        frontend_settings = app_builder._get_frontend_settings()

        data = {}

        user_texts = frontend_settings['userContent']['texts']

        for text_type, definition in user_texts.items():

            data[text_type] = text_type

        form = FrontendSettingsForm(self.meta_app, self.frontend, data=data)

        form.is_valid()

        self.assertEqual(form.errors, {})

        for text_type, definition in user_texts.items():
            self.assertEqual(form.cleaned_data[text_type], text_type)


    @test_settings
    def test_resource_file_fields_added(self):
        with patch.object(AppBuilder, '_get_frontend_settings',
                          add_resource_files_to_settings(AppBuilder._get_frontend_settings)):
            form = FrontendSettingsForm(self.meta_app, self.frontend)

        self.assertIn('resource_file_firebaseAndroid', form.fields)
        self.assertIn('resource_file_firebaseIOS', form.fields)

    @test_settings
    def test_resource_file_fields_always_not_required(self):
        with patch.object(AppBuilder, '_get_frontend_settings',
                          add_resource_files_to_settings(AppBuilder._get_frontend_settings)):
            form = FrontendSettingsForm(self.meta_app, self.frontend)

        self.assertFalse(form.fields['resource_file_firebaseAndroid'].required)
        self.assertFalse(form.fields['resource_file_firebaseIOS'].required)

    @test_settings
    def test_resource_file_fields_still_not_required_when_existing(self):
        FrontendResourceFile.objects.create(
            frontend=self.frontend,
            identifier='firebaseAndroid',
            resource_file=SimpleUploadedFile('google-services.json', b'{}'),
        )

        with patch.object(AppBuilder, '_get_frontend_settings',
                          add_resource_files_to_settings(AppBuilder._get_frontend_settings)):
            form = FrontendSettingsForm(self.meta_app, self.frontend)

        self.assertFalse(form.fields['resource_file_firebaseAndroid'].required)
        self.assertFalse(form.fields['resource_file_firebaseIOS'].required)

    @test_settings
    def test_resource_file_field_initial_set_when_existing(self):
        rf = FrontendResourceFile.objects.create(
            frontend=self.frontend,
            identifier='firebaseAndroid',
            resource_file=SimpleUploadedFile('google-services.json', b'{}'),
        )

        with patch.object(AppBuilder, '_get_frontend_settings',
                          add_resource_files_to_settings(AppBuilder._get_frontend_settings)):
            form = FrontendSettingsForm(self.meta_app, self.frontend,
                                        initial={'resource_file_firebaseAndroid': rf.resource_file})

        self.assertEqual(form.initial.get('resource_file_firebaseAndroid'), rf.resource_file)

    @test_settings
    def test_resource_file_field_rejects_wrong_extension(self):
        with patch.object(AppBuilder, '_get_frontend_settings',
                          add_resource_files_to_settings(AppBuilder._get_frontend_settings)):
            form = FrontendSettingsForm(
                self.meta_app,
                self.frontend,
                data={},
                files={'resource_file_firebaseAndroid': SimpleUploadedFile('wrong.xml', b'<xml/>')},
            )

        form.is_valid()
        self.assertIn('resource_file_firebaseAndroid', form.errors)

    @test_settings
    def test_resource_file_field_accepts_correct_extension(self):
        with patch.object(AppBuilder, '_get_frontend_settings',
                          add_resource_files_to_settings(AppBuilder._get_frontend_settings)):
            form = FrontendSettingsForm(
                self.meta_app,
                self.frontend,
                data={},
                files={
                    'resource_file_firebaseAndroid': SimpleUploadedFile('google-services.json', b'{}'),
                    'resource_file_firebaseIOS': SimpleUploadedFile('GoogleService-Info.plist', b'<plist/>'),
                },
            )

        form.is_valid()
        self.assertNotIn('resource_file_firebaseAndroid', form.errors)
        self.assertNotIn('resource_file_firebaseIOS', form.errors)

    @test_settings
    def test_resource_file_field_rejects_wrong_filename(self):
        with patch.object(AppBuilder, '_get_frontend_settings',
                          add_resource_files_to_settings(AppBuilder._get_frontend_settings)):
            form = FrontendSettingsForm(
                self.meta_app,
                self.frontend,
                data={},
                files={'resource_file_firebaseAndroid': SimpleUploadedFile('wrong-name.json', b'{}')},
            )

        form.is_valid()
        self.assertIn('resource_file_firebaseAndroid', form.errors)

    @test_settings
    def test_resource_file_saved_to_correct_path(self):
        rf = FrontendResourceFile.objects.create(
            frontend=self.frontend,
            identifier='firebaseAndroid',
            resource_file=SimpleUploadedFile('google-services.json', b'{}'),
        )

        expected_prefix = os.path.join(
            settings.APP_KIT_FRONTEND_RESOURCE_FILES_ROOT,
            str(self.frontend.pk),
            'firebaseAndroid',
        )
        self.assertTrue(rf.resource_file.path.startswith(expected_prefix))
        self.assertIn('google-services', os.path.basename(rf.resource_file.path))