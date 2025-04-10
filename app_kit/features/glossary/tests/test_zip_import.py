from django_tenants.test.cases import TenantTestCase

from app_kit.tests.common import test_settings
from app_kit.tests.mixins import (WithMetaApp, WithUser, WithMedia)

from app_kit.features.glossary.zip_import import (GlossaryZipImporter, GLOSSARY_SHEET_NAME)
from app_kit.tests.common import TESTS_ROOT

from app_kit.features.glossary.tests.test_models import WithGlossary

from app_kit.features.glossary.models import Glossary, GlossaryEntry, TermSynonym

import os



class TestGlossaryZipImporter(WithMedia, WithGlossary, WithUser, WithMetaApp, TenantTestCase):
    
    def setUp(self):
        super().setUp()
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.zip_contents_path = os.path.join(TESTS_ROOT, 'xlsx_for_testing', 'Glossary', 'valid')
        self.glossary = Glossary.objects.create('Glossary', 'en')
        
    def get_zip_importer(self):
        return GlossaryZipImporter(self.superuser, self.glossary, self.zip_contents_path)
    
    @test_settings
    def test_validate_definition_rows(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate_definition_rows()
        self.assertEqual(importer.errors, [])
        
        
    @test_settings
    def test_validate_content(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate_content()
        self.assertEqual(importer.errors, [])
        
    @test_settings
    def test_import(self):
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate()
        self.assertEqual(importer.errors, [])
        self.assertEqual(importer.is_valid, True)
        
        importer.import_generic_content()
        
        glossary_entry = GlossaryEntry.objects.get(glossary=self.glossary, term='Bark')
        self.assertEqual(glossary_entry.definition, 'outer, firm, often hard, bark-like layer surrounding the trunk, branches, and roots')
        
        term_synonyms = TermSynonym.objects.filter(glossary_entry=glossary_entry).values_list('term', flat=True)
        self.assertEqual(list(term_synonyms), ['Rind', 'Cortex'])
        
        
        glossary_entry_2 = GlossaryEntry.objects.get(glossary=self.glossary, term='mulm cavities')
        self.assertEqual(glossary_entry_2.definition, 'Cavities in the living tree')
        
        glossary_entry_3 = GlossaryEntry.objects.get(glossary=self.glossary, term='Seepage water')
        self.assertEqual(glossary_entry_3.definition, 'underground water that moves downward under the influence of gravity')
        
        # test the update
        updated_contents_path = os.path.join(TESTS_ROOT, 'xlsx_for_testing', 'Glossary', 'valid_update')
        update_importer = GlossaryZipImporter(self.superuser, self.glossary, updated_contents_path)
        
        update_importer.load_workbook()
        
        update_importer.errors = []
        update_importer.validate()
        self.assertEqual(importer.errors, [])
        self.assertEqual(importer.is_valid, True)
        
        update_importer.import_generic_content()
        
        glossary_entry.refresh_from_db()
        self.assertEqual(glossary_entry.definition, 'Updated bark text')
        self.assertEqual(glossary_entry.term, 'Bark')
        
        term_synonyms = TermSynonym.objects.filter(glossary_entry=glossary_entry).values_list('term', flat=True)
        self.assertEqual(list(term_synonyms), ['Rind'])
        
        glossary_entry_2 = GlossaryEntry.objects.filter(glossary=self.glossary, term='mulm cavities').exists()
        self.assertEqual(glossary_entry_2, False)
        
        glossary_entry_3.refresh_from_db()
        self.assertEqual(glossary_entry_3.definition, 'underground water that moves downward under the influence of gravity')
        
        glossary_rey_4 = GlossaryEntry.objects.get(glossary=self.glossary, term='New entry')
        self.assertEqual(glossary_rey_4.definition, 'New entry definition')
                
        
class TestGlossaryZipImporterInvalidData(WithMedia, WithGlossary, WithUser, WithMetaApp, TenantTestCase):
    
    def setUp(self):
        super().setUp()
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.zip_contents_path = os.path.join(TESTS_ROOT, 'xlsx_for_testing', 'Glossary', 'invalid')
        self.glossary = Glossary.objects.create('Glossary', 'en')
        
    
    def get_zip_importer(self):
        return GlossaryZipImporter(self.superuser, self.glossary, self.zip_contents_path)
    
    
    @test_settings
    def test_validate_definition_rows(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate_definition_rows()
        
        expected_errors = [
            '[Glossary.xlsx][Sheet:Glossary][cell:A1] Cell content has to be "Term", not Terms',
            '[Glossary.xlsx][Sheet:Glossary][cell:B1] Cell content has to be "Synonyms (optional)", not Synonyms',
            '[Glossary.xlsx][Sheet:Glossary][cell:C1] Cell content has to be "Definition", not Definitions'
        ]
        
        self.assertEqual(importer.errors, expected_errors)
        
        
    @test_settings
    def test_validate_content(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate_content()
        
        expected_errors = [
            '[Glossary.xlsx][Sheet:Glossary][cell:B1] Unambiguous synonym: cortex is mapped to mulm cavities and Bark',
            '[Glossary.xlsx][Sheet:Glossary][cell:B5] No definition found.',
            '[Glossary.xlsx][Sheet:Glossary][cell:A6] No term found.',
            "[Glossary.xlsx][Sheet:Glossary][cell:B7] Synonyms ['Leafy', 'leafy'] are not unique.",
            '[Glossary.xlsx][Sheet:Glossary][cell:A8] Term Bark is not unique.',
            '[Glossary.xlsx][Sheet:Glossary] Term bark is also listed as a synonym.',
        ]
        
        self.assertEqual(importer.errors, expected_errors)
    
    
        