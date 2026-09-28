from django_tenants.test.cases import TenantTestCase
from django.contrib.contenttypes.models import ContentType

from app_kit.tests.common import test_settings
from app_kit.tests.mixins import (WithMetaApp, WithUser, WithMedia)

from app_kit.features.taxon_profiles.zip_import import (TaxonProfilesZipImporter, ColumnType,
                                                        TAXON_PROFILES_SHEET_NAME,
                                                        TAXON_PROFILE_IMAGES_SHEET_NAME)
from app_kit.tests.common import TESTS_ROOT

from app_kit.features.taxon_profiles.tests.test_models import WithTaxonProfiles

from app_kit.features.taxon_profiles.models import TaxonProfile

from app_kit.features.object_classes.models import ObjectClass
from app_kit.features.object_classes.tests.test_models import WithObjectClasses

from taxonomy.lazy import LazyTaxon
from taxonomy.models import TaxonomyModelRouter

import os
from unittest.mock import patch

TEST_IMAGE_FILENAME = 'Leaf.jpg'

class MockCell:
    
    def __init__(self, value):
        self.value = value

class TestTaxonProfilesZipImporter(WithMedia, WithTaxonProfiles, WithUser, WithMetaApp, TenantTestCase):
    
    def setUp(self):
        super().setUp()
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.zip_contents_path = os.path.join(TESTS_ROOT, 'xlsx_for_testing', 'TaxonProfiles', 'valid')
        self.taxon_profiles = self.get_taxon_profiles()
        
    def get_zip_importer(self):
        return TaxonProfilesZipImporter(self.superuser, self.taxon_profiles, self.zip_contents_path)
    
    @test_settings
    def test_get_column_type(self):
        
        importer = self.get_zip_importer()
        
        empty_cell = MockCell("")
        
        # iterate over ColumnType enum
        for column_type in ColumnType:
            
            column_type = importer.get_column_type([column_type, empty_cell])
            self.assertEqual(column_type, column_type)
        
        
        test_type_1 = MockCell("shOrt_ProFIle")
        column_type = importer.get_column_type([test_type_1, empty_cell])
        self.assertEqual(column_type, ColumnType.SHORT_PROFILE.value)
        
        text_type_cell = MockCell("text type name")
        column_type = importer.get_column_type([empty_cell, text_type_cell])
        self.assertEqual(column_type, ColumnType.TEXT.value)
    
    
    @test_settings
    def test_validate_definition_rows(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate_definition_rows()
        self.assertEqual(importer.errors, [])
    
    @test_settings
    def test_validate_taxa(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        taxon_profiles_sheet = importer.get_sheet_by_name(TAXON_PROFILES_SHEET_NAME)
        
        importer.errors = []
        importer.validate_taxa(taxon_profiles_sheet, start_row=3)
        self.assertEqual(importer.errors, [])
    
    @test_settings
    def test_validate_external_media(self):
        pass
    
    @test_settings
    def test_validate_content(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate_content()
        self.assertEqual(importer.errors, [])

    @test_settings
    def test_validate_taxon_profile_images_sheet_reports_unused_identifier(self):

        importer = self.get_zip_importer()
        importer.load_workbook()

        images_sheet = importer.get_sheet_by_name(TAXON_PROFILE_IMAGES_SHEET_NAME)
        images_sheet['A2'] = 'Unused.jpg'

        importer.errors = []
        importer.validate_taxon_profile_images_sheet()

        expected_errors = [
            '[Taxon profiles.xlsx][Sheet:Taxon Profile Images][cell:A2] Image identifier "Unused.jpg" is not used in the "Taxon Profiles" sheet.'
        ]
        self.assertEqual(importer.errors, expected_errors)
    
    @test_settings
    def test_validate(self):
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate()
        self.assertEqual(importer.errors, [])
    
    
    @test_settings
    def test_import_generic_content(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate()
        
        self.assertEqual(importer.errors, [])
        
        importer.import_generic_content()
        
        # check if the 2 profiles are present with all contents
        quercus_robur_profile = TaxonProfile.objects.get(taxon_profiles=self.taxon_profiles,
                                                         taxon_latname='Quercus robur')
        
        self.assertEqual(quercus_robur_profile.short_profile,'Quercus robur short profile')
        
        qr_seo = quercus_robur_profile.seo_parameters.first()
        self.assertEqual(qr_seo.title, 'Quercus robur title')
        self.assertEqual(qr_seo.meta_description, 'Quercus robur meta_description')
        
        texts = quercus_robur_profile.texts()
        
        self.assertEqual(len(texts), 6)
        for taxon_text in texts:
            
            if taxon_text.taxon_text_type.text_type == 'Interesting facts':
                self.assertEqual(taxon_text.text, 'Quercus robur Interesting facts')
                self.assertEqual(taxon_text.taxon_text_type.category, None)
                self.assertEqual(taxon_text.taxon_text_type.position, 1)
            elif taxon_text.taxon_text_type.text_type == 'Forest protection':
                self.assertEqual(taxon_text.text, 'Quercus robur Forest protection shorttext')
                self.assertEqual(taxon_text.long_text, 'Quercus robur Forest protection longtext')
                self.assertEqual(taxon_text.taxon_text_type.category, None)
                self.assertEqual(taxon_text.taxon_text_type.position, 2)
            elif taxon_text.taxon_text_type.text_type == 'Occurrence':
                self.assertEqual(taxon_text.text, 'Quercus robur Occurrence')
                self.assertEqual(taxon_text.taxon_text_type.category, None)
                self.assertEqual(taxon_text.taxon_text_type.position, 3)
            elif taxon_text.taxon_text_type.text_type == 'Tree as habitat':
                self.assertEqual(taxon_text.text, 'Quercus robur Tree as habitat')
                self.assertEqual(taxon_text.long_text, 'Quercus robur Tree as habitat longtext')
                self.assertEqual(taxon_text.taxon_text_type.category.name, 'Test category')
                self.assertEqual(taxon_text.taxon_text_type.category.position, 1)
                self.assertEqual(taxon_text.taxon_text_type.position, 1)
            elif taxon_text.taxon_text_type.text_type == 'Habitat':
                self.assertEqual(taxon_text.text, 'Quercus robur Habitat')
                self.assertEqual(taxon_text.taxon_text_type.category.name, 'Test category')
                self.assertEqual(taxon_text.taxon_text_type.category.position, 1)
                self.assertEqual(taxon_text.taxon_text_type.position, 2)
            elif taxon_text.taxon_text_type.text_type == 'Economic use':
                self.assertEqual(taxon_text.text, 'Quercus robur Economic use')
                self.assertEqual(taxon_text.taxon_text_type.category.name, 'Test category 2')
                self.assertEqual(taxon_text.taxon_text_type.position, 1)
                self.assertEqual(taxon_text.taxon_text_type.category.position, 2)
                
        self.assertEqual(len(quercus_robur_profile.images()), 1)
        
        # position
        qrp_image = quercus_robur_profile.images()[0]
        # 15th column - 5 (offset) = 10
        self.assertEqual(qrp_image.position, 10)
        
        qr_image = quercus_robur_profile.images()[0]
        self.assertEqual(qr_image.title, 'Leaf title')
        self.assertEqual(qr_image.text, 'Leaf caption')
        self.assertEqual(qr_image.alt_text, 'Leaf alt text')
        
        self.assertEqual([tag.name for tag in quercus_robur_profile.tags.all()], ['tree', 'deciduous'])
        
        # test external media
        external_media = quercus_robur_profile.external_media.all()
        self.assertEqual(len(external_media), 7)
        
        external_image = quercus_robur_profile.external_media.filter(media_type='image').first()
        self.assertIsNotNone(external_image)
        self.assertEqual(external_image.url, 'https://code-for-nature.com/images/Biodiversity-illustration-screen-sm.png')
        self.assertEqual(external_image.title, 'Biodiversity illustration')
        self.assertEqual(external_image.author, 'external media author')
        self.assertEqual(external_image.licence, 'external media licence')
        self.assertEqual(external_image.caption, 'external media caption')
        self.assertEqual(external_image.alt_text, 'external media alt text')
        
        external_youtube = quercus_robur_profile.external_media.filter(media_type='youtube').first()
        self.assertIsNotNone(external_youtube)
        self.assertEqual(external_youtube.url, 'https://www.youtube.com/watch?v=v5ekOVJ5uzU')
        self.assertEqual(external_youtube.title, 'Patchwork Cuttlefish')
        self.assertEqual(external_youtube.author, None)
        self.assertEqual(external_youtube.licence, None)
        self.assertEqual(external_youtube.caption, None)
        self.assertEqual(external_youtube.alt_text, None)
        
        external_mp3 = quercus_robur_profile.external_media.filter(media_type='mp3').first()
        self.assertIsNotNone(external_mp3)
        self.assertEqual(external_mp3.url, 'https://samplelib.com/lib/preview/mp3/sample-3s.mp3')
        self.assertEqual(external_mp3.title, 'sample mp3')
        self.assertEqual(external_mp3.author, None)
        self.assertEqual(external_mp3.licence, None)
        self.assertEqual(external_mp3.caption, None)
        self.assertEqual(external_mp3.alt_text, None)
        
        external_wav = quercus_robur_profile.external_media.filter(media_type='wav').first()
        self.assertIsNotNone(external_wav)
        self.assertEqual(external_wav.url, 'https://samplelib.com/lib/preview/wav/sample-3s.wav')
        self.assertEqual(external_wav.title, 'sample wav')
        self.assertEqual(external_wav.author, None)
        self.assertEqual(external_wav.licence, None)
        self.assertEqual(external_wav.caption, None)
        self.assertEqual(external_wav.alt_text, None)
        
        external_pdf = quercus_robur_profile.external_media.filter(media_type='pdf').first()
        self.assertIsNotNone(external_pdf)
        self.assertEqual(external_pdf.url, 'https://file-examples.com/storage/fe42043ddc68bdea5933232/2017/10/file-sample_150kB.pdf')
        self.assertEqual(external_pdf.title, 'sample pdf')
        self.assertEqual(external_pdf.author, None)
        self.assertEqual(external_pdf.licence, None)
        self.assertEqual(external_pdf.caption, None)
        self.assertEqual(external_pdf.alt_text, None)
        
        external_website = quercus_robur_profile.external_media.filter(media_type='website').first()
        self.assertIsNotNone(external_website)
        self.assertEqual(external_website.url, 'https://code-for-nature.com')
        self.assertEqual(external_website.title, 'sample website')
        self.assertEqual(external_website.author, None)
        self.assertEqual(external_website.licence, None)
        self.assertEqual(external_website.caption, None)
        self.assertEqual(external_website.alt_text, None)
        
        external_file = quercus_robur_profile.external_media.filter(media_type='file').first()
        self.assertIsNotNone(external_file)
        self.assertEqual(external_file.url, 'https://file-examples.com/wp-content/storage/2017/02/file_example_CSV_5000.csv')
        self.assertEqual(external_file.title, 'sample file')
        self.assertEqual(external_file.author, None)
        self.assertEqual(external_file.licence, None)
        self.assertEqual(external_file.caption, None)
        self.assertEqual(external_file.alt_text, None)

        # now test the update
        self.zip_contents_path = os.path.join(TESTS_ROOT, 'xlsx_for_testing', 'TaxonProfiles', 'valid_update')
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate()
        
        self.assertEqual(importer.errors, [])
        
        importer.import_generic_content()
        
        # check if the 2 profiles are present with all contents
        quercus_robur_profile.refresh_from_db()
        self.assertEqual(quercus_robur_profile.short_profile,'Quercus robur short profile updated')
        self.assertEqual(quercus_robur_profile.seo_parameters.first().title, None)
        self.assertEqual(quercus_robur_profile.seo_parameters.first().meta_description, 'Quercus robur meta_description updated')
        texts = quercus_robur_profile.texts()
        self.assertEqual(len(texts), 2)
        for taxon_text in texts:
            if taxon_text.taxon_text_type.text_type == 'Interesting facts':
                self.assertEqual(taxon_text.text, 'Quercus robur Interesting facts updated')
                self.assertEqual(taxon_text.taxon_text_type.category, None)
                self.assertEqual(taxon_text.taxon_text_type.position, 1)
            elif taxon_text.taxon_text_type.text_type == 'Forest protection':
                self.assertEqual(taxon_text.text, 'Quercus robur Forest protection shorttext')
                self.assertEqual(taxon_text.long_text, 'Quercus robur Forest protection longtext')
                self.assertEqual(taxon_text.taxon_text_type.category, None)
                self.assertEqual(taxon_text.taxon_text_type.position, 2)
        
        self.assertEqual(len(quercus_robur_profile.images()), 1)
        qr_image = quercus_robur_profile.images()[0]
        
        # test external media update
        external_media = quercus_robur_profile.external_media.all()
        self.assertEqual(len(external_media), 7)
        
        external_image = quercus_robur_profile.external_media.filter(media_type='image').first()
        external_image.refresh_from_db()
        self.assertIsNotNone(external_image)
        self.assertEqual(external_image.url, 'https://code-for-nature.com/images/Biodiversity-illustration-screen-sm.png')
        self.assertEqual(external_image.title, 'Biodiversity illustration')
        self.assertEqual(external_image.author, 'external media author update')
        self.assertEqual(external_image.licence, None)
        self.assertEqual(external_image.caption, 'external media caption')
        self.assertEqual(external_image.alt_text, 'external media alt text')
        
        external_youtube = quercus_robur_profile.external_media.filter(media_type='youtube').first()
        external_youtube.refresh_from_db()
        self.assertIsNotNone(external_youtube)
        self.assertEqual(external_youtube.url, 'https://www.youtube.com/watch?v=v5ekOVJ5uzU')
        self.assertEqual(external_youtube.title, 'Patchwork Cuttlefish')
        self.assertEqual(external_youtube.author, 'Author 2')
        self.assertEqual(external_youtube.licence, None)
        self.assertEqual(external_youtube.caption, None)
        self.assertEqual(external_youtube.alt_text, None)
        
        external_mp3 = quercus_robur_profile.external_media.filter(media_type='mp3').first()
        external_mp3.refresh_from_db()
        self.assertIsNotNone(external_mp3)
        self.assertEqual(external_mp3.url, 'https://samplelib.com/lib/preview/mp3/sample-3s.mp3')
        self.assertEqual(external_mp3.title, 'sample mp3')
        self.assertEqual(external_mp3.author, None)
        self.assertEqual(external_mp3.licence, None)
        self.assertEqual(external_mp3.caption, None)
        self.assertEqual(external_mp3.alt_text, None)
        
        external_wav = quercus_robur_profile.external_media.filter(media_type='wav').first()
        external_wav.refresh_from_db()
        self.assertIsNotNone(external_wav)
        self.assertEqual(external_wav.url, 'https://samplelib.com/lib/preview/wav/sample-3s.wav')
        self.assertEqual(external_wav.title, 'sample wav')
        self.assertEqual(external_wav.author, None)
        self.assertEqual(external_wav.licence, None)
        self.assertEqual(external_wav.caption, None)
        self.assertEqual(external_wav.alt_text, None)
        
        external_pdf = quercus_robur_profile.external_media.filter(media_type='pdf').first()
        external_pdf.refresh_from_db()
        self.assertIsNotNone(external_pdf)
        self.assertEqual(external_pdf.url, 'https://file-examples.com/storage/fe42043ddc68bdea5933232/2017/10/file-sample_150kB.pdf')
        self.assertEqual(external_pdf.title, 'sample pdf')
        self.assertEqual(external_pdf.author, None)
        self.assertEqual(external_pdf.licence, None)
        self.assertEqual(external_pdf.caption, None)
        self.assertEqual(external_pdf.alt_text, None)
        
        external_website = quercus_robur_profile.external_media.filter(media_type='website').first()
        external_website.refresh_from_db()
        self.assertIsNotNone(external_website)
        self.assertEqual(external_website.url, 'https://code-for-nature.com')
        self.assertEqual(external_website.title, 'sample website')
        self.assertEqual(external_website.author, None)
        self.assertEqual(external_website.licence, None)
        self.assertEqual(external_website.caption, None)
        self.assertEqual(external_website.alt_text, None)
        
        external_file = quercus_robur_profile.external_media.filter(media_type='file').first()
        external_file.refresh_from_db()
        self.assertIsNotNone(external_file)
        self.assertEqual(external_file.url, 'https://file-examples.com/wp-content/storage/2017/02/file_example_CSV_5000.csv')
        self.assertEqual(external_file.title, 'sample file')
        self.assertEqual(external_file.author, None)
        self.assertEqual(external_file.licence, None)
        self.assertEqual(external_file.caption, None)
        self.assertEqual(external_file.alt_text, None)
        
        
        fraxinus_excelsior_profile = TaxonProfile.objects.get(taxon_profiles=self.taxon_profiles,
                                                            taxon_latname='Fraxinus excelsior', morphotype=None)
        self.assertEqual(fraxinus_excelsior_profile.short_profile, None)
        
        fraxinus_excielior_leaf_profile = TaxonProfile.objects.get(taxon_profiles=self.taxon_profiles,
                                                                  taxon_latname='Fraxinus excelsior', morphotype='leaf')
        self.assertEqual(fraxinus_excielior_leaf_profile.short_profile,'Fraxinus excelsior morphotype leaf short profile')
        
        
        
    @test_settings
    def test_import_generic_content_ignores_missing_image_data_when_configured(self):

        importer = TaxonProfilesZipImporter(
            self.superuser,
            self.taxon_profiles,
            self.zip_contents_path,
            ignore_nonexistent_images=True,
        )
        importer.load_workbook()

        importer.errors = []
        importer.validate()

        self.assertEqual(importer.errors, [])

        original_get_image_data = importer.get_image_data_from_images_sheet

        def missing_first_image(image_filename):
            if image_filename == 'Leaf.jpg':
                return None
            return original_get_image_data(image_filename)

        with patch.object(importer, 'get_image_data_from_images_sheet', side_effect=missing_first_image):
            importer.import_generic_content()

        quercus_robur_profile = TaxonProfile.objects.get(
            taxon_profiles=self.taxon_profiles,
            taxon_latname='Quercus robur',
        )

        self.assertEqual(quercus_robur_profile.short_profile, 'Quercus robur short profile')

    @test_settings
    def test_import_generic_content_raises_clear_error_for_missing_image_data(self):

        importer = self.get_zip_importer()
        importer.load_workbook()

        importer.errors = []
        importer.validate()

        self.assertEqual(importer.errors, [])

        original_get_image_data = importer.get_image_data_from_images_sheet

        def missing_first_image(image_filename):
            if image_filename == 'Leaf.jpg':
                return None
            return original_get_image_data(image_filename)

        with patch.object(importer, 'get_image_data_from_images_sheet', side_effect=missing_first_image):
            with self.assertRaisesMessage(ValueError, 'Image file "Leaf.jpg" not found in the "Taxon Profile Images" sheet.'):
                importer.import_generic_content()

    
        
    @test_settings
    def test_partial_import(self):
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate()
        
        self.assertEqual(importer.errors, [])
        
        importer.import_generic_content()
        
        # check if the 2 profiles are present with all contents
        quercus_robur_profile = TaxonProfile.objects.get(taxon_profiles=self.taxon_profiles,
                                                         taxon_latname='Quercus robur')
        
        all_initial_texts = quercus_robur_profile.categorized_texts()
        text_categories = all_initial_texts.keys()
        self.assertEqual(len(text_categories), 3)
        
        self.assertIn('Test category', text_categories)
        self.assertIn('Test category 2', text_categories)
        self.assertIn('uncategorized', text_categories)
        
        test_category_texts = all_initial_texts['Test category']
        self.assertEqual(len(test_category_texts), 2)
        self.assertEqual(test_category_texts[0].text, 'Quercus robur Tree as habitat')
        self.assertEqual(test_category_texts[0].long_text, 'Quercus robur Tree as habitat longtext')
        self.assertEqual(test_category_texts[0].taxon_text_type.text_type, 'Tree as habitat')
        self.assertEqual(test_category_texts[1].text, 'Quercus robur Habitat')
        self.assertEqual(test_category_texts[1].taxon_text_type.text_type, 'Habitat')
        
        test_category_2_texts = all_initial_texts['Test category 2']
        self.assertEqual(len(test_category_2_texts), 1)
        self.assertEqual(test_category_2_texts[0].text, 'Quercus robur Economic use')
        self.assertEqual(test_category_2_texts[0].taxon_text_type.text_type, 'Economic use')
        
        uncategorized_texts = all_initial_texts['uncategorized']
        self.assertEqual(len(uncategorized_texts), 3)
        self.assertEqual(uncategorized_texts[0].text, 'Quercus robur Interesting facts')
        self.assertEqual(uncategorized_texts[0].taxon_text_type.text_type, 'Interesting facts')
        self.assertEqual(uncategorized_texts[1].text, 'Quercus robur Forest protection shorttext')
        self.assertEqual(uncategorized_texts[1].taxon_text_type.text_type, 'Forest protection')
        self.assertEqual(uncategorized_texts[1].long_text, 'Quercus robur Forest protection longtext')
        self.assertEqual(uncategorized_texts[2].text, 'Quercus robur Occurrence')
        self.assertEqual(uncategorized_texts[2].taxon_text_type.text_type, 'Occurrence')
        
        
        self.assertEqual(quercus_robur_profile.short_profile, 'Quercus robur short profile')
        
        self.zip_contents_path = os.path.join(TESTS_ROOT, 'xlsx_for_testing', 'TaxonProfiles', 'valid_partial_update')
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate()
        
        self.assertEqual(importer.errors, [])
        
        importer.import_generic_content()
        
        updated_profile = TaxonProfile.objects.get(taxon_profiles=self.taxon_profiles,
                                                   taxon_latname='Quercus robur')
        all_updated_texts = updated_profile.categorized_texts()
        text_categories = all_updated_texts.keys()
        self.assertEqual(len(text_categories), 3)
        
        self.assertIn('Test category', text_categories)
        self.assertIn('Test category 2', text_categories)
        self.assertIn('uncategorized', text_categories)
        
        test_category_texts = all_updated_texts['Test category']
        self.assertEqual(len(test_category_texts), 2)
        self.assertEqual(test_category_texts[0].text, 'Quercus robur Tree as habitat')
        self.assertEqual(test_category_texts[0].long_text, 'Quercus robur Tree as habitat longtext')
        self.assertEqual(test_category_texts[0].taxon_text_type.text_type, 'Tree as habitat')
        self.assertEqual(test_category_texts[1].text, 'Quercus robur Habitat')
        self.assertEqual(test_category_texts[1].taxon_text_type.text_type, 'Habitat')
        
        test_category_2_texts = all_updated_texts['Test category 2']
        self.assertEqual(len(test_category_2_texts), 1)
        self.assertEqual(test_category_2_texts[0].text, 'Quercus robur Economic use')
        self.assertEqual(test_category_2_texts[0].taxon_text_type.text_type, 'Economic use')
        
        uncategorized_texts = all_updated_texts['uncategorized']
        self.assertEqual(len(uncategorized_texts), 3)
        self.assertEqual(uncategorized_texts[0].text, 'Quercus robur Interesting facts updated')
        self.assertEqual(uncategorized_texts[0].taxon_text_type.text_type, 'Interesting facts')
        self.assertEqual(uncategorized_texts[1].text, 'Quercus robur Forest protection shorttext')
        self.assertEqual(uncategorized_texts[1].taxon_text_type.text_type, 'Forest protection')
        self.assertEqual(uncategorized_texts[1].long_text, 'Quercus robur Forest protection longtext')
        self.assertEqual(uncategorized_texts[2].text, 'Quercus robur Occurrence')
        self.assertEqual(uncategorized_texts[2].taxon_text_type.text_type, 'Occurrence')
        
        self.assertEqual(updated_profile.short_profile, 'Quercus robur short profile')



class TestTaxonProfilesZipImporterInvalidCellContentType(WithTaxonProfiles, WithUser, WithMetaApp, TenantTestCase):
    def setUp(self):
        super().setUp()
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.zip_contents_path = os.path.join(TESTS_ROOT, 'xlsx_for_testing', 'TaxonProfiles', 'invalid_content_type')
        self.taxon_profiles = self.get_taxon_profiles()
        
    def get_zip_importer(self):
        return TaxonProfilesZipImporter(self.superuser, self.taxon_profiles, self.zip_contents_path)
    
    
    @test_settings
    def test_validate_cell_value_content_types(self):
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate_cell_value_content_types()
        expected_errors = [
            '[Taxon profiles.xlsx][Sheet:Taxon profiles][cell:F4] Invalid cell content: =SUM(0). Formulas are not allowed.'
        ]

        self.assertEqual(importer.errors, expected_errors)

class TestTaxonProfilesZipImporterInvalidData(WithTaxonProfiles, WithUser, WithMetaApp, TenantTestCase):
    
    def setUp(self):
        super().setUp()
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.zip_contents_path = os.path.join(TESTS_ROOT, 'xlsx_for_testing', 'TaxonProfiles', 'invalid')
        self.taxon_profiles = self.get_taxon_profiles()
        
    def get_zip_importer(self):
        return TaxonProfilesZipImporter(self.superuser, self.taxon_profiles, self.zip_contents_path)
    
    @test_settings
    def test_validate_definition_rows(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate_definition_rows()
        expected_errors = [
            '[Taxon profiles.xlsx][Sheet:Taxon Profiles][cell:A1] Cell content has to be "Scientific name", not Scientific Names',
            '[Taxon profiles.xlsx][Sheet:Taxon Profiles][cell:C1] Cell content has to be "Taxonomic source", not None',
            '[Taxon profiles.xlsx][Sheet:Taxon Profiles][cell:O3] Columns of type image are not allowed to have a value in row 2',
            '[Taxon profiles.xlsx][Sheet:Taxon Profiles][cell:R3] Cell content has to be one of title, meta_description. Found error instead',
            '[Taxon profiles.xlsx][Sheet:Taxon Profiles][cell:U1] Cell content has to be one of text, shorttext, longtext, short_profile, image, tags, external_media, seo. Found something wrong instead']
        self.assertEqual(importer.errors, expected_errors)
    
    @test_settings
    def test_validate_taxa(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        taxon_profiles_sheet = importer.get_sheet_by_name(TAXON_PROFILES_SHEET_NAME)
        
        importer.errors = []
        importer.validate_taxa(taxon_profiles_sheet, start_row=3)
        
        expected_errors = [
            '[Taxon profiles.xlsx][Sheet:Taxon Profiles][row:4] Multiple results found for Viola in taxonomy.sources.col. You have to specify an author.',
            '[Taxon profiles.xlsx][Sheet:Taxon Profiles][row:5] Nonexistant taxon not found in taxonomy.sources.col'
        ]
        self.assertEqual(importer.errors, expected_errors)
    
    @test_settings
    def test_validate_external_media(self):
        pass
    
    @test_settings
    def test_validate_content(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate_content()
        
        expected_errors = [
            '[Taxon profiles.xlsx][Sheet:Taxon profiles][cell:I6] Image file "MissingImage.png" not found in the "Taxon Profile Images" sheet.',
        ]
        self.assertEqual(importer.errors, expected_errors)


class TestObjectClassZipImport(WithMedia, WithObjectClasses, WithTaxonProfiles, WithUser, WithMetaApp, TenantTestCase):
    """Tests for validate_object_class, validate_object_classes, and object_class import."""

    def setUp(self):
        super().setUp()
        self.superuser = self.create_superuser()
        self.zip_contents_path = os.path.join(TESTS_ROOT, 'xlsx_for_testing', 'TaxonProfiles', 'valid')
        self.taxon_profiles = self.get_taxon_profiles()

        models = TaxonomyModelRouter('taxonomy.sources.col')
        quercus_db = models.TaxonTreeModel.objects.get(taxon_latname='Quercus')
        self.quercus_lazy = LazyTaxon(instance=quercus_db)
        quercus_robur_db = models.TaxonTreeModel.objects.get(taxon_latname='Quercus robur')
        self.quercus_robur_lazy = LazyTaxon(instance=quercus_robur_db)
        lacerta_db = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        self.lacerta_lazy = LazyTaxon(instance=lacerta_db)

        # create_object_class derives scientific_name as name.lower().replace(' ', '_')
        # so self.oak_class.scientific_name == 'bark'
        self.oak_class = self.create_object_class('Bark')
        self.create_object_class_taxon(self.oak_class, self.quercus_lazy)

    def get_zip_importer(self):
        importer = TaxonProfilesZipImporter(self.superuser, self.taxon_profiles, self.zip_contents_path)
        importer.errors = []
        return importer

    # ------------------------------------------------------------------ #
    # validate_object_class – unit tests                                   #
    # ------------------------------------------------------------------ #

    @test_settings
    def test_validate_object_class_found_by_scientific_name(self):
        importer = self.get_zip_importer()
        importer.validate_object_class(
            'bark', self.quercus_robur_lazy, 'test.xlsx', TAXON_PROFILES_SHEET_NAME, 0)
        self.assertEqual(importer.errors, [])

    @test_settings
    def test_validate_object_class_found_by_name(self):
        importer = self.get_zip_importer()
        importer.validate_object_class(
            'Bark', self.quercus_robur_lazy, 'test.xlsx', TAXON_PROFILES_SHEET_NAME, 0)
        self.assertEqual(importer.errors, [])

    @test_settings
    def test_validate_object_class_duplicate_name(self):
        # Two classes share the same name; the lookup value matches neither scientific_name.
        ObjectClass.objects.create(
            object_classes=self.object_classes,
            name='Ambiguous Name',
            scientific_name='ambiguous_1',
        )
        ObjectClass.objects.create(
            object_classes=self.object_classes,
            name='Ambiguous Name',
            scientific_name='ambiguous_2',
        )
        importer = self.get_zip_importer()
        importer.validate_object_class(
            'Ambiguous Name', self.quercus_robur_lazy, 'test.xlsx', TAXON_PROFILES_SHEET_NAME, 0)
        self.assertEqual(len(importer.errors), 1)
        self.assertIn('not unique', importer.errors[0])

    @test_settings
    def test_validate_object_class_not_found(self):
        importer = self.get_zip_importer()
        importer.validate_object_class(
            'nonexistent_class', self.quercus_robur_lazy, 'test.xlsx', TAXON_PROFILES_SHEET_NAME, 0)
        self.assertEqual(len(importer.errors), 1)
        self.assertIn('not found', importer.errors[0])

    @test_settings
    def test_validate_object_class_incompatible_taxon(self):
        importer = self.get_zip_importer()
        importer.validate_object_class(
            'bark', self.lacerta_lazy, 'test.xlsx', TAXON_PROFILES_SHEET_NAME, 0)
        self.assertEqual(len(importer.errors), 1)
        self.assertIn('not compatible', importer.errors[0])

    # ------------------------------------------------------------------ #
    # validate_object_classes – sheet-level tests                          #
    # ------------------------------------------------------------------ #

    @test_settings
    def test_validate_object_classes_no_data(self):
        importer = self.get_zip_importer()
        importer.load_workbook()
        sheet = importer.get_sheet_by_name(TAXON_PROFILES_SHEET_NAME)
        importer.validate_object_classes(sheet)
        self.assertEqual(importer.errors, [])

    @test_settings
    def test_validate_object_classes_valid_value(self):
        importer = TaxonProfilesZipImporter(
            self.superuser, self.taxon_profiles,
            os.path.join(TESTS_ROOT, 'xlsx_for_testing', 'TaxonProfiles', 'valid_with_object_class'))
        importer.errors = []
        importer.load_workbook()
        sheet = importer.get_sheet_by_name(TAXON_PROFILES_SHEET_NAME)
        importer.validate_object_classes(sheet)
        self.assertEqual(importer.errors, [])

    @test_settings
    def test_validate_object_classes_invalid_value(self):
        importer = TaxonProfilesZipImporter(
            self.superuser, self.taxon_profiles,
            os.path.join(TESTS_ROOT, 'xlsx_for_testing', 'TaxonProfiles', 'valid_with_invalid_object_class'))
        importer.errors = []
        importer.load_workbook()
        sheet = importer.get_sheet_by_name(TAXON_PROFILES_SHEET_NAME)
        importer.validate_object_classes(sheet)
        self.assertEqual(len(importer.errors), 1)
        self.assertIn('not found', importer.errors[0])

    # ------------------------------------------------------------------ #
    # import_generic_content – object_class persistence                    #
    # ------------------------------------------------------------------ #

    @test_settings
    def test_import_assigns_object_class(self):
        path = os.path.join(TESTS_ROOT, 'xlsx_for_testing', 'TaxonProfiles', 'valid_with_object_class')
        importer = TaxonProfilesZipImporter(self.superuser, self.taxon_profiles, path)
        importer.errors = []
        importer.validate()
        self.assertEqual(importer.errors, [])
        importer.import_generic_content()

        qr_base = TaxonProfile.objects.filter(
            taxon_profiles=self.taxon_profiles,
            taxon_latname='Quercus robur',
            morphotype__isnull=True,
            object_class__isnull=True,
        ).first()
        self.assertIsNotNone(qr_base, 'Quercus robur (no morphotype, no object class) not created')

        qr_morphotype = TaxonProfile.objects.filter(
            taxon_profiles=self.taxon_profiles,
            taxon_latname='Quercus robur',
            morphotype='sprout',
            object_class__isnull=True,
        ).first()
        self.assertIsNotNone(qr_morphotype, 'Quercus robur morphotype=sprout not created')

        qr_object_class = TaxonProfile.objects.filter(
            taxon_profiles=self.taxon_profiles,
            taxon_latname='Quercus robur',
            morphotype__isnull=True,
            object_class=self.oak_class,
        ).first()
        self.assertIsNotNone(qr_object_class, 'Quercus robur object_class=Bark not created')

        qr_both = TaxonProfile.objects.filter(
            taxon_profiles=self.taxon_profiles,
            taxon_latname='Quercus robur',
            morphotype='sprout',
            object_class=self.oak_class,
        ).first()
        self.assertIsNotNone(qr_both, 'Quercus robur morphotype=sprout + object_class=Bark not created')

        total = TaxonProfile.objects.filter(
            taxon_profiles=self.taxon_profiles,
            taxon_latname='Quercus robur',
        ).count()
        self.assertEqual(total, 4)

    @test_settings
    def test_import_does_not_duplicate_profile_on_reimport(self):
        path = os.path.join(TESTS_ROOT, 'xlsx_for_testing', 'TaxonProfiles', 'valid_with_object_class')
        # First import creates all 4 profiles; second import must find them rather than duplicate.
        for _ in range(2):
            importer = TaxonProfilesZipImporter(self.superuser, self.taxon_profiles, path)
            importer.errors = []
            importer.validate()
            self.assertEqual(importer.errors, [])
            importer.import_generic_content()

        total = TaxonProfile.objects.filter(
            taxon_profiles=self.taxon_profiles,
            taxon_latname='Quercus robur',
        ).count()
        self.assertEqual(total, 4)