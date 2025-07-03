from django_tenants.test.cases import TenantTestCase
from django.contrib.contenttypes.models import ContentType

from app_kit.tests.common import test_settings
from app_kit.tests.mixins import (WithMetaApp, WithUser, WithMedia)

from app_kit.features.taxon_profiles.zip_import import (TaxonProfilesZipImporter, ColumnType,
                                                        TAXON_PROFILES_SHEET_NAME)
from app_kit.tests.common import TESTS_ROOT

from app_kit.features.taxon_profiles.tests.test_models import WithTaxonProfiles

from app_kit.features.taxon_profiles.models import TaxonProfile


import os

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
        
        qr_image = quercus_robur_profile.images()[0]
        self.assertEqual(qr_image.title, 'Leaf title')
        self.assertEqual(qr_image.text, 'Leaf caption')
        self.assertEqual(qr_image.alt_text, 'Leaf alt text')
        
        self.assertEqual([tag.name for tag in quercus_robur_profile.tags.all()], ['tree', 'deciduous'])
            
    
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
            '[Taxon profiles.xlsx][Sheet:Taxon Profiles][cell:N3] Columns of type image are not allowed to have a value in row 2',
            '[Taxon profiles.xlsx][Sheet:Taxon Profiles][cell:Q3] Cell content has to be one of title, meta_description. Found error instead',
            '[Taxon profiles.xlsx][Sheet:Taxon Profiles][cell:T1] Cell content has to be one of text, shorttext, longtext, short_profile, image, tags, external_media, seo. Found something wrong instead']
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