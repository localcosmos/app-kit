##############################################################################################################
#
# TESTS FOR MODELS
#
##############################################################################################################

from django.conf import settings

from django_tenants.test.cases import TenantTestCase

from app_kit.tests.common import (test_settings, TEST_MEDIA_ROOT, TEST_IMAGE_PATH)
from app_kit.tests.mixins import WithMetaApp

from app_kit.features.fact_sheets.models import (FactSheet, FactSheetImages, FactSheets,
                factsheet_images_upload_path, factsheet_templates_upload_path, FactSheetTemplates)


import os, shutil

class WithFactSheets:

    def create_fact_sheets(self):
        fact_sheets = FactSheets.objects.create('Test Fact Sheets', 'en')
        return fact_sheets

    def create_fact_sheet(self):

        fact_sheet = FactSheet(
            fact_sheets = self.fact_sheets,
            template_name = self.template_name,
            title = self.title,
            navigation_link_name = self.navigation_link_name,
        )

        fact_sheet.save()

        return fact_sheet


    def get_image(self, name='test_image.jpg'):
        image = SimpleUploadedFile(name=name, content=open(TEST_IMAGE_PATH, 'rb').read(),
                                        content_type='image/jpeg')

        return image


    def clean_media(self):
        
        if os.path.isdir(TEST_MEDIA_ROOT):
            shutil.rmtree(TEST_MEDIA_ROOT)

        os.makedirs(TEST_MEDIA_ROOT)  

    
    def tearDown(self):
        super().tearDown()
        self.clean_media()
        

    def setUp(self):
        self.clean_media()
        super().setUp()
        self.fact_sheets = self.create_fact_sheets()
        
    
class TestFactSheet(WithFactSheets, WithMetaApp, TenantTestCase):

    template_name = 'test.html'
    title = 'Neobiota'
    navigation_link_name = 'Neobiota link'

    @test_settings
    def test_create(self):

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
        
        fact_sheet = self.create_fact_sheet()
        # just test execution
        template = fact_sheet.get_template(self.meta_app)


    @test_settings
    def test_get_atomic_content(self):

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

        fact_sheet = self.create_fact_sheet()

        html = fact_sheet.render_as_html(self.meta_app)
        self.assertTrue(isinstance(html, str))


    @test_settings
    def test_str(self):

        fact_sheet = self.create_fact_sheet()
        self.assertEqual(str(fact_sheet), self.title)



class TestFactSheetImagesUploadPath(WithFactSheets, WithMetaApp, TenantTestCase):

    @test_settings
    def test_path(self):

        fact_sheet = self.create_fact_sheet()

        filename = 'test.jpg'

        fact_sheet_image = FactSheetImages(
            fact_sheet = self.fact_sheet,
            microcontent_type = 'test_image',
            image = self.get_image(filename)
        )

        path = factsheet_images_upload_path(fact_sheet_image)

        expected_path = 'fact_sheets/content/{0}/{1}/images/{2}'.format(self.fact_sheets.id, self.fact_sheet.id,
                                                                        filename)
        self.assertEqual(path, expected_path)

class TestFactSheetImages(WithFactSheets, TenantTestCase):

    @test_settings
    def test_create(self):
        pass



class TestFactSheetTemplatesUploadPath(WithFactSheets, TenantTestCase):

    @test_settings
    def test_path(self):
        pass



class TestFactSheetTemplates(WithFactSheets, TenantTestCase):

    @test_settings
    def test_create(self):
        pass
