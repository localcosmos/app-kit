from django_tenants.test.cases import TenantTestCase

from app_kit.tests.common import test_settings
from app_kit.features.glossary.models import Glossary, GlossaryEntry, TermSynonym

from app_kit.features.glossary.zip_import import GlossaryZipImporter
from taxonomy.lazy import LazyTaxonList

class WithGlossary:

    def create_glossary(self):
        glossary = Glossary.objects.create('Test Glossary', 'en')
        return glossary


    def create_glossary_entry(self, glossary, term, definition):

        entry = GlossaryEntry(
            glossary=glossary,
            term=term,
            definition=definition,
        )

        entry.save()

        return entry

    def create_term_synonym(self, glossary_entry, term):

        synonym = TermSynonym(
            glossary_entry=glossary_entry,
            term=term,
        )

        synonym.save()

        return synonym

class TestGlossary(WithGlossary, TenantTestCase):

    @test_settings
    def test_zip_import_class(self):
        glossary = self.create_glossary()

        self.assertTrue(glossary.zip_import_supported)

        ZipImporterClass = glossary.zip_import_class

        self.assertEqual(ZipImporterClass, GlossaryZipImporter)


    @test_settings
    def test_taxa(self):
        glossary = self.create_glossary()

        taxa = glossary.taxa()
        self.assertTrue(isinstance(taxa, LazyTaxonList))

        self.assertEqual(taxa.count(), 0)
        

    @test_settings
    def test_higher_taxa(self):
        glossary = self.create_glossary()

        higher_taxa = glossary.higher_taxa()
        self.assertTrue(isinstance(higher_taxa, LazyTaxonList))

        self.assertEqual(higher_taxa.count(), 0)


    @test_settings
    def test_get_primary_localization(self):
        glossary = self.create_glossary()

        entry = self.create_glossary_entry(glossary, 'Test term', 'Test definition')

        locale = glossary.get_primary_localization()
        self.assertEqual(locale[glossary.name], glossary.name)
        self.assertEqual(locale[entry.term], entry.term)
        self.assertEqual(locale[entry.definition], entry.definition)
        

class TestGlossaryEntry(WithGlossary, TenantTestCase):

    @test_settings
    def test_str(self):
        glossary = self.create_glossary()

        entry = self.create_glossary_entry(glossary, 'Test term', 'Test definition')

        self.assertEqual(str(entry), entry.term)
        

    @test_settings
    def test_synonyms(self):
        glossary = self.create_glossary()

        entry = self.create_glossary_entry(glossary, 'Test term', 'Test definition')

        synonyms_text = ['syno 1', 'syno 2']

        for synonym_text in synonyms_text:
            term_synonym = self.create_term_synonym(entry, synonym_text)


        synonyms = entry.synonyms
        self.assertEqual(set(synonyms_text), set([s.term for s in synonyms]))


class TestTermSynonym(WithGlossary, TenantTestCase):

    @test_settings
    def test_str(self):

        glossary = self.create_glossary()

        entry = self.create_glossary_entry(glossary, 'Test term', 'Test definition')

        synonyms_text = ['syno 1', 'syno 2']

        for synonym_text in synonyms_text:
            term_synonym = self.create_term_synonym(entry, synonym_text)

            self.assertEqual(str(term_synonym), term_synonym.term)
        
