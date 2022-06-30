from django.core.files.uploadedfile import SimpleUploadedFile

from django.contrib.contenttypes.models import ContentType

from app_kit.tests.common import (test_settings, TEST_MEDIA_ROOT, TEST_IMAGE_PATH, TEST_TEMPLATE_PATH)
from app_kit.features.fact_sheets.models import FactSheet, FactSheets

from app_kit.appbuilder import AppPreviewBuilder

import os, shutil

class WithFactSheets:

    template_name = 'test.html'
    title = 'Neobiota'
    navigation_link_name = 'Neobiota link'

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

    def build_preview_app(self):
        # create the preview on disk
        preview_builder = AppPreviewBuilder(self.meta_app)
        preview_builder.build()

    
    def tearDown(self):
        super().tearDown()
        self.clean_media()
        

    def setUp(self):
        self.clean_media()
        super().setUp()
        self.fact_sheets = self.create_fact_sheets()

        self.content_type = ContentType.objects.get_for_model(FactSheets)
        self.generic_content = self.fact_sheets

