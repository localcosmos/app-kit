from django.test import TestCase

from taxonomy.sources.col.ColTaxonSourceManager import (ColTaxonSourceManager, ColSourceTreeTaxon)

from taxonomy.sources.col.models import ColTaxonTree, ColTaxonSynonym, ColTaxonLocale


class TestColTaxonLocale(TestCase):

    def setUp(self):
        self.taxon = ColTaxonTree.objects.create('001','Animalia',1,rank='kingdom')

    def tearDown(self):
        ColTaxonTree.objects.all().delete()


    def test_set_initial_preferred(self):
        locale = ColTaxonLocale.objects.create(
            self.taxon, 'test', 'de'
        )

        self.assertTrue(locale.preferred)

    def test_save_new_preferred(self):

        locale = ColTaxonLocale.objects.create(
            self.taxon, 'test', 'de'
        )

        self.assertTrue(locale.preferred)

        locale_2 = ColTaxonLocale.objects.create(
            self.taxon, 'test_new', 'de', preferred=True
        )

        self.assertTrue(locale_2.preferred)

        locale = ColTaxonLocale.objects.get(name='test')
        self.assertFalse(locale.preferred)


class TestColSourceTreeTaxon(TestCase):

    def test_get_source_object(self):

        source_taxon = ColSourceTreeTaxon(
            'name',
            'author',
            'rank',
            'source',
            2,
        )

        db_taxon = source_taxon._get_source_object()

        self.assertEqual(db_taxon['name'], 'Tasmaphena sinclairi')
        self.assertEqual(db_taxon['taxon_id'], 2)


    def test_get_vernacular_names(self):

        taxon_id = 316551

        source_taxon = ColSourceTreeTaxon(
            'name',
            'author',
            'rank',
            'source',
            316551,
        )

        vernaculars = source_taxon._get_vernacular_names()

        self.assertEqual(len(vernaculars), 6)

        for name in vernaculars:
            self.assertEqual(name.language, 'en')


    def test_get_synonyms(self):
        source_taxon = ColSourceTreeTaxon(
            'name',
            'author',
            'rank',
            'source',
            2,
        )

        synonyms = source_taxon._get_synonyms()

        self.assertEqual(len(synonyms), 3)

        # Helix sinclairi, Helix bombycina, Helix (Videna) quaestiosa

        expected_synonyms = ['Helix sinclairi', 'Helix bombycina', 'Helix (Videna) quaestiosa']

        latnames = [syno.latname for syno in synonyms]

        self.assertEqual(set(latnames), set(expected_synonyms))
        

class TextColTaxonSourceManager(TestCase):

    def setUp(self):
        self.treemanager = ColTaxonSourceManager()


    def _get_source_taxon_by_id(self, taxon_id):
        source_taxon = ColSourceTreeTaxon(
            'name',
            'author',
            'rank',
            'source',
            taxon_id,
        )

        db_taxon = source_taxon.get_source_object()

        source_taxon = self.treemanager._sourcetaxon_from_db_taxon(db_taxon)

        return source_taxon

    def test_get_author(self):

        source_taxon = ColSourceTreeTaxon(
            'name',
            'author',
            'rank',
            'source',
            2,
        )

        db_taxon = source_taxon.get_source_object()

        author = self.treemanager._get_author(db_taxon)

        self.assertEqual(author, '(Pfeiffer, 1846)')

    def test_sourcetaxon_from_db_taxon(self):

        _source_taxon = ColSourceTreeTaxon(
            'name',
            'author',
            'rank',
            'source',
            2,
        )

        db_taxon = _source_taxon.get_source_object()

        source_taxon = self.treemanager._sourcetaxon_from_db_taxon(db_taxon)

        self.assertEqual(db_taxon['name'], source_taxon.latname)
        self.assertEqual(db_taxon['rank'], source_taxon.rank)
        self.assertEqual(str(db_taxon['taxon_id']), source_taxon.source_id)
        self.assertEqual('col2015', source_taxon.source)
        self.assertEqual('(Pfeiffer, 1846)', source_taxon.author)

    def test_get_root_source_taxa(self):

        root_taxa = self.treemanager._get_root_source_taxa()

        root_latnames = [t.latname for t in root_taxa]

        self.assertEqual(['Animalia', 'Archaea', 'Bacteria', 'Chromista', 'Fungi', 'Plantae', 'Protozoa', 'Viruses'],
                         root_latnames)

    def test_get_children(self):

        # plantae has 2 children
        plantae_id = 22032971

        source_taxon = self._get_source_taxon_by_id(plantae_id)
        
        self.assertEqual(source_taxon.source_id, str(plantae_id))

        children = self.treemanager._get_children(source_taxon)

        self.assertEqual(len(children), 2)

        expected = ['Bryophyta', 'Tracheophyta']

        latnames = [taxon.latname for taxon in children]

        self.assertEqual(expected, latnames)


    def test_get_next_sibling(self):

        # after plantae comes protozoa
        plantae_id = 22032971

        source_taxon = self._get_source_taxon_by_id(plantae_id)

        next_sibling = self.treemanager._get_next_sibling(source_taxon)
        self.assertEqual(next_sibling.latname, 'Protozoa')
        
        # after viruses [22033098], nothing comes
        source_taxon = self._get_source_taxon_by_id(22033098)
        next_sibling = self.treemanager._get_next_sibling(source_taxon)
        self.assertEqual(next_sibling, None)
        

    def test_get_parent(self):

        tracheophyta_id = 22032972

        source_taxon = self._get_source_taxon_by_id(tracheophyta_id)
        parent = self.treemanager._get_parent(source_taxon)

        self.assertEqual(parent.latname, 'Plantae')

        parent_parent = self.treemanager._get_parent(parent)

        self.assertEqual(parent_parent, None)
        
