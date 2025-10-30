from django_tenants.test.cases import TenantTestCase

from app_kit.tests.common import test_settings
from app_kit.tests.mixins import (WithMetaApp, WithUser, WithMedia)

from app_kit.features.backbonetaxonomy.zip_import import (BackbonetaxonomyZipImporter, TAXON_RELATIONSHIP_TYPES_SHEET_NAME,
                                                          TAXON_RELATIONSHIPS_SHEET_NAME)
from app_kit.tests.common import TESTS_ROOT

from app_kit.features.backbonetaxonomy.models import TaxonRelationshipType, TaxonRelationship


import os

class MockCell:
    
    def __init__(self, value):
        self.value = value

class TestBackbonetaxonomyZipImporter(WithMedia, WithUser, WithMetaApp, TenantTestCase):

    def setUp(self):
        super().setUp()
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.zip_contents_path = os.path.join(TESTS_ROOT, 'xlsx_for_testing', 'BackboneTaxonomy', 'valid')
        self.backbonetaxonomy = self.meta_app.backbone()
        
    def get_zip_importer(self):
        return BackbonetaxonomyZipImporter(self.superuser, self.backbonetaxonomy, self.zip_contents_path)

    @test_settings
    def test_validate_definition_rows(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate_definition_rows()
        self.assertEqual(importer.errors, [])
    
    @test_settings
    def test_validate_relationship_types(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()

        importer.errors = []
        importer.validate_taxon_relationship_types_sheet()
        self.assertEqual(importer.errors, [])
    
    @test_settings
    def test_validate_taxon_relationships(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate_taxon_relationships_sheet()
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

        similar_type = TaxonRelationshipType.objects.filter(relationship_name='Similar species').first()
        self.assertIsNotNone(similar_type)
        
        self.assertEqual(similar_type.backbonetaxonomy, self.backbonetaxonomy)
        self.assertEqual(similar_type.taxon_role, None)
        self.assertEqual(similar_type.related_taxon_role, None)
        
        predation_type = TaxonRelationshipType.objects.filter(relationship_name='Predation').first()
        self.assertIsNotNone(predation_type)
        self.assertEqual(predation_type.backbonetaxonomy, self.backbonetaxonomy)
        self.assertEqual(predation_type.taxon_role, 'Predator')
        self.assertEqual(predation_type.related_taxon_role, 'Prey')
        
        relation_1 = TaxonRelationship.objects.filter(relationship_type=predation_type)
        self.assertEqual(relation_1.count(), 1)
        relation_1 = relation_1.first()
        self.assertIsNotNone(relation_1)
        
        self.assertEqual(relation_1.backbonetaxonomy, self.backbonetaxonomy)
        self.assertEqual(relation_1.description, 'Blackbird eats worm')
        self.assertEqual(relation_1.taxon_latname, 'Turdus merula')
        self.assertEqual(relation_1.taxon_author, 'Linnaeus, 1758')
        self.assertEqual(relation_1.taxon_source, 'taxonomy.sources.col')
        self.assertEqual(relation_1.related_taxon_latname, 'Lumbricus terrestris')
        self.assertEqual(relation_1.related_taxon_author, 'Linnaeus, 1758')
        self.assertEqual(relation_1.related_taxon_source, 'taxonomy.sources.col')
        
        relation_2 = TaxonRelationship.objects.filter(relationship_type=similar_type)
        self.assertEqual(relation_2.count(), 1)
        relation_2 = relation_2.first()
        self.assertIsNotNone(relation_2)

        self.assertEqual(relation_2.backbonetaxonomy, self.backbonetaxonomy)
        self.assertEqual(relation_2.description, None)
        self.assertEqual(relation_2.taxon_latname, 'Turdus merula')
        self.assertEqual(relation_2.taxon_author, 'Linnaeus, 1758')
        self.assertEqual(relation_2.taxon_source, 'taxonomy.sources.col')
        self.assertEqual(relation_2.related_taxon_latname, 'Sturnus vulgaris')
        self.assertEqual(relation_2.related_taxon_author, 'Linnaeus, 1758')
        self.assertEqual(relation_2.related_taxon_source, 'taxonomy.sources.col')


class TestBackboneTaxonomyZipImporterInvalidCellContentTypes(WithUser, WithMetaApp, TenantTestCase):
    def setUp(self):
        super().setUp()
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.zip_contents_path = os.path.join(TESTS_ROOT, 'xlsx_for_testing', 'BackboneTaxonomy', 'invalid_content_type')
        self.backbonetaxonomy = self.meta_app.backbone()
        
    def get_zip_importer(self):
        return BackbonetaxonomyZipImporter(self.superuser, self.backbonetaxonomy, self.zip_contents_path)


    @test_settings
    def test_validate_cell_value_content_types(self):
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate_cell_value_content_types()
        expected_errors = [
            '[Backbone taxonomy.xlsx][Sheet:Taxon Relationships][cell:H3] Invalid cell content: =I3. Formulas are not allowed.'
        ]

        self.assertEqual(importer.errors, expected_errors)


class TestTaxonProfilesZipImporterInvalidData(WithUser, WithMetaApp, TenantTestCase):
    
    def setUp(self):
        super().setUp()
        self.superuser = self.create_superuser()
        self.user = self.create_user()
        self.zip_contents_path = os.path.join(TESTS_ROOT, 'xlsx_for_testing', 'BackboneTaxonomy', 'invalid')
        self.backbonetaxonomy = self.meta_app.backbone()
        
    def get_zip_importer(self):
        return BackbonetaxonomyZipImporter(self.superuser, self.backbonetaxonomy, self.zip_contents_path)

    @test_settings
    def test_validate_definition_rows(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate_definition_rows()
        expected_errors = [
            '[Backbone taxonomy.xlsx][Sheet:Taxon Relationships][cell:C1] Cell content has to be "Taxon", not None',
            '[Backbone taxonomy.xlsx][Sheet:Taxon Relationships][cell:G1] Cell content has to be "Related Taxon", not None',
            '[Backbone taxonomy.xlsx][Sheet:Taxon Relationships][cell:A2] Cell content has to be "Relationship", not Relationships',
            '[Backbone taxonomy.xlsx][Sheet:Taxon Relationships][cell:B2] Cell content has to be "Scientific Name", not Scientific Names'
        ]
        self.assertEqual(importer.errors, expected_errors)
    

    @test_settings
    def test_validate_taxon_relationship_types_sheet(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate_taxon_relationship_types_sheet()
                
        expected_errors = [
            '[Backbone taxonomy.xlsx][Sheet:Taxon Relationship Types][cell:C6] Related Taxon Role is required if Taxon Role is provided.'
        ]
        self.assertEqual(importer.errors, expected_errors)
    
    @test_settings
    def test_get_taxon_relationship_type_by_name(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        relationship = importer.get_taxon_relationship_type_by_name('Unknown relationship')
        self.assertEqual(relationship, None)
        
        relationship_2 = importer.get_taxon_relationship_type_by_name('Predation')
        self.assertIsNotNone(relationship_2)
        self.assertEqual(relationship_2['name'], 'Predation')
        self.assertEqual(relationship_2['taxon_role'], 'Predator')
        self.assertEqual(relationship_2['related_taxon_role'], 'Prey')
        
    @test_settings
    def test_validate_taxon_relationships_sheet(self):
        
        importer = self.get_zip_importer()
        importer.load_workbook()
        
        importer.errors = []
        importer.validate_taxon_relationships_sheet()
        
        expected_errors = [
            '[Backbone taxonomy.xlsx][Sheet:Taxon Relationships][cell:A3] Relationship Type "Undefined type" not found.',
            '[Backbone taxonomy.xlsx][Sheet:Taxon Relationships][cell:A4] Relationship is required.'
        ]
        self.assertEqual(importer.errors, expected_errors)
        
        