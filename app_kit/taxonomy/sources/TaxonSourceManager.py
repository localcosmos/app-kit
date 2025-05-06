###################################################################################################################
#
# TAXON SOURCE MANAGER
# - import or update taxonomic database
# - usage: init TaxonSourceManager: manager = TaxonSourceManager()
# - run: manager.update_database()
#
###################################################################################################################
'''
    Interface for managing taxonomic sources
'''
from django.db.models.functions import Length
import sys, os, json
import time

from django.db import transaction

'''
    some vernacular names might contain html characters
'''

# Python 3
import logging, html


'''
    base
'''

nuid36 = ['0','1','2','3','4','5','6','7','8','9',                                                                    
          'a','b','c','d','e','f','g','h','i','j','k','l','m',
          'n','o','p','q','r','s','t','u','v','w','x','y','z']


def d2n(integer):
    number_n36_list = []

    integer = int(integer)
    
    add_trailing_zero = False
    add_trailing_doublezero = False

    if integer < 36:
        add_trailing_doublezero = True
    elif integer < 1296:
        add_trailing_zero = True
        
    if integer != 0:
        while integer != 0:
            rest = integer % 36
            rest_n36 = nuid36[int(rest)]
            integer = int(integer / 36)
            number_n36_list.insert(0,'%s' %str(rest_n36))

            
        if add_trailing_zero:
            number_n36_list.insert(0,'0')
        elif add_trailing_doublezero:
            number_n36_list.insert(0,'00')
        number_n36 = ''.join(number_n36_list)
    else:
        number_n36 = '000'
    return number_n36


def n2d(nuid):
    
    # before reversing, strip off trailing 0
    while nuid.startswith('0'):
        nuid = nuid[1:]
        
    nuid = nuid [::-1] # reverse the string
    dec = 0
    
    for exponent, x in enumerate(nuid, start=0):
        x_dec = nuid36.index(x)
        dec += x_dec * (36**exponent)

    return dec



'''
    vernacular names
'''
class VernacularName:

    def __init__(self, name, language, preferred=False, iso6392=None):
        self.name = html.unescape(name.strip())
        self.language = language.strip().lower() # iso6391 en, fr, de
        self.preferred = preferred
        self.iso6392 = iso6392 # 3-digit

'''
    SourceTaxon
    - superclass for SourceTreeTaxon, SourceSynonymTaxon
    - MAPPED_TAXON_RANKS maps duplicate ranks to one rank, eg in col: subsp == subspecies
    - SourceTaxon.source_object is only in kwargs because it cant be dumped/restored after dump
'''

class SourceTaxon:

    rank_map = {}

    def __init__(self, latname, author, rank, source, source_id, **kwargs):

        self.latname = latname
        self.author = author

        self.rank_map = kwargs.get('rank_map', {})
        
        if rank in self.rank_map:
            rank = self.rank_map[rank]
            
        self.rank = rank

        # source
        self.source = source
        self.source_id = str(source_id)
        self.source_object = kwargs.get('source_object', None)

        self.kwargs = kwargs

    def _get_source_object(self):
        raise NotImplementedError('SourceTaxon subclasses need a _get_source_object method')


    def get_source_object(self):

        if self.source_object is not None:
            return self.source_object

        else:
            source_object =  self._get_source_object()
            self.source_object = source_object
            return self.source_object

    def _get_vernacular_names(self):
        raise NotImplementedError('SourceTaxon subclasses need a _get_vernacular_names method')

    def vernacular_names(self):
        if not hasattr(self, 'vernacular_names_list'):
            self.vernacular_names_list = self._get_vernacular_names()
            
        return self.vernacular_names_list

    def _get_synonyms(self):
        raise NotImplementedError('SourceTaxon subclasses need a _get_synonyms method')

    def synonyms(self):
        if not hasattr(self, 'synonyms_list'):
            self.synonyms_list = self._get_synonyms()

        return self.synonyms_list


    '''
    nuid and rank_map are optional and therefore in kwargs -> put into dic_kwargs
    '''
    def to_dict(self):

        dic_kwargs = self.kwargs.copy()

        if self.get_nuid() is not None:
            dic_kwargs['nuid'] = self.get_nuid()
        
        dic = {
            'latname' : self.latname,
            'author' : self.author,
            'rank' : self.rank,
            'source' : self.source,
            'source_id' : self.source_id,
            'kwargs' : dic_kwargs,
        }

        return dic


class SourceSynonymTaxon(SourceTaxon):
    is_synonym = True
    is_tree_taxon = False
    
    
class SourceTreeTaxon(SourceTaxon):

    # needed fo fetching nuids from already saved taxa
    TreeModel = None
    
    is_synonym = False
    is_tree_taxon = True
    nuid = None

    '''
    nuid management
    '''
    def set_nuid(self, nuid):
        self.nuid = nuid

    # when travelling up or right in the sourcetree, these entries already exist in db
    # the source_taxon gets no nuids from the source tree -> fetch it from db to allow further
    # downwards travelling
    def set_nuid_from_db(self):

        if self.nuid is None:
            print('setting nuid from db')
            db_entry = self.TreeModel.objects.filter(source_id=self.source_id).first()
            if db_entry:
                self.nuid = db_entry.taxon_nuid
            else:
                print('No db entry found for source_id: {0}'.format(self.source_id))

        return self.nuid

    def get_nuid(self):
        if self.nuid is None:
            self.set_nuid_from_db()

        return self.nuid

    # parent in lc taxon db
    def get_parent(self):
        nuid = self.get_nuid()
        parent_nuid = nuid[:-3]
        if len(parent_nuid) > 0:
            parent = self.TreeModel.objects.get(taxon_nuid=parent_nuid)

            return parent

        return None

    
'''
    The Tree Models are only views
    - if a node is NEW (not only renamed), everything below that node is considered new
'''

'''
    TreeClimberState
    - for resuming and dumping the current state of the climb
    - the root taxa are important
'''
class TreeClimberState:

    last_parent = None
    last_saved_child = None
    current_root_taxon = None
    

    def __init__(self, SourceTreeTaxonClass, path):
        self.root_dir = path
        self.dump_filepath = os.path.join(self.root_dir, 'treeclimberstate.json')

        self.SourceTreeTaxonClass = SourceTreeTaxonClass

    def _source_taxon_from_dict(self, dic):

        source_taxon = self.SourceTreeTaxonClass(
            dic['latname'],
            dic['author'],
            dic['rank'],
            dic['source'],
            dic['source_id'],
            **dic['kwargs']
        )

        return source_taxon
    

    def load_last_state(self):

        if os.path.isfile(self.dump_filepath):

            with open(self.dump_filepath, 'r') as f:
                state = json.load(f)


            current_root_taxon_json = state['current_root_taxon']

            current_root_taxon = self._source_taxon_from_dict(current_root_taxon_json)
            self.set_current_root_taxon(current_root_taxon)

            last_parent_json = state.get('last_parent', None)

            if last_parent_json:
                last_parent = self._source_taxon_from_dict(last_parent_json)
                self.set_last_parent(last_parent)

            last_saved_child_json = state.get('last_saved_child', None)
            if last_saved_child_json:
                last_saved_child = self._source_taxon_from_dict(last_saved_child_json)
                self.set_last_saved_child(last_saved_child)
            
    def set_current_root_taxon(self, source_taxon):
        self.current_root_taxon = source_taxon

    def set_last_parent(self, source_taxon):
        self.last_parent = source_taxon

    def set_last_saved_child(self, source_taxon):
        self.last_saved_child = source_taxon

    def dump(self):

        # get the filepath of the manager
        state = {
            'current_root_taxon' : self.current_root_taxon.to_dict(),
            'last_parent' : self.last_parent.to_dict(),
            'last_saved_child' : self.last_saved_child.to_dict(),
            'timestamp' : int(time.time())
        }

        with open(self.dump_filepath, 'w') as f:
            f.write(json.dumps(state))
        

'''
    TreeCache
    - both saving fast and climbing up the saved tree fast/looking up nuids is impossible if using DB
    - faster lookup of get_next_downclimb_taxon
    - travels the cached tree, only upwards and right
    - upstream method for travelling up after resuming anywhere in the tree
'''
class TreeCache:

    SourceTreeTaxonClass = None
    TaxonTreeModel = None

    def __init__(self):
        
        self.upstream_is_built = False
    
        # a list of dictionaries {'parent_taxon': source_taxon, 'children':[]}
        self.cache = []

    '''
    adding to cache always adds a list below the list in which the parent_taxon is in
    all children lists
    '''    
    def add(self, parent_taxon, children):
        
        entry = self._make_cache_entry(parent_taxon, children)
        cache_length = len(self.cache)

        # the first entry is just added
        # all the following entries have to reference an entry in the cache
        # climbing down just appends entries, climbing up searches the parent taxon and inserts
        # below, removing all entries that are below the inserted entry
        if len(self.cache) == 0:
            self.cache.append(entry)
            # make sure the cache up to kingdom exists
            self._build_upstream()
        else:
            # find the level in which the parent taxon is present
            level_index = self._find_level(parent_taxon)

            # append or replace
            if cache_length -1 >= level_index + 1:
                self.cache[level_index+1] = entry
            else:
                self.cache.append(entry)

            for i in range(level_index+2, cache_length):
                self.cache[i] = None

    '''
    the main functions of the TreeCache Class
    - getting next sibling from cache
    - getting parent from cache
    '''
    def _get_parent(self, source_taxon):

        level_index = self._find_level(source_taxon)

        level = self.cache[level_index]

        for child in level['children']:
            if child.latname == source_taxon.latname and child.author == source_taxon.author and child.source_id != source_taxon.source_id:
                raise ValueError('get_parent: latname match but source_id mismatch')

        
        parent_taxon = level['parent_taxon']

        return parent_taxon

    def _get_next_sibling(self, source_taxon):
        level_index = self._find_level(source_taxon)

        level = self.cache[level_index]

        next_sibling_index = None

        for counter, child in enumerate(level['children']):

            if child.latname == source_taxon.latname and child.author == source_taxon.author and child.source_id == source_taxon.source_id:
                next_sibling_index = level['children'].index(child) + 1
                break

        if next_sibling_index:
            if len(level['children']) -1 >= next_sibling_index:
                return level['children'][next_sibling_index]

        return None
        
    
    def get_next_downclimb_taxon(self, source_taxon):
        # first, get siblings
        # second, get parent
        next_parent = self._get_next_sibling(source_taxon)

        # if the rightmost is reached
        while next_parent is None:

            # go 1 up
            parent = self._get_parent(source_taxon)

            # if the top of the tree is reached, return None
            if parent is None:
                break

            # otherwise go 1 right
            next_parent = self._get_next_sibling(parent)

            # if no next parent is there, assign the current parent as the source_taxon
            if next_parent is None:
                source_taxon = parent

        if next_parent is not None:
            # the parent already is in the db -> set_nuid_from_db
            next_parent.set_nuid_from_db()
            
        return next_parent

           
    def _build_upstream(self):
        
        if self.upstream_is_built:
            raise ValueError('Upstream already built')

        toplevel = self.cache[0]

        parent_taxon = toplevel['parent_taxon']

        root_taxon = None

        while parent_taxon:

            print('building upstream from %s' % parent_taxon.latname)

            root_taxon = parent_taxon

            children = self._get_siblings_group_from_db(parent_taxon)
            parent_taxon = self._get_parent_taxon_from_db(parent_taxon)

            entry = self._make_cache_entry(parent_taxon, children)

            self.cache.insert(0, entry)


        self.upstream_is_built = True


    def _get_parent_taxon_from_db(self, source_taxon):
        # the cache can only travel already stored taxa
        nuid = source_taxon.get_nuid()

        if len(nuid) > 3:

            parent_nuid = nuid[:-3]

            db_taxon = self.TaxonTreeModel.objects.get(taxon_nuid=parent_nuid)
            parent_taxon = self._make_source_taxon(db_taxon)
            parent_taxon.set_nuid(db_taxon.taxon_nuid)

        else:
            parent_taxon = None
        
        return parent_taxon
        
        
    def _get_siblings_group_from_db(self, source_taxon):
        # the cache can only trabel already stored taxa
        siblings = []
        
        nuid = source_taxon.get_nuid()

        if len(nuid) > 3:

            parent_nuid = nuid[:-3]

            db_taxa = self.TaxonTreeModel.objects.annotate(nuid_len=Length('taxon_nuid')).filter(
                taxon_nuid__startswith=parent_nuid, nuid_len=len(nuid)).exclude(
                    taxon_nuid=parent_nuid).order_by('taxon_nuid')

        else:
            db_taxa = self.TaxonTreeModel.objects.annotate(nuid_len=Length('taxon_nuid')).filter(nuid_len=3)

        for db_taxon in db_taxa:
            source_taxon = self._make_source_taxon(db_taxon)
            # make sure to set the nuid
            source_taxon.set_nuid(db_taxon.taxon_nuid)

            siblings.append(source_taxon)

        return siblings
        
    def _make_source_taxon(self, db_taxon):
        raise NotImplementedError('TreeCache Subclasses need a _make_source_taxon method')

    def _make_cache_entry(self, parent_taxon, children):
        # sort children by latname
        children.sort(key=lambda taxon: taxon.latname)
        
        cache_entry = {
            'parent_taxon' : parent_taxon,
            'children' : children
        }

        return cache_entry

    '''
    find_level only uses children, not parent_taxon
    '''
    def _find_level(self, source_taxon):
        # iterate over all levels in reverse order without reversing the list
        for i in range(-len(self.cache), 0):
            level_index = -i-1
            level = self.cache[level_index]

            # removed levels are set to None instead of shortening the list for performance reasons
            if level is not None:
                for child in level['children']:
                    if child.source_id == source_taxon.source_id:
                        return level_index

        return None



'''
    TSM
    __ prefixed methods indicate a manager specific method
    WorkFlow:
    - 1. fetch all root taxa [manager specific], sort these root taxa alphabetically
    - 2. assign nuids to all root taxa
    - 3. iterate over all root taxa 
    - - - 3.1. fetch all children [manager specific]
    - - - 3.2. compare with existing children and assign nuids to all new children
    - - - 3.3. save all new children
    - - - 3.4. return the first child (SourceTreeTaxon)
    - - - 3.5. check for new children and a) climb down if children, go to next sibling [manager specific] if no children
    - - - 3.6. if the last sibling is reached, go to parent and iterate over siblings until the last sibling is reached
    - - - 3.7. if no more parent is available, finish
    - fetches nuid from existing db for travelling the tree
'''
class TaxonSourceManager:

    # the classes are only used by manager specific methods
    # the manager independent methods use only instances of these classes
    SourceTreeTaxonClass = None
    SourceSynonymTaxonClass = None

    # classes and instances only used by methods of the independant manager
    TaxonTreeModel = None
    TaxonSynonymModel = None
    TaxonLocaleModel = None

    # caching
    TreeCacheClass = None

    source_name = None

    # the subclass needs to implement the taxon models
    def __init__(self):

        # path = os.path.dirname(os.path.abspath(__file__)) - does not respect subclasses
        # respect subclasses
        path = os.path.dirname(sys.modules[self.__module__].__file__)
        
        self.state = TreeClimberState(self.SourceTreeTaxonClass, path)

        self.cache = self.TreeCacheClass()

        self.first_run = False

        self.logger = self._get_logger()


    def _get_logger(self):
        logger = logging.getLogger(self.source_name)

        
        logging_folder = '/var/log/lc-taxonomy/'

        if not os.path.isdir(logging_folder):
            os.makedirs(logging_folder)

        logfile_path = os.path.join(logging_folder, 'TaxonSourceManager')
        hdlr = logging.FileHandler(logfile_path)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        logger.addHandler(hdlr)
        logger.setLevel(logging.INFO)

        return logger

    def _get_root_source_taxa(self):
        raise NotImplementedError('Tree Managers need a _get_root_source_taxa method')

    # fetch all root source taxa and sort them alphabetically
    def _get_sorted_root_source_taxa(self):
        root_taxa = self._get_root_source_taxa()

        # sort the taxa for assigning nuids
        root_taxa.sort(key=lambda taxon: taxon.latname)

        return root_taxa
    
    '''
    save the taxon and all its vernacular names into the LocalCosmos specific *Taxon* Tables
    should be the same for all sources
    '''
    def _save_new_taxon(self, source_taxon, is_root_taxon=False):

        parent = source_taxon.get_parent()

        taxon = self.TaxonTreeModel(
            parent = parent,
            taxon_nuid = source_taxon.get_nuid(),
            taxon_latname = source_taxon.latname,
            taxon_author = source_taxon.author,
            source_id = source_taxon.source_id,
            rank = source_taxon.rank,
            is_root_taxon = is_root_taxon,
        )

        taxon.save()

        # this is a new taxon that does not exist yet in the db -> just save synonyms and vernaculars directly
        # print('saving synonyms')
        with transaction.atomic():
            for synonym in source_taxon.synonyms():
                self._save_taxon_synonym(taxon, synonym)
        # print('saving vernaculars')
        with transaction.atomic():
            for vernacular_name in source_taxon.vernacular_names():
                self._save_taxon_vernacular_name(taxon, vernacular_name)
        # print('done')

    '''
    this does not perform any checks, it just saves
    - do not use objects.create() - which will create unique slugs which is slow
    '''
    def _save_taxon_synonym(self, db_taxon, source_synonym):

        synonym = self.TaxonSynonymModel(
            taxon = db_taxon,
            taxon_latname = source_synonym.latname,
            taxon_author = source_synonym.author,
            source_id = source_synonym.source_id,
        )

        synonym.save()

    '''
    this does not perform any checks, it just saves
    - do not use objects.create() - which will create unique slugs which is slow
    '''
    def _save_taxon_vernacular_name(self, db_taxon, vernacular_name):

        vernacular = self.TaxonLocaleModel(
            taxon = db_taxon,
            name = vernacular_name.name,
            language = vernacular_name.language,
            preferred = vernacular_name.preferred,
            iso6392 = vernacular_name.iso6392,
        )

        vernacular.save()

    '''
    this method reads the source db and updates the LC database
    - the root taxa do not have a parent taxon, otherwise their parent would be the root taxon
    - an iteration over all root taxa is needed
    '''
    def update_database(self):

        root_taxa = self._get_sorted_root_source_taxa()
        
        # check for existing taxa and assign their nuids, needed for db update
        for taxon in root_taxa:
            lc_db_taxon = self.TaxonTreeModel.objects.filter(is_root_taxon=True, taxon_latname=taxon.latname).order_by('taxon_latname').first()
            if lc_db_taxon:
                # use the database nuid
                taxon.set_nuid(lc_db_taxon.taxon_nuid)
            

        # this method assigns nuid - to the currently non existing root_taxa
        new_root_taxa = self._compare_new_children_with_existing_children(root_taxa)

        for root_taxon in new_root_taxa:
            self._save_new_taxon(root_taxon, is_root_taxon=True)

        # work ALL root_taxa, starting with the first one
        root_taxon = root_taxa[0]

        print('working new root taxon: {0}'.format(root_taxon.latname))            
        self.state.set_current_root_taxon(root_taxon)
            
        self._climb_tree(root_taxon)


    '''
    if the creation of the taxonomic database crashed or was manually aborted, resume
    '''
    def resume(self):
        
        self.state.load_last_state()
        
                # first finish the unfinished root_taxon branch
        # self.state.last_parent is always set - it is either the current root taxon or the last_parent
        # climbing down from the last_parent will ignore already existing taxa and do an update
        print('resuming with %s ' % self.state.last_parent.latname)
        self._climb_tree(self.state.last_parent)
        
    '''
    _climb tree combines both downwards and upwards climbing into a mechanism covering the whole tree
    1. climbs down from start_taxon
    2. fetches next_parent, which also can be a member of the last group of children
    3. climb down again
    '''
    def _climb_tree(self, start_taxon):

        # climb as long as there are "parent taxa" found - defined as a taxon that has children
        continue_climbing = True

        downclimb_counter = 0

        while continue_climbing:

            downclimb_counter += 1

            # print('climbing down from %s' %(start_taxon.latname))
            # climb down until no children of the leftmost branch are present anymore
            # last_child is the first child of the last group of children
            # during _climb_down (or methods used in it) nuids have to be set and saved for new taxa
            # the last_child as a SourceTreeTaxon instance either has a nuid set - or can fetch the nuid from the target db
            last_child = self._climb_down(start_taxon)

            message = 'last_child: {0}, nuid: {1}'.format(last_child.latname, last_child.get_nuid())
            print(message)
            # self.logger.info(message)

            # search siblings of this childless taxon, or parent siblings if no siblings available
            # start_taxon is always the last child, which is the first child of the last group of children
            # climbing up always uses the new tree - but the taxa it walks already have been saved and have nuids
            # the nuids have to be fetched from the lc db

            # get next parent node
            # first, this searches for siblings, then for parent siblings
            # use caching mechanism for speed
            # print('climbing up from %s' %(last_child.latname))
            next_parent = self.cache.get_next_downclimb_taxon(last_child)


            if next_parent:
                start_taxon = next_parent
                message = 'starting nuid (next_parent): {0}'.format(start_taxon.get_nuid())
                print(message)
                # self.logger.info(message)
                
            else:
                continue_climbing = False


            if downclimb_counter % 100 == 0:
                print('downclimb_counter: %s' % downclimb_counter)

        # return True when done
        return True


    '''
    remove or add existing/new synonyms for a taxon that exists in the db
    - existing_taxon is a TaxonTree instance
    - child is a self.SourceTreeTaxonClass instance
    '''
    def _check_existing_taxon_synonyms(self, existing_taxon, source_taxon):

        source_taxon_synonym_latnames = set([synonym.latname for synonym in source_taxon.synonyms()])

        if self.first_run == True:
            existing_synonyms_latnames = []
        else:
            existing_synonyms = self.TaxonSynonymModel.objects.filter(taxon=existing_taxon)
            existing_synonyms_latnames = set(list(existing_synonyms.values_list('taxon_latname', flat=True)))

        # get all latnames that are no longer present
        if self.first_run == False:
            delete_latnames = existing_synonyms_latnames - source_taxon_synonym_latnames
            self.TaxonSynonymModel.objects.filter(
                taxon=existing_taxon, taxon_latname__in=list(delete_latnames)).delete()

        # get all new latnames
        new_latnames = source_taxon_synonym_latnames - existing_synonyms_latnames

        with transaction.atomic():
            for synonym in source_taxon.synonyms():
                if synonym.latname in new_latnames:
                    self._save_taxon_synonym(existing_taxon, synonym)


    '''
    remove or add existing/new vernacular names for a taxon that exists in the db
    - existing_taxon is a TaxonTree instance
    - child is a self.SourceTreeTaxonClass instance
    '''
    def _check_existing_taxon_vernacular_names(self, existing_taxon, source_taxon):

        if self.first_run == True:
            existing_names = []
        else:
            existing_names = list(self.TaxonLocaleModel.objects.filter(taxon=existing_taxon))

        delete_names = existing_names[:] # shallow copy

        new_vernacular_names = []
        
        # check all vernacular names and languages
        for vernacular in source_taxon.vernacular_names():

            exists = None

            for locale in existing_names:

                if vernacular.name == locale.name and vernacular.language == locale.language:
                    exists = locale
                    break

            if exists is None:
                new_vernacular_names.append(vernacular)
                
            else:
                for existing in delete_names:
                    if existing.name == vernacular.name and existing.language == vernacular.language:
                        delete_names.pop(delete_names.index(existing))
                        break

        for delete_name in delete_names:
            delete_name.delete()

        with transaction.atomic():
            for vernacular_name in new_vernacular_names:
                self._save_taxon_vernacular_name(existing_taxon, vernacular_name)
                

    '''
    compare old children with current queried children
    - return new_children
    - delete no longer existing children
    - ensure that there are no duplicates -> duplicates with different author are saved as synonyms
    - check if that name already exists as a child of this parent
    - check synonyms:
    - there may be new synonyms for already existing taxa. this should be handled/triggered here
    - there might be removed synonyms

    - THIS METHOD ASSIGNS NUIDS

    - parent_taxon == None for root taxa
    '''
    def _compare_new_children_with_existing_children(self, children, parent_taxon=None):

        # get existing children from tree
        # existing_children_query contains all names, including synonyms
        
        existing_children_query = self._get_existing_children_query(parent_taxon)

        # new_children that need to be added to the db
        new_children = []

        cache_children = []

        # children that are in the db AND in the children list
        still_included_children = []

        # first, compare the latnames
        existing_children = []
        existing_children_map = {}
        
        if self.first_run == False:
            for taxon in existing_children_query:
                existing_children.append({'author': taxon.taxon_author, 'latname': taxon.taxon_latname})

                author = taxon.taxon_author
                if not author:
                    author = 'None'
                key = " ".join([taxon.taxon_latname, author])
                existing_children_map[key] = taxon

        for child in children:

            child_dict = {'author' : child.author, 'latname' : child.latname}
            still_included_children.append(child_dict)
            
            if child_dict in existing_children:
                # the taxon already exists in the tree
                # check synonyms for existing taxa
                existing_taxon = existing_children_query.filter(taxon_latname=child.latname,
                                                                taxon_author=child.author)
                if len(existing_taxon) > 1:
                    raise ValueError('Found more than one child with the same latname/author combination in the children group: %s' % child.latname)

                existing_taxon = existing_taxon[0]
                self._check_existing_taxon_synonyms(existing_taxon, child)
                self._check_existing_taxon_vernacular_names(existing_taxon, child)

                existing_taxon_source_taxon = self.SourceTreeTaxonClass(
                    existing_taxon.taxon_latname, existing_taxon.taxon_author, existing_taxon.rank,
                    self.TaxonTreeModel.__class__.__name__, existing_taxon.source_id, nuid=existing_taxon.taxon_nuid
                )
                cache_children.append(existing_taxon_source_taxon)
                
                continue
            
            # skip duplicates with the same author AND name
            # potential problem: one may have children
            is_new = True
            
            for added_child in new_children:
                if child.latname == added_child.latname and child.author == added_child.author:
                    is_new = False

            if is_new:
                new_children.append(child)

        # delete no longer occurring children from
        # - TaxonTreeModel (cascade deletes TaxonLocaleModel and TaxonSynonym entries)
        # - TaxonNuidModel - including all descendants

        for old_child in existing_children:
            if not old_child in still_included_children:
                old_author = old_child['author']
                if not old_author:
                    old_author = 'None'
                old_key = " ".join([old_child['latname'], old_author])
                delete_taxon = existing_children_map[old_key]
                self.TaxonTreeModel.objects.filter(taxon_nuid__startswith=delete_taxon.taxon_nuid).delete()

        # get the highest remaining nuid and start counting from there - this preserves the old nuids
        if existing_children_query.exists():
            # get the nuid from db
            highest_nuid = existing_children_query.order_by('-taxon_nuid')[0].taxon_nuid
            counter_start = n2d(highest_nuid[-3:]) + 1
        else:
            counter_start = 1
        
        # sort the new children before nuiding
        # sort children alphabetically by latname
        new_children.sort(key=lambda child: child.latname)
        
        # assign nuids to new children only
        for counter, child in enumerate(new_children, counter_start):
            nuid_suffix = d2n(counter)

            if parent_taxon:
                nuid = "%s%s" % (parent_taxon.get_nuid(), nuid_suffix)
            else:
                # this is for the root taxa
                nuid = nuid_suffix
                
            child.set_nuid(nuid)

        # add children to cache - if any
        cache_children = cache_children + new_children

        if cache_children:
            cache_children.sort(key=lambda child: child.latname)
            self.cache.add(parent_taxon, cache_children)
        # return new children only
        return new_children
            

    '''
    returns a list of SourceTreeTaxon entries
    
    '''
    def _get_existing_children_query(self, parent_taxon):

        if self.first_run == True:
            return self.TaxonTreeModel.objects.none()

        if parent_taxon is None:
            existing_children_query = self.TaxonTreeModel.objects.filter(is_root_taxon=True)
        else:
            if parent_taxon.get_nuid():
                children_nuid_length = len(parent_taxon.get_nuid()) + 3
                
                existing_children_query = self.TaxonTreeModel.objects.annotate(
                        nuid_len=Length('taxon_nuid')).filter(taxon_nuid__startswith=parent_taxon.get_nuid(),
                                                        nuid_len=children_nuid_length).exclude(taxon_nuid=parent_taxon.get_nuid())
            else:
                raise ValueError('parent_taxon has no nuid and is not None - cant query for children')

        return existing_children_query
    
    '''
    used by self._climb_down
    '''
    def _work_children(self, parent_taxon, children):
        # print('comparing')
        new_children = self._compare_new_children_with_existing_children(children, parent_taxon)
        # print('saving children')
        with transaction.atomic():
            for child in new_children:
                self._save_new_taxon(child)
                self.state.set_last_saved_child(child)
                self.state.dump()
        # print('saved children')
        return new_children
        

    '''
    climbs down until no children are present anymore
    travel direction : from top left to down left
    during climbing down, nuids have to be set
    '''
    def _check_taxon_duplicate(self, taxon):
        if self.first_run == True:
            return False
        
        if not taxon.get_nuid():
            if not self.TaxonTreeModel.objects.filter(taxon_latname=taxon.latname, author=taxon.author).exists():
                raise ValueError('Tried to classify taxon as duplicate, but no original found')

            return True

        return False
        
    def _climb_down(self, parent_taxon):

        message = 'climb down: {0}'.format(parent_taxon.latname)
        print(message)
        # self.logger.info(message)

        # if no nuid is found, it might be a duplicate
        is_duplicate = self._check_taxon_duplicate(parent_taxon)
        if is_duplicate:
            self.logger.info('Duplicate: {0}'.format(parent_taxon.latname))
            return parent_taxon

        self.state.set_last_parent(parent_taxon)

        has_children = True

        first_child = None

        while has_children:

            # TaxonSourceManager subclass specific
            children = self._get_children(parent_taxon)

            if children:
                self.state.set_last_parent(parent_taxon)
                new_children = self._work_children(parent_taxon, children)

                # do not use new_children here. all children are part of the tree
                # assign first (leftmost) child as new parent taxon
                parent_taxon = children[0]
                first_child = children[0]

                # self.logger.info('first child: {0}'.format(first_child.latname))

            else:

                # self.logger.info('no more children found for: {0}'.format(parent_taxon.latname))
                
                if self.first_run == False:
                    # check if there are children in the database thet need to be deleted
                    # print("parent: %s %s" % (parent_taxon.latname, parent_taxon.get_nuid()))
                    # check if it is a duplicate
                    is_duplicate = self._check_taxon_duplicate(parent_taxon)
                    if not is_duplicate:
                        need_deletion = self.TaxonTreeModel.objects.filter(
                            taxon_nuid__startswith=parent_taxon.get_nuid()).exclude(
                                taxon_nuid=parent_taxon.get_nuid()).delete()
                has_children = False

        # if a parent_taxon that has no children is passed, return the parent taxon
        # the tree climber will then go to the next sibling - as it would with the first_child
        if first_child is None:
            self.logger.info('[_climb_down] No first child found. Returning: {0}'.format(parent_taxon.latname))
            return parent_taxon

        # self.logger.info('climb down: {0}'.format(first_child.latname))
        return first_child
