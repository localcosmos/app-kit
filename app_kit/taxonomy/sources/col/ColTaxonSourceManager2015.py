from taxonomy.sources.TaxonSourceManager import (TaxonSourceManager, SourceTreeTaxon,
                                    SourceSynonymTaxon, VernacularName, TreeCache)

from taxonomy.sources.col.models import ColTaxonTree, ColTaxonSynonym, ColTaxonLocale

'''
    the CoL2015 uses language_codes with 3 letters -> create a dict
'''

import pymysql, os, csv

try:
    from html.parser import HTMLParser
except:
    from HTMLParser import HTMLParser
    
LANGUAGE_DICT = {}

dir_path = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(dir_path, 'countrycodes.csv'), 'r') as csvfile:
    spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
    for row in spamreader:
        LANGUAGE_DICT[row[3].lower()] = row[4].lower()

'''
    db interface for col db
'''


colCon = pymysql.connect(host='127.0.0.1', port=3306, user='root', passwd='ubuntu', db='col2015ac', charset='utf8')
colCursor = colCon.cursor(pymysql.cursors.DictCursor)


MAPPED_TAXON_RANKS = {
    "subsp" : "subspecies",
    "sub-variety" : "subvariety",
}

SOURCE_NAME = 'col2015'


class ColSourceTreeTaxon(SourceTreeTaxon):

    TreeModel = ColTaxonTree

    def _get_source_object(self):
        
        # return a db_taxon instance
        colCursor.execute("SELECT * FROM col2015ac._taxon_tree where taxon_id=%s", [self.source_id])
        db_taxon = colCursor.fetchone()
        
        return db_taxon

    # return VernacularName[]
    def _get_vernacular_names(self):

        vernquery = colCursor.execute('''SELECT * FROM common_name c
                        LEFT JOIN common_name_element e ON (c.common_name_element_id = e.id)
                        WHERE c.taxon_id=%s''', [self.source_id])

        vernacular_names_db = colCursor.fetchall()

        vernacular_names = []

        exists = False
        
        for db_name in vernacular_names_db:

            name = db_name['name']                
            
            iso = db_name['language_iso']

            if iso is not None:
                iso = iso.lower()

                language = LANGUAGE_DICT.get(iso,iso[:2])

                # avoid duplicates
                for v_name in vernacular_names:
                    if name == v_name.name and language == v_name.language:
                        exists = True
                        break

                if exists == True:
                    exists = False
                    continue
                
                vernacular_name = VernacularName(
                    name,
                    language,
                )

                vernacular_names.append(vernacular_name)
        
        return vernacular_names
        

    # return SourceTaxon[]
    # use _search_all for synonyms
    def _get_synonyms(self):
        # only do this for species becuase of col's way of handling this

        
        synonyms_query = colCursor.execute('''SELECT * FROM col2015ac._search_all
                        WHERE accepted_taxon_id=%s AND name_status=5;''', [self.source_id])

        synonyms = []

        synonyms_db = colCursor.fetchall()

        used_latnames = []
        
        for db_taxon in synonyms_db:
            
            if db_taxon['name'] in used_latnames:
                continue

            used_latnames.append(db_taxon['name'])
                
            synonym = ColSourceSynonymTaxon(
                db_taxon['name'], db_taxon['name_suffix'], db_taxon['rank'], SOURCE_NAME, db_taxon['id']
            )

            synonyms.append(synonym)

        return synonyms


class ColSourceSynonymTaxon(SourceSynonymTaxon):
    pass


class ColTreeCache(TreeCache):

    SourceTreeTaxonClass = ColSourceTreeTaxon
    TaxonTreeModel = ColTaxonTree
    
    def _make_source_taxon(self, db_taxon):
        return ColSourceTreeTaxon(
            db_taxon.taxon_latname, db_taxon.author, db_taxon.rank, 'ColTaxonTree', db_taxon.source_id,
            nuid = db_taxon.taxon_nuid
        )

class ColTaxonSourceManager(TaxonSourceManager):

    SourceTreeTaxonClass = ColSourceTreeTaxon
    SourceSynonymTaxonClass = ColSourceSynonymTaxon
    
    TaxonTreeModel = ColTaxonTree
    TaxonSynonymModel = ColTaxonSynonym
    TaxonLocaleModel = ColTaxonLocale

    TreeCacheClass = ColTreeCache

    '''
    author sits in different table
    '''
    def _get_author(self, db_taxon):
        
        author_string = None

        colCursor.execute("SELECT * FROM col2015ac.taxon_detail WHERE taxon_id=%s",[db_taxon['taxon_id']])

        taxon = colCursor.fetchone()

        if taxon is not None:

            colCursor.execute("SELECT * FROM col2015ac.author_string WHERE id=%s",[taxon["author_string_id"]])
            
            author = colCursor.fetchone()

            if author is not None:

                #some are html encoded - check for this

                author_string = author["string"]

                h = HTMLParser()

                author_string = h.unescape(author_string)

        return author_string

    def _sourcetaxon_from_db_taxon(self, db_taxon):

        source_taxon = self.SourceTreeTaxonClass(
            db_taxon['name'],
            self._get_author(db_taxon),
            db_taxon['rank'],
            SOURCE_NAME,
            db_taxon['taxon_id'],
        )

        return source_taxon

    # return a lust of SourceTreeTaxonClass instances
    def _get_root_source_taxa(self):

        root_taxa = []
        
        colCursor.execute("SELECT * FROM col2015ac._taxon_tree where rank='kingdom' ORDER BY name")

        kingdoms = colCursor.fetchall()

        for taxon in kingdoms:
            root_taxa.append(self._sourcetaxon_from_db_taxon(taxon))

        return root_taxa

    def _get_children(self, source_taxon):

        children = []

        children_query = colCursor.execute("SELECT * FROM col2015ac._taxon_tree where parent_id=%s ORDER BY name",
                                           [source_taxon.source_id])

        db_children = colCursor.fetchall()
        for child in db_children:
            source_taxon = self._sourcetaxon_from_db_taxon(child)
            children.append(source_taxon)
        
        return children


    # return SourceTaxon or None, next sibling in alphabetical order
    def _get_next_sibling(self, source_taxon):

        sibling = None

        # get all siblings of current taxon from db
        siblings_query = colCursor.execute("SELECT * FROM col2015ac._taxon_tree where parent_id=%s ORDER BY name",
                                           [source_taxon.get_source_object()['parent_id']])

        siblings = colCursor.fetchall()

        next_sibling_db = None
        
        for db_taxon in siblings:
            
            if db_taxon['taxon_id'] == int(source_taxon.source_id):

                # if the match is not the last entry of siblings assign sibling
                if not siblings.index(db_taxon) == (len(siblings) - 1):
                    next_sibling_db = siblings[siblings.index(db_taxon) + 1]
                    
                break

        if next_sibling_db is not None:
            
            sibling = self._sourcetaxon_from_db_taxon(next_sibling_db)

        return sibling

    # travel one up
    def _get_parent(self, source_taxon):

        parent = None
        
        parent_query = colCursor.execute("SELECT * FROM col2015ac._taxon_tree WHERE taxon_id=%s ORDER BY name",
                                           [source_taxon.get_source_object()['parent_id']])

        db_parent = colCursor.fetchone()

        if db_parent:
            parent = self._sourcetaxon_from_db_taxon(db_parent)

        return parent


def compare():

    limit = 10000
    offset = 0

    source_query = 'SELECT * FROM col2015ac._taxon_tree LIMIT %s OFFSET %s' %(limit, offset)
    colCursor.execute(source_query)
    taxa = colCursor.fetchall()

    while taxa:

        for taxon in taxa:
            if not ColTaxonTree.objects.filter(source_id=taxon['taxon_id']).exists():
                print('missing: %s' % taxon['taxon_id'])

        offset += limit
        source_query = 'SELECT * FROM col2015ac._taxon_tree LIMIT %s OFFSET %s' %(limit, offset)
        colCursor.execute(source_query)
        taxa = colCursor.fetchall()
