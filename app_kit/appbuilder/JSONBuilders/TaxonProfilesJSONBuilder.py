from django.conf import settings

from django.contrib.contenttypes.models import ContentType

from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder
from app_kit.appbuilder.JSONBuilders.NatureGuideJSONBuilder import MatrixFilterSerializer, NodeFilterSpaceListSerializer

from app_kit.features.taxon_profiles.models import TaxonProfile
from app_kit.features.nature_guides.models import (NatureGuidesTaxonTree, MatrixFilter, NodeFilterSpace, MetaNode,
                                                   NatureGuide)

from app_kit.features.generic_forms.models import GenericForm

from app_kit.models import ContentImage, MetaAppGenericContent

from localcosmos_server.template_content.models import TemplateContent

from collections import OrderedDict


'''
    Builds JSON for one TaxonProfiles
'''
class TaxonProfilesJSONBuilder(JSONBuilder):

    def __init__(self, app_release_builder, app_generic_content):
        super().__init__(app_release_builder, app_generic_content)

        self.trait_cache = {}
        self.built_taxon_profiles_cache = {}

        self.nature_guide_ids = []

        # primary language only
        self.vernacular_names_from_nature_guide_cache = {}
        

    small_image_size = (200,200)
    large_image_size = (1000, 1000)


    def build(self):
        return self._build_common_json()


    def get_nature_guide_ids(self):

        if not self.nature_guide_ids:
            nature_guide_links = self.meta_app.get_generic_content_links(NatureGuide)                                         
            self.nature_guide_ids = nature_guide_links.values_list('object_id', flat=True)

        return self.nature_guide_ids


    @property
    def installed_taxonomic_sources(self):
        installed_taxonomic_sources = [s[0] for s in settings.TAXONOMY_DATABASES]
        return installed_taxonomic_sources


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

        #self.app_release_builder.logger.info('finished collecting')

        return node_traits
    

    def get_vernacular_name_from_nature_guides(self, lazy_taxon):
        if lazy_taxon.name_uuid in self.vernacular_names_from_nature_guide_cache:
            return self.vernacular_names_from_nature_guide_cache[lazy_taxon.name_uuid]
        
        return lazy_taxon.get_primary_locale_vernacular_name_from_nature_guides(self.meta_app)

        

    # languages is for the vernacular name only, the rest are keys for translation
    def build_taxon_profile(self, profile_taxon, gbiflib, languages):

        #self.app_release_builder.logger.info('building profile for {0}'.format(profile_taxon.taxon_latname))

        # get the profile
        db_profile = TaxonProfile.objects.filter(taxon_source=profile_taxon.taxon_source,
                    taxon_latname=profile_taxon.taxon_latname, taxon_author=profile_taxon.taxon_author).first()
        
        if db_profile and db_profile.publication_status == 'draft':
            return None

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
            'templateContents' : [],
            'genericForms' : self.collect_usable_generic_forms(profile_taxon),
            'tags' : [],
        }

        synonyms = profile_taxon.synonyms()
        for synonym in synonyms:
            synonym_entry = {
                'taxonLatname' : synonym.taxon_latname,
                'taxonAuthor' : synonym.taxon_author,
            }

            taxon_profile_json['synonyms'].append(synonym_entry)

        for language_code in languages:

            preferred_vernacular_name = self.get_vernacular_name_from_nature_guides(profile_taxon)

            if not preferred_vernacular_name:
                preferred_vernacular_name = profile_taxon.vernacular(language=language_code)

            taxon_profile_json['vernacular'][language_code] = preferred_vernacular_name

            all_vernacular_names = profile_taxon.all_vernacular_names(language=language_code)
            
            if all_vernacular_names.exists():
                names_list = list(all_vernacular_names.values_list('name', flat=True))
                taxon_profile_json['allVernacularNames'][language_code] = names_list
                

        collected_content_image_ids = set([])
        collected_image_store_ids = set([])
        # get taxon_profile_images
        if db_profile:

            taxon_profile_json['tags'] = [tag.name for tag in db_profile.tags.all()]

            taxon_profile_images = db_profile.images().order_by('position')

            for content_image in taxon_profile_images:

                if content_image.id not in collected_content_image_ids and content_image.image_store.id not in collected_image_store_ids:
                    image_entry = self.get_image_entry(content_image)

                    taxon_profile_json['images']['taxonProfileImages'].append(image_entry)

                    collected_content_image_ids.add(content_image.id)
                    collected_image_store_ids.add(content_image.image_store.id)

        
        # get information (traits, node_names) from nature guides if possible
        # collect node images
        # only use occurrences in nature guides of this app
        nature_guide_ids = self.get_nature_guide_ids()

        if profile_taxon.taxon_source in self.installed_taxonomic_sources:

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

            is_in_inactive_branch = False

            for inactivated_nuid in self.app_release_builder.inactivated_nuids:
                if node.taxon_nuid.startswith(inactivated_nuid):
                    is_in_inactive_branch = True
                    break

            if is_in_inactive_branch == True:
                continue

            if node.taxon_nuid in self.app_release_builder.aggregated_node_filter_space_cache:
                node_traits = self.app_release_builder.aggregated_node_filter_space_cache[node.taxon_nuid]
                taxon_profile_json['traits'] += node_traits

            is_active = True

            if node.additional_data:
                is_active = node.additional_data.get('is_active', True)

            if is_active == True:
                if node.meta_node.name not in taxon_profile_json['nodeNames']:
                    taxon_profile_json['nodeNames'].append(node.meta_node.name)

                node_image = node.meta_node.image()

                if node_image is not None and node_image.id not in collected_content_image_ids and node_image.image_store.id not in collected_image_store_ids:
                    collected_content_image_ids.add(node_image.id)
                    image_entry = self.get_image_entry(node_image)

                    collected_content_image_ids.add(node_image.id)
                    collected_image_store_ids.add(node_image.image_store.id)

                    taxon_profile_json['images']['nodeImages'].append(image_entry)

                if node.decision_rule and node.decision_rule not in taxon_profile_json['nodeDecisionRules']:
                    taxon_profile_json['nodeDecisionRules'].append(node.decision_rule)

                #node_traits = self.collect_node_traits(node)
                #taxon_profile_json['traits'] += node_traits

                current_nuid = node.taxon_nuid
                while len(current_nuid) > 3:

                    #self.app_release_builder.logger.info('current_nuid {0}'.format(current_nuid))
                    
                    current_nuid = current_nuid[:-3]

                    # first 3 digits are the nature guide, not the root node
                    if len(current_nuid) > 3:
                        parent_nuids.add(current_nuid)

        # postprocess traits
        postprocessed_traits = self.postprocess_traits(taxon_profile_json['traits'])
        taxon_profile_json['traits'] = postprocessed_traits

        # collect all traits of all parent nuids
        #parents = NatureGuidesTaxonTree.objects.filter(taxon_nuid__in=parent_nuids)

        #self.app_release_builder.logger.info('Found {0} parents for {1}'.format(len(parents), profile_taxon.taxon_latname))
        '''
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
        '''
        

        # get taxonomic images
        taxon_images = ContentImage.objects.filter(image_store__taxon_source=profile_taxon.taxon_source,
                                    image_store__taxon_latname=profile_taxon.taxon_latname,
                                    image_store__taxon_author=profile_taxon.taxon_author).exclude(
                                    pk__in=list(collected_content_image_ids))

        #self.app_release_builder.logger.info('Found {0} images for {1}'.format(taxon_images.count(), profile_taxon.taxon_latname))

        for taxon_image in taxon_images:

            if taxon_image is not None and taxon_image.id not in collected_content_image_ids and taxon_image.image_store.id not in collected_image_store_ids:

                image_entry = self.get_image_entry(taxon_image)
                taxon_profile_json['images']['taxonImages'].append(image_entry)

                collected_content_image_ids.add(taxon_image.id)
                collected_image_store_ids.add(taxon_image.image_store.id)
            

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
                        'shortText' : None,
                        'shortTextKey' : None,
                        'longText' : None,
                        'longTextKey' : None
                    }

                    if text.text:
                        text_json['shortText'] = text.text
                        text_json['shortTextKey']  = self.generic_content.get_short_text_key(text)

                    if text.long_text:
                        text_json['longText'] = text.long_text
                        text_json['longTextKey'] = self.generic_content.get_long_text_key(text)



                    taxon_profile_json['texts'].append(text_json)

        # template_contents
        template_contents = TemplateContent.objects.filter_by_taxon(profile_taxon)

        for template_content in template_contents:

            if template_content.is_published:
                template_content_json = {}
                ltc = template_content.get_locale(self.meta_app.primary_language)
                template_content_json['templateName'] = template_content.template.name
                template_content_json['slug'] = ltc.slug
                taxon_profile_json['templateContents'].append(template_content_json)

        self.built_taxon_profiles_cache[str(profile_taxon.name_uuid)] = taxon_profile_json

        return taxon_profile_json


    '''
        if MatrixFilter with the same occur on multiple levels, mark those who are on the higher levels
        eg if 'Leaf Shape' occurs on the root level (001) and on a lower level (001003001), the one
        on the root level will be marked
    '''
    def postprocess_traits(self, traits):

        postprocessed_traits = []

        for trait in traits:
            matrix_filter = trait['matrixFilter']
            trait_taxon_nuid = matrix_filter['treeNode']['taxonNuid']

            trait_has_more_specific_occurrence = False

            for other_trait in traits:
                other_matrix_filter = other_trait['matrixFilter']

                if matrix_filter['uuid'] == other_matrix_filter['uuid'] or matrix_filter['name'] != other_matrix_filter['name']:
                    continue
                
                other_trait_taxon_nuid = other_matrix_filter['treeNode']['taxonNuid']

                if other_trait_taxon_nuid.startswith(trait_taxon_nuid):
                    trait_has_more_specific_occurrence = True
                    break
            
            trait['hasMoreSpecificOccurrence'] = trait_has_more_specific_occurrence
        
            postprocessed_traits.append(trait)
        
        return postprocessed_traits


    # look up taxonomic data by name_uuid
    def build_alphabetical_registry(self, taxon_list, languages):

        registry = {}
        localized_registries = {}

        included_taxa = []

        for lazy_taxon in taxon_list:

            if lazy_taxon.name_uuid in included_taxa:
                continue

            preferred_image = None
            # primary language!
            preferred_vernacular_name = self.get_vernacular_name_from_nature_guides(lazy_taxon)
            
            registry_entry = {
                'taxonSource' : lazy_taxon.taxon_source,
                'nameUuid' : str(lazy_taxon.name_uuid),
                'taxonLatname' : lazy_taxon.taxon_latname,
                'taxonAuthor' : lazy_taxon.taxon_author,
                'taxonNuid' : lazy_taxon.taxon_nuid,
                'vernacularNames' : {},
                'alternativeVernacularNames' : {},
                'images' : {
                    'taxonProfileImages' : [],
                    'nodeImages' : [],
                    'taxonImages' : [],
                }
            }

            # images
            built_taxon_profile = self.built_taxon_profiles_cache.get(str(lazy_taxon.name_uuid), None)
            if built_taxon_profile:
                registry_entry['images'] = built_taxon_profile['images']

                if len(registry_entry['images']['nodeImages']) > 0:
                    preferred_image = registry_entry['images']['nodeImages'][0]
                elif len(registry_entry['images']['taxonProfileImages']) > 0:
                    preferred_image = registry_entry['images']['taxonProfileImages'][0]
                elif len(registry_entry['images']['taxonImages']) > 0:
                    preferred_image = registry_entry['images']['taxonImages'][0]


            for language_code in languages:

                localized_preferred_vernacular_name = None

                if preferred_vernacular_name:
                    localized_preferred_vernacular_name = self.app_release_builder.get_localized(preferred_vernacular_name,
                        language_code)

                else:
                    localized_preferred_vernacular_name = lazy_taxon.vernacular(language=language_code)

                if preferred_vernacular_name:
                    registry_entry['vernacularNames'][language_code] = localized_preferred_vernacular_name

                
                # build the localized registry, same structure as BackboneTaxonomy vernacular_dic
                preferred_name = localized_preferred_vernacular_name
                if not preferred_name:
                    if lazy_taxon.taxon_author:
                        preferred_name = '{0} {1}'.format(lazy_taxon.taxon_latname, lazy_taxon.taxon_author)
                    else:
                        preferred_name = lazy_taxon.taxon_latname
                    
                if language_code not in localized_registries:
                    localized_registries[language_code] = []

                preferred_image_url = None
                if preferred_image:
                    preferred_image_url = preferred_image['imageUrl']

                vernacular_dic = {
                    'taxonSource': lazy_taxon.taxon_source,
                    'taxonLatname': lazy_taxon.taxon_latname,
                    'taxonAuthor': lazy_taxon.taxon_author,
                    'nameUuid': str(lazy_taxon.name_uuid),
                    'taxonNuid': lazy_taxon.taxon_nuid ,
                    'imageUrl': preferred_image_url,
                    'name': preferred_name,
                }

                localized_registries[language_code].append(vernacular_dic)

            registry[str(lazy_taxon.name_uuid)] = registry_entry

            included_taxa.append(lazy_taxon.name_uuid)

        # sort the localited registries
        for language_code, localized_registry in localized_registries.items():

            sorted_localized_registry = sorted(localized_registry, key=lambda x: x['name'])
            localized_registries[language_code] = sorted_localized_registry

        return registry, localized_registries
            

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
                    'taxonNuid' : lazy_taxon.taxon_nuid,
                    'nameUuid' : name_uuid, # for looking up the original taxon
                    'acceptedNameUuid': name_uuid,
                    'isSynonym' : False,
                }
                search_indices_json['taxonLatname'][taxon_latname_start_letter].append(taxon_latname_entry_json)

                # add synonyms
                synonyms = lazy_taxon.synonyms()
                for synonym in synonyms:

                    if synonym.taxon_author:
                        synonym_full_latname = '{0} {1}'.format(synonym.taxon_latname, synonym.taxon_author)
                    else:
                        synonym_full_latname = synonym.taxon_latname

                    synonym_start_letter = synonym_full_latname[0]

                    synonym_entry_json = {
                        'taxonLatname' : synonym.taxon_latname,
                        'taxonAuthor' : synonym.taxon_author,
                        'taxonSource' : lazy_taxon.taxon_source,
                        'taxonNuid' : lazy_taxon.taxon_nuid,
                        'nameUuid' : str(synonym.name_uuid), # name_uuid of accepted name
                        'acceptedNameUuid' : name_uuid,
                        'isSynonym' : True,
                    }

                    if synonym_start_letter not in search_indices_json['taxonLatname']:
                        search_indices_json['taxonLatname'][synonym_start_letter] = []

                    search_indices_json['taxonLatname'][synonym_start_letter].append(synonym_entry_json)


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
                        'taxonAuthor' : lazy_taxon.taxon_author,
                        'taxonNuid' : lazy_taxon.taxon_nuid,
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

        image_urls = self._get_image_urls(content_image_mixedin)
        licence = {}

        if image_urls:
            licence = self._get_image_licence(content_image_mixedin)

        image_entry = {
            'text': content_image_mixedin.text,
            'imageUrl' : image_urls,
            'licence' : licence
        }

        return image_entry


    def collect_usable_generic_forms(self, profile_taxon):

        usable_forms = []

        forms_with_nuid = []
        forms_without_nuid = []

        generic_forms_type = ContentType.objects.get_for_model(GenericForm)
        generic_form_links = MetaAppGenericContent.objects.filter(meta_app=self.meta_app, content_type=generic_forms_type)

        for link in generic_form_links:
            generic_form = link.generic_content
            taxonomic_restrictions = self.get_taxonomic_restriction(generic_form)

            generic_form_for_sorting = {
                'uuid' : str(generic_form.uuid),
                'generic_form' : generic_form,
                'taxonNuid' : None,
                'taxonomicRestrictions' : taxonomic_restrictions
            }

            if taxonomic_restrictions:
                for taxonomic_restriction in taxonomic_restrictions:
                    if taxonomic_restriction['taxonSource'] == profile_taxon.taxon_source and profile_taxon.taxon_nuid.startswith(taxonomic_restriction['taxonNuid']):
                        generic_form_for_sorting['taxonNuid'] = taxonomic_restriction['taxonNuid']
                        forms_with_nuid.append(generic_form_for_sorting)
                        break
            else:
                forms_without_nuid.append(generic_form_for_sorting)


        sorted_forms_with_nuid = sorted(forms_with_nuid, key=lambda d: d['taxonNuid'], reverse=True)

        for generic_form_for_sorting in sorted_forms_with_nuid:
            generic_form_json = self._get_generic_form_entry(generic_form_for_sorting)
            usable_forms.append(generic_form_json)

        for generic_form_for_sorting in forms_without_nuid:
            generic_form_json = self._get_generic_form_entry(generic_form_for_sorting)
            usable_forms.append(generic_form_json)
        
        return usable_forms

    def _get_generic_form_entry(self, generic_form_for_sorting):

        generic_form = generic_form_for_sorting['generic_form']

        generic_form_json = {
            'uuid': str(generic_form.uuid),
            'name': generic_form.name,
            'slug': self.app_release_builder.get_generic_content_slug(generic_form),
            'isDefault': False,
            'taxonomicRestrictions' : generic_form_for_sorting['taxonomicRestrictions']
        }

        is_default = generic_form.get_option(self.meta_app, 'is_default')
        if is_default:
            generic_form_json['isDefault'] = True

        return generic_form_json
