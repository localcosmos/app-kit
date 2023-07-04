from app_kit.features.nature_guides.models import (NatureGuide, MetaNode, NatureGuidesTaxonTree, MatrixFilter,
                                                   MatrixFilterSpace, NodeFilterSpace, ChildrenCacheManager)

from app_kit.features.nature_guides.matrix_filters import MATRIX_FILTER_TYPES

from taxonomy.lazy import LazyTaxon
from taxonomy.models import TaxonomyModelRouter


class TaxonFilterSpaceMixin:
    
    def get_taxonfilter_space(self):
        models = TaxonomyModelRouter('taxonomy.sources.col')
        animalia = models.TaxonTreeModel.objects.get(taxon_latname='Animalia')
        animalia = LazyTaxon(instance=animalia)

        taxon_dic = {
            'taxon_source' : animalia.taxon_source,
            'name_uuid' : str(animalia.name_uuid),
            'taxon_latname' : animalia.taxon_latname,
            'taxon_author' : animalia.taxon_author,
            'taxon_nuid' : animalia.taxon_nuid,
        }

        taxonfilter = {
            'taxa' : [taxon_dic],
            'latname' : 'Animalia',
            'is_custom' : False,
        }

        return [taxonfilter]


class WithNatureGuide(TaxonFilterSpaceMixin):

    def create_nature_guide(self, name='Test Nature Guide'):

        nature_guide = NatureGuide.objects.create(name, 'en')

        return nature_guide


    def create_node(self, parent_node, name, **kwargs):

        node_type = kwargs.pop('node_type', 'node')

        meta_node = MetaNode(
            name=name,
            nature_guide=parent_node.nature_guide,
            node_type=node_type,
        )

        meta_node.save()

        node = NatureGuidesTaxonTree(
            nature_guide=parent_node.nature_guide,
            meta_node=meta_node,
            **kwargs
        )

        node.save(parent_node)

        cache = ChildrenCacheManager(node.parent.meta_node)
        cache.add_or_update_child(node)

        return node


    def create_matrix_filter(self, name, meta_node, filter_type, **kwargs):

        matrix_filter = MatrixFilter(
            meta_node=meta_node,
            name=name,
            filter_type=filter_type,
            **kwargs
        )

        matrix_filter.save()

        return matrix_filter



class WithMatrixFilters(TaxonFilterSpaceMixin):

    def create_matrix_filter_with_space(self, parent_node, filter_type, encoded_space):


        matrix_filter = MatrixFilter(
            meta_node=parent_node.meta_node,
            name='{0} name'.format(filter_type),
            filter_type=filter_type,
        )

        matrix_filter.save()

        space = MatrixFilterSpace(
            matrix_filter=matrix_filter,
            encoded_space=encoded_space, 
        )

        space.save()

        return matrix_filter


    def create_all_matrix_filters(self, parent_node):

        matrix_filters = []

        taxonfilter = self.get_taxonfilter_space()

        encoded_spaces = {
            'ColorFilter' : [0,0,0,1],
            'RangeFilter' : [4,7],
            'DescriptiveTextAndImagesFilter' : ['description 1', 'description 2'],
            'NumberFilter' : [1,2,3,4],
            'TaxonFilter' : taxonfilter,
            'TextOnlyFilter' : 'Text only text',
        }
        
        # create all fields with values
        for filter_tuple in MATRIX_FILTER_TYPES:

            filter_type = filter_tuple[0]

            if filter_type == 'DescriptiveTextAndImagesFilter':
                encoded_space = encoded_spaces[filter_type][0]
                matrix_filter = self.create_matrix_filter_with_space(parent_node, filter_type, encoded_space)

                space_2 = MatrixFilterSpace(
                    matrix_filter=matrix_filter,
                    encoded_space=encoded_spaces[filter_type][1], 
                )

                space_2.save()
            
                matrix_filters.append(matrix_filter)

                
            else:

                encoded_space = encoded_spaces[filter_type]
                matrix_filter = self.create_matrix_filter_with_space(parent_node, filter_type, encoded_space)

                if filter_type in ['RangeFilter', 'NumberFilter']:
                    matrix_filter.definition = {
                        'unit' : 'cm',
                        'unit_verbose' : 'centimeters',
                    }
                    matrix_filter.save()
            
                matrix_filters.append(matrix_filter)
            

        return matrix_filters


    def fill_matrix_filters_nodes(self, parent_node, child_nodes):

        matrix_filters = MatrixFilter.objects.filter(meta_node=parent_node.meta_node)

        for matrix_filter in matrix_filters:

            for node in child_nodes:

                if matrix_filter.filter_type in ['DescriptiveTextAndImagesFilter', 'ColorFilter',
                                                 'TextOnlyFilter']:

                    space = matrix_filter.get_space()
                    node_space = NodeFilterSpace(
                        node=node,
                        matrix_filter=matrix_filter,
                    )
                    node_space.save()
                    node_space.values.add(space[0])


                elif matrix_filter.filter_type == 'RangeFilter':
                    node_space = NodeFilterSpace(
                        node=node,
                        matrix_filter=matrix_filter,
                        encoded_space = [5,6],
                    )
                    node_space.save()

                elif matrix_filter.filter_type == 'NumberFilter':
                    node_space = NodeFilterSpace(
                        node=node,
                        matrix_filter=matrix_filter,
                        encoded_space = [2,3],
                    )
                    node_space.save()
                    

                elif matrix_filter.filter_type != 'TaxonFilter':
                    raise ValueError('Invalid filter: {0}'.format(matrix_filter.filter_type))
                    

    def get_matrix_filter_post_data(self, matrix_filter):

        post_data = {}

        filter_type = matrix_filter.filter_type

        if filter_type == 'RangeFilter':
            post_data['{0}_0'.format(str(matrix_filter.uuid))] = '0.5'
            post_data['{0}_1'.format(str(matrix_filter.uuid))] = '4'

        elif filter_type in ['DescriptiveTextAndImagesFilter', 'ColorFilter', 'TextOnlyFilter']:
            space = matrix_filter.get_space()
            post_data[str(matrix_filter.uuid)] = [space[0].id]

        elif filter_type == 'NumberFilter':
            post_data[str(matrix_filter.uuid)] = [2,3]

        elif filter_type == 'TaxonFilter':
            pass

        else:
            raise ValueError('Invalid filter type: {0}'.format(matrix_filter.filter_type))

        return post_data

            
