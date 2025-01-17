from django_tenants.test.cases import TenantTestCase

from app_kit.tests.common import test_settings

from app_kit.features.frontend.forms import FrontendSettingsForm

from app_kit.appbuilder import AppBuilder

from .test_models import WithFrontend

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