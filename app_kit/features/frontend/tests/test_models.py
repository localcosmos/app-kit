from django_tenants.test.cases import TenantTestCase

from django.contrib.contenttypes.models import ContentType

from app_kit.tests.common import test_settings

from app_kit.tests.mixins import WithMetaApp

from app_kit.models import MetaAppGenericContent

from app_kit.features.frontend.models import Frontend, FrontendText

from app_kit.appbuilder import AppPreviewBuilder


class WithFrontend(WithMetaApp):

    def setUp(self):
        super().setUp()
        self.content_type = ContentType.objects.get_for_model(Frontend)
        self.frontend_link = MetaAppGenericContent.objects.get(meta_app=self.meta_app, content_type=self.content_type)

        self.frontend = self.frontend_link.generic_content
        self.meta_app = self.frontend_link.meta_app
        
    def build_preview(self):
        
        preview_builder = AppPreviewBuilder(self.meta_app)
        preview_builder.build()
        
        

class TestFrontend(WithFrontend, TenantTestCase):

    @test_settings
    def test_get_primary_localization(self):
        localization = self.frontend.get_primary_localization()

        # create some frontend texts
        test_texts = ['test', 'üäö', '<p>html content</p>']
        for text in test_texts:
            frontend_text = FrontendText(
                frontend = self.frontend,
                identifier = text,
                text = text,
            )

            frontend_text.save()

        localization = self.frontend.get_primary_localization()
        for frontend_text in FrontendText.objects.all():
            text_key = 'frontend-text-{0}'.format(frontend_text.identifier) 
            self.assertIn(text_key, localization)

    @test_settings
    def test_taxa_and_higher_taxa(self):
        taxa = self.frontend.taxa()
        higher_taxa = self.frontend.higher_taxa()
        
    @test_settings
    def test_get_content_image_restrictions(self):
        
        restrictions = self.frontend.get_content_image_restrictions('appLauncherIcon')

        self.assertIn('file_type', restrictions)


class TestFrontendText(WithFrontend, TenantTestCase):

    @test_settings
    def test_create(self):

        text = 'test_text'
        identifier = 'test_text_identifier'

        frontend_text = FrontendText(
            frontend = self.frontend,
            frontend_name = self.frontend.frontend_name,
            identifier = identifier,
            text = text,
        )

        frontend_text.save()

        self.assertEqual(frontend_text.frontend, self.frontend)
        self.assertEqual(frontend_text.frontend_name, self.frontend.frontend_name)
        self.assertEqual(frontend_text.identifier, identifier)
        self.assertEqual(frontend_text.text, text)