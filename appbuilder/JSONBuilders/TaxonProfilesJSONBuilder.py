from django.conf import settings

from django.contrib.contenttypes.models import ContentType

from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder
from app_kit.appbuilder.JSONBuilders.NatureGuideJSONBuilder import MatrixFilterSerializer

from app_kit.features.taxon_profiles.models import TaxonProfile
from app_kit.features.nature_guides.models import (NatureGuidesTaxonTree, MatrixFilter, NodeFilterSpace, MetaNode,
                                                   NatureGuide)

from app_kit.models import ContentImage, MetaAppGenericContent

from collections import OrderedDict

'''
    Builds JSON for one TaxonProfiles
'''
class TaxonProfilesJSONBuilder(JSONBuilder):

    def __init__(self, app_release_builder, app_generic_content):
        super().__init__(app_release_builder, app_generic_content)

        self.trait_cache = {}


    small_image_size = (200,200)
    large_image_size = (1000, 1000)


    def build(self):
        return self._build_common_json()


    def collect_node_traits(self, node):

        #self.app_release_builder.logger.info('collecting node traits for {0}'.format(node.meta_node.name))

        if node.taxon_nuid in self.trait_cache:
            node_traits = self.trait_cache[node.taxon_nuid]
        
        else:

            node_traits = []

            matrix_filters = MatrixFilter.objects.filter(meta_node=node.parent.meta_node)

            for matrix_filter in matrix_filters:

                # unique_together: node,matrix_filter
                node_space = NodeFilterSpace.objects.filter(node=node, matrix_filter=matrix_filter).first()

                if node_space:

                    serializer = MatrixFilterSerializer(self, matrix_filter)

                    matrix_filter_json = serializer.serialize_matrix_filter()

                    if matrix_filter.filter_type in ['RangeFilter', 'NumberFilter']:
                        space_list = [node_space]
                    else:
                        space_list = node_space.values.all()

                    node_space_json = serializer.get_space_list(matrix_filter, space_list)

                    matrix_filter_json['space'] = node_space_json

                    node_trait = {
                        'matrixFilter' : matrix_filter_json
                    }

                    node_traits.append(node_trait)

            self.trait_cache[node.taxon_nuid] = node_traits

        #self.app_release_builder.logger.info('finished collecting')

        return node_traits
    
    # languages is for the vernacular name only, the rest are keys for translation
    def build_taxon_profile(self, profile_taxon, gbiflib, languages):

        #self.app_release_builder.logger.info('building profile for {0}'.format(profile_taxon.taxon_latname))

        # get the profile
        db_profile = TaxonProfile.objects.filter(taxon_source=profile_taxon.taxon_source,
                    taxon_latname=profile_taxon.taxon_latname, taxon_author=profile_taxon.taxon_author).first()

        taxon_profile_json = {
            'taxonSource' : profile_taxon.taxon_source,
            'taxonLatname' : profile_taxon.taxon_latname,
            'taxonAuthor' : profile_taxon.taxon_author,
            'nameUuid' : profile_taxon.name_uuid,
            'taxonNuid' : profile_taxon.taxon_nuid,
            'vernacular' : {},
            'allVernacularNames' : {},
            'nodeNames' : [], # if the taxon occurs in a nature guide, primary_language only
            'nodeDecisionRules' : [],
            'traits' : [], # a collection of traits (matrix filters)
            'texts': [],
            'images' : {
                'taxonProfileImages' : [],
                'nodeImages' : [],
                'taxonImages' : [],
            },
            'synonyms' : [],
            'gbifNubKey' : None,
        }

        synonyms = profile_taxon.synonyms()
        for synonym in synonyms:
            synonym_entry = {
                'taxonLatname' : synonym.taxon_latname,
                'taxonAuthor' : synonym.taxon_author,
            }

            taxon_profile_json['synonyms'].append(synonym_entry)

        for language_code in languages:
            vernacular_name = profile_taxon.vernacular(language=language_code)

            taxon_profile_json['vernacular'][language_code] = vernacular_name

            all_vernacular_names = profile_taxon.all_vernacular_names(language=language_code)
            
            if all_vernacular_names.exists():
                names_list = list(all_vernacular_names.values_list('name', flat=True))
                taxon_profile_json['allVernacularNames'][language_code] = names_list
                

        collected_content_image_ids = set([])
        # get taxon_profile_images
        if db_profile:
            for content_image in db_profile.images():

                if content_image.id not in collected_content_image_ids:
                    image_entry = self.get_image_entry(content_image)

                    taxon_profile_json['images']['taxonProfileImages'].append(image_entry)

                    collected_content_image_ids.add(content_image.id)

        
        # get information (traits, node_names) from nature guides if possible
        # collect node images
        # only use occurrences in nature guides of this app
        nature_guide_type = ContentType.objects.get_for_model(NatureGuide)
        nature_guide_links = MetaAppGenericContent.objects.filter(meta_app=self.meta_app,
                                                                  content_type=nature_guide_type)
        nature_guide_ids = nature_guide_links.values_list('object_id', flat=True)

        installed_taxonomic_sources = [s[0] for s in settings.TAXONOMY_DATABASES]

        if profile_taxon.taxon_source in installed_taxonomic_sources:

            meta_nodes = MetaNode.objects.filter(
                nature_guide_id__in=nature_guide_ids,
                node_type='result',
                name_uuid = profile_taxon.name_uuid).values_list('pk', flat=True)

            node_occurrences = NatureGuidesTaxonTree.objects.filter(nature_guide_id__in=nature_guide_ids,
                       meta_node_id__in=meta_nodes).order_by('pk').distinct('pk')
        else:
            node_occurrences = NatureGuidesTaxonTree.objects.filter(nature_guide_id__in=nature_guide_ids,
                        meta_node__node_type='result',
                        taxon_latname=profile_taxon.taxon_latname,
                        taxon_author=profile_taxon.taxon_author).order_by('pk').distinct('pk')


        # collect traits of upward branch in tree (higher taxa)
        parent_nuids = set([])

        #self.app_release_builder.logger.info('{0} occurs {1} times in nature_guides'.format(profile_taxon.taxon_latname, node_occurrences.count()))
        
        for node in node_occurrences:

            is_active = True

            if node.additional_data:
                is_active = node.additional_data.get('is_active', True)

            if is_active == True:
                if node.meta_node.name not in taxon_profile_json['nodeNames']:
                    taxon_profile_json['nodeNames'].append(node.meta_node.name)

                node_image = node.meta_node.image()

                if node_image is not None and node_image.id not in collected_content_image_ids:
                    collected_content_image_ids.add(node_image.id)
                    image_entry = self.get_image_entry(node_image)

                    collected_content_image_ids.add(node_image.id)

                    taxon_profile_json['images']['nodeImages'].append(image_entry)

                if node.decision_rule and node.decision_rule not in taxon_profile_json['nodeDecisionRules']:
                    taxon_profile_json['nodeDecisionRules'].append(node.decision_rule)

                node_traits = self.collect_node_traits(node)
                for node_trait in node_traits:
                    
                    taxon_profile_json['traits'].append(node_trait)

                current_nuid = node.taxon_nuid
                while len(current_nuid) > 3:

                    #self.app_release_builder.logger.info('current_nuid {0}'.format(current_nuid))
                    
                    current_nuid = current_nuid[:-3]

                    # first 3 digits are the nature guide, not the root node
                    if len(current_nuid) > 3:
                        parent_nuids.add(current_nuid)

        
        # collect all traits of all parent nuids
        parents = NatureGuidesTaxonTree.objects.filter(taxon_nuid__in=parent_nuids)

        #self.app_release_builder.logger.info('Found {0} parents for {1}'.format(len(parents), profile_taxon.taxon_latname))

        for parent in parents:

            is_active = True

            # respect NatureGuidesTaxonTree.additional_data['is_active'] == True
            if parent.additional_data:
                is_active = parent.additional_data.get('is_active', True)

            if is_active == True:

                if parent.parent:

                    #self.app_release_builder.logger.info('Collecting parent traits of {0}'.format(parent.taxon_latname))

                    parent_node_traits = self.collect_node_traits(parent)
                    for parent_node_trait in parent_node_traits:
                        
                        taxon_profile_json['traits'].append(parent_node_trait)
        

        # get taxonomic images
        taxon_images = ContentImage.objects.filter(image_store__taxon_source=profile_taxon.taxon_source,
                                    image_store__taxon_latname=profile_taxon.taxon_latname,
                                    image_store__taxon_author=profile_taxon.taxon_author).exclude(
                                    pk__in=list(collected_content_image_ids))

        #self.app_release_builder.logger.info('Found {0} images for {1}'.format(taxon_images.count(), profile_taxon.taxon_latname))

        for taxon_image in taxon_images:

            if taxon_image is not None and taxon_image.id not in collected_content_image_ids:

                image_entry = self.get_image_entry(taxon_image)
                taxon_profile_json['images']['taxonImages'].append(image_entry)

                collected_content_image_ids.add(taxon_image.id)
            

        # get the gbif nubKey
        if self.app_release_builder.use_gbif == True:
            gbif_nubKey = gbiflib.get_nubKey(profile_taxon)
            if gbif_nubKey :
                taxon_profile_json['gbifNubKey'] = gbif_nubKey


        if db_profile:

            for text in db_profile.texts():

                if text.text or text.long_text:

                    text_json = {
                        'taxonTextType' : text.taxon_text_type.text_type,
                        'shortText' : text.text,
                        'shortTextKey' : self.generic_content.get_short_text_key(text),
                        'longText' : text.long_text,
                        'longTextKey' : self.generic_content.get_long_text_key(text),
                    }

                    taxon_profile_json['texts'].append(text_json)


        return taxon_profile_json


    # look up taxonomic data by name_uuid
    def build_alphabetical_registry(self, taxon_list, languages):

        registry = {}

        for lazy_taxon in taxon_list:
            
            registry_entry = {
                'taxonSource' : lazy_taxon.taxon_source,
                'nameUuid' : str(lazy_taxon.name_uuid),
                'taxonLatname' : lazy_taxon.taxon_latname,
                'taxonAuthor' : lazy_taxon.taxon_author,
                'vernacularNames' : {},
                'alternativeVernacularNames' : {},
            }

            for language_code in languages:
                vernacular_name = lazy_taxon.vernacular(language=language_code)

                if vernacular_name:
                    registry_entry['vernacularNames'][language_code] = vernacular_name

            registry[str(lazy_taxon.name_uuid)] = registry_entry

        return registry
            

    '''
    {
        'taxon_latname' : {
            'A' : {
                'A latname with author' : name_uuid
            },
        },
        'vernacular' : {
            'en' : {
                'A' : [
                    {'name': 'A name', 'name_uuid': name_uuid, 'taxon_latname': 'abc', 'taxon_author': 'def'}
                ]
            }
        }
    }
    '''
    def build_search_indices(self, taxon_list, languages):

        search_indices_json = {
            'taxonLatname' : {},
            'vernacular' : {},
        }

        used_taxon_full_latnames = set([])

        for lazy_taxon in taxon_list:

            name_uuid = str(lazy_taxon.name_uuid)

            # latname incl author is unique
            if lazy_taxon.taxon_author:
                taxon_full_latname = '{0} {1}'.format(lazy_taxon.taxon_latname, lazy_taxon.taxon_author)
            else:
                taxon_full_latname = lazy_taxon.taxon_latname

            if taxon_full_latname not in used_taxon_full_latnames:

                used_taxon_full_latnames.add(taxon_full_latname)
                    
                taxon_latname_start_letter = lazy_taxon.taxon_latname[0].upper()
                
                if taxon_latname_start_letter not in search_indices_json['taxonLatname']:
                    search_indices_json['taxonLatname'][taxon_latname_start_letter] = []

                taxon_latname_entry_json = {
                    'taxonLatname' : lazy_taxon.taxon_latname,
                    'taxonAuthor' : lazy_taxon.taxon_author,
                    'taxonSource' : lazy_taxon.taxon_source, # for looking up the original taxon
                    'nameUuid' : name_uuid, # for looking up the original taxon
                    'isSynonym' : False,
                }
                search_indices_json['taxonLatname'][taxon_latname_start_letter].append(taxon_latname_entry_json)

                # add synonyms
                synonyms = lazy_taxon.synonyms()
                for synonym in synonyms:

                    synonym_full_latname = '{0} {1}'.format(synonym.taxon_latname, synonym.taxon_author)

                    synonym_entry_json = {
                        'taxonLatname' : synonym.taxon_latname,
                        'taxonAuthor' : synonym.taxon_author,
                        'taxonSource' : lazy_taxon.taxon_source,
                        'nameUuid' : name_uuid, # name_uuid of accepted name
                        'synonymNameUuid' : str(synonym.name_uuid),
                        'isSynonym' : True,
                    }

                    search_indices_json['taxonLatname'][taxon_latname_start_letter].append(synonym_entry_json)


            # add vernacular names - these might not be unique, therefore use a list
            # search result should look like this: "Vernacular (Scientfic name)"
            for language_code in languages:

                if language_code not in search_indices_json['vernacular']:
                    search_indices_json['vernacular'][language_code] = OrderedDict()
                    
                vernacular_names = lazy_taxon.all_vernacular_names(language=language_code)

                for locale in vernacular_names:

                    vernacular_name = locale.name

                    list_entry_json = {
                        'taxonSource' : lazy_taxon.taxon_source,
                        'name' : vernacular_name,
                        'nameUuid' : name_uuid,
                        'taxonLatname' : lazy_taxon.taxon_latname,
                        'taxonAuthor' : lazy_taxon.taxon_author
                    }

                    vernacular_name_start_letter = vernacular_name[0].upper()

                    if vernacular_name_start_letter not in search_indices_json['vernacular'][language_code]:
                        search_indices_json['vernacular'][language_code][vernacular_name_start_letter] = []

                    search_indices_json['vernacular'][language_code][vernacular_name_start_letter].append(list_entry_json)


                # sort start letters
                vernacular_sorted_start_letters = sorted(search_indices_json['vernacular'][language_code].items(),
                                                     key=lambda x: x[0])
        
                search_indices_json['vernacular'][language_code] = OrderedDict(vernacular_sorted_start_letters)

                # sort list inside start letters
                for start_letter, names_list in search_indices_json['vernacular'][language_code].items():

                    sorted_names_list = sorted(names_list, key=lambda d: d['name']) 
                    search_indices_json['vernacular'][language_code][start_letter] = sorted_names_list


        # sort taxon_latname dict start letters and entries
        taxon_latnames_sorted_start_letters = sorted(search_indices_json['taxonLatname'].items(),
                                                     key=lambda x: x[0])
        
        search_indices_json['taxonLatname'] = OrderedDict(taxon_latnames_sorted_start_letters)

        for taxon_latname_start_letter, taxon_latname_list in search_indices_json['taxonLatname'].items():
            sorted_taxon_latname_list = sorted(taxon_latname_list, key=lambda i: i['taxonLatname'])
            
            search_indices_json['taxonLatname'][taxon_latname_start_letter] = sorted_taxon_latname_list
            
        return search_indices_json


    def get_image_entry(self, content_image_mixedin):

        image_entry = {
            'text': content_image_mixedin.text,
            'imageUrl' : self._get_image_url(content_image_mixedin),
            'smallUrl' : self._get_image_url(content_image_mixedin, size=self.small_image_size),
            'largeUrl' : self._get_image_url(content_image_mixedin, size=self.large_image_size),
        }

        return image_entry
