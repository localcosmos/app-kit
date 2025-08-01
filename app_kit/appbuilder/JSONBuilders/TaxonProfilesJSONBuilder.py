from django.conf import settings

from django.contrib.contenttypes.models import ContentType

from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder
from app_kit.appbuilder.JSONBuilders.NatureGuideJSONBuilder import MatrixFilterSerializer, NodeFilterSpaceListSerializer

from app_kit.features.taxon_profiles.models import (TaxonProfile, TaxonProfilesNavigation,
    TaxonProfilesNavigationEntry)
from app_kit.features.nature_guides.models import (MatrixFilter, NodeFilterSpace)

from app_kit.features.generic_forms.models import GenericForm

from app_kit.models import ContentImage, MetaAppGenericContent

from django.template.defaultfilters import slugify

from localcosmos_server.template_content.models import TemplateContent

from taxonomy.lazy import LazyTaxon
from taxonomy.models import TaxonomyModelRouter

from collections import OrderedDict


'''
    Builds JSON for one TaxonProfiles
'''
class TaxonProfilesJSONBuilder(JSONBuilder):

    def __init__(self, app_release_builder, app_generic_content):
        super().__init__(app_release_builder, app_generic_content)

        self.trait_cache = {}
        
        self.built_taxon_profiles_cache = {}

        # primary language only
        self.vernacular_names_from_nature_guide_cache = {}
        

    small_image_size = (200,200)
    large_image_size = (1000, 1000)


    def build(self):
        return self._build_common_json()

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
    def build_taxon_profile(self, profile_taxon, languages):
        
        lazy_taxon = LazyTaxon(instance=profile_taxon)

        #self.app_release_builder.logger.info('building profile for {0}'.format(profile_taxon.taxon_latname))

        # get the profile
        db_profile = TaxonProfile.objects.filter(taxon_profiles=self.generic_content,
            taxon_source=profile_taxon.taxon_source, taxon_latname=profile_taxon.taxon_latname,
            taxon_author=profile_taxon.taxon_author).first()
        
        
        taxon_profile_json = self.app_release_builder.taxa_builder.serialize_taxon_extended(lazy_taxon)
        
        # if the taxonomic db got updated, still use the old taxon latname and author here
        taxon_profile_json['taxonLatname'] = lazy_taxon.taxon_latname
        taxon_profile_json['taxonAuthor'] = lazy_taxon.taxon_author
        
        images = self.app_release_builder.taxa_builder.serialize_taxon_images(lazy_taxon)

        is_featured = False
        if db_profile:
            if db_profile.publication_status == 'draft':
                return None
            
            if db_profile.is_featured:
                is_featured = True

        taxon_profile_json.update({
            'taxonProfileId': db_profile.id if db_profile else None,
            'vernacular' : {},
            'allVernacularNames' : {},
            'nodeNames' : [], # if the taxon occurs in a nature guide, primary_language only
            'nodeDecisionRules' : [],
            'traits' : [], # a collection of traits (matrix filters)
            'shortProfile' : None,
            'texts': [],
            'categorizedTexts' : [],
            'images' : images,
            'synonyms' : [],
            'templateContents' : [],
            'genericForms' : self.collect_usable_generic_forms(profile_taxon),
            'tags' : [],
            'seo': {
                'title': None,
                'meta_description': None,
            },
            'isFeatured': is_featured,
        })

        synonyms = profile_taxon.synonyms()
        for synonym in synonyms:
            synonym_entry = {
                'taxonLatname' : synonym.taxon_latname,
                'taxonAuthor' : synonym.taxon_author,
            }

            taxon_profile_json['synonyms'].append(synonym_entry)

        for language_code in languages:

            preferred_vernacular_name = lazy_taxon.get_preferred_vernacular_name(language_code,
                                                                                    self.meta_app)

            taxon_profile_json['vernacular'][language_code] = preferred_vernacular_name

            all_vernacular_names = profile_taxon.all_vernacular_names(self.meta_app,
                                                                      languages=[language_code])
            
            
            names_list = [name_reference['name'] for name_reference in all_vernacular_names]
            taxon_profile_json['allVernacularNames'][language_code] = names_list

        # get taxon_profile_images
        if db_profile:
            # this has to be changed to esnure ordering by pk of taggeditem
            taxon_profile_json['tags'] = [tag.name for tag in db_profile.tags.all()]
            
            # localized SEO
            seo_parameters = db_profile.seo_parameters.first()
            
            if seo_parameters:
                
                if seo_parameters.title:
                    taxon_profile_json['seo']['title'] = seo_parameters.title
                if seo_parameters.meta_description:
                    taxon_profile_json['seo']['meta_description'] = seo_parameters.meta_description
                        
        # get information (traits, node_names) from nature guides if possible
        # collect node images
        # only use occurrences in nature guides of this app
        node_occurrences = self.app_release_builder.taxa_builder.get_nature_guide_occurrences(lazy_taxon)

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

                #if node.decision_rule and node.decision_rule not in taxon_profile_json['nodeDecisionRules']:
                #    taxon_profile_json['nodeDecisionRules'].append(node.decision_rule)

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

        if db_profile:
            
            taxon_profile_json['shortProfile'] = db_profile.short_profile

            for category_name, text_list in db_profile.categorized_texts().items():
                
                categorized_texts_json = {
                    'category' : category_name,
                    'texts' : [],
                }
                
                for text in text_list:

                    if text.text or text.long_text:
                        
                        images = self.get_taxon_text_images(text)

                        text_json = {
                            'taxonTextType' : text.taxon_text_type.text_type,
                            'shortText' : None,
                            'shortTextKey' : None,
                            'longText' : None,
                            'longTextKey' : None,
                            'images': images,
                        }

                        if text.text:
                            text_json['shortText'] = text.text
                            text_json['shortTextKey']  = self.generic_content.get_short_text_key(text)

                        if text.long_text:
                            text_json['longText'] = text.long_text
                            text_json['longTextKey'] = self.generic_content.get_long_text_key(text)


                        if category_name == 'uncategorized':
                            taxon_profile_json['texts'].append(text_json)
                            
                        else:
                            categorized_texts_json['texts'].append(text_json)
                    
                if category_name != 'uncategorized' and len(categorized_texts_json['texts']) > 0:
                    taxon_profile_json['categorizedTexts'].append(categorized_texts_json)

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
        
        
    # Taxon Profiles Registry
    # registry.json: only one occurrence per taxon (name_uuid) - usable for alphabetical display by taxon latname
    # vernacular/de.json: 
    def build_alphabetical_registry(self, taxon_list, languages):

        registry = {}
        localized_registries = {}

        start_letters = {
            'taxonLatname' : [],
            'vernacular': {},
        }

        included_taxa = []

        for lazy_taxon in taxon_list:

            if lazy_taxon.name_uuid in included_taxa:
                continue
            
            full_scientific_name = str(lazy_taxon)
            registry_taxon_json = self.app_release_builder.taxa_builder.serialize_as_registry_taxon(
                lazy_taxon, languages, 'scientific', full_scientific_name, True)
            
            # fix for an algaebase problem
            registry_taxon_json['taxonLatname'] = lazy_taxon.taxon_latname
            registry_taxon_json['taxonAuthor'] = lazy_taxon.taxon_author
            
            registry[str(lazy_taxon.name_uuid)] = registry_taxon_json
            
            scientific_start_letter = full_scientific_name[0].upper()
            if scientific_start_letter not in start_letters['taxonLatname']:
                start_letters['taxonLatname'].append(scientific_start_letter)
            

            for language_code in languages:
                
                if language_code not in start_letters['vernacular']:
                    start_letters['vernacular'][language_code] = []

                preferred_vernacular_name = lazy_taxon.get_preferred_vernacular_name(language_code,
                                                                                     self.meta_app)

                if preferred_vernacular_name:
                    
                    if language_code not in localized_registries:
                        localized_registries[language_code] = []

                    vernacular_search_taxon_json = self.app_release_builder.taxa_builder.serialize_as_search_taxon(
                        lazy_taxon, 'vernacular', preferred_vernacular_name, True)
                    
                    # fix for an algaebase problem
                    vernacular_search_taxon_json['taxonLatname'] = lazy_taxon.taxon_latname
                    vernacular_search_taxon_json['taxonAuthor'] = lazy_taxon.taxon_author

                    localized_registries[language_code].append(vernacular_search_taxon_json)
                    
                    vernacular_start_letter = vernacular_search_taxon_json['name'][0].upper()
                    if vernacular_start_letter not in start_letters['vernacular'][language_code]:
                        start_letters['vernacular'][language_code].append(vernacular_start_letter)

            included_taxa.append(lazy_taxon.name_uuid)

        # sort the localited registries
        for language_code, localized_registry in localized_registries.items():

            sorted_localized_registry = sorted(localized_registry, key=lambda x: x['name'])
            localized_registries[language_code] = sorted_localized_registry
            
        start_letters['taxonLatname'].sort()
        for language_code, letters_list in start_letters['vernacular'].items():
            start_letters['vernacular'][language_code].sort()

        return registry, localized_registries, start_letters


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
    
    
    def _build_navigation_child(self, navigation_entry):
        
        taxa = []
        
        images = self.get_navigation_entry_images(navigation_entry)
        
        for taxon_link in navigation_entry.taxa:
            lazy_taxon = LazyTaxon(instance=taxon_link)
            taxon = self.app_release_builder.taxa_builder.serialize_taxon(lazy_taxon)
            taxa.append(taxon)
        
        navigation_entry_json = {
            'key': navigation_entry.key,
            'parentKey': None,
            'name': navigation_entry.name or None,
            'verboseName': str(navigation_entry),
            'taxa': taxa,
            'images': images,
            'primaryImage': None,
        }
        
        if images:
            navigation_entry_json['primaryImage'] = images[0]
        
        if navigation_entry.parent:
            navigation_entry_json.update({
                'parentKey': navigation_entry.parent.key,
            })
        
        return navigation_entry_json
    
    
    def get_navigation_entry_slug(self, navigation_slugs, navigation_entry):
        name = slugify(navigation_entry['verboseName'])
        
        slug = name
        
        counter = 2
        
        while slug in navigation_slugs:
            slug = '{0}-{1}'.format(name, counter)
            counter = counter +1
            
        return slug
    
    
    def get_empty_navigation_node(self, is_start_node=False):
        
        navigation_node = {
            'name': None,
            'description': None,
            'verboseName': None,
            'isTerminalNode': False,
            'isStartNode' : is_start_node,
            'images': [],
            'imageAnalysis' : {
                'maxImages' : 0,
                'minImages' : 0,
                'modeImages': 0,
            },
            'children' : [],
            'taxonProfiles': [],
        }
        
        return navigation_node
    
    
    def get_navigation_entry_images(self, navigation_entry):
        
        images = []
        
        for content_image in navigation_entry.images():
            image_entry = self.get_image_json(content_image)
            images.append(image_entry)
            
        return images
        
        
    def get_taxon_text_images(self, taxon_text):
        images = []
        
        for content_image in taxon_text.images():
            image_entry = self.get_image_json(content_image)
            images.append(image_entry)
            
        return images
    
    
    def get_image_analysis(self, navigation_node_json):
        
        # {'4':3, '1':2}
        image_counts = {
            'nodes' : {},
            'taxonProfiles' : {},
        }
        
        for child in navigation_node_json['children']:
            
            node_type = 'nodes'

            image_count = str(len(child['images']))
            if image_count not in image_counts:
                image_counts[node_type][image_count] = 0
            image_counts[node_type][image_count] = image_counts[node_type][image_count] + 1
            
        
        for taxon_profile in navigation_node_json['taxonProfiles']:
            
            node_type = 'taxonProfiles'
            
            image_count = str(len(taxon_profile['images']))
            if image_count not in image_counts:
                image_counts[node_type][image_count] = 0
            image_counts[node_type][image_count] = image_counts[node_type][image_count] + 1
        
        
        image_analysis = {}
        
        for node_type, typed_counts in image_counts.items():
            
            max_images = 0
            min_images = None
            mode_images = 0
            mode_images_occurrence_count = 0
            
            for image_count, occurrence_count in typed_counts.items():
                
                image_count_number = int(image_count)
                
                if image_count_number > max_images:
                    max_images = image_count_number
                
                if min_images == None:
                    min_images = image_count_number
                    
                if image_count_number < min_images:
                    min_images = image_count_number
                    
                if occurrence_count > mode_images_occurrence_count:
                    mode_images = image_count_number
                    mode_images_occurrence_count = occurrence_count
            
            if min_images == None:
                min_images = 0
            
            image_analysis[node_type] = {
                'maxImages' : max_images,
                'minImages' : min_images,
                'modeImages': mode_images,
            }
        
        return image_analysis
    
    def get_attached_taxon_profiles_json(self, navigation_entry):
        # fetch all taxon profiles matching this node
        attached_taxon_profiles = []
        attached_taxon_profiles_json = []
        
        for taxon_profile in navigation_entry.attached_taxon_profiles:
            if taxon_profile not in attached_taxon_profiles:
                attached_taxon_profiles.append(taxon_profile)
        
        # jsonify all taxon profiles
        for taxon_profile in attached_taxon_profiles:
            
            lazy_taxon = LazyTaxon(instance=taxon_profile)
            taxon_json = self.app_release_builder.taxa_builder.serialize_taxon_with_profile_images(lazy_taxon)
            attached_taxon_profiles_json.append(taxon_json)
            
        return attached_taxon_profiles_json
    
    
    def build_navigation(self):
        
        # navigation slugs are group names or taxon latnames
        navigation_slugs = {
            'start': 'start',
        }
        
        navigation = TaxonProfilesNavigation.objects.filter(taxon_profiles=self.generic_content).first()
        built_navigation = {
            'start' : self.get_empty_navigation_node(is_start_node=True),
        }
        
        if navigation:
            root_elements = TaxonProfilesNavigationEntry.objects.filter(navigation=navigation,
                                parent=None).exclude(publication_status='draft').order_by('position')
            for root_element in root_elements:
                
                root_element_json = self._build_navigation_child(root_element)
                slug = self.get_navigation_entry_slug(navigation_slugs, root_element_json)
                root_element_json['slug'] = slug
                navigation_slugs[slug] = root_element_json['key']
                built_navigation['start']['children'].append(root_element_json)
                toplevel_image_analysis = self.get_image_analysis(built_navigation['start'])
                built_navigation['start']['imageAnalysis'] = toplevel_image_analysis
                
            all_elements = TaxonProfilesNavigationEntry.objects.filter(
                navigation=navigation).exclude(publication_status='draft').order_by('position')
            
            for navigation_entry in all_elements:
                
                navigation_entry_json = self.get_empty_navigation_node()
                
                navigation_entry_json.update({
                    'name': navigation_entry.name or None,
                    'description': navigation_entry.description or None,
                    'verboseName': str(navigation_entry),
                    'images': self.get_navigation_entry_images(navigation_entry),                    
                })
                
                children = TaxonProfilesNavigationEntry.objects.filter(navigation=navigation,
                        parent=navigation_entry).exclude(publication_status='draft').order_by('position')
                
                if children:
                    children_json = []
                    
                    for child in children:
                        child_json = self._build_navigation_child(child)
                        slug = self.get_navigation_entry_slug(navigation_slugs, child_json)
                        child_json['slug'] = slug
                        navigation_slugs[slug] = child_json['key']
                        children_json.append(child_json)
                        
                    navigation_entry_json['children'] = children_json
                
                else:
                    navigation_entry_json['isTerminalNode'] = True
                    
                
                navigation_entry_json['taxonProfiles'] = self.get_attached_taxon_profiles_json(navigation_entry)
                
                # update image counts
                navigation_entry_json['imageAnalysis'] = self.get_image_analysis(navigation_entry_json)
                    
                built_navigation[navigation_entry.key] = navigation_entry_json
                
        
        return built_navigation, navigation_slugs
    
    
    def build_featured_taxon_profiles_list(self, languages):
        
        featured_profiles_qry = TaxonProfile.objects.filter(taxon_profiles=self.generic_content,
                                                            is_featured=True)

        featured_taxon_profiles = []
        
        for taxon_profile in featured_profiles_qry:
            
            lazy_taxon = LazyTaxon(instance=taxon_profile)
            taxon_profile_json = self.app_release_builder.taxa_builder.serialize_taxon_extended(lazy_taxon)
                
            featured_taxon_profiles.append(taxon_profile_json)
        
        return featured_taxon_profiles