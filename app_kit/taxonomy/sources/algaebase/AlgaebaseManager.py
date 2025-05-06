####################################################################################################################
#
#   IMPORT Algaebase.org
#
####################################################################################################################

from taxonomy.sources.TaxonSourceManager import (TaxonSourceManager, SourceTreeTaxon, d2n, n2d,
                                    SourceSynonymTaxon, VernacularName, TreeCache)

from taxonomy.sources.algaebase.models import AlgaebaseTaxonTree, AlgaebaseTaxonSynonym, AlgaebaseTaxonLocale

import psycopg2, psycopg2.extras, os, csv

from html.parser import HTMLParser



# the CoL2019 uses language names like "English" -> use langcodes
import langcodes, logging

DEBUG = False


# db interface for algaebase 2020 postgres db
algaebaseCon = psycopg2.connect(dbname="algaebase_2020", user="localcosmos", password="localcosmos",
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

SOURCE_NAME = 'algaebase2020'

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

DEBUG = True

class AlgaebaseSourceTreeTaxon(SourceTreeTaxon):

    TreeModel = AlgaebaseTaxonTree


    def __init__(self, latname, author, rank, source, source_id, parent_name, parent_rank, **kwargs):

        super().__init__(latname, author, rank, source, source_id, **kwargs)

        self.parent_rank = parent_rank        
        self.parent_name = parent_name

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
                                    AND id_current_name = 0
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

                    synonym_rank = RANK_MAP[db_taxon['level']]

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
    @classmethod
    def get_scientific_name(cls, db_taxon, taxon_rank):

        if DEBUG == True:
            print('get scientific_name for {0} of {1}'.format(taxon_rank, db_taxon[taxon_rank]))

        # go from current rank upwards up to genus
        if taxon_rank in LOWER_RANKS:

            start_rank = taxon_rank
            start_rank_index = RANKS.index(start_rank)
            genus_index = RANKS.index('genus')

            abbreviation = INFRASPECIFIC_ABBREVIATIONS.get(taxon_rank, '')

            scientific_name = ''

            if db_taxon[start_rank]:
                scientific_name = '{0} {1}'.format(abbreviation, db_taxon[start_rank])
                scientific_name = scientific_name.replace('  ', ' ').strip()
            
            one_rank_up_index = start_rank_index - 1

            while one_rank_up_index >= genus_index:

                one_rank_up = RANKS[one_rank_up_index]
                
                name_part = db_taxon[one_rank_up]

                if name_part:

                    abbreviation = INFRASPECIFIC_ABBREVIATIONS.get(one_rank_up, '')
                    name_part = '{0} {1}'.format(abbreviation, name_part)

                    name_part = name_part.replace('  ', ' ').strip()
                
                    scientific_name = '{0} {1}'.format(name_part, scientific_name)

                scientific_name = scientific_name.replace('  ', ' ').strip()

                one_rank_up_index = one_rank_up_index - 1

        else:
            scientific_name = db_taxon[taxon_rank]

        return scientific_name


class AlgaebaseSourceSynonymTaxon(SourceSynonymTaxon):
    pass


class AlgaebaseTreeCache(TreeCache):

    SourceTreeTaxonClass = AlgaebaseSourceTreeTaxon
    TaxonTreeModel = AlgaebaseTaxonTree
    

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
    # genus Neofragilaria occurs in two different families: Fragilariaceae, Plagiogrammaceae
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

    # author, id impossible for taxon higher than genus
    @classmethod
    def _get_author(cls, db_taxon, taxon_rank):

        author_string = None

        if taxon_rank in LOWER_RANKS:

            ids = list(db_taxon['ids'])
            if len(ids) > 1:
                
                ids_str = ','.join([str(taxon_id) for taxon_id in ids])
                raise ValueError('Multiple ids found: {0}'.format(ids_str))

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
                                    AND id_current_name = 0
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
                            AND id_current_name = 0
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
    
    
    def _get_higher_children_simple(self, source_taxon, parent_rank, parent_name):

        children_rank = self._get_children_rank(parent_rank)
        children_rank_index = RANKS.index(children_rank)

        select_ranks_str, group_by_ranks_str = self._get_select_ranks_str_and_group_by_ranks_str(children_rank)
        null_ranks_str = self._get_null_ranks_str(children_rank)
        grandparent_query = self._get_grandparent_query(source_taxon)

        sql = '''SELECT DISTINCT("{0}"), {1}, ARRAY_AGG("id") AS ids FROM taxa
                    WHERE "{2}" = '{3}'
                    AND "{0}" IS NOT NULL
                    AND id_current_name = 0
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

    # subphylum can be skipped
    def _get_higher_children_phylum(self, source_taxon, parent_rank, parent_name):

        children_rank = self._get_children_rank(parent_rank)

        select_ranks_str, group_by_ranks_str = self._get_select_ranks_str_and_group_by_ranks_str(children_rank)
        grandparent_query = self._get_grandparent_query(source_taxon)

        # get all subphylums
        sql_subphylum = '''SELECT DISTINCT("subphylum"), {0}, ARRAY_AGG("id") AS ids FROM taxa
                    WHERE "phylum" = '{1}'
                    AND "subphylum" IS NOT NULL
                    AND id_current_name = 0
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
                    AND id_current_name = 0
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
    

    # subfamily and / or tribe can be skipped
    def _get_higher_children_family(self, source_taxon, parent_rank, parent_name):

        children_rank = self._get_children_rank(parent_rank)

        select_ranks_str, group_by_ranks_str = self._get_select_ranks_str_and_group_by_ranks_str(children_rank)
        grandparent_query = self._get_grandparent_query(source_taxon)

        # get all subfamilies
        sql_subfamily = '''SELECT DISTINCT("subfamily"), {0}, ARRAY_AGG("id") AS ids FROM taxa
                    WHERE "family" = '{1}'
                    AND "subfamily" IS NOT NULL
                    AND id_current_name = 0
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
                    AND id_current_name = 0
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
                    AND id_current_name = 0
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

    # tribe can be skipped
    def _get_higher_children_subfamily(self, source_taxon, parent_rank, parent_name):
        
        children_rank = self._get_children_rank(parent_rank)

        select_ranks_str, group_by_ranks_str = self._get_select_ranks_str_and_group_by_ranks_str(children_rank)
        grandparent_query = self._get_grandparent_query(source_taxon)

        # get all tribes
        sql_tribe = '''SELECT DISTINCT("tribe"), {0}, ARRAY_AGG("id") AS ids FROM taxa
                    WHERE "subfamily" = '{1}'
                    AND "tribe" IS NOT NULL
                    AND id_current_name = 0
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
                    AND id_current_name = 0
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

    
    def _get_higher_children(self, source_taxon, parent_rank, parent_name):

        if DEBUG == True:
            print('_get_higher_children: parent_rank: {0}, parent_name: {1}'.format(parent_rank, parent_name))


        if parent_rank == 'phylum':
            children_db = self._get_higher_children_phylum(source_taxon, parent_rank, parent_name)

        elif parent_rank == 'family':
            children_db = self._get_higher_children_family(source_taxon, parent_rank, parent_name)
        
        elif parent_rank == 'subfamily':
            children_db = self._get_higher_children_subfamily(source_taxon, parent_rank, parent_name)

        else:
            children_db = self._get_higher_children_simple(source_taxon, parent_rank, parent_name)


        children = []
        
        # children rank might differ within children
        for child in children_db:

            children_rank = child['rank']

            # there might be different authors for the same name
            if children_rank in LOWER_RANKS and len(child['ids']) > 1:

                if children_rank != 'species':
                    raise ValueError('invalid children rank for _get_higher_children: {0}'.format(
                        children_rank))

                for child_id in child['ids']:
                    unique_child = self._get_db_taxon_by_id(child_id)
                    rank_is_valid = self._verify_lower_taxon_rank(unique_child, children_rank)

                    if rank_is_valid == True:
                        source_taxon = self._sourcetaxon_from_db_taxon(unique_child, children_rank,
                                                                       parent_name, parent_rank)
                        children.append(source_taxon)

            elif children_rank == 'genus':
                has_species = self._verify_genus_has_species(child, parent_rank, parent_name)
                if has_species == True:
                    source_taxon = self._sourcetaxon_from_db_taxon(child, children_rank, parent_name,
                                                                   parent_rank)
                    children.append(source_taxon)

            else:

                source_taxon = self._sourcetaxon_from_db_taxon(child, children_rank, parent_name,
                                                               parent_rank)
                children.append(source_taxon)

        return children
    

    # only for species and below
    def _child_already_exists_in_tree(self, source_taxon):

        exists = self.TaxonTreeModel.objects.filter(source_id=str(source_taxon.source_id)).first()

        if exists:
            print('Child already exists: {0}'.format(source_taxon.source_id))
            # make a check if the existence is a valid one, which means the parent has the correct
            # name and rank
            db_taxon = source_taxon._get_source_object()
            scientific_name = source_taxon.get_scientific_name(db_taxon, source_taxon.rank)

            existing_parent = exists.parent

            parent_rank = RANKS[RANKS.index(source_taxon.rank)-1]
            # passing the child, but the parent rank
            parent_taxon_latname = source_taxon.get_scientific_name(db_taxon, parent_rank)

            if existing_parent.taxon_latname == parent_taxon_latname:
                return True
            else:
                raise ValueError('Inconsistent tree: {0} ||| {1}'.format(existing_parent.taxon_latname,
                                                                     parent_taxon_latname))
            
        return False

    # grandparent rank might nor exist
    def _get_grandparent_query(self, parent):

        if DEBUG == True:
            print ('_get_grandparent_query. parent: {0}'.format(parent.latname))

        sql = ''

        parent_rank = parent.rank
        parent_rank_index = RANKS.index(parent_rank)
        grandparent_rank_index = parent_rank_index -1

        if grandparent_rank_index >= 0:

            grandparent_rank = RANKS[grandparent_rank_index]
            
            parent_rank_index = RANKS.index(parent.rank)
            
            if parent_rank_index > 0:

                cache_level_index = self.cache._find_level(parent)

                #if cache_level_index:

                grandparent = self.cache._get_parent(parent)

                #grandparent_rank_index = RANKS.index(grandparent.rank)
                
                #if grandparent_rank_index < parent_rank_index:
                sql = ''' AND "{0}" = '{1}' '''.format(grandparent.rank, grandparent.latname)

                #else:
                #    # error log
                #    print('failed to get grandparent_query: {0} :::: {1}'.format(self.cache, parent))

        return sql
            

    # get children of species, subspecies, variety and forma
    # case: Denticulopsis praedimorpha exists twice in db, with different authors
    # problem: fetching children of Denticulopsis praedimorpha occurs twice
    # problem: a FORMA does not need a VARIETY
    #          if a species has a varieta and a forma without variety, the forma is skipped
    #          solution: search all infraspecies that have NULL columns between species and infraspecifi epithet
    def _get_children_sql(self, source_taxon, children_rank, select_ranks, parent_rank, parent_name,
                          null_ranks_str):

        # psql requires quoted "order", not order
        select_ranks_fixed = ['"{0}"'.format(rank) for rank in select_ranks]
        select_ranks_str = ','.join(select_ranks_fixed)

        group_by_ranks_str = '{0}'.format(children_rank)
        group_by_ranks_str = '"{0}", {1}'.format(group_by_ranks_str, select_ranks_str)

        grandparent_query = self._get_grandparent_query(source_taxon)

        parent_name = parent_name.replace("'", "''")

        sql = '''SELECT DISTINCT("{0}"), {1}, ARRAY_AGG("id") AS ids FROM taxa
                    WHERE "{2}" = '{3}'
                    AND "{0}" IS NOT NULL
                    AND id_current_name = 0
                    AND id != {4}
                    {5}
                    {6}
                    GROUP BY {7}
                    ORDER BY "{0}"'''.format(children_rank, select_ranks_str, parent_rank, parent_name,
                                    source_taxon.source_id, grandparent_query,
                                    null_ranks_str, group_by_ranks_str)

        return sql

        
    def _get_select_ranks(self, rank):
        select_ranks = RANKS[:RANKS.index(rank)]
        return select_ranks
    
    
    def _get_all_subspecies(self, source_taxon):        
        # min rank: species
        # max rank: species
        # variety and forma are NULL

        subspecies_db = []

        source_object = source_taxon._get_source_object()
        
        if source_taxon.rank == 'species':

            children_rank = 'subspecies'
            
            select_ranks = self._get_select_ranks(children_rank)

            parent_rank = source_taxon.rank
            parent_name = source_object[parent_rank]
            
            null_ranks_str = self._get_null_ranks_str(children_rank)

            sql = self._get_children_sql(source_taxon, children_rank, select_ranks, parent_rank, parent_name,
                                         null_ranks_str)

            if DEBUG == True:
                print(sql)

            algaebaseCursor.execute(sql)

            subspecies_db = algaebaseCursor.fetchall()
            
        return subspecies_db
    
    # a variety can be attached to a species or subspecies. The subspecies is optional
    def _get_all_varieties(self, source_taxon):
        # min rank: species
        # max rank: subspecies
        # forma IS NULL
        # if species: subspecies is NULL

        varieties_db = []

        source_object = source_taxon._get_source_object()

        if source_taxon.rank in ['species', 'subspecies']:

            children_rank = 'variety'
            parent_rank = source_taxon.rank
            parent_name = source_object[parent_rank]
            select_ranks = self._get_select_ranks(children_rank)

            if source_taxon.rank == 'species':
                null_ranks_str = self._get_null_ranks_str(children_rank)
                null_ranks_str = ''' {0} AND "subspecies" IS NULL '''.format(null_ranks_str)

            elif source_taxon.rank == 'subspecies':
                null_ranks_str = self._get_null_ranks_str(children_rank)


            sql = self._get_children_sql(source_taxon, children_rank, select_ranks, parent_rank, parent_name,
                                         null_ranks_str)

            if DEBUG == True:
                print(sql)

            algaebaseCursor.execute(sql)

            varieties_db = algaebaseCursor.fetchall()

        return varieties_db
    

    def _get_all_formas(self, source_taxon):
        # min rank: species
        # max rank: variety
        # if species: subspecies IS NULL AND variety IS NULL
        # if subspecies: variety IS NULL

        formas_db = []

        source_object = source_taxon._get_source_object()

        if source_taxon.rank in ['species', 'subspecies', 'variety']:

            children_rank = 'forma'
            parent_rank = source_taxon.rank
            parent_name = source_object[parent_rank]
            select_ranks = self._get_select_ranks(children_rank)
            
            # forma attached to a species
            if source_taxon.rank == 'species':
                null_ranks_str = self._get_null_ranks_str(children_rank)
                null_ranks_str = ''' {0} AND "subspecies" IS NULL
                                            AND "variety" IS NULL '''.format(null_ranks_str)

            # forma attached to subspecies
            elif source_taxon.rank == 'subspecies':
                null_ranks_str = self._get_null_ranks_str(children_rank)
                null_ranks_str = ''' {0} AND "variety" IS NULL '''.format(null_ranks_str)

            # forma attached to variety
            elif source_taxon.rank == 'variety':
                null_ranks_str = self._get_null_ranks_str(children_rank)

            sql = self._get_children_sql(source_taxon, children_rank, select_ranks, parent_rank, parent_name,
                                         null_ranks_str)

            if DEBUG == True:
                print(sql)

            algaebaseCursor.execute(sql)

            formas_db = algaebaseCursor.fetchall()

        return formas_db
    


    def _get_lower_children(self, source_taxon):

        children = []

        source_object = source_taxon._get_source_object()
        parent_rank = source_taxon.rank
        parent_name = source_object[parent_rank]

        ranked_children = {
            'subspecies' : self._get_all_subspecies(source_taxon),
            'variety' : self._get_all_varieties(source_taxon),
            'forma' : self._get_all_formas(source_taxon),
        }

        children_db = self._children_dict_to_children_list(ranked_children)

        ##################################################################################
        # Check if the children already have been assigned to a different parent with the
        # same name
        ##################################################################################

        # there might be different authors for the same name

        for child in children_db:

            children_rank = child['rank']

            for child_id in child['ids']:
                unique_child = self._get_db_taxon_by_id(child_id)

                source_taxon = self._sourcetaxon_from_db_taxon(unique_child, children_rank,
                                                               parent_name, parent_rank)

                exists = self._child_already_exists_in_tree(source_taxon)
                if not exists:
                    children.append(source_taxon)

        return children


    ###
    # getting children in algaebase depends on the higher taxon, as higher taxa are not listed
    # in the tree as taxa, but only as higher taxa of species
    ###
    def _get_children(self, source_taxon):

        if DEBUG == True:
            print('_get_children for {0} {1}'.format(source_taxon.latname, source_taxon.author))


        if source_taxon.rank in LOWER_RANKS:
            children = self._get_lower_children(source_taxon)

        else:
            
            parent_rank = source_taxon.rank
            source_object = source_taxon._get_source_object()
            parent_name = source_object[parent_rank]

            # this does not work for subspecies, variety and form - for those, more WHERE clauses are required
            children = self._get_higher_children(source_taxon, parent_rank, parent_name)

        if DEBUG == True:
            print('found {0} children for {1}'.format(len(children), source_taxon.latname))

        return children


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
        
                if taxon['id_current_name'] == 0:

                    if not AlgaebaseTaxonTree.objects.filter(source_id=taxon['id']).exists():

                        if taxon['level'] == 'F':

                            # get the species of this form
                            sql = '''SELECT * FROM taxa
                                WHERE "genus" = '{0}'
                                AND "family" = '{1}'
                                AND "species" = '{2}'
                                AND "subspecies" IS NULL
                                AND "variety" IS NULL
                                AND "forma" IS NULL'''.format(taxon['genus'], taxon['family'],
                                                                    taxon['species'])

                            algaebaseCursor.execute(sql)

                            species = algaebaseCursor.fetchall()
                            if len(species) == 0:
                                self._integrate_forma_without_species(taxon)

                            elif len(species) == 1:
                                self._integrate_forma_of_synonym(taxon, species[0])

                            else:
                                self.logger.info('Multiple species found for forma {0}: {1}'.format(taxon,
                                                                                                    species))        

                        else:
                            self.logger.info('Failed to integrate taxon, not a forma: {0}'.format(taxon))

                else:
                    # it is a synonym
                    if not AlgaebaseTaxonSynonym.objects.filter(source_id=taxon['id']).exists():
                        self.logger.info('Failed to integrate synonym: {0}'.format(taxon))

            offset += limit
            source_query = '''SELECT * FROM taxa ORDER BY id LIMIT {0} OFFSET {1}'''.format(limit, offset)
            algaebaseCursor.execute(source_query)
            taxa = algaebaseCursor.fetchall()
            

    def _integrate_forma_without_species(self, taxon):

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

    
    def _integrate_forma_of_synonym(self, taxon, species):

        if species['id_current_name'] != 0:

            synonym = AlgaebaseTaxonSynonym.objects.get(source_id=str(species['id']))
            primary_taxon = synonym.taxon

            sql = '''SELECT * from taxa where id = {0}'''.format(primary_taxon.source_id)

            if DEBUG == True:
                print(sql)

            algaebaseCursor.execute(sql)

            current_species = algaebaseCursor.fetchone()

            parent_name = current_species['species']

            taxon_clean = {}
            taxon_clean['ids'] = [taxon['id']]
            
            for key, value in taxon.items():
                taxon_clean[key] = value
                
            source_taxon = self._sourcetaxon_from_db_taxon(taxon_clean, 'forma', parent_name, 'species')

            # add forma as a child
            print('current name id: {0}'.format(species['id_current_name']))
            parent = AlgaebaseTaxonTree.objects.get(source_id='{0}'.format(species['id_current_name']))

            # get the nuid
            children = AlgaebaseTaxonTree.objects.filter(parent=parent).order_by('-taxon_nuid')

            if children:
                highest_nuid = children[0].taxon_nuid
                new_suffix = d2n(n2d(highest_nuid[-3:]) + 1)
            else:
                new_suffix = '001'

            print('integrating {0}'.format(taxon))
            print('parent: {0}, nuid: {1}'.format(parent, parent.taxon_nuid))

            nuid_prefix = parent.taxon_nuid
            taxon_nuid = '{0}{1}'.format(nuid_prefix, new_suffix)
            
            taxon = self.TaxonTreeModel(
                parent = parent,
                taxon_nuid = taxon_nuid,
                taxon_latname = source_taxon.latname,
                taxon_author = source_taxon.author,
                source_id = source_taxon.source_id,
                rank = source_taxon.rank,
                is_root_taxon = False,
            )

            taxon.save()

        else:
            self.logger.info('Failed to integrate forma: {0}, because parent is not a synonym: {1}'.format(
                taxon, species))

    # some species do not have a phylum assigned
    def _integrate_orphans(self):
        pass


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
                        AND "id_current_name" = 0'''.format(genus, family, species)

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
        level = taxon['level']

        if level == 'S':

            for l in ['U', 'V', 'F']:

                rank = RANK_MAP[l]

                if taxon[rank] != None:
                    self.logger.info('Level is species, but infraspecific epithet is present: {0}:{1}'.format(
                        rank, taxon[rank]))

        # S may not be null, taxon with S only has to be presend, V and F have to be null
        elif level == 'U':

            for l in ['V', 'F']:

                rank = RANK_MAP[l]

                if taxon[rank] != None:
                    self.logger.info('Level is subspecies, but lower infraspecific epithet is present: {0}:{1}'.format(
                        rank, taxon[rank]))

            # check if species exists
            self.check_if_species_exists(taxon)


        elif level == 'V':

            for l in ['F']:

                rank = RANK_MAP[l]

                if taxon[rank] != None:
                    self.logger.info('Level is subspecies, but lower infraspecific epithet is present: {0}:{1}'.format(
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

        if not AlgaebaseTaxonSynonym.objects.filter(source_id=taxon['id']).exists():
            message = 'missing synonym: {0}'.format(synonym)
            self.logger.info(message)
        

    # Staurosira capucina var. mesolepta, (Rabenhorst) Comère 1892) already exists. ids: 167085, 138580
    def check_taxon_unique(self, taxon):
        sql = ''' SELECT * FROM taxa WHERE "phylum" = '{0}' '''.format(taxon['phylum'])

        for rank in RANKS:

            if taxon[rank]:
                qry = ''' AND "{0}" = '{1}' '''.format(rank, taxon[rank])
            else:
                qry = ''' AND "{0}" IS NULL '''.format(rank)

            sql = '{0} {1}'.format(sql, qry)


        author = taxon['nomenclatural_authorities']
        author = author.replace("'","''")
        author_sql = ''' AND "nomenclatural_authorities" = '{0}' '''.format(author)

        year_sql = ''' AND "year_of_publication" = '{0}' '''.format(taxon['year_of_publication'])

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

        source_query = '''SELECT * FROM taxa WHERE id_current_name = 0 LIMIT %s OFFSET %s''' %(limit, offset)
        algaebaseCursor.execute(source_query)
        taxa = algaebaseCursor.fetchall()

        while taxa:

            for taxon in taxa:
        
                self.check_existence_in_lc(taxon)
                self.validate_parent(taxon)
                self.check_taxon_unique(taxon)

            offset += limit
            source_query = '''SELECT * FROM taxa WHERE id_current_name = 0 LIMIT %s OFFSET %s''' %(limit, offset)
            algaebaseCursor.execute(source_query)
            taxa = algaebaseCursor.fetchall()
        
        
    def analyze_synonyms(self):

        limit = 10000
        offset = 0

        source_query = '''SELECT * FROM taxa WHERE id_current_name != 0 LIMIT %s OFFSET %s''' %(limit, offset)
        algaebaseCursor.execute(source_query)
        synonyms = algaebaseCursor.fetchall()

        while synonyms:

            for taxon in synonyms:
        
                self.check_synonym_existence_in_lc(taxon)
                self.validate_parent(taxon)
                self.check_taxon_unique(taxon)

            offset += limit
            source_query = '''SELECT * FROM taxa WHERE id_current_name != 0 LIMIT %s OFFSET %s''' %(limit, offset)
            algaebaseCursor.execute(source_query)
            synonyms = algaebaseCursor.fetchall()
        


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
