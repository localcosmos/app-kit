from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder

from app_kit.features.nature_guides.models import (NatureGuidesTaxonTree, MatrixFilter, NodeFilterSpace,
                                                   MatrixFilterRestriction, IDENTIFICATION_MODE_STRICT)


from app_kit.features.fact_sheets.models import FactSheet

from django.utils.text import slugify

import base64, json



'''
    build one file for all languages, only keys for translation
'''
class NatureGuideJSONBuilder(JSONBuilder):


    def build(self):

        self.nature_guide_json = self._build_common_json()

        nature_guide = self.app_generic_content.generic_content

        start_node = NatureGuidesTaxonTree.objects.get(nature_guide=nature_guide, meta_node__node_type='root')
        
        self.nature_guide_json.update({
            'tree' : {},
            'crosslinks' : nature_guide.crosslinks(),
            'startNodeUuid' : str(start_node.name_uuid),
            'slugs' : {},
        })

        # iterate over all parent nodes
        parent_nodes = NatureGuidesTaxonTree.objects.filter(nature_guide=nature_guide).exclude(
            meta_node__node_type='result')

        # {"de" : {key:value}}
        self.localized_slugs = {}

        for parent_node in parent_nodes:

            is_active = True

            if parent_node.additional_data:
                is_active = parent_node.additional_data.get('is_active', True)

            if is_active == False:
                continue

            identification_mode = IDENTIFICATION_MODE_STRICT

            if parent_node.meta_node.settings:
                identification_mode = parent_node.meta_node.settings.get('identification_mode', IDENTIFICATION_MODE_STRICT)

            fact_sheets = []

            if parent_node.meta_node.taxon:
                fact_sheets = self.get_fact_sheets_json_for_taxon(parent_node.meta_node.taxon)

            primary_locale_slug = self.add_to_localized_slugs(parent_node)

            parent_node_json = {
                'uuid' : str(parent_node.name_uuid),
                'name' : parent_node.meta_node.name,
                'taxon' : None,
                'children' : [],
                'matrixFilters' : {},
                'identificationMode' : identification_mode,
                'factSheets' : fact_sheets,
                'slug' : primary_locale_slug,
            }            

            if parent_node.meta_node.taxon:
                parent_node_json['taxon'] = parent_node.meta_node.taxon.as_json()
            
            matrix_filters = MatrixFilter.objects.filter(meta_node=parent_node.meta_node).order_by('position')

            # build all matrix filters
            for matrix_filter in matrix_filters:
                matrix_filter_json = self._get_matrix_filter_json(matrix_filter)

                parent_node_json['matrixFilters'][str(matrix_filter.uuid)] = matrix_filter_json

            for child in parent_node.children:

                child_is_active = True

                if child.additional_data:
                    child_is_active = child.additional_data.get('is_active', True)

                if child_is_active == False:
                    continue

                # fill the space
                # there is only one NodeFilterSpace per matrix_filter/node combination
                space_query = NodeFilterSpace.objects.filter(node=child, matrix_filter__in=matrix_filters)

                child_max_points = 0
                child_space = {}

                for node_filter_space in space_query:

                    # get the matrix_filter for this specific space
                    node_matrix_filter = node_filter_space.matrix_filter

                    node_matrix_filter_uuid = str(node_matrix_filter.uuid)

                    # iterate over all spaces for this filter
                    spaces = node_matrix_filter.matrix_filter_type.get_filter_space_as_list_with_identifiers(
                        node_filter_space)

                    # a list of spaces applicable for this entry/matrix_filter combination
                    child_space[node_matrix_filter_uuid] = spaces

                    weight = node_matrix_filter.weight
                    child_max_points = child_max_points + weight


                # apply taxon filters
                taxon_filters = matrix_filters.filter(filter_type='TaxonFilter')
                for matrix_filter in taxon_filters:
                    
                    matrix_filter_uuid = str(matrix_filter.uuid)
                    
                    taxon_filter = matrix_filter.matrix_filter_type
                    node_taxon_space = taxon_filter.get_space_for_node_with_identifiers(child)
                    child_space[matrix_filter_uuid] = node_taxon_space

                    weight = matrix_filter.weight
                    child_max_points = child_max_points + weight


                child_fact_sheets = []
                if child.meta_node.taxon:
                    child_fact_sheets = self.get_fact_sheets_json_for_taxon(child.meta_node.taxon)


                child_primary_locale_slug = self.add_to_localized_slugs(child)

                child_json = {
                    'uuid' : str(child.name_uuid),
                    #'id' : child.id,
                    #'metaNodeId' : child.meta_node.id,
                    'nodeType' : child.meta_node.node_type,
                    'imageUrl' : self._get_image_url(child.meta_node),
                    'space' : child_space,
                    'maxPoints' : child_max_points,
                    'isVisible' : True,
                    'name' : child.meta_node.name, # all langs as json
                    'decisionRule' : child.decision_rule,
                    'taxon' : None,
                    'factSheets' : child_fact_sheets,
                    'slug' : child_primary_locale_slug,
                }

                if child.meta_node.taxon:
                    child_json['taxon'] = child.meta_node.taxon.as_json()
                    
                elif child.meta_node.node_type == 'result':
                    # fall back to the nature guide as a taxonomic source
                    child_json['taxon'] = child.lazy_taxon.as_json()

                parent_node_json['children'].append(child_json)
                
            parent_node_json['childrenCount'] = len(parent_node.children)

            self.nature_guide_json['tree'][str(parent_node.name_uuid)] = parent_node_json

        return self.nature_guide_json


    def _get_matrix_filter_json(self, matrix_filter):

        serializer = MatrixFilterSerializer(self, matrix_filter)

        matrix_filter_json = serializer.serialize()

        return matrix_filter_json


    def get_localized_slug(self, language_code, id, text):

        localized_text = self.app_release_builder.get_localized(text, language_code)

        if not localized_text:
            raise ValueError('[NatureGuideJSONBuilder] did not find localized text to create slug for language {0}: {1}'.format(
                language_code, text))
        
        slug = '{0}-{1}'.format(id, slugify(localized_text))
        return slug


    def add_to_localized_slugs(self, node):

        node_slug_primary_locale = self.get_localized_slug(self.meta_app.primary_language, node.id, node.meta_node.name)
        self.nature_guide_json['slugs'][node_slug_primary_locale] = str(node.name_uuid)

        if self.meta_app.primary_language not in self.localized_slugs:
            self.localized_slugs[self.meta_app.primary_language] = {
                'slugs' : {}
            }

        self.localized_slugs[self.meta_app.primary_language]['slugs'][node_slug_primary_locale] = node_slug_primary_locale            

        # add to slugs
        for language_code in self.meta_app.secondary_languages():
            localized_node_slug = self.get_localized_slug(language_code, node.id, node.meta_node.name)
            self.nature_guide_json['slugs'][localized_node_slug] = str(node.name_uuid)
            
            if language_code not in self.localized_slugs:
                self.localized_slugs[language_code] = {
                    'slugs' : {}
                }

            self.localized_slugs[language_code]['slugs'][node_slug_primary_locale] = localized_node_slug

        return node_slug_primary_locale


    def get_options(self):
        
        options = {}

        if self.app_generic_content.options:


            ''' options:
            "result_action": {
                "id": 3,
                "uuid": "244e0745-20b8-4223-badf-6cb4da13d3ca",
                "model": "TaxonProfiles",
                "action": "TaxonProfiles",
                "app_label": "taxon_profiles"
            }
            '''

            if 'result_action' in self.app_generic_content.options:

                result_action = self.app_generic_content.options['result_action']

                result_action_json = {
                    'feature' : result_action['action'],
                    'uuid' : result_action['uuid'],
                }

                options['resultAction'] = result_action_json

        return options
        



class MatrixFilterSerializer:

    def __init__(self, jsonbuilder, matrix_filter):
        self.matrix_filter = matrix_filter
        self.jsonbuilder = jsonbuilder


    def serialize(self):

        matrix_filter_json = self.serialize_matrix_filter()

        space = self.matrix_filter.get_space()
        space_list = self.get_space_list(self.matrix_filter, space)

        matrix_filter_json['space'] = space_list

        # get restrictions
        matrix_filter_restrictions = MatrixFilterRestriction.objects.filter(
            restricted_matrix_filter=self.matrix_filter)

        for matrix_filter_restriction in matrix_filter_restrictions:

            # handlebars {{#if restrictions }} returns always True, even if the object is empty
            if matrix_filter_json['isRestricted'] != True:
                matrix_filter_json['isRestricted'] = True

            restrictive_matrix_filter = matrix_filter_restriction.restrictive_matrix_filter
            restrictive_matrix_filter_uuid = str(restrictive_matrix_filter.uuid)

            if restrictive_matrix_filter.filter_type in ['RangeFilter', 'NumberFilter']:
                restrictive_space_list = [matrix_filter_restriction]
            else:
                restrictive_space_list = matrix_filter_restriction.values.all()

            restrictive_space_list_json = self.get_space_list(restrictive_matrix_filter, restrictive_space_list, simple=True)


            matrix_filter_json['restrictions'][restrictive_matrix_filter_uuid] = restrictive_space_list_json
            

        return matrix_filter_json


    def serialize_matrix_filter(self):

        allow_multiple_values = False

        if self.matrix_filter.definition:
            allow_multiple_values = self.matrix_filter.definition.get('allow_multiple_values', False)

        matrix_filter_json = {
            'uuid' : str(self.matrix_filter.uuid),
            'name' : self.matrix_filter.name,
            'type' : self.matrix_filter.filter_type,
            'position' : self.matrix_filter.position,
            'description' : self.matrix_filter.description,
            'weight' : self.matrix_filter.weight,
            'restrictions' : {},
            'isRestricted' : False,
            'allowMultipleValues' : allow_multiple_values,
            'space' : [],
            'definition' : {},
        }


        if self.matrix_filter.filter_type == 'RangeFilter':

            if self.matrix_filter.definition:
                
                matrix_filter_json['definition'].update({
                    'min' : self.matrix_filter.definition.get('min', None),
                    'max' : self.matrix_filter.definition.get('max', None),
                    'step' : self.matrix_filter.definition.get('step', None),
                })

        if self.matrix_filter.filter_type in ['RangeFilter', 'NumberFilter']:

            if self.matrix_filter.definition:
                
                matrix_filter_json['definition'].update({
                    'unit' : self.matrix_filter.definition.get('unit', None),
                    'unit_verbose' : self.matrix_filter.definition.get('unit_verbose', None),
                })
        
        return matrix_filter_json


    def get_space_list(self, matrix_filter, space_list, simple=False):
        
        list_serializer = MatrixFilterSpaceListSerializer(self.jsonbuilder, matrix_filter, space_list)

        space_list_json = list_serializer.serialize(simple=simple)

        return space_list_json
        


class MatrixFilterSpaceListSerializer:

    def __init__(self, jsonbuilder, matrix_filter, space_list):
        self.jsonbuilder = jsonbuilder
        self.matrix_filter = matrix_filter
        self.space_list = space_list

    def serialize(self, simple=False):

        space_list_json = []

        if self.matrix_filter.filter_type == 'NumberFilter':
            
            encoded_space = self.space_list[0].encoded_space

            for subspace in encoded_space:

                space_identifier = self.matrix_filter.matrix_filter_type.get_space_identifier(subspace)   

                space_json = {
                    'spaceIdentifier' : space_identifier,
                    'encodedSpace' : subspace,
                }

                space_list_json.append(space_json)
            

        elif self.matrix_filter.filter_type == 'RangeFilter':

            encoded_space = self.space_list[0].encoded_space
            space_identifier = self.matrix_filter.matrix_filter_type.get_space_identifier(encoded_space)

            space_list_json = [
                {
                    'encodedSpace' : encoded_space,
                    'spaceIdentifier' : space_identifier,
                }
            ]


        elif self.matrix_filter.filter_type == 'TaxonFilter':
            # encoded_space is json
            encoded_space = self.space_list[0].encoded_space

            for subspace in encoded_space:

                #json.dumps(encoded_space, separators=(',', ':'))
                # no whitespace in encoded space for compatibility with javascript
                space_b64 = self.matrix_filter.matrix_filter_type.get_taxonfilter_space_b64(subspace)
                
                space_identifier = self.matrix_filter.matrix_filter_type.get_space_identifier(subspace)

                space_json = {
                    'spaceIdentifier' : space_identifier,
                    'encodedSpace' : space_b64,
                }

                if simple == False:
                    space_json.update({
                        'shortName' : subspace['latname'][:3],
                        'latname' : subspace['latname'],
                        'isCustom' : subspace['is_custom'],
                    })

                space_list_json.append(space_json)
            

        elif self.matrix_filter.filter_type == 'ColorFilter':

            for subspace in self.space_list:
                
                encoded_space = subspace.encoded_space

                html = self.matrix_filter.matrix_filter_type.encoded_space_to_html(encoded_space)

                space_identifier = self.matrix_filter.matrix_filter_type.get_space_identifier(subspace)

                description = None
                gradient = False

                if subspace.additional_information:
                    description = subspace.additional_information.get('description', None)
                    gradient = subspace.additional_information.get('gradient', False)
                
                space_json = {
                    'spaceIdentifier' : space_identifier,
                    'encodedSpace' : encoded_space,
                }

                if simple == False:
                    space_json.update({
                        'html' : html,
                        'gradient' : gradient,
                        'description' : description,
                    })

                space_list_json.append(space_json)


        elif self.matrix_filter.filter_type == 'DescriptiveTextAndImagesFilter':

            for subspace in self.space_list:

                space_identifier = self.matrix_filter.matrix_filter_type.get_space_identifier(subspace)

                space_json = {
                    'spaceIdentifier' : space_identifier,
                    'encodedSpace' : subspace.encoded_space,
                }

                if simple == False:
                    space_json['imageUrl'] = self.jsonbuilder._get_image_url(subspace)

                    secondary_image = self.jsonbuilder._get_content_image(subspace, image_type='secondary')

                    if secondary_image:
                        space_json['secondaryImageUrl'] = self.jsonbuilder._get_image_url(subspace, image_type='secondary')
                    else:
                        space_json['secondaryImageUrl'] = None
                
                space_list_json.append(space_json)


        elif self.matrix_filter.filter_type == 'TextOnlyFilter':

            for subspace in self.space_list:

                space_identifier = self.matrix_filter.matrix_filter_type.get_space_identifier(subspace)
                encoded_space = subspace.encoded_space

                space_json = {
                    'spaceIdentifier' : space_identifier,
                    'encodedSpace' : encoded_space,
                }
                
                space_list_json.append(space_json)

        else:
            raise ValueError('Unsupported filter_type: {0}'.format(self.matrix_filter.filter_type))

        
        return space_list_json
