from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder

from app_kit.features.nature_guides.models import (NatureGuidesTaxonTree, MatrixFilter, NodeFilterSpace,
                                                   MatrixFilterRestriction, IDENTIFICATION_MODE_FLUID)


from app_kit.features.fact_sheets.models import FactSheet

from django.utils.text import slugify

import base64, json



'''
    build one file for all languages, only keys for translation
'''
class NatureGuideJSONBuilder(JSONBuilder):


    def build(self):

        nature_guide_json = self._build_common_json()

        nature_guide = self.app_generic_content.generic_content

        start_node = NatureGuidesTaxonTree.objects.get(nature_guide=nature_guide, meta_node__node_type='root')
        
        nature_guide_json.update({
            'tree' : {},
            'crosslinks' : nature_guide.crosslinks(),
            'startNodeUuid' : str(start_node.name_uuid),
            'slugs' : {},
        })

        # iterate over all parent nodes
        parent_nodes = NatureGuidesTaxonTree.objects.filter(nature_guide=nature_guide).exclude(
            meta_node__node_type='result')

        for parent_node in parent_nodes:

            is_active = True

            if parent_node.additional_data:
                is_active = parent_node.additional_data.get('is_active', True)

            if is_active == False:
                continue

            identification_mode = IDENTIFICATION_MODE_FLUID

            if parent_node.meta_node.settings:
                identification_mode = parent_node.meta_node.settings.get('identification_mode', IDENTIFICATION_MODE_FLUID)

            fact_sheets = []

            if parent_node.meta_node.taxon:
                fact_sheets = self.get_fact_sheets_json_for_taxon(parent_node.meta_node.taxon)

            parent_node_json = {
                'uuid' : str(parent_node.name_uuid),
                'name' : parent_node.meta_node.name,
                'taxon' : None,
                'children' : [],
                'matrixFilters' : {},
                'identificationMode' : identification_mode,
                'factSheets' : fact_sheets,
                'slugs' : {},
            }

            # add to slugs
            for language_code in self.meta_app.languages():
                localized_parent_node_slug = self.get_localized_slug(language_code, parent_node.id, parent_node.meta_node.name)
                nature_guide_json['slugs'][localized_parent_node_slug] = str(parent_node.name_uuid)
                parent_node_json['slugs'][language_code] = localized_parent_node_slug


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
                    'slugs' : {},
                }

                # add to slugs
                for language_code in self.meta_app.languages():
                    localized_child_slug = self.get_localized_slug(language_code, child.id, child.meta_node.name)
                    nature_guide_json['slugs'][localized_child_slug] = str(child.name_uuid)
                    child_json['slugs'][language_code] = localized_child_slug

                if child.meta_node.taxon:
                    child_json['taxon'] = child.meta_node.taxon.as_json()
                    
                elif child.meta_node.node_type == 'result':
                    # fall back to the nature guide as a taxonomic source
                    child_json['taxon'] = child.lazy_taxon.as_json()

                parent_node_json['children'].append(child_json)
                
            parent_node_json['childrenCount'] = len(parent_node.children)

            nature_guide_json['tree'][str(parent_node.name_uuid)] = parent_node_json

        return nature_guide_json


    def _get_matrix_filter_json(self, matrix_filter):

        allow_multiple_values = False

        if matrix_filter.definition:
            allow_multiple_values = matrix_filter.definition.get('allow_multiple_values', False)

        matrix_filter_json = {
            'uuid' : str(matrix_filter.uuid),
            'name' : matrix_filter.name,
            'type' : matrix_filter.filter_type,
            'position' : matrix_filter.position,
            'description' : matrix_filter.description,
            #'definition' : matrix_filter.definition,
            'weight' : matrix_filter.weight,
            'restrictions' : {},
            'isRestricted' : False,
            'allowMultipleValues' : allow_multiple_values
        }

        space = matrix_filter.get_space()

        if matrix_filter.filter_type == 'NumberFilter':
            
            encoded_space = space.first().encoded_space

            spaces = []

            for subspace in encoded_space:

                space_identifier = matrix_filter.matrix_filter_type.get_space_identifier(subspace)   

                space_entry = {
                    'spaceIdentifier' : space_identifier,
                    'encodedSpace' : subspace,
                }

                spaces.append(space_entry)
            
            matrix_filter_json['space'] = spaces
        
        elif matrix_filter.filter_type == 'RangeFilter':

            encoded_space = space.first().encoded_space            

            matrix_filter_json['encodedSpace'] = encoded_space


        elif matrix_filter.filter_type == 'TaxonFilter':
            # encoded_space is json
            encoded_space = space.first().encoded_space

            spaces = []

            for subspace in encoded_space:

                #json.dumps(encoded_space, separators=(',', ':'))
                # no whitespace in encoded space for compatibility with javascript
                space_b64 = matrix_filter.matrix_filter_type.get_taxonfilter_space_b64(subspace)
                
                space_identifier = matrix_filter.matrix_filter_type.get_space_identifier(subspace)

                space_entry = {
                    'spaceIdentifier' : space_identifier,
                    'shortName' : subspace['latname'][:3],
                    'latname' : subspace['latname'],
                    'encodedSpace' : space_b64,
                    'isCustom' : subspace['is_custom'],
                }

                spaces.append(space_entry)


            matrix_filter_json['space'] = spaces
            

        elif matrix_filter.filter_type == 'ColorFilter':
            spaces = []

            for subspace in space:
                
                encoded_space = subspace.encoded_space

                html = matrix_filter.matrix_filter_type.encoded_space_to_html(encoded_space)

                space_identifier = matrix_filter.matrix_filter_type.get_space_identifier(subspace)

                description = None
                gradient = False

                if subspace.additional_information:
                    description = subspace.additional_information.get('description', None)
                    gradient = subspace.additional_information.get('gradient', False)
                
                subspace_entry = {
                    'spaceIdentifier' : space_identifier,
                    'encodedSpace' : encoded_space,
                    'html' : html,
                    'gradient' : gradient,
                    'description' : description,
                }
                spaces.append(subspace_entry)
                
            matrix_filter_json['space'] = spaces


        elif matrix_filter.filter_type == 'DescriptiveTextAndImagesFilter':

            spaces = []

            for subspace in space:

                space_identifier = matrix_filter.matrix_filter_type.get_space_identifier(subspace)

                entry = {
                    'spaceIdentifier' : space_identifier,
                    'encodedSpace' : subspace.encoded_space,
                    'imageUrl' : self._get_image_url(subspace),
                }

                secondary_image = self._get_content_image(subspace, image_type='secondary')

                if secondary_image:
                    entry['secondaryImageUrl'] = self._get_image_url(subspace, image_type='secondary')
                else:
                    entry['secondaryImageUrl'] = None
                
                spaces.append(entry)
                
            matrix_filter_json['space'] = spaces


        elif matrix_filter.filter_type == 'TextOnlyFilter':
            
            spaces = []

            for subspace in space:

                space_identifier = matrix_filter.matrix_filter_type.get_space_identifier(subspace)
                encoded_space = subspace.encoded_space

                subspace_entry = {
                    'spaceIdentifier' : space_identifier,
                    'encodedSpace' : encoded_space,
                }
                
                spaces.append(subspace_entry)
                
            matrix_filter_json['space'] = spaces

        else:
            raise ValueError('Unsupported filter_type: {0}'.format(matrix_filter.filter_type))


        # get restrictions
        matrix_filter_restrictions = MatrixFilterRestriction.objects.filter(
            restricted_matrix_filter=matrix_filter)

        for matrix_filter_restriction in matrix_filter_restrictions:

            # handlebars {{#if restrictions }} returns always True, even if the object is empty
            if matrix_filter_json['isRestricted'] != True:
                matrix_filter_json['isRestricted'] = True

            restrictive_matrix_filter = matrix_filter_restriction.restrictive_matrix_filter
            restrictive_matrix_filter_uuid = str(restrictive_matrix_filter.uuid)

            restrictive_space = restrictive_matrix_filter.matrix_filter_type.get_filter_space_as_list(
                matrix_filter_restriction)

            matrix_filter_json['restrictions'][restrictive_matrix_filter_uuid] = restrictive_space
            

        return matrix_filter_json


    def get_localized_slug(self, language_code, id, text):

        localized_text = self.app_release_builder.get_localized(text, language_code)

        if not localized_text:
            raise ValueError('[NatureGuideJSONBuilder] did not find localized text to create slug for language {0}: {1}'.format(
                language_code, text))
        
        slug = '{0}-{1}'.format(id, slugify(localized_text))
        return slug


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
        
