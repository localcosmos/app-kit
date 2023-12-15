from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder

# prevent caching of large queries
from app_kit.server_side_cursors import server_side_cursors
from taxonomy.lazy import LazyTaxon

from app_kit.generic import AppContentTaxonomicRestriction

from app_kit.features.taxon_profiles.models import TaxonProfile


'''
    App Backbone Taxonomy builder
    - latnames are stored as alphabetic files, e.g. AA.json
    - vernacular names are stored
    - vernacular names are also fetched from the nature guide, the taxonomic source is the nature guide itself
      if no taxon is assigned
'''
class BackboneTaxonomyJSONBuilder(JSONBuilder):

    def build(self):
        return self._build_common_json()


    ##############################################################################################################
    # BUILD LAT NAMES
    
    def build_latname_alphabet(self, use_gbif):

        backbone_taxonomy = self.generic_content

        # create and dump the alphabet - one file per 2 letters: AA.json, 
        include_full_tree = backbone_taxonomy.include_full_tree()

        if include_full_tree:
            raise ValueError('Fulltree support not implemented yet')

        else:
            # respect taxon_include_descendants, using the lazytaxon.descendants() method
            higher_taxa = self.meta_app.higher_taxa(include_draft_contents=False)

            # first iterate over higher taxa and their descendants
            for queryset in higher_taxa.querysets:

                for taxon_instance in queryset:

                    lazy_higher_taxon = LazyTaxon(instance=taxon_instance)

                    if isinstance(taxon_instance, AppContentTaxonomicRestriction):
                        # do not include descendants for restrictions
                        taxon_dic = self._create_taxon_json_from_lazy_taxon(lazy_higher_taxon, use_gbif)
                        start_letters = lazy_higher_taxon.taxon_latname[:2].upper()
                        yield start_letters, [taxon_dic]

                    else:
    
                        descendant_taxa = lazy_higher_taxon.descendants()

                        for start_letters, letters_taxa in self._work_taxon_alphabet_queryset(descendant_taxa, use_gbif):
                            yield start_letters, letters_taxa
                        
            # higher taxa are done, work 'normal' taxa
            taxa = self.meta_app.taxa(include_draft_contents=False)

            # iterating over the queryset directly might need creating LazyTaxon instance manually
            for taxon_queryset in taxa.querysets:
                for start_letters, letters_taxa in self._work_taxon_alphabet_queryset(taxon_queryset, use_gbif):
                    yield start_letters, letters_taxa


    def _work_taxon_alphabet_queryset(self, taxon_queryset, use_gbif):

        # taxa for one pair of start letters, e.g. AA, which will be dumped as soon as AB is reached
        current_letters_taxa = []
        current_start_letters = None

        with server_side_cursors(taxon_queryset, itersize=1000):

            for lazy_taxon in taxon_queryset:

                if not isinstance(lazy_taxon, LazyTaxon):
                    lazy_taxon = LazyTaxon(instance=lazy_taxon)

                start_letters = lazy_taxon.taxon_latname[:2].upper()
        
                if not current_start_letters:
                    current_start_letters = start_letters

                # we iterate over several querysets, AA can occur in each queryset
                # querset 1 dumps AA when AB is reached
                # queryset 2 starts with AA and loads AA.json file first, adds taxa and dumps when AB
                # is reached
                if start_letters != current_start_letters:

                    yield current_start_letters, current_letters_taxa

                    # reset
                    current_start_letters = start_letters
                    current_letters_taxa = []

                # add taxon to list if not yet exists
                taxon_dic = self._create_taxon_json_from_lazy_taxon(lazy_taxon, use_gbif)

                if taxon_dic not in current_letters_taxa:
                    current_letters_taxa.append(taxon_dic)


            # final yield
            yield current_start_letters, current_letters_taxa


    def _create_taxon_json_from_lazy_taxon(self, lazy_taxon, use_gbif):
        return self.app_release_builder._create_taxon_json_from_lazy_taxon(lazy_taxon, use_gbif)
        

    ##############################################################################################################
    # BUILD VERNACULAR NAMES
    # create a search index with all vernacular names
    # create a nameUuid: vernacularNames[] lookup dictionary
    
    def build_vernacular_names(self, use_gbif):

        for language_code in self.meta_app.languages():

            vernacular_names = VernacularNames()

            # collect and add vernacular nams from nature guides
            vernacular_names_from_nature_guides = self.app_release_builder._collect_vernacular_names_from_nature_guides(
                language_code)
                
            for name_uuid, vernacular_dic in vernacular_names_from_nature_guides.items():
                taxon_kwargs = {
                    'taxon_source': vernacular_dic['taxonSource'],
                    'taxon_latname': vernacular_dic['taxonLatname'],
                    'taxon_author': vernacular_dic['taxonAuthor'],
                    'name_uuid': vernacular_dic['nameUuid'],
                    'taxon_nuid': vernacular_dic['taxonNuid'],
                }
                lazy_ng_taxon = LazyTaxon(**taxon_kwargs)
                vernacular_dic['imageUrl'] = self.get_image_urls_for_lazy_taxon(lazy_ng_taxon)
                vernacular_names.add(vernacular_dic, is_primary=True, force_add=True)

            # secondly, use taxa from col and others, not using force_add
            for lazy_taxon in self.meta_app.taxa(include_draft_contents=False):

                if lazy_taxon.taxon_include_descendants and not isinstance(lazy_taxon.instance, AppContentTaxonomicRestriction):

                    for d_taxon in lazy_taxon.descendants():
                        lazy_d_taxon = LazyTaxon(instance=d_taxon)
                        vernacular_dic = self._create_vernacular_dic(lazy_d_taxon, language_code, use_gbif)

                        if vernacular_dic:
                            vernacular_names.add(vernacular_dic)

                else:
                    vernacular_dic = self._create_vernacular_dic(lazy_taxon, language_code, use_gbif)

                    if vernacular_dic:
                        vernacular_names.add(vernacular_dic)
                

            yield language_code, vernacular_names


    def _create_vernacular_dic(self, lazy_taxon, language_code, use_gbif):

        vernacular_name = lazy_taxon.vernacular(language_code)

        if vernacular_name:

            vernacular_dic = self._create_taxon_json_from_lazy_taxon(lazy_taxon, use_gbif)
            vernacular_dic['imageUrl'] = self.get_image_urls_for_lazy_taxon(lazy_taxon)
            vernacular_dic['name'] = vernacular_name

            return vernacular_dic

        return None

    def get_image_urls_for_lazy_taxon(self, lazy_taxon):
        return self.app_release_builder._get_image_urls_for_lazy_taxon(lazy_taxon)


# WIP, currently unused
class TaxonSerializer:

    def __init__(self, lazy_taxon):
        self.lazy_taxon = lazy_taxon

    def serialize(self):

        taxon_json = {
            'taxonLatname' : self.lazy_taxon.taxon_latname,
            'taxonAuthor' : self.lazy_taxon.taxon_author,
            'taxonSource' : self.lazy_taxon.taxon_source,
            'taxonNuid' : self.lazy_taxon.taxon_nuid,
            'nameUuid' : self.lazy_taxon.name_uuid, 
        }

        return taxon_json


class VernacularNames:

    def __init__(self):
        self.occurred_names = {}
        self.vernacular_names = []
        self.lookup = {}

    def add(self, vernacular_dic, is_primary=False, force_add=False):

        vernacular_name = vernacular_dic['name']
        name_uuid = vernacular_dic['nameUuid']
        if vernacular_name not in self.occurred_names or force_add == True:
            self.vernacular_names.append(vernacular_dic)
            self.occurred_names[vernacular_name] = name_uuid

            if name_uuid not in self.lookup:

                self.lookup[name_uuid] = {
                    'primary': vernacular_name,
                    'secondary': [],
                }

            else:

                current_primary = self.lookup[name_uuid]['primary']

                if is_primary == True:
                    if current_primary != vernacular_name and len(current_primary) > len(vernacular_name):
                        self.lookup[name_uuid]['primary'] = vernacular_name

                new_primary = self.lookup[name_uuid]['primary']
                if vernacular_name != new_primary and vernacular_name not in self.lookup[name_uuid]['secondary']:
                    self.lookup[name_uuid]['secondary'].append(vernacular_name)

        