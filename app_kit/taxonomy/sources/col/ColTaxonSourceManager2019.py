####################################################################################################################
#
#   IMPORT CATALOGUE OF LIFE 2019
#
####################################################################################################################

from taxonomy.sources.TaxonSourceManager import (TaxonSourceManager, SourceTreeTaxon,
                                    SourceSynonymTaxon, VernacularName, TreeCache)

from taxonomy.sources.col.models import ColTaxonTree, ColTaxonSynonym, ColTaxonLocale

import psycopg2, psycopg2.extras, os, csv

from html.parser import HTMLParser



# the CoL2019 uses language names like "English" -> use langcodes
import langcodes

DEBUG = False

'''
    db interface for col 2019 postgres db
'''


colCon = psycopg2.connect(dbname="col2019", user="localcosmos", password="localcosmos", host="localhost", port="5432")
colCursor = colCon.cursor(cursor_factory = psycopg2.extras.DictCursor)


MAPPED_TAXON_RANKS = {
    "subsp" : "subspecies",
    "sub-variety" : "subvariety",
}

SOURCE_NAME = 'col2019'

RANKS = ['kingdom', 'phylum', 'class', 'order', 'superfamily', 'family', 'genus', 'species', 'infraspecies'] 


class ColSourceTreeTaxon(SourceTreeTaxon):

    TreeModel = ColTaxonTree

    def _get_source_object(self):
        
        # return a db_taxon instance
        colCursor.execute('''SELECT * FROM taxon where "taxonID"=%s''', [self.source_id])
        db_taxon = colCursor.fetchone()
        
        return db_taxon
        

    # return VernacularName[]
    def _get_vernacular_names(self):

        colCursor.execute('''SELECT * FROM vernacular WHERE "taxonID"=%s''', [self.source_id])

        vernacular_names_db = colCursor.fetchall()

        vernacular_names = []

        exists = False
        
        for db_name in vernacular_names_db:

            name = db_name['vernacularName']                
            
            language_fuzzy = db_name['language']

            if language_fuzzy:

                iso6391 = None
                iso6392 = None

                language_obj = None


                try:
                    language_obj = langcodes.find(language_fuzzy)

                    if language_obj and len(str(language_obj)) == 2:
                        iso6391 = str(language_obj)
                        
                except LookupError:
                    if len(language_fuzzy) in [2,3]:
                        language_obj = langcodes.Language.get(language_fuzzy)

                        if language_obj and len(str(language_obj)) == 2:
                            iso6391 = str(language_obj)


                if len(language_fuzzy) == 3:
                    iso6392 = language_fuzzy.lower()
                        
                    
                if iso6391 is not None:

                    language = iso6391

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
                        iso6392=iso6392,
                    )

                    vernacular_names.append(vernacular_name)
        
        return vernacular_names

    @classmethod
    def get_scientific_name(cls, db_taxon):

        taxon_rank = db_taxon['taxonRank']

        is_species_or_below = RANKS.index(taxon_rank) >= RANKS.index('species')

        if is_species_or_below:

            infraspecific_epithet = db_taxon['infraspecificEpithet']

            scientific_name = '{0} {1}'.format(db_taxon['genus'], db_taxon['specificEpithet'])

            if infraspecific_epithet:
                scientific_name = '{0} {1}'.format(scientific_name, infraspecific_epithet)
            
            scientific_name = scientific_name.strip()

        else:
            scientific_name = db_taxon[taxon_rank]

        return scientific_name
    

    # return SourceTaxon[]
    # use _search_all for synonyms
    def _get_synonyms(self):
        # only do this for species becuase of col's way of handling this
        
        synonyms_query = colCursor.execute('''SELECT * FROM taxon
                        WHERE "acceptedNameUsageID"=%s AND "taxonomicStatus" IN ('synonym', 'ambiguous synonym');''',
                                           [self.source_id])

        synonyms = []

        synonyms_db = colCursor.fetchall()

        used_latnames = []
        
        for db_taxon in synonyms_db:

            taxon_name = self.get_scientific_name(db_taxon)
            
            if taxon_name in used_latnames:
                continue

            used_latnames.append(taxon_name)
                
            synonym = ColSourceSynonymTaxon(
                taxon_name, db_taxon['scientificNameAuthorship'], db_taxon['taxonRank'], SOURCE_NAME,
                db_taxon['taxonID']
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
        
        author_string = db_taxon['scientificNameAuthorship']

        if author_string is not None:

            h = HTMLParser()

            author_string = h.unescape(author_string)

        return author_string
    

    def _sourcetaxon_from_db_taxon(self, db_taxon):

        taxon_name = ColSourceTreeTaxon.get_scientific_name(db_taxon)

        source_taxon = self.SourceTreeTaxonClass(
            taxon_name,
            self._get_author(db_taxon),
            db_taxon['taxonRank'],
            SOURCE_NAME,
            db_taxon['taxonID'],
        )

        return source_taxon
        

    # return a lust of SourceTreeTaxonClass instances
    def _get_root_source_taxa(self):

        root_taxa = []
        
        colCursor.execute('''SELECT * FROM taxon where "taxonRank"='kingdom' ORDER BY "scientificName" ''')

        kingdoms = colCursor.fetchall()

        for taxon in kingdoms:
            root_taxa.append(self._sourcetaxon_from_db_taxon(taxon))

        return root_taxa


    def _get_children(self, source_taxon):

        if DEBUG == True:
            print('_get_children for %s start' %(source_taxon.latname))

        children = []
        
        colCursor.execute('''SELECT * FROM taxon WHERE "parentNameUsageID" = %s AND ("taxonomicStatus" IS NULL OR "taxonomicStatus" = 'accepted name' OR "taxonomicStatus" = 'provisionally accepted name') ORDER BY "scientificName" ASC, "taxonomicStatus" ASC ''',
                          [source_taxon.source_id,])

        db_children = colCursor.fetchall()
        for child in db_children:
            source_taxon = self._sourcetaxon_from_db_taxon(child)
            children.append(source_taxon)


        if DEBUG == True:
            print('_get_children end')
        
        return children


    # return SourceTaxon or None, next sibling in alphabetical order
    def _get_next_sibling(self, source_taxon):

        if DEBUG == True:
            print('_get_next_sibling start')

        sibling = None

        parent_taxon = self._get_parent(source_taxon)

        # get all siblings of current taxon from db
        siblings = self._get_children(parent_taxon)

        
        for source_sibling_taxon in siblings:
            
            if int(source_sibling_taxon) == int(source_taxon.source_id):

                # if the match is not the last entry of siblings assign sibling
                if not siblings.index(source_sibling_taxon) == (len(siblings) - 1):
                    sibling = siblings[siblings.index(source_sibling_taxon) + 1]
                    
                break

        if DEBUG == True:
            print('_get_next_sibling end, found {0}'.format(sibling.latname))

        return sibling


        
    # travel one up
    def _get_parent(self, source_taxon):

        if DEBUG == True:
            print('_get_parent start')

        parent = None

        db_taxon = source_taxon._get_source_object()

        colCursor.execute('''SELECT * FROM taxon WHERE "taxonID" = %s ''',
                          [db_taxon['parentNameUsageID'],])

        db_parent = colCursor.fetchone()
  
        if db_parent:
            parent = self._sourcetaxon_from_db_taxon(db_parent)


        if DEBUG == True:
            print('_get_parent end, found %s' %(parent.latname))

        return parent


def compare():

    limit = 10000
    offset = 0

    source_query = '''SELECT * FROM taxon WHERE "taxonomicStatus" IS NULL OR "taxonomicStatus" = 'accepted name' OR "taxonomicStatus" = 'provisionally accepted name' ORDER BY "taxonID" LIMIT %s OFFSET %s''' %(limit, offset)
    colCursor.execute(source_query)
    taxa = colCursor.fetchall()

    while taxa:

        for taxon in taxa:
            if not ColTaxonTree.objects.filter(source_id=taxon['taxonID']).exists():
                print('missing: %s %s (%s)' % (taxon['taxonID'], taxon['scientificName'], taxon['taxonRank']))

        offset += limit
        source_query = '''SELECT * FROM taxon WHERE "taxonomicStatus" IS NULL OR "taxonomicStatus" = 'accepted name' OR "taxonomicStatus" = 'provisionally accepted name' ORDER BY "taxonID" LIMIT %s OFFSET %s''' %(limit, offset)
        colCursor.execute(source_query)
        taxa = colCursor.fetchall()
