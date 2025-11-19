####################################################################################################################
#
#   IMPORT Algaebase
#
####################################################################################################################

# A: id
# B: genus
# C: species
# D: subspecies
# E: variety
# F: forma
# G: taxon authority (nomenclatural_authorities)
# H: year (year_of_publication)
# I: accepted_name_id (id_current_name)
# J: current_flag
# K: record_status
# L: phylum
# M: subphylum
# N: class
# O: order
# P: family
# Q: subfamiy
# R: tribe
# S: habitat
# T: Link
from taxonomy.sources.TaxonSourceManager import (TaxonSourceManager, SourceTreeTaxon, d2n, n2d,
                                    SourceSynonymTaxon, VernacularName, TreeCache)

from taxonomy.sources.algaebase.models import AlgaebaseTaxonTree, AlgaebaseTaxonSynonym, AlgaebaseTaxonLocale

import psycopg2, psycopg2.extras, os

import logging, csv

from django.db import transaction, connection, connections

DEBUG = False

# db interface for algaebase 2020 postgres db
algaebaseCon = psycopg2.connect(dbname="algaebase_2025", user="localcosmos", password="localcosmos",
                          host="localhost", port="5432")

algaebaseCursor = algaebaseCon.cursor(cursor_factory = psycopg2.extras.DictCursor)

# algaebase uses specific ranks as table columns
# no kingdom for algaebase
# the ranks are also column names
RANKS = ['phylum', 'subphylum', 'class', 'order', 'family', 'subfamily', 'tribe', 'genus',
         'species', 'subspecies', 'variety', 'forma']

LOWER_RANKS = ['species', 'subspecies', 'variety', 'forma']
HIGHER_RANKS = ['phylum', 'subphylum', 'class', 'order', 'family', 'subfamily', 'tribe', 'genus']

SKIPPABLE_RANKS = ['subphylum', 'subfamily', 'tribe', 'subspecies', 'variety']

RANK_MAP = {
    'S' : 'species',
    'U' : 'subspecies',
    'V' : 'variety',
    'F' : 'forma',
}

SOURCE_NAME = 'algaebase2025'

HIGHER_TAXA_PARENT_MAP = {}

# see https://www.iapt-taxon.org/nomen/pages/main/art_5.html
'''
For purposes of standardization, the following abbreviations are recommended:
cl. (class), ord. (order), fam. (family), tr. (tribe), gen. (genus), sect. (section), ser. (series),
sp. (species), var. (variety), f. (forma).
The abbreviations for additional ranks created by the addition of the prefix sub-,
or for nothotaxa with the prefix notho-, should be formed by adding the prefixes, e.g. subsp. (subspecies),
nothosp. (nothospecies), but subg. (subgenus) not “subgen.” 
'''
'''
Saxifraga aizoon subf. surculosa Engl. & Irmsch.
This taxon may also be referred to as
Saxifraga aizoon var. aizoon subvar. brevifolia f. multicaulis subf. surculosa Engl. & Irmsch.;
in this way a full classification of the subforma within the species is given, not only its name. 
'''
INFRASPECIFIC_ABBREVIATIONS = {
    'subspecies' : 'subsp.',
    'variety' : 'var.',
    'forma' : 'f.',
}

class AlgaebaseSourceTreeTaxon(SourceTreeTaxon):

    TreeModel = AlgaebaseTaxonTree

    # higher taxa are not db entries in algaebase
    # genus Chaetopia occurs in Heteropediaceae AND Radiococcaceae
    # _get_source_object should use both rank + name and parent_rank + parent_name
    def _get_source_object(self):
        
        if self.rank in HIGHER_RANKS:

            parent_sql = ''
            parent_rank_sql = ''
            
            if self.parent_name and self.parent_name != 'root':
                parent_sql = ''' AND "{0}" = '{1}' '''.format(self.parent_rank, self.parent_name)
                parent_rank_sql = ' , "{0}" '.format(self.parent_rank)

            sql = '''SELECT DISTINCT("{0}") {3} FROM taxa
                                    WHERE "{0}" = '{1}'
                                    {2}
                                    AND id_current_name IS NULL
                                    '''.format(self.rank, self.latname, parent_sql, parent_rank_sql)

            if DEBUG == True:
                print(sql)
                
            algaebaseCursor.execute(sql)

            db_taxon = algaebaseCursor.fetchone()

        else:

            # return a db_taxon instance
            algaebaseCursor.execute('''SELECT * FROM taxa where "id"=%s''', [self.source_id])
            db_taxon = algaebaseCursor.fetchone()
        
        return db_taxon

    # no vernacular names for algaebase
    def _get_vernacular_names(self):
        return []

    # there is a synonym chain: primary <- syno <- syno
    def _get_synonyms(self):

        synonyms = []

        used_latnames = []
        
        if self.rank in LOWER_RANKS:

            sql = '''SELECT * FROM taxa WHERE id_current_name = {0} '''.format(self.source_id)

            algaebaseCursor.execute(sql)

            db_synonyms = algaebaseCursor.fetchall()

            while db_synonyms:

                synonym_ids = []

                for db_taxon in db_synonyms:

                    synonym_ids.append(str(db_taxon['id']))

                    cleaned_taxon = {
                        'ids' : [db_taxon['id']],
                    }
                    for key, value in db_taxon.items():
                        cleaned_taxon[key] = value

                    synonym_rank = RANK_MAP[db_taxon['record_status']]
                    
                    taxon_name = self.get_scientific_name(db_taxon, synonym_rank)

                    author = AlgaebaseManager._get_author(cleaned_taxon, synonym_rank)

                    full_scientific_name = '{0} {1}'.format(taxon_name, author)
                    
                    if full_scientific_name in used_latnames:
                        continue

                    used_latnames.append(full_scientific_name)
                        
                    synonym = AlgaebaseSourceSynonymTaxon( taxon_name, author, synonym_rank, SOURCE_NAME,
                                                           db_taxon['id'])

                    synonyms.append(synonym)

                ids_str = ','.join(synonym_ids)
                sql = '''SELECT * FROM taxa WHERE id_current_name IN ({0}) '''.format(ids_str)
                
                algaebaseCursor.execute(sql)
                db_synonyms = algaebaseCursor.fetchall()
            
        return synonyms

    # respect, subgenus, subspecies, variety, form, and their abbreviations
    # scientific name without author
    @classmethod
    def get_scientific_name(cls, db_taxon, taxon_rank):

        if DEBUG == True:
            print('get scientific_name for {0} of {1}'.format(taxon_rank, db_taxon[taxon_rank]))

        # go from current rank upwards up to genus
        if taxon_rank in LOWER_RANKS:
            
            if taxon_rank == 'species':
                scientific_name = '{0} {1}'.format(db_taxon['genus'], db_taxon['species'])
            
            
            else:
                abbreviation = INFRASPECIFIC_ABBREVIATIONS[taxon_rank]
            
                if taxon_rank == 'subspecies':
                    
                    scientific_name = '{0} {1} {2} {3}'.format(db_taxon['genus'], db_taxon['species'],
                                                            abbreviation, db_taxon['subspecies'])
                
                elif taxon_rank == 'variety':
                    
                    scientific_name = '{0} {1}'.format(db_taxon['genus'], db_taxon['species'])
                    
                    if db_taxon['subspecies']:
                        scientific_name = '{0} subsp. {1}'.format(scientific_name, db_taxon['subspecies'])
                        
                    scientific_name = '{0} {1} {2}'.format(scientific_name, abbreviation, db_taxon['variety'])
                
                elif taxon_rank == 'forma':
                    scientific_name = '{0} {1}'.format(db_taxon['genus'], db_taxon['species'])
                    
                    if db_taxon['subspecies']:
                        scientific_name = '{0} subsp. {1}'.format(scientific_name, db_taxon['subspecies'])
                        
                    if db_taxon['variety']:
                        scientific_name = '{0} var. {1}'.format(scientific_name, db_taxon['variety'])
                        
                    scientific_name = '{0} {1} {2}'.format(scientific_name, abbreviation, db_taxon['forma'])
                
                else:
                    raise ValueError('invalid taxon_rank for scientific name: {0}'.format(taxon_rank))

        else:
            scientific_name = db_taxon[taxon_rank]
            
        return scientific_name


class AlgaebaseSourceSynonymTaxon(SourceSynonymTaxon):
    pass


class AlgaebaseTreeCache(TreeCache):

    SourceTreeTaxonClass = AlgaebaseSourceTreeTaxon
    TaxonTreeModel = AlgaebaseTaxonTree
    
    def _make_source_taxon(self, db_taxon):

        parent_taxon = db_taxon.parent
        parent_name = None
        parent_rank = None
        
        if parent_taxon:
            parent_name = parent_taxon.taxon_latname
            parent_rank = parent_taxon.rank
        
        return AlgaebaseSourceTreeTaxon(
            db_taxon.taxon_latname, db_taxon.taxon_author, db_taxon.rank, 'Algaebase', db_taxon.source_id,
            parent_name, parent_rank,
            nuid = db_taxon.taxon_nuid
        )
    

class AlgaebaseManager(TaxonSourceManager):

    SourceTreeTaxonClass = AlgaebaseSourceTreeTaxon
    SourceSynonymTaxonClass = AlgaebaseSourceSynonymTaxon
    
    TaxonTreeModel = AlgaebaseTaxonTree
    TaxonSynonymModel = AlgaebaseTaxonSynonym
    TaxonLocaleModel = AlgaebaseTaxonLocale

    TreeCacheClass = AlgaebaseTreeCache

    source_name = SOURCE_NAME

    # higher taxa might not have an id
    # parent_name is required because eg
    def _sourcetaxon_from_db_taxon(self, db_taxon, taxon_rank, parent_name, parent_rank):

        taxon_name = AlgaebaseSourceTreeTaxon.get_scientific_name(db_taxon, taxon_rank)

        author = self._get_author(db_taxon, taxon_rank)

        if taxon_rank in LOWER_RANKS:
            ids = list(db_taxon['ids'])
            if len(ids) > 1:
                print('found multiple ids for {0}'.format(taxon_name))
            taxon_id = ids[0]
            
        else:
            taxon_id = '{0}_{1}_{2}_{3}'.format(taxon_rank, taxon_name, parent_rank, parent_name)

        source_taxon = self.SourceTreeTaxonClass(
            taxon_name,
            author,
            taxon_rank,
            SOURCE_NAME,
            taxon_id,
            parent_name,
            parent_rank
        )

        return source_taxon
    
    @classmethod
    def _taxa_are_duplicates(cls, id_list):
        
        reference_taxon_id = id_list[0]
        
        refetence_taxon_sql = '''SELECT * FROM taxa WHERE "id" = {0}'''.format(reference_taxon_id)
        
        algaebaseCursor.execute(refetence_taxon_sql)
        reference_taxon = algaebaseCursor.fetchone()
        
        fields_to_compare = ['genus', 'species', 'nomenclatural_authorities']

        for taxon_id in id_list[1:]:
            
            taxon_sql = '''SELECT * FROM taxa WHERE "id" = {0}'''.format(taxon_id)
            
            algaebaseCursor.execute(taxon_sql)
            taxon = algaebaseCursor.fetchone()
            
            # compare genus, species, nomenclatural_authorities, year_of_publication
            # accept different years for the same author as "same"
            
            for field in fields_to_compare:
                if reference_taxon[field] != taxon[field]:
                    return False
            
        return True

    # author, id impossible for taxon higher than genus
    @classmethod
    def _get_author(cls, db_taxon, taxon_rank):

        author_string = None

        if taxon_rank in LOWER_RANKS:

            ids = list(db_taxon['ids'])
            
            # these are possibly just duplicates
            if len(ids) > 1:
                
                taxa_are_duplicates = cls._taxa_are_duplicates(ids)
                if not taxa_are_duplicates:
                    ids_str = ','.join([str(taxon_id) for taxon_id in ids])
                    raise ValueError('Multiple ids found for taxon {0} of rank {1}: {2}. Checked and found that they are not duplicates.'.format(
                        db_taxon, taxon_rank, ids_str))
                #ids_str = ','.join([str(taxon_id) for taxon_id in ids])
                #raise ValueError('Multiple ids found: {0}'.format(ids_str))

            taxon_id = ids[0]

            algaebaseCursor.execute('''SELECT * FROM taxa
                                    WHERE "id" = {0}'''.format(taxon_id))

            full_db_taxon = algaebaseCursor.fetchone()
        
            author_string = full_db_taxon['nomenclatural_authorities']

            if author_string is not None:

                year = full_db_taxon['year_of_publication']

                if year is not None:
                    author_string = '{0} {1}'.format(author_string, year)

        return author_string
    

    def _get_root_source_taxa(self):

        root_taxa = []
        
        algaebaseCursor.execute('''SELECT DISTINCT(phylum) FROM taxa
                                    WHERE "phylum" IS NOT NULL
                                    AND id_current_name IS NULL
                                    ORDER BY "phylum"''')

        phylums = algaebaseCursor.fetchall()

        for taxon in phylums:
            root_taxa.append(self._sourcetaxon_from_db_taxon(taxon, 'phylum', 'root', None))

        return root_taxa


    def _get_parent_rank(self, taxon_rank):

        taxon_rank_index = RANKS.index(taxon_rank)
        parent_rank_index = taxon_rank_index - 1

        if parent_rank_index >= 0:
            parent_rank = RANKS[parent_rank_index]
            return parent_rank

        return None


    def _get_children_rank(self, taxon_rank):

        taxon_rank_index = RANKS.index(taxon_rank)
        children_rank_index = taxon_rank_index + 1

        max_index = len(RANKS) - 1

        if children_rank_index <= max_index:
            children_rank = RANKS[children_rank_index]
            return children_rank

        return None


    def _get_db_taxon_by_id(self, taxon_id):

        sql = '''SELECT * FROM taxa WHERE "id" = {0}'''.format(taxon_id)
        if DEBUG == True:
            print(sql)
            
        algaebaseCursor.execute(sql)

        db_taxon = algaebaseCursor.fetchone()

        db_taxon_clean = {}
        for key, value in db_taxon.items():
            db_taxon_clean[key] = value
            
        db_taxon_clean['ids'] = [db_taxon['id']]

        return db_taxon_clean


    def _append_is_null_clauses(self, clauses_str, columns_list):

        for null_column in columns_list:

            new_clause = 'AND {0} IS NULL'.format(null_column)

            if new_clause in clauses_str:
                raise ValueError('{0} already in {1}'.format(new_clause, clauses_str))
            
            clauses_str = ' {0} {1} '.format(clauses_str, new_clause)


        return clauses_str
        

    # only include a genus if it has at lease one species where id_current_name == 0
    # some genus occur multiple times, like Chaetopia
    def _verify_genus_has_species(self, genus, parent_rank, parent_name):

        genus_name = genus['genus']

        if parent_rank not in ['family', 'subfamily', 'tribe']:
            raise ValueError('Invalid parent rank for genus {0}: {1}'.format(genus, parent_rank))

        sql = '''SELECT * FROM taxa
                            WHERE "genus" = '{0}'
                            AND "{1}" = '{2}'
                            AND "species" IS NOT NULL
                            AND "subspecies" IS NULL
                            AND "variety" IS NULL
                            AND "forma" IS NULL
                            AND id_current_name IS NULL
                            '''.format(genus_name, parent_rank, parent_name)
        if DEBUG == True:
            print(sql)

        algaebaseCursor.execute(sql)
        exists = algaebaseCursor.fetchall()

        print('Found {0} species for genus {1}'.format(len(exists), genus_name))
        if len(exists) == 0:
            return False

        return True


    def _verify_lower_taxon_rank(self, taxon, rank):
        # the lower ranks have to be null
        null_ranks = LOWER_RANKS[LOWER_RANKS.index(rank) + 1 : ]
        for null_rank in null_ranks:
            if taxon[null_rank] != None:
                print('rank error: {0} {1}. expected {2} to be null, but is {3}'.format(taxon, rank, null_rank,
                                                                                        taxon[null_rank]))
                return False
        return True
        
        

    # get children, not ancestors
    # if species: subspecies, variety and forma have to be NULL
    # if subspecies: variety and forma have to be NULL
    # getting children of higher taxa: subphylum might be null
    ##################################################################
    # problem with genus Grunoviella:
    # no species without "id_current_name"
    # BUT: 2 varieties without "id_current_name"
    ##################################################################
    #

    # no skipable subranks for 'subphylum', 'class', 'order', 'genus'

    def _get_select_ranks_str_and_group_by_ranks_str(self, children_rank):

        select_ranks = RANKS[:RANKS.index(children_rank)]
        # psql requires quoted "order", not order
        select_ranks_fixed = ['"{0}"'.format(rank) for rank in select_ranks]
        select_ranks_str = ','.join(select_ranks_fixed)

        group_by_ranks_str = '{0}'.format(children_rank)
        if select_ranks:
            group_by_ranks_str = '"{0}", {1}'.format(group_by_ranks_str, select_ranks_str)

        return select_ranks_str, group_by_ranks_str


    def _get_null_ranks_str(self, children_rank):
        children_rank_index = RANKS.index(children_rank)

        null_ranks_str = ''

        if children_rank in LOWER_RANKS:

            null_ranks = RANKS[children_rank_index+1:]
            null_ranks_str = self._append_is_null_clauses(null_ranks_str, null_ranks)

        return null_ranks_str


    def _children_dict_to_children_list(self, children_dict):

        children = []
        
        for rank, children_list in children_dict.items():

            for child_db in children_list:

                child = {
                    'sort_name' : child_db[rank],
                    'rank' : rank,
                }
                
                for key, value in child_db.items():
                    child[key] = value

                children.append(child)

        children.sort(key=lambda child: child['sort_name'])

        return children
    

    # grandparent rank might not exist
    # grandparent might skip a few ranks upwards:
    # case: genus is present, grandparent is family. that means subfamily and tribe have to be null
    def _get_grandparent_query(self, parent):

        if DEBUG == True:
            print ('_get_grandparent_query. parent: {0}'.format(parent.latname))

        sql = ''
        
        grandparent_rank = parent.parent_rank
        grandparent_name = parent.parent_name

        if grandparent_rank and grandparent_name:
            sql = ''' AND "{0}" = '{1}' '''.format(grandparent_rank, grandparent_name)
            
        parent_rank_index = RANKS.index(parent.rank)
        grandparent_rank_index = RANKS.index(grandparent_rank)
        
        # skipable ranks between parent and grandparent have to be NULL
        if grandparent_rank_index < parent_rank_index - 1:

            null_ranks = RANKS[grandparent_rank_index + 1 : parent_rank_index]

            sql = self._append_is_null_clauses(sql, null_ranks)

        return sql
            
    
        
    def _get_select_ranks(self, rank):
        select_ranks = RANKS[:RANKS.index(rank)]
        return select_ranks

    ###
    # getting children in algaebase depends on the higher taxon, as higher taxa are not listed
    # in the tree as taxa, but only as higher taxa of species
    # make one method per rank
    ###
    def _get_children(self, source_taxon):

        if DEBUG == True:
            print('_get_children for {0} {1}'.format(source_taxon.latname, source_taxon.author))


        children_method_str = '_get_children_{0}'.format(source_taxon.rank)
        children_method = getattr(self, children_method_str)
        
        db_children = children_method(source_taxon)
        
        if DEBUG == True:
            print('found {0} children for {1}'.format(len(db_children), source_taxon.latname))
        
        children = []
        for child_db in db_children:
            child = self._sourcetaxon_from_db_taxon(
                child_db, child_db['rank'], source_taxon.latname, source_taxon.rank)
            children.append(child)
        
        return children 
    
    # this will query only one taxonomic level down, for example query all classes of a subphylum
    def _get_children_next_rank_only(self, source_taxon):
        
        parent_rank = source_taxon.rank
        parent_name = source_taxon.latname

        children_rank = self._get_children_rank(parent_rank)

        select_ranks_str, group_by_ranks_str = self._get_select_ranks_str_and_group_by_ranks_str(children_rank)
        null_ranks_str = '' #self._get_null_ranks_str(children_rank)
        grandparent_query = self._get_grandparent_query(source_taxon)

        sql = '''SELECT DISTINCT("{0}"), {1}, ARRAY_AGG("id") AS ids FROM taxa
                    WHERE "{2}" = '{3}'
                    AND "{0}" IS NOT NULL
                    AND id_current_name IS NULL
                    {4}
                    {5}
                    GROUP BY {6}
                    ORDER BY "{0}"'''.format(children_rank, select_ranks_str, parent_rank, parent_name,
                                             null_ranks_str, grandparent_query, group_by_ranks_str)

        if DEBUG == True:
            print(sql)

        algaebaseCursor.execute(sql)

        children_db_list = algaebaseCursor.fetchall()

        children_db = {}
        children_db[children_rank] = children_db_list

        children = self._children_dict_to_children_list(children_db)

        return children
    
    
    def _get_children_phylum(self, source_taxon):
        # subphylum might be empty
        # so it can be subphylum or class
        # "parent" means parent of the children we want to fetch
        parent_rank = source_taxon.rank
        parent_name = source_taxon.latname
        
        # this will return subphylum
        children_rank = self._get_children_rank(parent_rank)

        select_ranks_str, group_by_ranks_str = self._get_select_ranks_str_and_group_by_ranks_str(children_rank)
        # phyla do not have parents
        grandparent_query = '' #self._get_grandparent_query(source_taxon)

        # get all subphylums
        sql_subphylum = '''SELECT DISTINCT("subphylum"), {0}, ARRAY_AGG("id") AS ids FROM taxa
                    WHERE "phylum" = '{1}'
                    AND "subphylum" IS NOT NULL
                    AND "id_current_name" IS NULL
                    {2}
                    GROUP BY {3}
                    ORDER BY "subphylum"'''.format(select_ranks_str, parent_name, grandparent_query,
                                                   group_by_ranks_str)

        if DEBUG == True:
            print(sql_subphylum)


        algaebaseCursor.execute(sql_subphylum)

        children_subphylum_db = algaebaseCursor.fetchall()

        # get all classes
        group_by_ranks_str = '{0}, "class"'.format(group_by_ranks_str)
        sql_class = '''SELECT DISTINCT("class"), {0}, ARRAY_AGG("id") AS ids FROM taxa
                    WHERE "phylum" = '{1}'
                    AND "subphylum" IS NULL
                    AND "class" IS NOT NULL
                    AND "id_current_name" IS NULL
                    {2}
                    GROUP BY {3}
                    ORDER BY "class"'''.format(select_ranks_str, parent_name, grandparent_query,
                                                 group_by_ranks_str)

        if DEBUG == True:
            print(sql_class)

        algaebaseCursor.execute(sql_class)

        children_class_db = algaebaseCursor.fetchall()

        children_db = {
            'subphylum' : children_subphylum_db,
            'class' : children_class_db,
        }

        children = self._children_dict_to_children_list(children_db)

        return children
    
    # only class is a valid subrank of subphylum
    # class is given for all taxa
    def _get_children_subphylum(self, source_taxon):
        return self._get_children_next_rank_only(source_taxon)
    
    # only order is a valid subclass of class
    # order is given for all taxa
    def _get_children_class(self, source_taxon):
        return self._get_children_next_rank_only(source_taxon)
    
    # only family is a valid subclass of order
    # family is given for all taxa
    def _get_children_order(self, source_taxon):
        return self._get_children_next_rank_only(source_taxon)
    
    # can be subfamily, but subfamily can be empty
    # can be tribe, but tribe can be empty
    # so it can be subfamily, tribe or genus
    # genus cannot be empty
    def _get_children_family(self, source_taxon):

        # "parent" means parent of the children we want to fetch
        parent_rank = source_taxon.rank
        parent_name = source_taxon.latname

        children_rank = self._get_children_rank(parent_rank)

        select_ranks_str, group_by_ranks_str = self._get_select_ranks_str_and_group_by_ranks_str(children_rank)
        grandparent_query = self._get_grandparent_query(source_taxon)

        # get all subfamilies
        sql_subfamily = '''SELECT DISTINCT("subfamily"), {0}, ARRAY_AGG("id") AS ids FROM taxa
                    WHERE "family" = '{1}'
                    AND "subfamily" IS NOT NULL
                    AND "id_current_name" IS NULL
                    {2}
                    GROUP BY {3}
                    ORDER BY "subfamily"'''.format(select_ranks_str, parent_name, grandparent_query,
                                                     group_by_ranks_str)

        if DEBUG == True:
            print(sql_subfamily)
                
        algaebaseCursor.execute(sql_subfamily)

        children_subfamily_db = algaebaseCursor.fetchall()

        # get all tribes
        group_by_ranks_str = '{0}, "tribe"'.format(group_by_ranks_str)
        sql_tribe = '''SELECT DISTINCT("tribe"), {0}, ARRAY_AGG("id") AS ids FROM taxa
                    WHERE "family" = '{1}'
                    AND "subfamily" IS NULL
                    AND "tribe" IS NOT NULL
                    AND "id_current_name" IS NULL
                    {2}
                    GROUP BY {3}
                    ORDER BY "tribe"'''.format(select_ranks_str, parent_name, grandparent_query,
                                                 group_by_ranks_str)

        if DEBUG == True:
            print(sql_tribe)

        algaebaseCursor.execute(sql_tribe)

        children_tribe_db = algaebaseCursor.fetchall()

        # get all genuses
        group_by_ranks_str = '{0}, "genus"'.format(group_by_ranks_str)
        sql_genus = '''SELECT DISTINCT("genus"), {0}, ARRAY_AGG("id") AS ids FROM taxa
                    WHERE "family" = '{1}'
                    AND "subfamily" IS NULL
                    AND "tribe" IS NULL
                    AND "genus" IS NOT NULL
                    AND "id_current_name" IS NULL
                    {2}
                    GROUP BY {3}
                    ORDER BY "genus"'''.format(select_ranks_str, parent_name, grandparent_query,
                                                 group_by_ranks_str)

        if DEBUG == True:
            print(sql_genus)

        algaebaseCursor.execute(sql_genus)

        children_genus_db = algaebaseCursor.fetchall()


        children_db = {
            'subfamily' : children_subfamily_db,
            'tribe' : children_tribe_db,
            'genus' : children_genus_db,
        }

        children = self._children_dict_to_children_list(children_db)

        return children

    
    # tribe can be empty
    # so it can be tribe or genus
    def _get_children_subfamily(self, source_taxon):
        
        # "parent" means parent of the children we want to fetch
        parent_rank = source_taxon.rank
        parent_name = source_taxon.latname
        
        children_rank = self._get_children_rank(parent_rank)

        select_ranks_str, group_by_ranks_str = self._get_select_ranks_str_and_group_by_ranks_str(children_rank)
        grandparent_query = self._get_grandparent_query(source_taxon)

        # get all tribes
        sql_tribe = '''SELECT DISTINCT("tribe"), {0}, ARRAY_AGG("id") AS ids FROM taxa
                    WHERE "subfamily" = '{1}'
                    AND "tribe" IS NOT NULL
                    AND "id_current_name" IS NULL
                    {2}
                    GROUP BY {3}
                    ORDER BY "tribe"'''.format(select_ranks_str, parent_name, grandparent_query,
                                                 group_by_ranks_str)

        if DEBUG == True:
            print(sql_tribe)

        algaebaseCursor.execute(sql_tribe)

        children_tribe_db = algaebaseCursor.fetchall()

        # get all genuses
        group_by_ranks_str = '{0}, "genus"'.format(group_by_ranks_str)
        sql_genus = '''SELECT DISTINCT("genus"), {0}, ARRAY_AGG("id") AS ids FROM taxa
                    WHERE "subfamily" = '{1}'
                    AND "tribe" IS NULL
                    AND "genus" IS NOT NULL
                    AND "id_current_name" IS NULL
                    {2}
                    GROUP BY {3}
                    ORDER BY "genus"'''.format(select_ranks_str, parent_name, grandparent_query,
                                                 group_by_ranks_str)

        if DEBUG == True:
            print(sql_genus)

        algaebaseCursor.execute(sql_genus)

        children_genus_db = algaebaseCursor.fetchall()


        children_db = {
            'tribe' : children_tribe_db,
            'genus' : children_genus_db,
        }

        children = self._children_dict_to_children_list(children_db)

        return children
    
    # has to be genus
    # tribe is given, not empty
    def _get_children_tribe(self, source_taxon):
        return self._get_children_next_rank_only(source_taxon)
    
    # species column has to be present
    # subspecies has to be empy
    # variety has to be empty
    # forma has to be empty
    def _get_children_genus(self, source_taxon):
        # "parent" means parent of the children we want to fetch
        parent_rank = source_taxon.rank
        parent_name = source_taxon.latname
        
        # subspecies
        children_rank = self._get_children_rank(parent_rank)

        select_ranks_str, group_by_ranks_str = self._get_select_ranks_str_and_group_by_ranks_str(children_rank)
        grandparent_query = self._get_grandparent_query(source_taxon)

        # get all tribes
        sql_species = '''SELECT "species", "nomenclatural_authorities", {0}, ARRAY_AGG("id") AS ids FROM taxa
                    WHERE "genus" = '{1}'
                    AND "subspecies" IS NULL
                    AND "variety" IS NULL
                    AND "forma" IS NULL
                    AND "id_current_name" IS NULL
                    {2}
                    GROUP BY "species", "nomenclatural_authorities", {3}
                    ORDER BY "species"'''.format(select_ranks_str, parent_name,
                                               grandparent_query, group_by_ranks_str)

        if DEBUG == True:
            print(sql_species)

        algaebaseCursor.execute(sql_species)

        children_species_db = algaebaseCursor.fetchall()
        
        if DEBUG == True:
            print('found {0} db_species for genus {1}'.format(len(children_species_db), parent_name))
        
        children_db = {}
        children_db[children_rank] = children_species_db

        children = self._children_dict_to_children_list(children_db)

        return children
    
    
    # sometimes, two species with different authors exist in algabease
    # we can append infrascpecies only to one of those species
    def _check_if_infrascpecies_exists(self, db_taxon):
        
        ids = list(db_taxon['ids'])
        if len(ids) > 1:
            print('multiple ids found for taxon {0}: {1}'.format(
                db_taxon, ids))
        
        source_id = ids[0]
        
        exists = AlgaebaseTaxonTree.objects.filter(
            source_id = source_id,
        ).exists()
        
        return exists
    
    
    def _clean_children(self, children_db):
        cleaned_children = []
        
        for child in children_db:
            
            taxa_are_duplicates = self._taxa_are_duplicates(list(child['ids']))
            if not taxa_are_duplicates:
                ids_str = ','.join([str(taxon_id) for taxon_id in child['ids']])
                raise ValueError('Multiple ids found for taxon {0}: {1}. Checked and found that they are not duplicates.'.format(
                    child, ids_str))
            
            if not self._check_if_infrascpecies_exists(child):
                cleaned_children.append(child)
        
        return cleaned_children

    
    # species can have subspecies
    # species can have a variety without subspecies
    # species can have a forma without subspecies and variety
    def _get_children_species(self, source_taxon):
        
        db_species = source_taxon._get_source_object()
        genus_name = db_species['genus']
        species_epithet = db_species['species']
        
        grandparent_query = self._get_grandparent_query(source_taxon)

        # subspecies
        sel_sub, _ = self._get_select_ranks_str_and_group_by_ranks_str('subspecies')
        grp_sub = f'"subspecies", "nomenclatural_authorities", {sel_sub}'
        sql_subspecies = f'''SELECT DISTINCT("subspecies"), "nomenclatural_authorities", {sel_sub},
                                    ARRAY_AGG("id") AS ids
                             FROM taxa
                             WHERE "genus" = '{genus_name}'
                               AND "species" = '{species_epithet}'
                               AND "subspecies" IS NOT NULL
                               AND "variety" IS NULL
                               AND "forma" IS NULL
                               AND "id_current_name" IS NULL
                               {grandparent_query}
                             GROUP BY {grp_sub}
                             ORDER BY "subspecies"'''
        if DEBUG:
            print(sql_subspecies)
        algaebaseCursor.execute(sql_subspecies)
        children_subspecies_db = algaebaseCursor.fetchall()
        
        children_subspecies_db = self._clean_children(children_subspecies_db)

        # varieties directly under species
        sel_var, _ = self._get_select_ranks_str_and_group_by_ranks_str('variety')
        grp_var = f'"variety", "nomenclatural_authorities", {sel_var}'
        sql_varieties = f'''SELECT DISTINCT("variety"), "nomenclatural_authorities", {sel_var},
                                   ARRAY_AGG("id") AS ids
                            FROM taxa
                            WHERE "genus" = '{genus_name}'
                              AND "species" = '{species_epithet}'
                              AND "subspecies" IS NULL
                              AND "variety" IS NOT NULL
                              AND "forma" IS NULL
                              AND "id_current_name" IS NULL
                              {grandparent_query}
                            GROUP BY {grp_var}
                            ORDER BY "variety"'''
        if DEBUG:
            print(sql_varieties)
        algaebaseCursor.execute(sql_varieties)
        children_varieties_db = algaebaseCursor.fetchall()
        
        children_varieties_db = self._clean_children(children_varieties_db)

        # forma directly under species
        sel_for, _ = self._get_select_ranks_str_and_group_by_ranks_str('forma')
        grp_for = f'"forma", "nomenclatural_authorities", {sel_for}'
        sql_forma = f'''SELECT DISTINCT("forma"), "nomenclatural_authorities", {sel_for},
                               ARRAY_AGG("id") AS ids
                        FROM taxa
                        WHERE "genus" = '{genus_name}'
                          AND "species" = '{species_epithet}'
                          AND "subspecies" IS NULL
                          AND "variety" IS NULL
                          AND "forma" IS NOT NULL
                          AND "id_current_name" IS NULL
                          {grandparent_query}
                        GROUP BY {grp_for}
                        ORDER BY "forma"'''
        if DEBUG:
            print(sql_forma)
        algaebaseCursor.execute(sql_forma)
        children_forma_db = algaebaseCursor.fetchall()
        
        children_forma_db = self._clean_children(children_forma_db)
        
        children_db = {
            'subspecies' : children_subspecies_db,
            'variety'    : children_varieties_db,
            'forma'      : children_forma_db,
        }
        children = self._children_dict_to_children_list(children_db)
        if children:
            print('found {0} children for species {1}'.format(len(children), source_taxon.latname))
        return children
    
    # can be variety (forma None)
    # can be forma (variety None)
    # we always nee genus amd species in the query
    def _get_children_subspecies(self, source_taxon):
        subspecies_source = source_taxon._get_source_object()

        # varieties under subspecies
        sel_var, _ = self._get_select_ranks_str_and_group_by_ranks_str('variety')
        grp_var = f'"variety", "nomenclatural_authorities", {sel_var}'
        sql_varieties = '''SELECT DISTINCT("variety"), "nomenclatural_authorities", {0},
                                  ARRAY_AGG("id") AS ids
                           FROM taxa
                           WHERE "genus" = '{1}'
                             AND "species" = '{2}'
                             AND "subspecies" = '{3}'
                             AND "variety" IS NOT NULL
                             AND "forma" IS NULL
                             AND "id_current_name" IS NULL
                           GROUP BY {4}
                           ORDER BY "variety"'''.format(
                               sel_var, subspecies_source['genus'], subspecies_source['species'],
                               subspecies_source['subspecies'], grp_var)
        if DEBUG:
            print(sql_varieties)
        algaebaseCursor.execute(sql_varieties)
        children_varieties_db = algaebaseCursor.fetchall()
        
        # clean
        children_varieties_db = self._clean_children(children_varieties_db)

        # forma under subspecies (no variety)
        sel_for, _ = self._get_select_ranks_str_and_group_by_ranks_str('forma')
        grp_for = f'"forma", "nomenclatural_authorities", {sel_for}'
        sql_forma = '''SELECT DISTINCT("forma"), "nomenclatural_authorities", {0},
                              ARRAY_AGG("id") AS ids
                       FROM taxa
                       WHERE "genus" = '{1}'
                         AND "species" = '{2}'
                         AND "subspecies" = '{3}'
                         AND "variety" IS NULL
                         AND "forma" IS NOT NULL
                         AND "id_current_name" IS NULL
                       GROUP BY {4}
                       ORDER BY "forma"'''.format(
                           sel_for, subspecies_source['genus'], subspecies_source['species'],
                           subspecies_source['subspecies'], grp_for)
        if DEBUG:
            print(sql_forma)
        algaebaseCursor.execute(sql_forma)
        children_forma_db = algaebaseCursor.fetchall()
        
        # clean
        children_forma_db = self._clean_children(children_forma_db)

        children_db = {
            'variety' : children_varieties_db,
            'forma'   : children_forma_db,
        }
        return self._children_dict_to_children_list(children_db)
    
    def clean_search_sting(self, search_string):
        if search_string and "'" in search_string:
            cleaned_string = search_string.replace("'", "''")
            return cleaned_string
        
        return search_string
    
    # this can only be forma
    def _get_children_variety(self, source_taxon):
        variety_source = source_taxon._get_source_object()

        sel_for, _ = self._get_select_ranks_str_and_group_by_ranks_str('forma')
        grp_for = f'"forma", "nomenclatural_authorities", {sel_for}'
        
        variety = self.clean_search_sting(variety_source['variety'])

        if variety_source['subspecies'] is None:
            sql_forma = '''SELECT DISTINCT("forma"), "nomenclatural_authorities", {0},
                                  ARRAY_AGG("id") AS ids
                           FROM taxa
                           WHERE "genus" = '{1}'
                             AND "species" = '{2}'
                             AND "subspecies" IS NULL
                             AND "variety" = '{3}'
                             AND "forma" IS NOT NULL
                             AND "id_current_name" IS NULL
                           GROUP BY {4}
                           ORDER BY "forma"'''.format(
                               sel_for, variety_source['genus'], variety_source['species'],
                               variety, grp_for)
        else:
            sql_forma = '''SELECT DISTINCT("forma"), "nomenclatural_authorities", {0},
                                  ARRAY_AGG("id") AS ids
                           FROM taxa
                           WHERE "genus" = '{1}'
                             AND "species" = '{2}'
                             AND "subspecies" = '{3}'
                             AND "variety" = '{4}'
                             AND "forma" IS NOT NULL
                             AND "id_current_name" IS NULL
                           GROUP BY {5}
                           ORDER BY "forma"'''.format(
                               sel_for, variety_source['genus'], variety_source['species'],
                               variety_source['subspecies'], variety, grp_for)

        if DEBUG:
            print(sql_forma)
        algaebaseCursor.execute(sql_forma)
        children_forma_db = algaebaseCursor.fetchall()
        
        # clean
        children_forma_db = self._clean_children(children_forma_db)

        children_db = { 'forma' : children_forma_db }
        return self._children_dict_to_children_list(children_db)
    
    # there are no children for forma
    def _get_children_forma(self, source_taxon):
        return []
    

    # integrate special cases:
    # iterate over all taxa, check if it has been integrated.
    # if not, try to integrate it by identifying one of 3 cases:
    # 1. forma without species -> add the forma to the genus
    # 2. forma of synonym -> add the forma to the primary taxon
    # 3. no higher taxa provided -> create a new root taxon ("life" or "unassigned"), and append to those
    def integrate_missing_taxa(self):

        limit = 10000
        offset = 0

        source_query = '''SELECT * FROM taxa ORDER BY id LIMIT {0} OFFSET {1}'''.format(limit, offset)
        algaebaseCursor.execute(source_query)
        taxa = algaebaseCursor.fetchall()

        while taxa:

            for taxon in taxa:
                # the taxon is not a synonym, but its parent taxon is
                if taxon['id_current_name'] == None:
                    
                    # the taxon should not yet exist in the tree
                    if not AlgaebaseTaxonTree.objects.filter(source_id=str(taxon['id'])).exists():

                        if taxon['record_status'] in ['F', 'V', 'S']:  # forma, variety, subspecies
                            
                            infraspecies = taxon

                            # get the species of this form, which has to be a synonym
                            sql = '''SELECT * FROM taxa
                                WHERE "genus" = '{0}'
                                AND "family" = '{1}'
                                AND "species" = '{2}'
                                AND id_current_name IS NOT NULL
                                AND "subspecies" IS NULL
                                AND "variety" IS NULL
                                AND "forma" IS NULL'''.format(infraspecies['genus'], infraspecies['family'],
                                                                    infraspecies['species'])

                            algaebaseCursor.execute(sql)

                            possible_synonyms = algaebaseCursor.fetchall()
                            if len(possible_synonyms) == 0:
                                self._integrate_infraspecies_without_species(infraspecies)

                            elif len(possible_synonyms) == 1:
                                self._integrate_infraspecies_of_synonym(infraspecies, possible_synonyms[0])

                            else:
                                self.logger.info('Multiple species found for infraspecies {0}: {1}'.format(infraspecies,
                                                                                                    possible_synonyms))      
                            
                        else:
                            self.logger.info('Failed to integrate taxon, not a infraspecies: {0}'.format(taxon))

                else:
                    # it is a synonym
                    if not AlgaebaseTaxonSynonym.objects.filter(source_id=taxon['id']).exists():
                        self.logger.info('Failed to integrate synonym: {0}'.format(taxon))

            offset += limit
            source_query = '''SELECT * FROM taxa ORDER BY id LIMIT {0} OFFSET {1}'''.format(limit, offset)
            
            print(offset)
            
            algaebaseCursor.execute(source_query)
            taxa = algaebaseCursor.fetchall()
            

    def _integrate_infraspecies_without_species(self, taxon):

        genus_name = taxon['genus']

        sql = '''SELECT DISTINCT("genus") FROM taxa
                                WHERE "genus" = '{0}'
                                AND "family" = '{1}'
                                AND "species" IS NULL
                                AND "subspecies" IS NULL
                                AND "variety" IS NULL
                                AND "forma" IS NULL'''.format(taxon['genus'], taxon['family'],
                                                                    taxon['species'])

        if DEBUG == True:
            print(sql)

        algaebaseCursor.execute(sql)
        genus = algaebaseCursor.fetchall()

        if len(genus) == 1:

            genus_db = genus[0]

            tree_genus = AlgaebaseTaxonTree.objects.get(source_id='{0}'.format(genus_db['id']))

        elif len(genus) == 0:
            self.logger.info('Failed to integrate forma: {0}, because genus was not found: {1}'.format(taxon,
                                                                                                genus_name))

        else:
            self.logger.info('Failed to integrate forma: {0}, multiple genus were not found: {1}'.format(taxon,
                                                                                                genus))

    
    def get_accepted_name(self, synonym):
        
        visited_ids = set()
        id_current_name = synonym['id_current_name']
        
        while id_current_name is not None:
            
            if id_current_name in visited_ids:
                return None
            
            visited_ids.add(id_current_name)
            
            sql = '''SELECT * FROM taxa WHERE id = {0}'''.format(id_current_name)
            
            if DEBUG == True:
                print(sql)
            
            algaebaseCursor.execute(sql)
            accepted_taxon_candidate = algaebaseCursor.fetchone()
            
            if accepted_taxon_candidate is None:
                print('accepted taxon candidate not found for id_current_name: {0}'.format(id_current_name))
                return None
            
            print('found accepted taxon candidate: {0}'.format(accepted_taxon_candidate))
            
            if accepted_taxon_candidate['id_current_name'] is None:
                return accepted_taxon_candidate
            else:
                id_current_name = accepted_taxon_candidate['id_current_name']
        
        # If id_current_name was initially None, but synonym should have it
        return None

    def _integrate_infraspecies_of_synonym(self, infraspecies, synonym):
        
        rank = RANK_MAP[infraspecies['record_status']]

        if synonym['id_current_name'] != None:
            
            print('integrating {0} of synonym {1}'.format(rank, synonym))
            
            accepted_species_algaebase = self.get_accepted_name(synonym)
            
            if accepted_species_algaebase:

                primary_parent_taxon = AlgaebaseTaxonTree.objects.filter(
                    source_id = str(accepted_species_algaebase['id'])
                ).first()
                
                if primary_parent_taxon:

                    parent_name = '{0} {1}'.format(synonym['genus'], synonym['species'])

                    infraspecies_clean = {}
                    infraspecies_clean['ids'] = [infraspecies['id']]
                    
                    for key, value in infraspecies.items():
                        infraspecies_clean[key] = value
                        
                    source_taxon = self._sourcetaxon_from_db_taxon(infraspecies_clean, rank, parent_name, 'species')
                    
                    children = AlgaebaseTaxonTree.objects.filter(parent=primary_parent_taxon).order_by('-taxon_nuid')

                    if children:
                        highest_nuid = children[0].taxon_nuid
                        new_suffix = d2n(n2d(highest_nuid[-3:]) + 1)
                    else:
                        new_suffix = '001'

                    print('integrating {0}'.format(source_taxon.latname))
                    print('parent: {0}, nuid: {1}'.format(primary_parent_taxon, primary_parent_taxon.taxon_nuid))

                    nuid_prefix = primary_parent_taxon.taxon_nuid
                    taxon_nuid = '{0}{1}'.format(nuid_prefix, new_suffix)
                    
                    
                    taxon = self.TaxonTreeModel(
                        parent = primary_parent_taxon,
                        taxon_nuid = taxon_nuid,
                        taxon_latname = source_taxon.latname,
                        taxon_author = source_taxon.author,
                        source_id = source_taxon.source_id,
                        rank = source_taxon.rank,
                        is_root_taxon = False,
                    )

                    taxon.save()
                
                else:
                    print('Failed to integrate {0}: {1}, because primary parent taxon not found in tree: {2}'.format(
                        rank, infraspecies, accepted_species_algaebase))
                
            else:
                print('Failed to integrate {0}: {1}, because accepted name could not be found for synonym: {2}'.format(
                    rank, infraspecies, synonym))

        else:
            print('Failed to integrate {0}: {1}, because parent is not a synonym: {2}'.format(
                rank, infraspecies, synonym))

    # some species do not have a phylum assigned
    def _integrate_orphans(self):
        pass
    

    def update_name_uuids(self, path_to_csv_file):
        with open(path_to_csv_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='|')
            rows = list(reader)

        # name_uuid, taxon_latname, taxon_author
        for row in rows:
            name_uuid = row['name_uuid']
            taxon_latname = row['taxon_latname']
            taxon_author = row['taxon_author']
            
            
            taxa = AlgaebaseTaxonTree.objects.filter(
                taxon_latname=taxon_latname,
                taxon_author=taxon_author
            )
            
            if len(taxa) == 0:
                
                synonyms = AlgaebaseTaxonSynonym.objects.filter(
                    taxon_latname=taxon_latname,
                    taxon_author=taxon_author
                )
                
                if len(synonyms) == 1:
                    synonym = synonyms[0]
                    
                    if str(synonym.name_uuid) == str(name_uuid):
                        continue
                    
                    synonym.name_uuid = name_uuid
                    synonym.save()
                    
                    print(f'Updated name_uuid for synonym {taxon_latname} {taxon_author} to {name_uuid}.')
                
                elif len(synonyms) > 1:
                    self.logger.info(f'Multiple synonyms found for {taxon_latname} {taxon_author}, skipping.')
                    
                else:
                    self.logger.info(f'No taxon or synonym found for {taxon_latname} {taxon_author}, skipping.')
                
            elif len(taxa) > 1:
                self.logger.info(f'Multiple taxa found for {taxon_latname} {taxon_author}, skipping.')
                
            else:
                taxon = taxa[0]
                
                if str(taxon.name_uuid) == str(name_uuid):
                    continue
                
                taxon.name_uuid = name_uuid
                
                # this requires ON UPDATE CASCADE set for the foreign key on the database level
                # django orm does not support on update cascade
                taxon.save()
                
                print(f'Updated name_uuid for {taxon_latname} {taxon_author} to {name_uuid}.')
               
                
    def drop_duplicate_synonyms(self):
        
        taxa = AlgaebaseTaxonTree.objects.all()
        
        for taxon in taxa:
            
            synonyms = AlgaebaseTaxonSynonym.objects.filter(
                taxon_latname=taxon.taxon_latname,
                taxon_author=taxon.taxon_author
            )
            
            # these synonyms are exact name duplicates of a real taxon
            if len(synonyms) > 0:
                print(f'Checking {taxon.taxon_latname} {taxon.taxon_author}, found {len(synonyms)} duplicates in synonyms.')
                
                synonyms.delete()
                print(f'Deleted duplicate synonyms for {taxon.taxon_latname} {taxon.taxon_author}.')
            


class AlgaebaseAnalyzer:

    def __init__(self):

        self.logger = logging.getLogger('algaebase')
        logging_folder = '/home/tom/algaebase_analysis/'

        if not os.path.isdir(logging_folder):
            os.makedirs(logging_folder)

        logfile_path = os.path.join(logging_folder, 'algaebase_analysis_log')
        hdlr = logging.FileHandler(logfile_path)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        self.logger.addHandler(hdlr)
        self.logger.setLevel(logging.INFO)


    def get_species(self, family, genus, species):
        sql = '''SELECT * FROM taxa
                        WHERE "genus" = '{0}'
                        AND "family" = '{1}'
                        AND "species" = '{2}'
                        AND "subspecies" IS NULL
                        AND "variety" IS NULL
                        AND "forma" IS NULL
                        AND "id_current_name" IS NULL'''.format(genus, family, species)

        algaebaseCursor.execute(sql)

        species = algaebaseCursor.fetchall()

        return species
    

    def check_if_species_exists(self, taxon):

        species = self.get_species(taxon['family'], taxon['genus'], taxon['species'])
        if len(species) == 1:

            species = species[0]

            check_levels = HIGHER_RANKS + ['tribe', 'subfamily']

            for taxonlevel in check_levels:
                if species[taxonlevel] != taxon[taxonlevel]:
                    message = 'inconsistent higher taxa for level {0}. {1} |||| {2}'.format(taxonlevel,
                                                                                taxon, species)
                    self.logger.info(message)


        else:
            ids = []
            for s in species:
                ids.append(s['id'])
            message = 'multiple parents or no parent found for {0}: ids:{1}'.format(taxon, ids)
            self.logger.info(message)
        
    
    # check that there is a parent of the taxon which is not a synonym
    def validate_parent(self, taxon):

        # S = species, U=subspecies, V= Variety, F= forma
        level = taxon['record_status']

        if level == 'S':

            for l in ['U', 'V', 'F']:

                rank = RANK_MAP[l]

                if taxon[rank] != None:
                    self.logger.info('Record status is species, but infraspecific epithet is present: {0}:{1}'.format(
                        rank, taxon[rank]))

        # S may not be null, taxon with S only has to be presend, V and F have to be null
        elif level == 'U':

            for l in ['V', 'F']:

                rank = RANK_MAP[l]

                if taxon[rank] != None:
                    self.logger.info('Record status is subspecies, but lower infraspecific epithet is present: {0}:{1}'.format(
                        rank, taxon[rank]))

            # check if species exists
            self.check_if_species_exists(taxon)


        elif level == 'V':

            for l in ['F']:

                rank = RANK_MAP[l]

                if taxon[rank] != None:
                    self.logger.info('Record status is subspecies, but lower infraspecific epithet is present: {0}:{1}'.format(
                        rank, taxon[rank]))

            # check if species exists
            self.check_if_species_exists(taxon)

        elif level == 'F':
            pass

        else:
            self.logger.info('Invalid level: {0} ||| {1}'.format(level, taxon))


    def check_existence_in_lc(self, taxon):

        if not AlgaebaseTaxonTree.objects.filter(source_id=taxon['id']).exists():
            message = 'missing: {0}'.format(taxon)
            self.logger.info(message)


    def check_synonym_existence_in_lc(self, synonym):

        if not AlgaebaseTaxonSynonym.objects.filter(source_id=synonym['id']).exists():
            message = 'missing synonym: {0}'.format(synonym)
            self.logger.info(message)
        

    # Staurosira capucina var. mesolepta, (Rabenhorst) Comère 1892) already exists. ids: 167085, 138580
    def check_taxon_unique(self, taxon):
        sql = ''' SELECT * FROM taxa WHERE "phylum" = '{0}' '''.format(taxon['phylum'])

        for rank in RANKS:

            if taxon[rank]:
                taxon_name = taxon[rank]
                taxon_name = taxon_name.replace("'", "''")
                qry = ''' AND "{0}" = '{1}' '''.format(rank, taxon_name)
            else:
                qry = ''' AND "{0}" IS NULL '''.format(rank)

            sql = '{0} {1}'.format(sql, qry)


        author = taxon['nomenclatural_authorities']
        author = author.replace("'","''")
        author_sql = ''' AND "nomenclatural_authorities" = '{0}' '''.format(author)

        year = taxon['year_of_publication']
        if year:
            year = year.replace("'","''")
        year_sql = ''' AND "year_of_publication" = '{0}' '''.format(year)

        sql = '{0} {1} {2}'.format(sql, author_sql, year_sql)
        
        algaebaseCursor.execute(sql)

        results = algaebaseCursor.fetchall()
        if len(results) > 1:
            message = 'found duplicates: {0}'.format(results)
            self.logger.info(message)

    
    def analyze(self):
        
        self.analyze_tree()
        self.analyze_synonyms()
        

    def analyze_tree(self):

        limit = 10000
        offset = 0

        source_query = '''SELECT * FROM taxa WHERE id_current_name IS NULL LIMIT %s OFFSET %s''' %(limit, offset)
        algaebaseCursor.execute(source_query)
        taxa = algaebaseCursor.fetchall()

        while taxa:

            for taxon in taxa:
        
                self.check_existence_in_lc(taxon)
                self.validate_parent(taxon)
                self.check_taxon_unique(taxon)

            offset += limit
            source_query = '''SELECT * FROM taxa WHERE id_current_name IS NULL LIMIT %s OFFSET %s''' %(limit, offset)
            algaebaseCursor.execute(source_query)
            taxa = algaebaseCursor.fetchall()
        
        
    def analyze_synonyms(self):

        limit = 10000
        offset = 0

        source_query = '''SELECT * FROM taxa WHERE id_current_name IS NOT NULL LIMIT %s OFFSET %s''' %(limit, offset)
        algaebaseCursor.execute(source_query)
        synonyms = algaebaseCursor.fetchall()

        while synonyms:

            for taxon in synonyms:
        
                self.check_synonym_existence_in_lc(taxon)
                self.validate_parent(taxon)
                self.check_taxon_unique(taxon)

            offset += limit
            source_query = '''SELECT * FROM taxa WHERE id_current_name IS NOT NULL LIMIT %s OFFSET %s''' %(limit, offset)
            algaebaseCursor.execute(source_query)
            synonyms = algaebaseCursor.fetchall()
    
    def check_higher_taxa(self):
        
        for rank in HIGHER_RANKS:
            
            if HIGHER_RANKS.index(rank) == 0:
                continue
            
            # Quote the column name to handle reserved words like 'order'
            quoted_rank = f'"{rank}"'
            
            # Get all distinct ranks from algaebase db
            sql = f'''SELECT DISTINCT({quoted_rank}) FROM taxa
                                    WHERE "phylum" IS NOT NULL
                                    ORDER BY {quoted_rank}'''
                                    
            algaebaseCursor.execute(sql)
            
            higher_taxa = algaebaseCursor.fetchall()
            
            for higher_taxon in higher_taxa:
                
                # Select all rows for this higher taxon
                taxon_name = higher_taxon[rank]
                
                sql = f'''SELECT * FROM taxa
                                WHERE {quoted_rank} = '{taxon_name}'
                                '''
                                
                algaebaseCursor.execute(sql)
                
                taxa = algaebaseCursor.fetchall()
                                
                parent_names = set()
                for taxon in taxa:
                    # Travel up the ranks to find the first non-null higher rank
                    current_index = HIGHER_RANKS.index(rank) - 1
                    parent_name = None
                    while current_index >= 0:
                        potential_parent_rank = HIGHER_RANKS[current_index]
                        if taxon[potential_parent_rank]:
                            parent_name = taxon[potential_parent_rank]
                            break
                        current_index -= 1
                    
                    if parent_name:
                        parent_name_with_rank = f'{parent_name}({potential_parent_rank})'
                        parent_names.add(parent_name_with_rank)
                    
                if len(parent_names) > 1:
                    print(f'Multiple parents found for {rank} {taxon_name}: {parent_names}')
    
    
    def analyze_name_uuids(self, path_to_csv_file):
        # open the csv file
        # the columns of the csv are: name_uuid, taxon_latname and taxon_author
        import csv
        
        with open(path_to_csv_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='|')
            for row in reader:
                name_uuid = row['name_uuid']
                taxon_latname = row['taxon_latname']
                taxon_author = row['taxon_author']
                
                # find the taxon in the AlgaebaseTaxonTree
                tree_entries = AlgaebaseTaxonTree.objects.filter(name_uuid=name_uuid)
                
                tree_entry_exists = tree_entries.exists()
                
                if tree_entry_exists:
                    tree_entry = tree_entries.first()
                    if tree_entry.taxon_latname != taxon_latname or tree_entry.taxon_author != taxon_author:
                        message = f'Inconsistent taxon for name_uuid {name_uuid}: {taxon_latname} {taxon_author} vs {tree_entry.taxon_latname} {tree_entry.taxon_author}'
                        self.logger.info(message)
                
                synonym_entry_exists = False
                
                if not tree_entry_exists:
                    synonym_entries = AlgaebaseTaxonSynonym.objects.filter(name_uuid=name_uuid)
                    synonym_entry_exists = synonym_entries.exists()
                    
                    if synonym_entry_exists:
                        synonym_entry = synonym_entries.first()
                        if synonym_entry.taxon_latname != taxon_latname or synonym_entry.taxon_author != taxon_author:
                            message = f'Inconsistent synonym for name_uuid {name_uuid}: {taxon_latname} {taxon_author} vs {synonym_entry.taxon_latname} {synonym_entry.taxon_author}'
                            self.logger.info(message)
                
                if not tree_entry_exists and not synonym_entry_exists:
                    message = f'Taxon with name_uuid not found: {taxon_latname} {taxon_author} {name_uuid}'
                    self.logger.info(message)
                

            
'''
import xlrd
import os 

def check_seatax():

    dir_path = os.path.dirname(os.path.realpath(__file__))
    
    seataxa_path = os.path.join(dir_path, 'SeaTAXA.xlsx')
    workbook = xlrd.open_workbook(seataxa_path)

    spreadsheet = workbook.sheet_by_name('Tabelle1')

    for row_index, row in enumerate(spreadsheet.get_rows(), 0):

        if row_index == 0:
            continue

        latname = row[0].value

        exists = AlgaebaseTaxonTree.objects.filter(taxon_latname=latname)

        if len(exists) == 1:
            continue
        elif len(exists) == 0:
            exists = AlgaebaseTaxonSynonym.objects.filter(taxon_latname=latname)
            if len(exists) == 0:
                print('Taxon does not exist: {0}'.format(latname))
        else:
            print('Multiple entries found for {0}'.format(latname))
'''