from app_kit.appbuilders.JSONBuilders.JSONBuilder import JSONBuilder

from app_kit.features.nature_guides.models import (NatureGuidesTaxonTree, MatrixFilter, NodeFilterSpace)

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
            'start_node_uuid' : str(start_node.name_uuid)
        })

        # iterate over all parent nodes
        parent_nodes = NatureGuidesTaxonTree.objects.filter(nature_guide=nature_guide).exclude(
            meta_node__node_type='result')

        for parent_node in parent_nodes:

            parent_node_json = {
                'children' : [],
                'matrix_filters' : [],
                'matrix_filter_types' : {},
            }

            
            matrix_filters = MatrixFilter.objects.filter(meta_node=parent_node.meta_node).order_by('position')

            # build all matrix filters
            for matrix_filter in matrix_filters:
                matrix_filter_json = self._get_matrix_filter_json(matrix_filter)

                parent_node_json['matrix_filters'].append(matrix_filter_json)

                parent_node_json['matrix_filter_types'][str(matrix_filter.uuid)] = matrix_filter.filter_type

            for child in parent_node.children:

                # fill the space
                # there is only one NodeFilterSpace per matrix_filter/node combination
                space_query = NodeFilterSpace.objects.filter(node=child, matrix_filter__in=matrix_filters)
                
                child_space = {}

                for node_filter_space in space_query:

                    # get the matrix_filter for this specific space
                    node_matrix_filter = node_filter_space.matrix_filter

                    node_matrix_filter_uuid = str(node_matrix_filter.uuid)

                    # a list of spaces applicable for this entry/matrix_filter combination
                    # is added to the cache
                    child_space[node_matrix_filter_uuid] = node_matrix_filter.matrix_filter_type.get_node_filter_space_as_list(
                        node_filter_space)


                child_json = {
                    'id' : child.id,
                    'meta_node_id' : child.meta_node.id,
                    'node_type' : child.meta_node.node_type,
                    'image_url' : self._get_image_url(child.meta_node),
                    'uuid' : str(child.name_uuid),
                    'space' : child_space,
                    'is_visible' : True,
                    'name' : child.meta_node.name, # all langs as json
                    'decision_rule' : child.decision_rule,
                    'taxon' : None
                }

                if child.meta_node.taxon:
                    child_json['taxon'] = child.meta_node.taxon.as_json()
                    
                elif child.meta_node.node_type == 'result':
                    # fall back to the nature guide as a taxonomic source
                    child_json['taxon'] = child.lazy_taxon.as_json()

                parent_node_json['children'].append(child_json)
                
            parent_node_json['children_count'] = len(parent_node.children)

            nature_guide_json['tree'][str(parent_node.name_uuid)] = parent_node_json

        return nature_guide_json


    def _get_matrix_filter_json(self, matrix_filter):

        matrix_filter_json = {
            'uuid' : str(matrix_filter.uuid),
            'name' : matrix_filter.name,
            'filter_type' : matrix_filter.filter_type,
            'description' : matrix_filter.description,
            'definition' : matrix_filter.definition,
            'weight' : matrix_filter.weight,
        }

        space = matrix_filter.get_space()

        if matrix_filter.filter_type in ['NumberFilter', 'RangeFilter']:
            encoded_space = space.first().encoded_space            

            matrix_filter_json['space'] = encoded_space


        elif matrix_filter.filter_type == 'TaxonFilter':
            encoded_space = space.first().encoded_space

            space = []

            for subspace in encoded_space:

                space_b64 = base64.b64encode(json.dumps(subspace).encode('utf-8')).decode('utf-8')
                
                space_entry = {
                    'short_name' : subspace['latname'][:3],
                    'latname' : subspace['latname'],
                    'encoded' : space_b64,
                    'is_custom' : subspace['is_custom'],
                }

                space.append(space_entry)


            matrix_filter_json['space'] = space
            

        elif matrix_filter.filter_type == 'ColorFilter':
            spaces = []

            for subspace in space:
                encoded_space = subspace.encoded_space
                subspace_entry = {
                    'encoded_space' : encoded_space,
                    'rgba' : 'rgba({0},{1},{2},{3})'.format(encoded_space[0], encoded_space[1], encoded_space[2],
                                                           encoded_space[3]),
                }
                spaces.append(subspace_entry)
                
            matrix_filter_json['space'] = spaces


        elif matrix_filter.filter_type == 'DescriptiveTextAndImagesFilter':

            encoded_space = []

            for subspace in space:
                entry = {}
                entry['encoded_space'] = subspace.encoded_space
                entry['image_url'] = self._get_image_url(subspace),
                
                encoded_space.append(entry)
                
            matrix_filter_json['space'] = encoded_space


        elif matrix_filter.filter_type == 'TextOnlyFilter':
            
            spaces = []

            for subspace in space:
                encoded_space = subspace.encoded_space
                subspace_entry = {
                    'encoded_space' : encoded_space,
                }
                
                spaces.append(subspace_entry)
                
            matrix_filter_json['space'] = spaces

        else:
            raise ValueError('Unsupported filter_type: {0}'.format(matrix_filter.filter_type))

        return matrix_filter_json
        
        
