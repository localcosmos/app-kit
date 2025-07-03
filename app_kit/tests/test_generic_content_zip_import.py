from django_tenants.test.cases import TenantTestCase
from django.contrib.contenttypes.models import ContentType

from app_kit.tests.common import test_settings
from app_kit.tests.mixins import (WithMetaApp, WithUser)

from app_kit.generic_content_zip_import import GenericContentZipImporter
from app_kit.tests.common import TESTS_ROOT

from app_kit.models import ContentImage

from content_licencing.models import ContentLicenceRegistry

import os

TEST_IMAGE_FILENAME = 'Leaf.jpg'

class MockGenericcontent():
    name = "Generic Content"

class TestGenericContentZipImporter(WithUser, WithMetaApp, TenantTestCase):
    
    def setUp(self):
        super().setUp()
        self.generic_content = MockGenericcontent()
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.zip_contents_path = os.path.join(TESTS_ROOT, 'xlsx_for_testing', 'valid')
    
    def get_zip_importer(self):
        return GenericContentZipImporter(self.superuser, self.generic_content, self.zip_contents_path)
    
    @test_settings
    def test_init(self):
        importer = self.get_zip_importer()
        self.assertIsInstance(importer, GenericContentZipImporter)
        self.assertEqual(importer.generic_content, self.generic_content)
        self.assertEqual(importer.user, self.superuser)
        self.assertEqual(importer.zip_contents_path, self.zip_contents_path)
        self.assertEqual(importer.image_folder, os.path.join(self.zip_contents_path, 'images'))
        
        
    @test_settings
    def test_get_stripped_cell_value(self):
        
        importer = self.get_zip_importer()
        
        cell_value = '  Hello World  '
        stripped_value = importer.get_stripped_cell_value(cell_value)
        
        self.assertEqual(stripped_value, 'Hello World')
        
        cell_value = None
        stripped_value = importer.get_stripped_cell_value(cell_value)
        
        self.assertEqual(stripped_value, None)
        
    @test_settings
    def test_get_stripped_cell_value_lowercase(self):
        
        importer = self.get_zip_importer()
        
        cell_value = '  Hello World  '
        stripped_value = importer.get_stripped_cell_value_lowercase(cell_value)
        
        self.assertEqual(stripped_value, 'hello world')
        
        cell_value = None
        stripped_value = importer.get_stripped_cell_value_lowercase(cell_value)
        
        self.assertEqual(stripped_value, None)  
    
    @test_settings
    def test_get_filepath(self):
        
        importer = self.get_zip_importer()
        
        filepath = importer.get_filepath(self.generic_content.name, ['xlsx'])
        
        self.assertEqual(filepath, os.path.join(self.zip_contents_path, 'Generic Content.xlsx'))
        
        filepath = importer.get_filepath('Generic Content wrong name.xlsx', ['xlsx'])
        
        self.assertEqual(filepath, None)
    
    @test_settings
    def test_check_file_presence(self):
        
        importer = self.get_zip_importer()
        importer.errors = []
        
        importer.check_file_presence()
        self.assertEqual(importer.errors, [])
        
        self.generic_content.name = 'Generic Content wrong name'
        importer = self.get_zip_importer()
        importer.errors = []
        importer.check_file_presence()
        self.assertEqual(importer.errors, ['Missing spreadsheet file. Expected one of these files: Generic Content wrong name.xlsx'])
    
    @test_settings
    def test_load_workbook(self):
        
        importer = self.get_zip_importer()
        
        importer.load_workbook()
        self.assertIsNotNone(importer.workbook)
        
        self.assertEqual(importer.workbook_filename, 'Generic Content.xlsx')
        
        self.generic_content.name = 'Generic Content wrong name'
        with self.assertRaises(ValueError):
            importer.load_workbook()
    
    @test_settings
    def test_get_sheet_by_name(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
         
        sheet = importer.get_sheet_by_name(self.generic_content.name)
        self.assertIsNotNone(sheet)
        self.assertEqual(sheet.title, 'Generic Content')
        sheet = importer.get_sheet_by_name('Images')
        self.assertIsNotNone(sheet)
        self.assertEqual(sheet.title, 'Images')
        sheet = importer.get_sheet_by_name('Nonexistent Sheet')
        self.assertIsNone(sheet)
    
    @test_settings
    def test_get_image_data_from_images_sheet(self):
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        image_filename = TEST_IMAGE_FILENAME
        
        image_data = importer.get_image_data_from_images_sheet(image_filename)
        
        expected_image_data = {
            'alt_text': 'A green lizard climbing a rock',
            'author': 'Art Vandeley',
            'caption': 'A hungry lizard waiting for the sun',
            'identifier': 'Leaf.jpg',
            'licence': 'CC BY-SA',
            'licence_version': '4.0',
            'link_to_source_image': 'https://imageworld.com/lacerta-agilis.jpg',
            'primary_image': None,
            'title': 'Lizard'
        }
        
        self.assertEqual(image_data, expected_image_data)
        
        
    @test_settings
    def test_validate_listing_in_images_sheet(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate_listing_in_images_sheet(TEST_IMAGE_FILENAME, 'A', 2)
        self.assertEqual(importer.errors, [])
    
    @test_settings
    def test_validate_image_data(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        importer.errors = []
        
        image_filename = TEST_IMAGE_FILENAME
        
        image_data = importer.get_image_data_from_images_sheet(image_filename)
        
        importer.validate_image_data(image_data, importer.images_sheet_name, 2)
        
        self.assertEqual(importer.errors, [])
    
    @test_settings
    def test_validate_images_sheet(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        importer.errors = []
        
        importer.validate_images_sheet()
        self.assertEqual(importer.errors, [])
        
    @test_settings
    def test_validate_square_image(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        importer.errors = []
        
        image_filepath = os.path.join(self.zip_contents_path, 'images', TEST_IMAGE_FILENAME)
        
        importer.validate_square_image(image_filepath)
        self.assertEqual(importer.errors, [])
        
    @test_settings
    def test_validate_taxon(self):
        
        importer = self.get_zip_importer()
        
        taxon_latname = 'Quercus robur'
        taxon_author = None
        taxon_source = 'taxonomy.sources.col'
        workbook_filename = 'Generic Content.xlsx'
        sheet_name = 'Generic Content'
        row_number = 2
        taxon_latname_column_index = 1
        taxon_source_column_index = 2
        
        importer.errors = []
        
        importer.validate_taxon(taxon_latname, taxon_author, taxon_source, workbook_filename, sheet_name,
                       row_number, taxon_latname_column_index, taxon_source_column_index)
        
        self.assertEqual(importer.errors, [])
    
    @test_settings
    def test_add_cell_error(self):
        importer = self.get_zip_importer()
        importer.errors = []
        #filename, sheet_name, column, row, message
        importer.add_cell_error(self.generic_content.name, 'Sheet1', 'A', 2, 'Error message')
        self.assertEqual(importer.errors, ['[Generic Content][Sheet:Sheet1][cell:A3] Error message'])
        importer.add_cell_error(self.generic_content.name, 'Sheet2', 2, 4, 'Another error message')
        self.assertEqual(importer.errors, [
            '[Generic Content][Sheet:Sheet1][cell:A3] Error message',
            '[Generic Content][Sheet:Sheet2][cell:B5] Another error message',
        ])
    
    @test_settings
    def test_add_row_error(self):
        
        importer = self.get_zip_importer()
        importer.errors = []
        
        importer.add_row_error(self.generic_content.name, 'Sheet1', 2, 'Error message')
        self.assertEqual(importer.errors, ['[Generic Content][Sheet:Sheet1][row:3] Error message'])
        importer.add_row_error(self.generic_content.name, 'Sheet2', 4, 'Another error message')
        self.assertEqual(importer.errors, [
            '[Generic Content][Sheet:Sheet1][row:3] Error message',
            '[Generic Content][Sheet:Sheet2][row:5] Another error message',
        ])
        
    @test_settings
    def test_get_crop_parameters(self):
        
        importer = self.get_zip_importer()
        image_filepath = os.path.join(self.zip_contents_path, 'images', TEST_IMAGE_FILENAME)
        
        crop_parameters = importer.get_crop_parameters(image_filepath)
        self.assertEqual(crop_parameters, {
            'x': 0,
            'y': 0,
            'width': 400,
            'height': 400,
            'rotate': 0,
        })
    
    @test_settings
    def test_save_content_image(self):
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        content_object = self.meta_app
        image_filepath = os.path.join(self.zip_contents_path, 'images', TEST_IMAGE_FILENAME)
        image_data = importer.get_image_data_from_images_sheet(TEST_IMAGE_FILENAME)
        
        content_type = ContentType.objects.get_for_model(self.meta_app)
        content_image_qry = ContentImage.objects.filter(
            content_type=content_type,
            object_id=self.meta_app.id,
        )
        
        self.assertFalse(content_image_qry.exists())
        
        importer.save_content_image(image_filepath, content_object, image_data)
        
        self.assertTrue(content_image_qry.exists())
        
        content_image = content_image_qry.first()
        
        expected_image_attrs = {
            'alt_text': 'A green lizard climbing a rock',
            'text': 'A hungry lizard waiting for the sun',
            'is_primary': False,
            'title': 'Lizard',
        }
        
        for attr, expected_value in expected_image_attrs.items():
            self.assertEqual(getattr(content_image, attr), expected_value)
            
        
        licence = content_image.image_store.licences.first()
        self.assertEqual(licence.licence, 'CC BY-SA')
        self.assertEqual(licence.licence_version, '4.0')
        self.assertEqual(licence.source_link, 'https://imageworld.com/lacerta-agilis.jpg')
        self.assertEqual(licence.creator_name, 'Art Vandeley')
        
        # re-save the image with different data
        new_image_data = image_data.copy()
        new_image_data.update({
            'alt_text': 'A new alt text',
            'author': 'New Author',
            'caption': 'A new caption',
            'licence': 'CC BY-NC',
            'primary_image': True,
        })
        
        importer.save_content_image(image_filepath, content_object, new_image_data)
        
        self.assertEqual(content_image_qry.count(), 1)
        content_image.refresh_from_db()
        licence.refresh_from_db()
        self.assertEqual(content_image.image_store.licences.count(), 1)
        self.assertEqual(licence.licence, 'CC BY-NC')
        self.assertEqual(licence.licence_version, '4.0')
        self.assertEqual(licence.source_link, 'https://imageworld.com/lacerta-agilis.jpg')
        self.assertEqual(licence.creator_name, 'Art Vandeley')
        self.assertEqual(content_image.alt_text, 'A new alt text')
        self.assertEqual(content_image.text, 'A new caption')
        self.assertEqual(content_image.title, 'Lizard')
        self.assertEqual(content_image.is_primary, True)
        self.assertEqual(content_image.content_type, content_type)
        self.assertEqual(content_image.object_id, content_object.id)
    
    @test_settings
    def test_register_content_licence(self):
        
        importer = self.get_zip_importer()
        
        image_licence = image_licence = {
           'short_name' : 'CC BY-SA',
           'version' : '4.0',
           'creator_name' : 'Art Vandeley',
           'source_link' : 'https://imageworld.com/lacerta-agilis.jpg',
        }
        
        importer.register_content_licence(self.meta_app, 'name', image_licence)
        
        registry_entry = ContentLicenceRegistry.objects.get(
            content_type=ContentType.objects.get_for_model(self.meta_app),
            object_id=self.meta_app.id,
        )
        
        self.assertEqual(registry_entry.licence, 'CC BY-SA')
        self.assertEqual(registry_entry.licence_version, '4.0')
        self.assertEqual(registry_entry.source_link, 'https://imageworld.com/lacerta-agilis.jpg')
        self.assertEqual(registry_entry.creator_name, 'Art Vandeley')
        self.assertEqual(registry_entry.content, self.meta_app)
    
    @test_settings
    def test_get_lazy_taxon(self):
        
        importer = self.get_zip_importer()
        
        taxon_latname = 'Quercus robur'
        taxon_author = None
        taxon_source = 'taxonomy.sources.col'
        
        lazy_taxon = importer.get_lazy_taxon(taxon_latname, taxon_source, taxon_author)
        self.assertIsNotNone(lazy_taxon)
        self.assertEqual(lazy_taxon.taxon_latname, taxon_latname)
        self.assertEqual(lazy_taxon.taxon_author, 'L.')
        self.assertEqual(lazy_taxon.taxon_source, taxon_source)

    @test_settings
    def test_get_lazy_taxon_with_tolerance(self):
        importer = self.get_zip_importer()
        # Assume the DB contains "Quercus robur" with author "L."
        taxon_latname = 'Quercus robur'
        taxon_source = 'taxonomy.sources.col'

        # Exact match
        lazy_taxon = importer.get_lazy_taxon_with_tolerance(taxon_latname, taxon_source, 'L.')
        self.assertIsNotNone(lazy_taxon)
        self.assertEqual(lazy_taxon.taxon_latname, taxon_latname)
        self.assertEqual(lazy_taxon.taxon_author, 'L.')
        self.assertEqual(lazy_taxon.taxon_source, taxon_source)

        # Tolerate one missing space (e.g. "L." vs "L .")
        lazy_taxon = importer.get_lazy_taxon_with_tolerance(taxon_latname, taxon_source, 'L .')
        self.assertIsNotNone(lazy_taxon)
        self.assertEqual(lazy_taxon.taxon_latname, taxon_latname)
        self.assertEqual(lazy_taxon.taxon_author, 'L.')
        self.assertEqual(lazy_taxon.taxon_source, taxon_source)

        # Should raise if no match
        with self.assertRaises(ValueError):
            importer.get_lazy_taxon_with_tolerance(taxon_latname, taxon_source, 'L  .')
    
    @test_settings
    def test_get_taxa_with_taxon_author_tolerance(self):
        importer = self.get_zip_importer()
        taxon_latname = 'Quercus robur'
        taxon_source = 'taxonomy.sources.col'

        # Exact match
        matches = importer.get_taxa_with_taxon_author_tolerance(taxon_source, taxon_latname, 'L.')
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].taxon_latname, taxon_latname)
        self.assertEqual(matches[0].taxon_author, 'L.')

        # Tolerate one missing space
        matches = importer.get_taxa_with_taxon_author_tolerance(taxon_source, taxon_latname, 'L .')
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].taxon_author, 'L.')

        # Tolerate one extra space (should not match if more than one space)
        matches = importer.get_taxa_with_taxon_author_tolerance(taxon_source, taxon_latname, 'L  .')
        self.assertEqual(len(matches), 0)

        # No match for wrong author
        matches = importer.get_taxa_with_taxon_author_tolerance(taxon_source, taxon_latname, 'Smith')
        self.assertEqual(len(matches), 0)
        
        # real world test
        # algaebase entry is : Desmarestia viridis (O.F.Müller) J.V.Lamouroux 1813
        taxon_latname = 'Desmarestia viridis'
        taxon_author= '(O.F.Müller) J.V. Lamouroux 1813'
        taxon_source = 'taxonomy.sources.algaebase'
        matches = importer.get_taxa_with_taxon_author_tolerance(taxon_source, taxon_latname, taxon_author)
        #print(matches)
        self.assertEqual(len(matches), 1)
    
# try to cover all possible errors
class TestGenericContentZipImporterInvalidData(WithUser, WithMetaApp, TenantTestCase):
    
    def setUp(self):
        super().setUp()
        self.generic_content = MockGenericcontent()
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.zip_contents_path = os.path.join(TESTS_ROOT, 'xlsx_for_testing', 'invalid')
    
    def get_zip_importer(self):
        return GenericContentZipImporter(self.superuser, self.generic_content, self.zip_contents_path)
    
    @test_settings
    def test_validate_image_data(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        importer.errors = []
        
        image_filename = TEST_IMAGE_FILENAME
        
        image_data = importer.get_image_data_from_images_sheet(image_filename)
        
        importer.validate_image_data(image_data, importer.images_sheet_name, 2)
        
        expected_errors = [
            'Image height is too large: Leaf.jpg. Maximum allowed height is 2000',
            'Image width is too large: Leaf.jpg. Maximum allowed width is 2000',
        ]
        
        self.assertEqual(importer.errors, expected_errors)
        
        importer.errors = []
        
        new_image_data = image_data.copy()
        new_image_data.update({
            'identifier': 'unlisted.jpg',
        })
        
        importer.validate_image_data(new_image_data, importer.images_sheet_name, 2)
        expected_errors = [
            '[Generic Content.xlsx][Sheet:Images][cell:A3] Image file not found: unlisted.jpg. Image file should be in the images folder.'
        ]
        
        self.assertEqual(importer.errors, expected_errors)
        
        ignoring_importer = GenericContentZipImporter(self.superuser, self.generic_content, self.zip_contents_path, ignore_nonexistent_images=True)
        ignoring_importer.load_workbook()
        ignoring_importer.errors = []
        ignoring_importer.validate_image_data(new_image_data, importer.images_sheet_name, 2)
        self.assertEqual(ignoring_importer.errors, [])
    
    @test_settings
    def test_validate_images_sheet(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        importer.errors = []
        
        importer.validate_images_sheet()
        
        expected_errors = [
            'Image height is too large: Leaf.jpg. Maximum allowed height is 2000',
            'Image width is too large: Leaf.jpg. Maximum allowed width is 2000',
            '[Generic Content.xlsx][Sheet:Images][cell:B3] Cell content has to be an author, found empty cell instead',
            '[Generic Content.xlsx][Sheet:Images][cell:A3] Image file not found: MissingAuthor.jpg. Image file should be in the images folder.',
            '[Generic Content.xlsx][Sheet:Images][cell:C4] Invalid licence: None. Licence choices are: All Rights Reserved, PDM, CC0, CC BY, CC BY-SA, CC BY-ND, CC BY-NC, CC BY-NC-SA, CC BY-NC-ND',
            '[Generic Content.xlsx][Sheet:Images][cell:A4] Image file not found: MissingLicence.jpg. Image file should be in the images folder.',
            '[Generic Content.xlsx][Sheet:Images][cell:D5] Invalid licence version: None. Licence version choices are: 1.0, 2.0, 2.5, 3.0, 4.0',
            '[Generic Content.xlsx][Sheet:Images][cell:A5] Image file not found: MissingVersion.jpg. Image file should be in the images folder.',
            '[Generic Content.xlsx][Sheet:Images][cell:B6] Cell content has to be an author, found empty cell instead',
            '[Generic Content.xlsx][Sheet:Images][cell:C6] Invalid licence: None. Licence choices are: All Rights Reserved, PDM, CC0, CC BY, CC BY-SA, CC BY-ND, CC BY-NC, CC BY-NC-SA, CC BY-NC-ND',
            '[Generic Content.xlsx][Sheet:Images][cell:A6] Image file not found: AllMissing.jpg. Image file should be in the images folder.',
            '[Generic Content.xlsx][Sheet:Images][cell:A7] Invalid image format: .wrong. Valid formats are: .jpg, .jpeg, .png, .webp, .gif',
            '[Generic Content.xlsx][Sheet:Images][cell:A7] Image file not found: Leaf2.wrong. Image file should be in the images folder.'
        ]

        self.assertEqual(importer.errors, expected_errors)
        
    @test_settings
    def test_validate_square_image(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        importer.errors = []
        
        image_filepath = os.path.join(self.zip_contents_path, 'images', TEST_IMAGE_FILENAME)
        
        importer.validate_square_image(image_filepath)
        
        expected_errors = [
            'Image height is too large: Leaf.jpg. Maximum allowed height is 2000',
            'Image width is too large: Leaf.jpg. Maximum allowed width is 2000',
        ]
        self.assertEqual(importer.errors, expected_errors)
        
    @test_settings
    def test_validate_taxon(self):
        
        importer = self.get_zip_importer()
        
        taxon_latname = 'Quercus robur'
        taxon_author = None
        taxon_source = None
        workbook_filename = 'Generic Content.xlsx'
        sheet_name = 'Generic Content'
        row_number = 2
        taxon_latname_column_index = 1
        taxon_source_column_index = 2
        
        importer.errors = []
        
        importer.validate_taxon(taxon_latname, taxon_author, taxon_source, workbook_filename, sheet_name,
                       row_number, taxon_latname_column_index, taxon_source_column_index)
        
        self.assertEqual(importer.errors, ['[Generic Content.xlsx][Sheet:Generic Content][cell:B3] Invalid taxonomic source: None'])
        
        
        taxon_latname = 'Weird taxon'
        taxon_author = None
        
        importer.errors = []
        taxon_source = 'taxonomy.sources.col'
        importer.validate_taxon(taxon_latname, taxon_author, taxon_source, workbook_filename, sheet_name,
                       row_number, taxon_latname_column_index, taxon_source_column_index)
        
        self.assertEqual(importer.errors, ['[Generic Content.xlsx][Sheet:Generic Content][row:3] Weird taxon not found in taxonomy.sources.col'])
        
        taxon_latname = 'Viola'
        importer.errors = []
        taxon_source = 'taxonomy.sources.col'
        importer.validate_taxon(taxon_latname, taxon_author, taxon_source, workbook_filename, sheet_name,
                       row_number, taxon_latname_column_index, taxon_source_column_index)
        
        self.assertEqual(importer.errors, ['[Generic Content.xlsx][Sheet:Generic Content][row:3] Multiple results found for Viola in taxonomy.sources.col. You have to specify an author.'])
        
        
    @test_settings
    def test_validate_listing_in_images_sheet(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate_listing_in_images_sheet('unlisted.jpg', 'A', 2)
        
        expected_errors = [
            '[Generic Content.xlsx][Sheet:Generic Content][cell:A3] Image file "unlisted.jpg" not found in the "{0}" sheet.'.format(importer.images_sheet_name)
        ]
        self.assertEqual(importer.errors, expected_errors)
        
        ignorin_importer = GenericContentZipImporter(self.superuser, self.generic_content, self.zip_contents_path, ignore_nonexistent_images=True)
        ignorin_importer.load_workbook()
        ignorin_importer.errors = []
        ignorin_importer.validate_listing_in_images_sheet('unlisted.jpg', 'A', 2)
        self.assertEqual(ignorin_importer.errors, [])