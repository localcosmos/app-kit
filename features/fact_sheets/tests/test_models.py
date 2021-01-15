##############################################################################################################
#
# TESTS FOR MODELS
#
##############################################################################################################

from django.conf import settings

from django_tenants.test.cases import TenantTestCase

from app_kit.tests.common import (test_settings, TEST_MEDIA_ROOT, TEST_IMAGE_PATH, TEST_TEMPLATE_PATH)
from app_kit.tests.mixins import WithMetaApp, WithUser
from django.core.files.uploadedfile import SimpleUploadedFile

from app_kit.features.fact_sheets.models import (FactSheet, FactSheetImages, FactSheets,
                factsheet_images_upload_path, factsheet_templates_upload_path, FactSheetTemplates)


from app_kit.features.fact_sheets.tests.common import WithFactSheets


import os, shutil


class TestFactSheet(WithFactSheets, WithMetaApp, TenantTestCase):

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
            fact_sheet = fact_sheet,
            microcontent_type = 'test_image',
            image = self.get_image(filename)
        )

        fact_sheet_image.save()

        path = factsheet_images_upload_path(fact_sheet_image, filename)

        expected_path = 'fact_sheets/content/{0}/{1}/images/test_image/{2}'.format(self.fact_sheets.id,
                                                                        fact_sheet.id, filename)
        self.assertEqual(path, expected_path)



class TestFactSheetImages(WithFactSheets, TenantTestCase):

    @test_settings
    def test_create(self):

        fact_sheet = self.create_fact_sheet()

        filename = 'test.jpg'

        fact_sheet_image = FactSheetImages(
            fact_sheet = fact_sheet,
            microcontent_type = 'test_image',
            image = self.get_image(filename)
        )

        fact_sheet_image.save()

        fact_sheet_image.refresh_from_db()

        self.assertEqual(fact_sheet_image.microcontent_type, 'test_image')
        self.assertEqual(fact_sheet_image.fact_sheet, fact_sheet)



class TestFactSheetTemplates(WithFactSheets, WithUser, TenantTestCase):

    @test_settings
    def test_create_and_path(self):

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

