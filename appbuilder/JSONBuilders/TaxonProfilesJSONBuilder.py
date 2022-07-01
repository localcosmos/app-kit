from django.conf import settings

from django.contrib.contenttypes.models import ContentType

from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder

from app_kit.features.taxon_profiles.models import TaxonProfile
from app_kit.features.nature_guides.models import (NatureGuidesTaxonTree, MatrixFilter, NodeFilterSpace,
                                                   NatureGuide)

from app_kit.models import ContentImage, MetaAppGenericContent

from collections import OrderedDict

'''
    Builds JSON for one TaxonProfiles
'''
class TaxonProfilesJSONBuilder(JSONBuilder):

    small_image_size = (200,200)
    large_image_size = (1000, 1000)


    def build(self):
        return self._build_common_json()


    def collect_node_traits(self, node):

        node_traits = []

        matrix_filters = MatrixFilter.objects.filter(meta_node=node.parent.meta_node)

        for matrix_filter in matrix_filters:
            node_spaces = NodeFilterSpace.objects.filter(node=node, matrix_filter=matrix_filter)


            node_trait = {
                'matrix_filter' : {
                    'name' : matrix_filter.name,
                    'is_multispace' : matrix_filter.matrix_filter_type.is_multispace,
                    'description' : matrix_filter.description,
                    'filter_type' : matrix_filter.filter_type,
                    'definition' : matrix_filter.definition,
                },
            }

            if matrix_filter.matrix_filter_type.is_multispace == True:
                node_trait['values'] = []

            for node_space in node_spaces:

                if matrix_filter.matrix_filter_type.is_multispace == True:
                    
                    for value in node_space.values.all():
                        values_entry = {
                            'encoded_space': value.encoded_space,
                            'image_url' : self._get_image_url(value),
                        }

                        if matrix_filter.filter_type == 'ColorFilter':
                            encoded_space = value.encoded_space
                            gradient = False
                            description = None

                            if value.additional_information:
                                description = value.additional_information.get('description', None)
                                gradient = value.additional_information.get('gradient', False)
                                

                            html = matrix_filter.matrix_filter_type.encoded_space_to_html(encoded_space)
                            values_entry['html'] = html
                            values_entry['gradient'] = gradient
                            values_entry['description'] = description
                            
                        node_trait['values'].append(values_entry)

                else:
                    node_trait['values'] = node_space.encoded_space

            node_traits.append(node_trait)


        return node_traits
    
    # languages is for the vernacular name only, the rest are keys for translation
    def build_taxon_profile(self, profile_taxon, gbiflib, languages):

        self.app_release_builder.logger.info('building profile for {0}'.format(profile_taxon.taxon_latname))

        # get the profile
        db_profile = TaxonProfile.objects.filter(taxon_source=profile_taxon.taxon_source,
                    taxon_latname=profile_taxon.taxon_latname, taxon_author=profile_taxon.taxon_author).first()

        taxon_profile = {
            'taxon_source' : profile_taxon.taxon_source,
            'taxon_latname' : profile_taxon.taxon_latname,
            'taxon_author' : profile_taxon.taxon_author,
            'name_uuid' : profile_taxon.name_uuid,
            'taxon_nuid' : profile_taxon.taxon_nuid,
            'vernacular' : {},
            'all_vernacular_names' : {},
            'node_names' : [], # if the taxon occurs in a nature guide, primary_language only
            'node_decision_rules' : [],
            'traits' : [], # a collection of traits (matrix filters)
            'texts': [],
            'images' : {
                'taxon_profile_images' : [],
                'node_images' : [],
                'taxon_images' : [],
            },
            'synonyms' : [],
            'gbif_nubKey' : None,
        }

        synonyms = profile_taxon.synonyms()
        for synonym in synonyms:
            synonym_entry = {
                'taxon_latname' : synonym.taxon_latname,
                'taxon_author' : synonym.taxon_author,
            }

            taxon_profile['synonyms'] = synonym_entry

        for language_code in languages:
            vernacular_name = profile_taxon.vernacular(language=language_code)

            taxon_profile['vernacular'][language_code] = vernacular_name

            all_vernacular_names = profile_taxon.all_vernacular_names(language=language_code)
            
            if all_vernacular_names.exists():
                names_list = list(all_vernacular_names.values_list('name', flat=True))
                taxon_profile['all_vernacular_names'][language_code] = names_list
                

        collected_content_image_ids = set([])
        # get taxon_profile_images
        if db_profile:
            for content_image in db_profile.images():
                image_entry = {
                    'text' : content_image.text,
                    'image_url' : self._get_image_url(content_image),
                    'small_url' : self._get_image_url(content_image, self.small_image_size),
                    'large_url' : self._get_image_url(content_image, self.large_image_size),
                }

                taxon_profile['images']['taxon_profile_images'].append(image_entry)

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
            node_occurrences = NatureGuidesTaxonTree.objects.filter(nature_guide_id__in=nature_guide_ids,
                        meta_node__taxon_latname=profile_taxon.taxon_latname,
                        meta_node__taxon_author=profile_taxon.taxon_author).order_by('pk').distinct('pk')
        else:
            node_occurrences = NatureGuidesTaxonTree.objects.filter(nature_guide_id__in=nature_guide_ids,
                        taxon_latname=profile_taxon.taxon_latname,
                        taxon_author=profile_taxon.taxon_author).order_by('pk').distinct('pk')


        # collect traits of upward branch in tree (higher taxa)
        parent_nuids = set([])

        self.app_release_builder.logger.info('{0} occurs {1} times in nature_guides'.format(profile_taxon.taxon_latname, node_occurrences.count()))
        
        for node in node_occurrences:

            is_active = True

            if node.additional_data:
                is_active = node.additional_data.get('is_active', True)

            if is_active == True:
                if node.meta_node.name not in taxon_profile['node_names']:
                    taxon_profile['node_names'].append(node.meta_node.name)

                node_image = node.meta_node.image()

                if node_image is not None and node_image.id not in collected_content_image_ids:
                    collected_content_image_ids.add(node_image.id)
                    image_entry = {
                        'text' : node_image.text,
                        'image_url' : self._get_image_url(node_image),
                        'small_url' : self._get_image_url(node_image, self.small_image_size),
                        'large_url' : self._get_image_url(node_image, self.large_image_size),
                    }

                    taxon_profile['images']['node_images'].append(image_entry)

                if node.decision_rule and node.decision_rule not in taxon_profile['node_decision_rules']:
                    taxon_profile['node_decision_rules'].append(node.decision_rule)

                node_traits = self.collect_node_traits(node)
                for node_trait in node_traits:
                    
                    taxon_profile['traits'].append(node_trait)

                current_nuid = node.taxon_nuid
                while len(current_nuid) > 3:

                    self.app_release_builder.logger.info('current_nuid {0}'.format(current_nuid))
                    
                    current_nuid = current_nuid[:-3]

                    # first 3 digits are the nature guide, not the root node
                    if len(current_nuid) > 3:
                        parent_nuids.add(current_nuid)

        
        # collect all traits of all parent nuids
        parents = NatureGuidesTaxonTree.objects.filter(taxon_nuid__in=parent_nuids)

        self.app_release_builder.logger.info('Found {0} parents for {1}'.format(len(parents), profile_taxon.taxon_latname))

        for parent in parents:

            is_active = True

            # respect NatureGuidesTaxonTree.additional_data['is_active'] == True
            if parent.additional_data:
                is_active = parent.additional_data.get('is_active', True)

            if is_active == True:

                if parent.parent:

                    self.app_release_builder.logger.info('Collecting parent traits of {0}'.format(parent.taxon_latname))

                    parent_node_traits = self.collect_node_traits(parent)
                    for parent_node_trait in parent_node_traits:
                        
                        taxon_profile['traits'].append(parent_node_trait)
        
        
                

        # get taxonomic images
        taxon_images = ContentImage.objects.filter(image_store__taxon_source=profile_taxon.taxon_source,
                                    image_store__taxon_latname=profile_taxon.taxon_latname,
                                    image_store__taxon_author=profile_taxon.taxon_author).exclude(
                                    pk__in=list(collected_content_image_ids))

        self.app_release_builder.logger.info('Found {0} images for {1}'.format(taxon_images.count(), profile_taxon.taxon_latname))

        for taxon_image in taxon_images:
            image_entry = {
                'text': taxon_image.text,
                'image_url' : self._get_image_url(taxon_image),
                'small_url' : self._get_image_url(taxon_image, self.small_image_size),
                'large_url' : self._get_image_url(taxon_image, self.large_image_size),
            }

        # get the gbif nubKey
        if self.app_release_builder.use_gbif == True:
            self.logger.info('[TaxonPofiles] querying gbif')
            gbif_nubKey = gbiflib.get_nubKey(profile_taxon)
            if gbif_nubKey :
                taxon_profile['gbif_nubKey'] = gbif_nubKey


        if db_profile:

            for text in db_profile.texts():

                if text.text:

                    text_dic = {
                        'taxon_text_type' : text.taxon_text_type.text_type,
                        'text' : text.text,
                        'text_key' : self.generic_content.get_text_key(text),
                    }

                    taxon_profile['texts'].append(text_dic)


        return taxon_profile


    # look up taxonomic data by name_uuid
    def build_alphabetical_registry(self, taxon_list, languages):

        registry = {}

        for lazy_taxon in taxon_list:
            
            registry_entry = {
                'taxon_source' : lazy_taxon.taxon_source,
                'name_uuid' : str(lazy_taxon.name_uuid),
                'taxon_latname' : lazy_taxon.taxon_latname,
                'taxon_author' : lazy_taxon.taxon_author,
                'vernacular_names' : {},
                'alternative_vernacular_names' : {},
            }

            for language_code in languages:
                vernacular_name = lazy_taxon.vernacular(language=language_code)

                if vernacular_name:
                    registry_entry['vernacular_names'][language_code] = vernacular_name

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

        search_indices = {
            'taxon_latname' : {},
            'vernacular' : {},
        }

        for lazy_taxon in taxon_list:

            name_uuid = str(lazy_taxon.name_uuid)

            # latname incl author is unique
            if lazy_taxon.taxon_author:
                taxon_full_latname = '{0} {1}'.format(lazy_taxon.taxon_latname, lazy_taxon.taxon_author)
            else:
                taxon_full_latname = lazy_taxon.taxon_latname
                
            taxon_latname_start_letter = lazy_taxon.taxon_latname[0].upper()
            
            if taxon_latname_start_letter not in search_indices['taxon_latname']:
                search_indices['taxon_latname'][taxon_latname_start_letter] = {}

            taxon_latname_entry = {
                'taxon_latname' : lazy_taxon.taxon_latname,
                'taxon_author' : lazy_taxon.taxon_author,
                'taxon_source' : lazy_taxon.taxon_source, # for looking up the original taxon
                'name_uuid' : name_uuid, # for looking up the original taxon
                'is_synonym' : False,
            }
            search_indices['taxon_latname'][taxon_latname_start_letter][taxon_full_latname] = taxon_latname_entry

            # add synonyms
            synonyms = lazy_taxon.synonyms()
            for synonym in synonyms:

                synonym_full_latname = '{0} {1}'.format(synonym.taxon_latname, synonym.taxon_author)

                synonym_entry = {
                    'taxon_latname' : synonym.taxon_latname,
                    'taxon_author' : synonym.taxon_author,
                    'taxon_source' : lazy_taxon.taxon_source,
                    'name_uuid' : name_uuid, # name_uuid of accepted name
                    'synonym_name_uuid' : str(synonym.name_uuid),
                    'is_synonym' : True,
                }

                search_indices['taxon_latname'][taxon_latname_start_letter][synonym_full_latname] = synonym_entry


            # add vernacular names - these might not be unique, therefore use a list
            # search result should look like this: "Vernacular (Scientfic name)"
            for language_code in languages:

                if language_code not in search_indices['vernacular']:
                    search_indices['vernacular'][language_code] = OrderedDict()
                    
                vernacular_names = lazy_taxon.all_vernacular_names(language=language_code)

                for locale in vernacular_names:

                    vernacular_name = locale.name

                    list_entry = {
                        'taxon_source' : lazy_taxon.taxon_source,
                        'name' : vernacular_name,
                        'name_uuid' : name_uuid,
                        'taxon_latname' : lazy_taxon.taxon_latname,
                        'taxon_author' : lazy_taxon.taxon_author
                    }

                    vernacular_name_start_letter = vernacular_name[0].upper()

                    if vernacular_name_start_letter not in search_indices['vernacular'][language_code]:
                        search_indices['vernacular'][language_code][vernacular_name_start_letter] = []

                    search_indices['vernacular'][language_code][vernacular_name_start_letter].append(list_entry)


                # sort start letters
                vernacular_sorted_start_letters = sorted(search_indices['vernacular'][language_code].items(),
                                                     key=lambda x: x[0])
        
                search_indices['vernacular'][language_code] = OrderedDict(vernacular_sorted_start_letters)

                # sort list inside start letters
                for start_letter, names_list in search_indices['vernacular'][language_code].items():

                    sorted_names_list = sorted(names_list, key=lambda d: d['name']) 
                    search_indices['vernacular'][language_code][start_letter] = sorted_names_list


        # sort taxon_latname dict start letters and entries
        taxon_latnames_sorted_start_letters = sorted(search_indices['taxon_latname'].items(),
                                                     key=lambda x: x[0])
        
        search_indices['taxon_latname'] = OrderedDict(taxon_latnames_sorted_start_letters)

        for taxon_latname_start_letter, taxon_latname_entries in search_indices['taxon_latname'].items():
            sorted_taxon_latname_entries = OrderedDict(sorted(taxon_latname_entries.items(),
                                                              key=lambda x: x[0]))
            
            search_indices['taxon_latname'][taxon_latname_start_letter] = sorted_taxon_latname_entries
            
        return search_indices
