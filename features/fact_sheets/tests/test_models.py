##############################################################################################################
#
# TESTS FOR MODELS
#
##############################################################################################################

from django.conf import settings

from django_tenants.test.cases import TenantTestCase

from django.contrib.contenttypes.models import ContentType

from app_kit.tests.common import (test_settings, TEST_TEMPLATE_PATH)
from app_kit.tests.mixins import WithMetaApp, WithUser, WithMedia, WithImageStore
from django.core.files.uploadedfile import SimpleUploadedFile

from app_kit.features.fact_sheets.models import (FactSheet, factsheet_templates_upload_path, FactSheetTemplates)


from app_kit.features.fact_sheets.tests.common import WithFactSheets

from app_kit.models import ContentImage

class TestFactSheets(WithMedia, WithImageStore, WithFactSheets, WithUser, WithMetaApp, TenantTestCase):

    @test_settings
    def test_get_primary_localization(self):

        self.build_preview_app()

        fact_sheet = FactSheet(
            fact_sheets = self.fact_sheets,
            template_name = self.template_name,
            title = self.title,
            navigation_link_name = self.navigation_link_name,
            contents = {
                'test_type' : '<a href="#">test</a>',
            },
        )

        fact_sheet.save()

        # fact sheet image
        fact_sheet_content_type = ContentType.objects.get_for_model(FactSheet)
        image_store = self.create_image_store()
        
        fact_sheet_image = ContentImage(
            image_store = image_store,
            content_type = fact_sheet_content_type,
            object_id = fact_sheet.id,
            image_type = 'test_image',
        )

        fact_sheet_image.save()

        
        image_locale_key = fact_sheet_image.get_image_locale_key()

        locale = self.fact_sheets.get_primary_localization(self.meta_app)

        self.assertFalse(image_locale_key in locale)
        self.assertFalse(image_locale_key in locale['_meta'])

        self.assertEqual(locale[self.fact_sheets.name], self.fact_sheets.name)
        
        self.assertEqual(locale[fact_sheet.navigation_link_name], fact_sheet.navigation_link_name)
        self.assertEqual(locale[fact_sheet.title], fact_sheet.title)

        self.assertEqual(locale['{0}_test_type'.format(fact_sheet.id)], fact_sheet.contents['test_type'])

        # mark the image translatable
        fact_sheet_image.requires_translation = True
        fact_sheet_image.save()

        locale = self.fact_sheets.get_primary_localization(self.meta_app)

        '''
            {
                '_meta': {
                    'localized_image_77_1.jpg': {
                        'type': 'image',
                        'media_url': '/media/fact_sheets/content/1/1/images/test_image/test.jpg',
                        'content_type_id': 77,
                        'object_id': 1
                    }
                },
                'Test Fact Sheets': 'Test Fact Sheets',
                'Neobiota': 'Neobiota',
                'Neobiota link': 'Neobiota link',
                '1_test_type': '<a href="#">test</a>',
                'localized_image_77_1.jpg': 'locales/en/images/localized_image_77_1_en.jpg'
            }
        '''

        self.assertIn(image_locale_key, locale)
        self.assertEqual(locale[image_locale_key]['image_type'], 'test_image')
        self.assertEqual(locale[image_locale_key]['media_url'], fact_sheet_image.image_url())
        self.assertEqual(locale[image_locale_key]['content_type_id'], fact_sheet_content_type.id)
        self.assertEqual(locale[image_locale_key]['object_id'], fact_sheet.id)        


class TestFactSheet(WithFactSheets, WithMetaApp, TenantTestCase):

    @test_settings
    def test_create(self):

        self.build_preview_app()

        fact_sheet = FactSheet(
            fact_sheets = self.fact_sheets,
            template_name = self.template_name,
            title = self.title,
            navigation_link_name = self.navigation_link_name,
        )

        fact_sheet.save()

        fact_sheet.refresh_from_db()

        self.assertEqual(fact_sheet.fact_sheets, self.fact_sheets)
        self.assertEqual(fact_sheet.template_name, self.template_name)
        self.assertEqual(fact_sheet.title, self.title)
        self.assertEqual(fact_sheet.navigation_link_name, self.navigation_link_name)
        self.assertEqual(fact_sheet.slug, 'neobiota-{0}'.format(fact_sheet.pk))
        

    @test_settings
    def test_get_template(self):

        self.build_preview_app()
        
        fact_sheet = self.create_fact_sheet()
        # just test execution
        template = fact_sheet.get_template(self.meta_app)


    @test_settings
    def test_get_atomic_content(self):

        self.build_preview_app()

        fact_sheet = self.create_fact_sheet()

        html = '<a href="#">test</a>'
        fact_sheet.contents = {
            'test_type' : html,
        }

        fact_sheet.save()

        content = fact_sheet.get_atomic_content('test_type')
        self.assertEqual(content, html)
        

    @test_settings
    def test_render_as_html(self):

        self.build_preview_app()

        fact_sheet = self.create_fact_sheet()

        html = fact_sheet.render_as_html(self.meta_app)
        self.assertTrue(isinstance(html, str))


    @test_settings
    def test_str(self):

        self.build_preview_app()

        fact_sheet = self.create_fact_sheet()
        self.assertEqual(str(fact_sheet), self.title)


    @test_settings
    def test_get_content_image_restrictions(self):

        self.build_preview_app()

        fact_sheet = self.create_fact_sheet()

        restrictions = fact_sheet.get_content_image_restrictions(image_type='image')
        expected_restrictions = {
            'allow_features' : False,
            'allow_cropping' : False,
        }
        self.assertEqual(restrictions, expected_restrictions)


class TestFactSheetTemplates(WithFactSheets, WithUser, WithMetaApp, TenantTestCase):

    @test_settings
    def test_create_and_path(self):

        self.build_preview_app()

        filename = 'neobiota.html'

        template = SimpleUploadedFile(name=filename, content=open(TEST_TEMPLATE_PATH , 'rb').read(),
                                        content_type='text/html')

        user = self.create_user()

        fact_sheet_template = FactSheetTemplates(
            fact_sheets = self.fact_sheets,
            template = template,
            uploaded_by = user,
        )

        fact_sheet_template.save()

        fact_sheet_template.refresh_from_db()
        self.assertEqual(fact_sheet_template.fact_sheets, self.fact_sheets)
        self.assertEqual(fact_sheet_template.uploaded_by, user)

        # test upload path

        path = factsheet_templates_upload_path(fact_sheet_template, filename)
        expected_path = 'fact_sheets/templates/{0}/{1}'.format(self.fact_sheets.id, filename)
        self.assertEqual(path, expected_path)

