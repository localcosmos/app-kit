from django.test import TestCase

from taxonomy.sources.TaxonSourceManager import (TaxonSourceManager, SourceTreeTaxon,
                        SourceSynonymTaxon, n2d, d2n, TreeClimberState, VernacularName, TreeCache)

from taxonomy.sources.col.models import ColTaxonTree, ColTaxonSynonym, ColTaxonLocale

import os, shutil, json

'''
    create a test tree in two versions
'''
tree_1 = {
    'A' : {
        'A.A' : {
            'A.A.A' : {},
            'A.A.B' : {},
        },
        'A.B' : {
            'A.B.A' : {}, # important! childless first child, with sibling that has children
            'A.B.B' : {
                'A.B.B.A' : {
                    'A.B.B.A.A' : {} #
                }
            },
            'A.B.C' : {
            },
            'A.B.D' : {
                'A.B.D.A' : {}
            },
            'A.B.E' : {},
        },
        'A.C' : {}
    },
    'B' : {
        'B.A' : {
            'B.A.A' : {},
            'B.A.B' : {},
        },
        'B.B' : {
            'B.B.A': {},
        }
    },
    'C' : {
        'C.A' : {}
    },
}


# some are deleted, some are new
tree_2 = {
    'A' : {
        'A.A' : {
            'A.A.A' : {},
            'A.A.B' : {},
        },
        'A.B' : {
            'A.B.A' : {}, # important! childless first child, with sibling that has children
            'A.B.B' : {
                'A.B.B.A' : {
                }
            },
            'A.B.C' : {
            },
            'A.B.D' : {
                'A.B.D.A' : {}
            },
        },
        'A.C' : {}
    },
    'B' : {
        'B.A' : {
            'B.A.A' : {},
            'B.A.B' : {},
        },
    },
    'C' : {
        'C.A' : {
            'C.A.A' : {},
            'C.A.B' : {},
        }
    },
    'D' : {
        'D.A' : {}
    },
}        

vernacular_1 = {
    'B.A.A' : {
        'de' : 'de002001001',
        'en' : 'en002001001',
    },
    'B.A.B' : {
        'de' : 'de002001002',
    },
}

synonyms_1 = {
    'B.A.A' : [
        {'latname' : 'syno1', 'author' : 'syno1author'},
        {'latname' :'syno2', 'author' : 'syno2author'},
    ],
    'B.A' : [
        {'latname' : 'syno3', 'author' : 'syno3author'},
        {'latname' : 'syno4', 'author' : 'syno4author'},
    ],
}

vernacular_2 = {
    'B.A.A' : {
        'en' : 'en002001001',
    },
    'B.A.B' : {
        'de' : 'de002001002',
        'en' : 'en002001002',
        'fr' : 'fr002001002',
    },
}

synonyms_2 = {
    'B.A.A' : [
        {'latname' :'syno2', 'author' : 'syno2author'},
    ],
    'B.A' : [
        {'latname' : 'syno3', 'author' : 'syno3author'},
        {'latname' : 'syno5', 'author' : 'syno5author'},
    ],
}


def iterate_dics(dic, latnames_list):

    for key, value in dic.items():

        latnames_list.append(key)

        if type(value) == dict:
            iterate_dics(value, latnames_list)

    return latnames_list


def count_synonyms(synos):

    count = 0

    for key, lst in synos.items():
        count += len(lst)

    return count

def get_synonym_latnames(synos):

    synonyms = []

    for key, lst in synos.items():
        for synonym in lst:
            synonyms.append(synonym['latname'])

    return synonyms


tree_1_latnames = iterate_dics(tree_1, [])
tree_2_latnames = iterate_dics(tree_2, [])


trees = {
    'tree_1' : {
        'latnames' : tree_1_latnames,
        'entry_count' : len(tree_1_latnames),
        'synonym_count' : count_synonyms(synonyms_1),
        'synonym_latnames' : get_synonym_latnames(synonyms_1),
        'synonyms' : synonyms_1,
        'vernacular' : vernacular_1,
        'vernacular_count' : count_synonyms(vernacular_1),
    },
    'tree_2' : {
        'latnames' : tree_2_latnames,
        'entry_count' : len(tree_2_latnames),
        'synonym_count' : count_synonyms(synonyms_2),
        'synonym_latnames' : get_synonym_latnames(synonyms_2),
        'synonyms' : synonyms_2,
        'vernacular' : vernacular_2,
        'vernacular_count' : count_synonyms(vernacular_2),
    },
}

ACTIVE_TREE = tree_1
ACTIVE_TREE_NAME = 'tree_1'


def get_tree_entry_by_latname(latname):
    
    tree = ACTIVE_TREE

    ## make A.A -> [A,A.A]

    parts = latname.split('.')

    # [A,A]
    entry = None

    for counter, e in enumerate(parts):

        join_list = parts[:counter+1]

        key = ".".join(join_list)

        if not key in tree:
            return None
        
        entry = tree[key]
        
        tree = entry

    return entry


alphabet = ['A','B','C','D','E','F']
def latname_to_nuid(latname):
    parts = latname.split('.')

    nuid = ""

    for part in parts:
        nuid += d2n(alphabet.index(part) + 1)

    return nuid


def get_parent_from_latname(latname):

    if len(latname) >=3:
        return latname[:-2]

    return None


def get_all_siblings_from_latname(latname):

    siblings = []

    parent_latname = get_parent_from_latname(latname)

    if parent_latname:

        for letter in alphabet:
            key = '%s.%s' %(parent_latname, letter)

            exists = get_tree_entry_by_latname(key)

            if exists is not None:
                siblings.append(key)

    else:
        for letter in alphabet:
            
            exists = get_tree_entry_by_latname(letter)

            if exists is not None:
                siblings.append(letter)

    return siblings


class TestHelperFunctions(TestCase):

    def test_latname_to_nuid(self):

        latname = 'A.B.C'
        nuid = latname_to_nuid(latname)
        self.assertEqual(nuid, '001002003')


        latname = 'C.A'
        nuid = latname_to_nuid(latname)
        self.assertEqual(nuid, '003001')

        latname = 'C'
        nuid = latname_to_nuid(latname)
        self.assertEqual(nuid, '003')

    def test_get_parent_from_latname(self):

        latname = 'A.A.B'
        parent_latname = get_parent_from_latname(latname)
        self.assertEqual(parent_latname, 'A.A')

        latname = 'A.A'
        parent_latname = get_parent_from_latname(latname)
        self.assertEqual(parent_latname, 'A')


        latname = 'A'
        parent_latname = get_parent_from_latname(latname)
        self.assertEqual(parent_latname, None)


    def test_get_all_siblings_from_latname(self):

        siblings = get_all_siblings_from_latname('A')
        self.assertEqual(siblings,['A','B','C'])

        siblings = get_all_siblings_from_latname('A.A')
        self.assertEqual(siblings,['A.A','A.B','A.C'])

        siblings = get_all_siblings_from_latname('B.A.A')
        self.assertEqual(siblings,['B.A.A','B.A.B'])

        siblings = get_all_siblings_from_latname('A.B.D.A')
        self.assertEqual(siblings, ['A.B.D.A'])


        

class JSONTreeTreeTaxon(SourceTreeTaxon):

    TreeModel = ColTaxonTree

    def _get_source_object(self):

        return get_tree_entry_by_latname(self.latname)
        

    def _get_synonyms(self):
        synonyms = []

        tree_synonyms = trees[ACTIVE_TREE_NAME]['synonyms']

        if self.latname in tree_synonyms:
            for dic in tree_synonyms[self.latname]:
                taxon = JSONTreeSynonymTaxon(
                    dic['latname'], dic['author'], 'rank', 'source', dic['latname'], source_object=dic
                )

                synonyms.append(taxon)

        return synonyms

    
    def _get_vernacular_names(self):

        vernaculars = []

        tree_vernacular = trees[ACTIVE_TREE_NAME]['vernacular']

        if self.latname in tree_vernacular:
            for language, name in tree_vernacular[self.latname].items():
                vernacular_name = VernacularName(
                    name, language, True,
                )

                vernaculars.append(vernacular_name)

        return vernaculars


class JSONTreeSynonymTaxon(SourceSynonymTaxon):
    pass


class JSONTreeCache(TreeCache):

    SourceTreeTaxonClass = JSONTreeTreeTaxon
    TaxonTreeModel = ColTaxonTree

    def _make_source_taxon(self, db_taxon):

        # def __init__(self, latname, author, rank, source, source_id, **kwargs):
        source_taxon = self.SourceTreeTaxonClass(
            db_taxon.taxon_latname, db_taxon.author, db_taxon.rank, 'JSONTREE', db_taxon.source_id,
            nuid=db_taxon.taxon_nuid
        )

        return source_taxon


class JSONTreeManager(TaxonSourceManager):

    SourceTreeTaxonClass = JSONTreeTreeTaxon
    
    TaxonTreeModel = ColTaxonTree
    TaxonSynonymModel = ColTaxonSynonym
    TaxonLocaleModel = ColTaxonLocale

    TreeCacheClass = JSONTreeCache

    def __init__(self, jsontree):
        self.jsontree = jsontree
        super().__init__()
        
    
    def _get_root_source_taxa(self):
        source_root_taxa = []
        for latname, dic in self.jsontree.items():
            taxon = self.SourceTreeTaxonClass(
                latname, 'author', 'rank', 'testjson', latname, source_object=dic
            )

            source_root_taxa.append(taxon)

        source_root_taxa.sort(key=lambda taxon:taxon.latname)
        return source_root_taxa
    

    def _create_source_taxon(self, latname, dic):
        source_taxon = self.SourceTreeTaxonClass(
            latname, 'author', 'rank', 'testjson', latname, source_object=dic
        )

        return source_taxon
    

    def _get_jsontree_taxon_by_latname(self, latname):

        # create a list ['A', 'A.A',...] that is the route to the latname

        source_object = get_tree_entry_by_latname(latname)

        if source_object is None:
            return None
        
        return self._create_source_taxon(latname, source_object)


    '''
    this function has to travel right and up until the next parent taxon which has not been climbed down
    yet has been found
    source_taxon is a childless taxon, its siblings might have children
    '''

    def _get_next_sibling(self, source_taxon):

        parts = source_taxon.latname.split('.')

        next_letter = chr(ord(parts[-1]) + 1)

        next_latname = source_taxon.latname[:-1] + next_letter
        
        sibling = self._get_jsontree_taxon_by_latname(next_latname)
        
        return sibling

    
    def _get_parent(self, source_taxon):

        if len(source_taxon.latname) > 1:
            parent_latname = source_taxon.latname[:-2]
            parent = self._get_jsontree_taxon_by_latname(parent_latname)
            return parent
        else:
            return None


    def _get_children(self, source_taxon):

        children = []
        
        for latname, dic in source_taxon._get_source_object().items():
            taxon = self._create_source_taxon(latname, dic)
            children.append(taxon)

        children.sort(key=lambda child: child.latname)

        return children


class DatabaseHelpers(object):

    def _prepare_database(self, latname):
        # insert all taxa w siblings that are above the current tree entry

        while latname:

            sibling_latnames = get_all_siblings_from_latname(latname)
            
            for latname in sibling_latnames:
                self._create_lc_db_taxon(latname)

            latname = get_parent_from_latname(latname)

                    
    def _create_lc_db_taxon(self, latname):
        source_taxon = self.treemanager._get_jsontree_taxon_by_latname(latname)

        # create the nuid from the latname
        source_taxon.set_nuid(latname_to_nuid(latname))
        
        self.treemanager._save_new_taxon(source_taxon)
        
        return source_taxon

    

class JSONTreeTreeCacheTest(TestCase, DatabaseHelpers):

    def setUp(self):
        self.treemanager = JSONTreeManager(tree_1)

    def tearDown(self):
        self.treemanager.TaxonTreeModel.objects.all().delete()
        self.treemanager.TaxonSynonymModel.objects.all().delete()
        self.treemanager.TaxonLocaleModel.objects.all().delete()


    def test_make_source_taxon(self):
        cache = JSONTreeCache()

        source_taxon = self._create_lc_db_taxon('A')

        db_taxon = cache.TaxonTreeModel.objects.get(taxon_latname='A')
        
        source_taxon = cache._make_source_taxon(db_taxon)

        self.assertEqual(source_taxon.latname, 'A')
        

    def test_make_cache_entry(self):

        cache = JSONTreeCache()

        parent_taxon = self._create_lc_db_taxon('A')
        parent_taxon.set_nuid(latname_to_nuid('A'))

        children_latnames = ['A.A', 'A.B', 'A.C']

        children = []

        for latname in children_latnames:
            
            source_taxon = self._create_lc_db_taxon(latname)
            source_taxon.set_nuid(latname_to_nuid(latname))
            children.append(source_taxon)


        entry = cache._make_cache_entry(parent_taxon, children)

        self.assertEqual(entry['parent_taxon'], parent_taxon)
        self.assertEqual(entry['children'], children)
        

    def test_add_to_empty(self):

        cache = JSONTreeCache()

        parent_taxon = None
        children_latnames = ['A','B','C']
        children = []
        for latname in children_latnames:
            
            source_taxon = self._create_lc_db_taxon(latname)
            source_taxon.set_nuid(latname_to_nuid(latname))
            children.append(source_taxon)
        

        cache.add(parent_taxon, children)

        self.assertEqual(len(cache.cache), 1)
        self.assertEqual(cache.cache[0]['children'], children)
        self.assertEqual(cache.cache[0]['parent_taxon'], parent_taxon)


    def test_find_level_simple(self):
        self._prepare_database('A')
        parent_taxon = self.treemanager._get_jsontree_taxon_by_latname('A')

        latnames = ['A.A', 'A.B', 'A.C']
        children = []

        for latname in latnames:
            source_taxon = self.treemanager._get_jsontree_taxon_by_latname(latname)
            children.append(source_taxon)

        cache = JSONTreeCache()
        cache.add(parent_taxon, children)
        # the upstream was triggered
        
        child = self.treemanager._get_jsontree_taxon_by_latname('A.B')

        level_index = cache._find_level(child)
        self.assertEqual(level_index, 1)


    def test_add_with_existing_level_index(self):
        self._prepare_database('A')

        query = ColTaxonTree.objects.all()

        self. assertEqual(query.count(), 3)
        
        cache = JSONTreeCache()
        
        levels = [
            {
                'parent' : 'A',
                'children' : ['A.A', 'A.B', 'A.C'],
            },
            {
                'parent' : 'A.A',
                'children' : ['A.A.A', 'A.A.B'],
            },
        ]

        for level in levels:
            
            parent_taxon = self.treemanager._get_jsontree_taxon_by_latname(level['parent'])

            children = []
            for latname in level['children']:
                source_taxon = self.treemanager._get_jsontree_taxon_by_latname(latname)
                children.append(source_taxon)

            cache.add(parent_taxon, children)

        # the upstream has been created
        self.assertEqual(cache.cache[0]['parent_taxon'], None)
        self.assertEqual(len(cache.cache[0]['children']), 3)

        self.assertEqual(cache.cache[1]['parent_taxon'].latname, 'A')
        self.assertEqual(len(cache.cache[1]['children']), 3)

        self.assertEqual(cache.cache[2]['parent_taxon'].latname, 'A.A')
        self.assertEqual(len(cache.cache[2]['children']), 2)


    def test_find_level_complex(self):
        # this does not create an upstream (while loop) because it inserts the root taxa first
        cache = JSONTreeCache()
        
        levels = [
            {
                'parent' : None,
                'children' : ['A','B','C'],
            },
            {
                'parent' : 'A',
                'children' : ['A.A', 'A.B', 'A.C'],
            },
            {
                'parent' : 'A.A',
                'children' : ['A.A.A', 'A.A.B'],
            },
        ]

        for level in levels:
            if level['parent'] is not None:
                parent_taxon = self.treemanager._get_jsontree_taxon_by_latname(level['parent'])
            else:
                parent_taxon = None
            children = []
            for latname in level['children']:
                source_taxon = self.treemanager._get_jsontree_taxon_by_latname(latname)
                children.append(source_taxon)

            cache.add(parent_taxon, children)

        source_taxon = self.treemanager._get_jsontree_taxon_by_latname('B')
        level_index = cache._find_level(source_taxon)
        self.assertEqual(level_index, 0)

        source_taxon = self.treemanager._get_jsontree_taxon_by_latname('A.B')
        level_index = cache._find_level(source_taxon)
        self.assertEqual(level_index, 1)

        source_taxon = self.treemanager._get_jsontree_taxon_by_latname('A.A.B')
        level_index = cache._find_level(source_taxon)
        self.assertEqual(level_index, 2)


    def test_build_upstream(self):
        
        latname = 'A.B.B.A'
        parent_taxon = self.treemanager._get_jsontree_taxon_by_latname(latname)
        parent_taxon.set_nuid(latname_to_nuid(latname))

        latname_2 = 'A.B.B.A.A'
        taxon = self.treemanager._get_jsontree_taxon_by_latname(latname_2)
        taxon.set_nuid(latname_to_nuid(latname_2))
        children = [taxon]

        self._prepare_database(latname_2)
        query = ColTaxonTree.objects.all()

        self.assertEqual(query.count(), 13)

        cache = JSONTreeCache()

        cache.add(parent_taxon, children)

        # 3 3 5 1 1
        self.assertEqual(len(cache.cache), 5)
        self.assertEqual(len(cache.cache[0]['children']), 3)
        self.assertEqual(len(cache.cache[1]['children']), 3)
        self.assertEqual(len(cache.cache[2]['children']), 5)
        self.assertEqual(len(cache.cache[3]['children']), 1)
        self.assertEqual(len(cache.cache[4]['children']), 1)

        self.assertEqual(cache.cache[0]['parent_taxon'], None)
        self.assertEqual(cache.cache[1]['parent_taxon'].latname, 'A')
        self.assertEqual(cache.cache[2]['parent_taxon'].latname, 'A.B')
        self.assertEqual(cache.cache[3]['parent_taxon'].latname, 'A.B.B')
        self.assertEqual(cache.cache[4]['parent_taxon'].latname, 'A.B.B.A')

    def test_get_parent_taxon_from_db(self):
        self._prepare_database('C.A')

        cache = JSONTreeCache()

        source_taxon = self.treemanager._get_jsontree_taxon_by_latname('C.A')
        
        parent_taxon =  cache._get_parent_taxon_from_db(source_taxon)

        self.assertEqual(parent_taxon.latname, 'C')
        self.assertEqual(parent_taxon.nuid, '003')

    def test_get_siblings_group_from_db(self):
        latname = 'B.B'
        self._prepare_database(latname)

        source_taxon = self.treemanager._get_jsontree_taxon_by_latname('C.A')
        source_taxon.set_nuid(latname_to_nuid(latname))

        cache = JSONTreeCache()
        siblings = cache._get_siblings_group_from_db(source_taxon)

        self.assertEqual(len(siblings), 2)
        self.assertEqual(siblings[0].latname, 'B.A')
        self.assertEqual(siblings[1].latname, 'B.B')

    def test_get_parent(self):
        latname = 'B.B'
        self._prepare_database(latname)

        parent_taxon = self.treemanager._get_jsontree_taxon_by_latname(latname)
        parent_taxon.set_nuid(latname_to_nuid(latname))

        cache = JSONTreeCache()
        latnames = ['B.B.A']
        children = []

        for latname in latnames:
            source_taxon = self.treemanager._get_jsontree_taxon_by_latname(latname)
            children.append(source_taxon)

        cache.add(parent_taxon, children)
        
        parent_parent = cache._get_parent(parent_taxon)
        self.assertEqual(parent_parent.latname, 'B')

        # test the None case
        source_taxon = self.treemanager._get_jsontree_taxon_by_latname('B')
        parent = cache._get_parent(source_taxon)
        self.assertEqual(parent, None)

    def test_get_next_sibling(self):

        latname = 'A.B.B.A'
        parent_taxon = self.treemanager._get_jsontree_taxon_by_latname(latname)
        parent_taxon.set_nuid(latname_to_nuid(latname))

        latname_2 = 'A.B.B.A.A'
        taxon = self.treemanager._get_jsontree_taxon_by_latname(latname_2)
        taxon.set_nuid(latname_to_nuid(latname_2))
        children = [taxon]

        self._prepare_database(latname_2)

        cache = JSONTreeCache()
        cache.add(parent_taxon, children)

        # upstreamed

        source_taxon = self.treemanager._get_jsontree_taxon_by_latname('A.B.C')

        next_sibling = cache._get_next_sibling(source_taxon)
        self.assertEqual(next_sibling.latname, 'A.B.D')

        next_sibling = cache._get_next_sibling(next_sibling)
        self.assertEqual(next_sibling.latname, 'A.B.E')

        next_sibling = cache._get_next_sibling(next_sibling)
        self.assertEqual(next_sibling, None)


'''
    First test the JSONTreeTreeTaxon
'''

class JSONTreeTreeTaxonTest(TestCase):

    def setUp(self):
        self.source_taxon = JSONTreeTreeTaxon(
            'testlatname', 'testauthor', 'testrank', 'testsource', 'testsourceid',
        )


    def test_get_source_object(self):
        self.source_taxon.latname = 'A.B'
        source_object = self.source_taxon._get_source_object()

        self.assertEqual(tree_1['A']['A.B'], source_object)


        self.source_taxon.latname = 'A.B.A'
        source_object = self.source_taxon._get_source_object()

        self.assertEqual(tree_1['A']['A.B']['A.B.A'], source_object)


    def test_get_syonyms(self):

        self.source_taxon.latname = 'B.A.A'
        synonyms = self.source_taxon.synonyms()

        self.assertEqual(len(synonyms), 2)

        synonym_latnames = [synonym.latname for synonym in synonyms]

        self.assertTrue('syno1' in synonym_latnames)
        self.assertTrue('syno2' in synonym_latnames)


    def test_get_vernacular_names(self):

        self.source_taxon.latname = 'B.A.A'

        vernaculars = self.source_taxon.vernacular_names()

        self.assertEqual(len(vernaculars), 2)

        vnames = [v.name for v in vernaculars]

        self.assertTrue('de002001001' in vnames)
        self.assertTrue('en002001001' in vnames)

'''
    Second test the JSONTreeManager, which is only there for testing purposes
'''

class JSONTreeManagerTest(TestCase):

    def setUp(self):
        self.treemanager = JSONTreeManager(tree_1)

    # first test if the JSONTreeManager works as expected

    def test_get_root_source_taxa(self):
        root_taxa = self.treemanager._get_root_source_taxa()

        self.assertEqual(len(root_taxa), 3)
        self.assertEqual(root_taxa[0].latname, 'A')
        self.assertEqual(root_taxa[1].latname, 'B')
        self.assertEqual(root_taxa[2].latname, 'C')

        # check source_object
        self.assertEqual(root_taxa[0].get_source_object(), tree_1['A'])
        self.assertEqual(root_taxa[1].get_source_object(), tree_1['B'])
        self.assertEqual(root_taxa[2].get_source_object(), tree_1['C'])
        
    
    def test_get_jsontree_taxon_by_latname(self):

        entry = self.treemanager._get_jsontree_taxon_by_latname('A')
        entry_expected_taxon = self.treemanager._create_source_taxon('A', tree_1['A'])
        
        self.assertEqual(entry.get_source_object(), entry_expected_taxon.get_source_object())
        self.assertEqual(entry.latname, entry_expected_taxon.latname)

        entry_1 = self.treemanager._get_jsontree_taxon_by_latname('A.A.B')
        entry_1_expected_taxon= self.treemanager._create_source_taxon('A.A.B', tree_1['A']['A.A']['A.A.B'])
        self.assertEqual(entry_1.get_source_object(), entry_1_expected_taxon.get_source_object())
        self.assertEqual(entry_1.latname, entry_1_expected_taxon.latname)

        entry_2 = self.treemanager._get_jsontree_taxon_by_latname('B.B')
        entry_2_expected_taxon = self.treemanager._create_source_taxon('B.B', tree_1['B']['B.B'])
        self.assertEqual(entry_2.get_source_object(), entry_2_expected_taxon.get_source_object())
        self.assertEqual(entry_2.latname, entry_2_expected_taxon.latname)

        entry_3 = self.treemanager._get_jsontree_taxon_by_latname('A.E.F.G')
        self.assertEqual(entry_3, None)

    
    def test_get_next_sibling(self):
        source_taxon = self.treemanager._get_jsontree_taxon_by_latname('A.B')

        sibling = self.treemanager._get_next_sibling(source_taxon)
        self.assertEqual(sibling.latname, 'A.C')

        # sibling of last = None
        source_taxon = self.treemanager._get_jsontree_taxon_by_latname('A.C')
        sibling = self.treemanager._get_next_sibling(source_taxon)
        self.assertEqual(sibling, None)

    
    def test_get_next_parent(self):
        source_taxon = self.treemanager._get_jsontree_taxon_by_latname('A.B')
        parent = self.treemanager._get_parent(source_taxon)
        self.assertEqual(parent.latname, 'A')

        source_taxon = self.treemanager._get_jsontree_taxon_by_latname('A')
        parent = self.treemanager._get_parent(source_taxon)
        self.assertEqual(parent, None)
        

    def test_get_children(self):

        latname = 'A.B'
        dic = tree_1['A']['A.B']

        source_taxon = self.treemanager._create_source_taxon(latname, dic)

        children = self.treemanager._get_children(source_taxon)

        # 3 children are present
        
        for counter, latname in enumerate(['A.B.A','A.B.B','A.B.C'], 0):
            expected_child = self.treemanager._get_jsontree_taxon_by_latname(latname)

            self.assertEqual(children[counter].latname, expected_child.latname)
            self.assertEqual(children[counter].get_source_object(), expected_child.get_source_object())
            


class TreeClimberStateTest(TestCase):

    root_taxon_dic = {
        'latname' : 'test_root_latname',
        'author' : 'test_root_author',
        'rank' : 'test_root_rank',
        'source' : 'test_root_source',
        'source_id' : 'test_root_source_id',
        'kwargs' : {
            'nuid' : '001'
        },
    }

    def setUp(self):
        root_path = os.path.dirname(os.path.abspath(__file__))
        self.dump_path = os.path.join(root_path, 'treeclimberstate_tests_dumps')

        if not os.path.isdir(self.dump_path):
            os.makedirs(self.dump_path)

        self.taxon_1 = JSONTreeTreeTaxon(
            'latname_1', 'author_1', 'rank_1', 'source_1', 'source_id_1',
        )

        self.taxon_2 = JSONTreeTreeTaxon(
            'latname_2', 'author_2', 'rank_2', 'source_2', 'source_id_2',
        )

        self.taxon_3 = JSONTreeTreeTaxon(
            'latname_3', 'author_3', 'rank_3', 'source_3', 'source_id_3',
        )

    def tearDown(self):
        shutil.rmtree(self.dump_path)

    def test_source_taxon_from_dict(self):

        state = TreeClimberState(JSONTreeTreeTaxon, self.dump_path)
        source_taxon = state._source_taxon_from_dict(self.root_taxon_dic)

        for key, value in self.root_taxon_dic.items():
            self.assertEqual(value, getattr(source_taxon, key))

    
    def test_set_current_root_taxon(self):
        state = TreeClimberState(JSONTreeTreeTaxon, self.dump_path)
        root_taxon = state._source_taxon_from_dict(self.root_taxon_dic)
        
        state.set_current_root_taxon(root_taxon)

        self.assertEqual(state.current_root_taxon, root_taxon)

    
    def test_set_last_parent(self):
        state = TreeClimberState(JSONTreeTreeTaxon, self.dump_path)
        taxon = state._source_taxon_from_dict(self.root_taxon_dic)
        
        state.set_last_parent(taxon)

        self.assertEqual(state.last_parent, taxon)

    def test_set_last_saved_child(self):
        state = TreeClimberState(JSONTreeTreeTaxon, self.dump_path)
        taxon = state._source_taxon_from_dict(self.root_taxon_dic)
        
        state.set_last_saved_child(taxon)

        self.assertEqual(state.last_saved_child, taxon)


    def perform_dump(self):
        state = TreeClimberState(JSONTreeTreeTaxon, self.dump_path)

        state.set_current_root_taxon(self.taxon_3)
        state.set_last_parent(self.taxon_1)
        state.set_last_saved_child(self.taxon_2)

        state.dump()

        return state


    def test_dump(self):
        state = self.perform_dump()

        with open(state.dump_filepath, 'r') as f:
            state_json = json.load(f)

        self.assertIn('timestamp', state_json)

        taxon_map = {
            'current_root_taxon' : self.taxon_3,
            'last_parent' : self.taxon_1,
            'last_saved_child' : self.taxon_2,
        }

        for taxon_dic_key in ['current_root_taxon', 'last_parent', 'last_saved_child']:
            self.assertIn(taxon_dic_key, state_json)

            dic = state_json[taxon_dic_key]

            for key, value in dic.items():
                self.assertEqual(value, getattr(taxon_map[taxon_dic_key], key))
        
        
    def test_load_last_state(self):
        state_ = self.perform_dump()

        # create independant state
        state = TreeClimberState(JSONTreeTreeTaxon, self.dump_path)

        # read the dump
        state.load_last_state()

        taxon_map = {
            'current_root_taxon' : self.taxon_3,
            'last_parent' : self.taxon_1,
            'last_saved_child' : self.taxon_2,
        }

        for key, taxon in taxon_map.items():

            check_taxon = getattr(state, key)

            # source_object attribute differs
            for attr in ['latname', 'author', 'rank', 'source', 'source_id', 'kwargs', 'nuid', 'rank_map']:

                self.assertEqual(getattr(taxon, attr), getattr(check_taxon, attr))



'''
    Assuming that the JSONTreeManager does what it is expected to do, test the TaxonSourceManager
'''

class TaxonSourceManagerTest(TestCase, DatabaseHelpers):

    def setUp(self):
        self.treemanager = JSONTreeManager(tree_1)
        self.treemanager_2 = JSONTreeManager(tree_2)

    def tearDown(self):
        global ACTIVE_TREE
        global ACTIVE_TREE_NAME
        
        ACTIVE_TREE = tree_1
        ACTIVE_TREE_NAME = 'tree_1'
        
        self.treemanager.TaxonTreeModel.objects.all().delete()
        self.treemanager.TaxonSynonymModel.objects.all().delete()
        self.treemanager.TaxonLocaleModel.objects.all().delete()
    
    def test_save_new_taxon(self):
        latname = 'B.A.A' 
        source_taxon = self.treemanager._get_jsontree_taxon_by_latname(latname)
        source_taxon.set_nuid(latname_to_nuid(latname))
        self.treemanager._save_new_taxon(source_taxon)

        query = self.treemanager.TaxonTreeModel.objects.filter(taxon_latname = source_taxon.latname)

        self.assertTrue(query.exists())
        self.assertEqual(query.count(), 1)

        db_taxon = query.first()

        self.assertEqual(db_taxon.taxon_latname, source_taxon.latname)
        self.assertEqual(db_taxon.taxon_nuid, source_taxon.nuid)
        self.assertEqual(db_taxon.author, source_taxon.author)
        self.assertEqual(db_taxon.source_id, source_taxon.source_id)

        # test the 2 synonyms and the 2 vernacular names
        synonyms = self.treemanager.TaxonSynonymModel.objects.filter(taxon=db_taxon)

        self.assertEqual(synonyms.count(), 2)

        synonym_latnames = list(synonyms.values_list('taxon_latname', flat=True))

        self.assertIn('syno1', synonym_latnames)
        self.assertIn('syno2', synonym_latnames)

        vernacular_names = self.treemanager.TaxonLocaleModel.objects.filter(taxon=db_taxon)

        self.assertEqual(vernacular_names.count(), 2)
        
        v_latnames = list(vernacular_names.values_list('name', flat=True))

        self.assertIn('de002001001', v_latnames)
        self.assertIn('en002001001', v_latnames)

    
    def _test_check_existing_taxon_synonyms(self, latname):
        global ACTIVE_TREE
        global ACTIVE_TREE_NAME
        
        source_taxon = self._create_lc_db_taxon(latname)

        # now, create a new source taxon from tree_2
        existing_taxon = self.treemanager.TaxonTreeModel.objects.get(taxon_latname=latname)

        existing_synonyms = self.treemanager.TaxonSynonymModel.objects.filter(taxon=existing_taxon)
        self.assertEqual(existing_synonyms.count(), len(synonyms_1[latname]))

        source_taxon_updated = self.treemanager_2._get_jsontree_taxon_by_latname(latname)

        # switch to the new tree
        ACTIVE_TREE = tree_2
        ACTIVE_TREE_NAME = 'tree_2'
        self.treemanager_2._check_existing_taxon_synonyms(existing_taxon, source_taxon_updated)

        # check if it has been deleted
        syno_query = self.treemanager.TaxonSynonymModel.objects.all()

        self.assertEqual(syno_query.count(), len(synonyms_2[latname]))

    
    def test_check_existing_taxon_synonyms_simple(self):
        self._test_check_existing_taxon_synonyms('B.A.A')
        

    def test_check_existing_taxon_synonyms_simple2(self):
        self._test_check_existing_taxon_synonyms('B.A')

    
    def _test_check_existing_taxon_vernacular_names(self, latname):
        global ACTIVE_TREE
        global ACTIVE_TREE_NAME

        source_taxon = self._create_lc_db_taxon(latname)

        v_query = self.treemanager.TaxonLocaleModel.objects.filter(taxon__taxon_latname=latname)
        self.assertEqual(v_query.count(), len(vernacular_1[latname]))

        # now, create a new source taxon from tree_2
        existing_taxon = self.treemanager.TaxonTreeModel.objects.get(taxon_latname=latname)

        existing_vernaculars = self.treemanager.TaxonLocaleModel.objects.filter(taxon=existing_taxon)
        self.assertEqual(existing_vernaculars.count(), len(vernacular_1[latname]))

        source_taxon_updated = self.treemanager_2._get_jsontree_taxon_by_latname(latname)

        # switch to the new tree
        ACTIVE_TREE = tree_2
        ACTIVE_TREE_NAME = 'tree_2'
        self.treemanager_2._check_existing_taxon_vernacular_names(existing_taxon, source_taxon_updated)

        # check if it has been deleted
        v_query = self.treemanager.TaxonLocaleModel.objects.filter(taxon=existing_taxon)

        self.assertEqual(v_query.count(), len(vernacular_2[latname]))
        
    
    def test_check_existing_taxon_vernacular_names_simple(self):
        self._test_check_existing_taxon_vernacular_names('B.A.A')

    def test_check_existing_taxon_vernacular_names_complex(self):
        self._test_check_existing_taxon_vernacular_names('B.A.B')

    
    # also check nuids
    def test_compare_new_children_with_existing_children_all_new(self):
        self._prepare_database('A.B')
        source_taxon = self.treemanager._get_jsontree_taxon_by_latname('A.B')
        children = self.treemanager._get_children(source_taxon)

        new_children = self.treemanager._compare_new_children_with_existing_children(children, source_taxon)

        self.assertEqual(new_children, children)

        self.assertEqual(new_children[0].nuid, '001002001')
        self.assertEqual(new_children[1].nuid, '001002002')
        self.assertEqual(new_children[2].nuid, '001002003')
        self.assertEqual(new_children[3].nuid, '001002004')

    
    # also check nuids
    def test_compare_new_children_with_existing_children_new_child(self):
        self._prepare_database('A.B')
        # these 4 exist in the tree
        taxon_1 = self._create_lc_db_taxon('A.B.A')
        taxon_2 = self._create_lc_db_taxon('A.B.B')
        taxon_3 = self._create_lc_db_taxon('A.B.C')
        taxon_4 = self._create_lc_db_taxon('A.B.D')

        old_children = [taxon_1, taxon_2, taxon_3, taxon_4]

        children = old_children[:] # shallow copy

        # add one new child, not existing in db -> it should add only this
        latname = 'A.B.E'
        taxon_5 = JSONTreeTreeTaxon(
            latname, 'author', 'rank', 'testjson', latname
        )


        # children contain 4 which are already in db and one new
        children.append(taxon_5)

        parent_taxon = self.treemanager._get_jsontree_taxon_by_latname('A.B')
        # set the nuid - normally done by TreeManager during downclimb
        parent_taxon.set_nuid('001002')
        
        new_children = self.treemanager._compare_new_children_with_existing_children(children, parent_taxon)

        self.assertEqual(len(new_children), 1)
        self.assertEqual(new_children[0], taxon_5)
        self.assertEqual(new_children[0].latname, 'A.B.E')
        # check if the nuid has been assigned properly
        self.assertEqual(new_children[0].nuid, '001002005')

    def test_compare_new_children_with_existing_children_new_child_nuid_continuation(self):
        self._prepare_database('A.B')
        # these 2 exist in the tree
        taxon_1 = self._create_lc_db_taxon('A.B.A')
        taxon_4 = self._create_lc_db_taxon('A.B.D')

        old_children = [taxon_1, taxon_4]

        children = old_children[:] # shallow copy

        # add one new child, not existing in db -> it should add only this
        taxon_5 = self.treemanager._get_jsontree_taxon_by_latname('A.B.E')


        # children contain 4 which are already in db and one new
        children.append(taxon_5)

        parent_taxon = self.treemanager._get_jsontree_taxon_by_latname('A.B')
        # set the nuid - normally done by TreeManager during downclimb
        parent_taxon.set_nuid('001002')
        
        new_children = self.treemanager._compare_new_children_with_existing_children(children, parent_taxon)

        self.assertEqual(len(new_children), 1)
        self.assertEqual(new_children[0], taxon_5)
        self.assertEqual(new_children[0].latname, 'A.B.E')
        # check if the nuid has been assigned properly
        self.assertEqual(new_children[0].nuid, '001002005')

    
    # no new nuids are created
    def test_compare_new_children_with_existing_children_delete_old(self):
        self._prepare_database('A.B')
        # add existing taxa
        taxon_1 = self._create_lc_db_taxon('A.B.A')
        taxon_2 = self._create_lc_db_taxon('A.B.B')
        taxon_3 = self._create_lc_db_taxon('A.B.C')
        taxon_4 = self._create_lc_db_taxon('A.B.D')

        db_children = [taxon_1, taxon_2, taxon_3, taxon_4]

        children = db_children[:-3]

        # add parent to tree
        parent_taxon = self.treemanager._get_jsontree_taxon_by_latname('A.B')
        parent_taxon.set_nuid('001002')
        
        new_children = self.treemanager._compare_new_children_with_existing_children(children, parent_taxon)

        self.assertEqual(len(new_children),0)

        db_query = self.treemanager.TaxonTreeModel.objects.filter(taxon_nuid__startswith='001002').exclude(
            taxon_nuid='001002')

        self.assertEqual(db_query.count(), 1)

        db_child = db_query.first()

        self.assertEqual(taxon_1.latname, db_child.taxon_latname)
        
    
    # also check nuids
    def test_compare_new_children_with_old_children_compared(self):
        self._prepare_database('A.B')
        # test all functions at once:
        # - some exist
        # - some are new
        # - some are removed

        # db_taxa:
        taxon_1 = self._create_lc_db_taxon('A.B.A')
        taxon_2 = self._create_lc_db_taxon('A.B.B')

        db_children = [taxon_1, taxon_2]

        # taxon_1 will be removed
        # taxon_3 will be added (new_children, not db)
        # taxon_2 stays

        taxon_3 = self.treemanager._get_jsontree_taxon_by_latname('A.B.C')
        self.assertEqual(taxon_3.nuid, None)
        children = [taxon_2, taxon_3]


        parent_taxon = self.treemanager._get_jsontree_taxon_by_latname('A.B')
        parent_taxon.set_nuid('001002')

        # now, all nuids are set
        new_children = self.treemanager._compare_new_children_with_existing_children(children, parent_taxon)

        self.assertEqual(len(new_children), 1)

        self.assertEqual(new_children[0], taxon_3)
        self.assertEqual(new_children[0].nuid, '001002003')

        db_query = self.treemanager.TaxonTreeModel.objects.filter(taxon_nuid__startswith='001002').exclude(
            taxon_nuid='001002')

        self.assertEqual(db_query.count(), 1)

        db_taxon = db_query.first()
        self.assertEqual(db_taxon.taxon_latname, taxon_2.latname)

    
    # test nuids
    def test_compare_new_children_with_old_children_compared_2(self):
        self._prepare_database('A.B')
        # db_taxa:
        taxon_1 = self._create_lc_db_taxon('A.B.A')
        taxon_2 = self._create_lc_db_taxon('A.B.B')

        db_children = [taxon_1, taxon_2]

        # taxon_1 stays
        # taxon_3 will be added (new_children, not db)
        # taxon_2 will be removed

        taxon_3 = self.treemanager._get_jsontree_taxon_by_latname('A.B.C')
        children = [taxon_1, taxon_3]

        parent_taxon = self.treemanager._get_jsontree_taxon_by_latname('A.B')
        parent_taxon.set_nuid('001002')

        # now nuids are set
        new_children = self.treemanager._compare_new_children_with_existing_children(children, parent_taxon)

        self.assertEqual(len(new_children), 1)

        self.assertEqual(new_children[0], taxon_3)
        # the remaining taxon has the nuid '001002001' -> next is '001002002'
        self.assertEqual(new_children[0].nuid, '001002002')

        db_query = self.treemanager.TaxonTreeModel.objects.filter(taxon_nuid__startswith='001002').exclude(
            taxon_nuid='001002')

        self.assertEqual(db_query.count(), 1)

        db_taxon = db_query.first()
        self.assertEqual(db_taxon.taxon_latname, taxon_1.latname)

    
    def test_compare_new_children_with_existing_children_root_taxa_all_new(self):

        children = self.treemanager._get_root_source_taxa()

        new_children = self.treemanager._compare_new_children_with_existing_children(children)

        self.assertEqual(new_children, children)

        self.assertEqual(new_children[0].nuid, '001')
        self.assertEqual(new_children[1].nuid, '002')
        self.assertEqual(new_children[2].nuid, '003')

    
    def test_compare_new_children_with_existing_children_same_latname_different_author(self):
        self._prepare_database('A.B')
        parent_taxon = self.treemanager._get_jsontree_taxon_by_latname('A.B')
        parent_taxon.set_nuid('001002')

        latname_1 = 'A.B.A'
        child_1 = JSONTreeTreeTaxon(
            latname_1, 'author_1', 'rank', 'testjson', latname_1
        )

        child_2 = JSONTreeTreeTaxon(
            latname_1, 'author_2', 'rank', 'testjson', 'different source_id'
        )

        children = [child_1, child_2]

        new_children = self.treemanager._compare_new_children_with_existing_children(children, parent_taxon)

        for child in new_children:
            self.treemanager._save_new_taxon(child)

        # check
        db_query = self.treemanager.TaxonTreeModel.objects.filter(taxon_nuid__startswith='001002').exclude(
            taxon_nuid='001002').order_by('author')
        self.assertEqual(db_query.count(),2)
        self.assertEqual(db_query[0].taxon_latname, latname_1)
        self.assertEqual(db_query[0].author, 'author_1')

        self.assertEqual(db_query[1].taxon_latname, latname_1)
        self.assertEqual(db_query[1].author, 'author_2')

    
    def test_get_next_downclimb_taxon(self):
        # upclimb needs db entries -> save the necessary db entry (done by _prepare_database)
        self._prepare_database('A.B.B.A.A')

        
        # 'A.B.B.A.A' -> next: 'A.B.C', bcause '001002002' and 'A.B.A' have no children
        latname = 'A.B.B.A.A'
        source_taxon = self.treemanager._get_jsontree_taxon_by_latname(latname)

        # prepare the cache
        parent_taxon = self.treemanager._get_jsontree_taxon_by_latname('A.B.B.A')
        self.treemanager.cache.add(parent_taxon, [source_taxon])

        # perform the tests
        next_latname = 'A.B.C'
        expected_next_taxon = self.treemanager._get_jsontree_taxon_by_latname(next_latname)
        expected_next_taxon.set_nuid(latname_to_nuid(next_latname))
        
        next_taxon = self.treemanager.cache.get_next_downclimb_taxon(source_taxon)

        self.assertEqual(next_taxon.nuid, expected_next_taxon.nuid)
        self.assertEqual(next_taxon.get_source_object(), expected_next_taxon.get_source_object())


        # empty child, but sibling has descendants
        # 001002001 has no children
        # 001002002 has children
        final_node = self.treemanager._get_jsontree_taxon_by_latname('A.B.A')
        expected_taxon = self.treemanager._get_jsontree_taxon_by_latname('A.B.B')
        expected_taxon.set_nuid(latname_to_nuid(('A.B.B')))
        next_taxon = self.treemanager.cache.get_next_downclimb_taxon(final_node)
        self.assertEqual(next_taxon.nuid, expected_taxon.nuid)

        # the none
        # first put missing elements in the db, do not use prepare_database again, C already has been added
        source_taxon = self._create_lc_db_taxon('C.A')
        parent_taxon = self.treemanager._get_jsontree_taxon_by_latname('C')

        # prepare the cache
        self.assertEqual(len(self.treemanager.cache.cache[0]['children']), 3)
        
        self.treemanager.cache.add(parent_taxon, [source_taxon])

        self.assertEqual(len(self.treemanager.cache.cache[0]['children']), 3)
        self.assertEqual(len(self.treemanager.cache.cache[1]['children']), 1)

        # first, C.A has no siblings
        # second, C.A has C as parent
        # third, C has no sibling and no parent_taxon
        next_taxon = self.treemanager.cache.get_next_downclimb_taxon(source_taxon)
        self.assertEqual(next_taxon, None)
        
    
    # climb_down does not set the current root taxon, needs to be set manually
    def test_climb_down(self):
        
        parent_taxon = self.treemanager._get_jsontree_taxon_by_latname('B')
        parent_taxon.set_nuid('002')

        self.treemanager.state.set_current_root_taxon(parent_taxon)

        # first child of last group of children
        first_child = self.treemanager._climb_down(parent_taxon)

        self.assertEqual(first_child.nuid, '002001001')

        # expected taxa in db: 'B.A', 'B.B', '002001001', 'B.A.B'
        db_query = self.treemanager.TaxonTreeModel.objects.all().order_by('taxon_nuid')

        self.assertEqual(db_query.count(), 4)

        self.assertEqual(db_query[0].taxon_nuid, '002001')
        self.assertEqual(db_query[1].taxon_nuid, '002001001')
        self.assertEqual(db_query[2].taxon_nuid, '002001002')

        self.assertEqual(db_query[3].taxon_nuid, '002002')

        # also check the dump file

        self.treemanager.state.load_last_state()
        self.assertEqual(self.treemanager.state.last_saved_child.latname, 'B.A.B')
        self.assertEqual(self.treemanager.state.current_root_taxon.latname, 'B')
        # _climb_down sets a new last_parent if the node has children
        self.assertEqual(self.treemanager.state.last_parent.latname, 'B.A')
        
    
    def _test_tree_completion(self, nuidtree_name):
        db_query = self.treemanager.TaxonTreeModel.objects.all().order_by('taxon_nuid')

        entry_count = trees[nuidtree_name]['entry_count']
        latnames = trees[nuidtree_name]['latnames']

        tree_latnames_set = set(latnames)
        self.assertEqual(tree_latnames_set, set(list(db_query.values_list('taxon_latname', flat=True))))

        self.assertEqual(db_query.count(), entry_count)

        # check synonyms
        synoquery = self.treemanager.TaxonSynonymModel.objects.all()

        self.assertEqual(set(synoquery.values_list('taxon_latname', flat=True)), set(trees[nuidtree_name]['synonym_latnames']))
        self.assertEqual(synoquery.count(), trees[nuidtree_name]['synonym_count'])

        # check vernacular names
        vernquery = self.treemanager.TaxonLocaleModel.objects.all()

        self.assertEqual(vernquery.count(), trees[nuidtree_name]['vernacular_count'])

    
    def test_update_database_new_database(self):
        
        # full run
        
        self.treemanager.update_database()

        self._test_tree_completion('tree_1')


     
    def test_resume(self):

        # break at taxon 'A.B.A'

        installed = ['A', 'B', 'C', # root taxa are saved before 'working iteration'
            'A.A', 'A.B', 'A.C',
            'A.A.A', 'A.A.B',
            'A.B.A',
        ]

        for nuid in installed:
            taxon = self._create_lc_db_taxon(nuid)

        # set the correct state
        root_taxon = self.treemanager._get_jsontree_taxon_by_latname('A')
        self.treemanager.state.set_current_root_taxon(root_taxon)
        
        last_parent = self.treemanager._get_jsontree_taxon_by_latname('A.B')
        self.treemanager.state.set_last_parent(last_parent)

        last_saved_child = self.treemanager._get_jsontree_taxon_by_latname('A.B.A')
        self.treemanager.state.set_last_saved_child(last_saved_child)

        self.treemanager.state.dump()

        self.treemanager.resume()

        self._test_tree_completion('tree_1')

    
    def test_update_existing_database_with_new_database(self):

        global ACTIVE_TREE
        global ACTIVE_TREE_NAME
        
        self.treemanager.update_database()

        update_treemanager = JSONTreeManager(tree_2)

        ACTIVE_TREE = tree_2
        ACTIVE_TREE_NAME = 'tree_2'
        update_treemanager.update_database()

        self._test_tree_completion('tree_2')


    def test_first_run(self):
        self.treemanager.first_run = True
        self.treemanager.update_database()

        self._test_tree_completion('tree_1')

