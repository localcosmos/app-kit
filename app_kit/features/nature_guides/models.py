from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

from app_kit.generic import GenericContentManager, GenericContent

from localcosmos_server.taxonomy.generic import ModelWithTaxon
from taxonomy.lazy import LazyTaxon, LazyTaxonList

from app_kit.models import ContentImage, ContentImageMixin, UpdateContentImageTaxonMixin, MetaAppGenericContent

from app_kit.features.taxon_profiles.models import TaxonProfiles, TaxonProfile

from .definitions import TEXT_LENGTH_RESTRICTIONS

import uuid, shutil, os, json

IDENTIFICATION_MODE_FLUID = 'fluid'
IDENTIFICATION_MODE_STRICT = 'strict'

'''
    Universal identification key system:
    dichotomous keys and polytomus keys/matrix keys or a combination of both
    Nature Guides can be identification keys or just a list of taxa
'''

class NatureGuideManager(GenericContentManager):
    
    def create(self, name, primary_language):

        nature_guide = super().create(name, primary_language)

        # create the start node
        meta_node = MetaNode(
            nature_guide=nature_guide,
            name=name,
            node_type = 'root',
        )

        meta_node.save()

        start_node = NatureGuidesTaxonTree(
            nature_guide=nature_guide,
            meta_node=meta_node,
        )

        start_node.save(None)

        return nature_guide



RESULT_ACTIONS = (
    ('taxon_profile', _('Species detail page')),
    ('observation_form', _('Observation form')),
)


class NatureGuide(ContentImageMixin, GenericContent):

    # has to be rewritten
    zip_import_supported = False

    objects = NatureGuideManager()

    @property
    def zip_import_class(self):
        from .zip_import import NatureGuideZipImporter
        return NatureGuideZipImporter


    @property
    def root_node(self):
        return NatureGuidesTaxonTree.objects.get(nature_guide=self, meta_node__node_type='root')


    def get_primary_localization(self, meta_app=None):
        locale = super().get_primary_localization(meta_app)

        # fetch all meta_nodes
        meta_nodes = MetaNode.objects.filter(nature_guide=self)

        for meta_node in meta_nodes:

            if meta_node.name:
                locale[meta_node.name] = meta_node.name

            # fetch all decision rules
            tree_entries = NatureGuidesTaxonTree.objects.filter(nature_guide=self, meta_node=meta_node)

            for tree_entry in tree_entries:

                if tree_entry.decision_rule:
                    locale[tree_entry.decision_rule] = tree_entry.decision_rule

                # get all crosslinks
                crosslinks = NatureGuideCrosslinks.objects.filter(child=tree_entry,
                                                                   decision_rule__isnull=False)

                for crosslink in crosslinks:
                    locale[crosslink.decision_rule] = crosslink.decision_rule


            # fetch all matrix filters
            matrix_filters = MatrixFilter.objects.filter(meta_node=meta_node)

            for matrix_filter in matrix_filters:

                locale[matrix_filter.name] = matrix_filter.name

                if matrix_filter.description:
                    locale[matrix_filter.description] = matrix_filter.description

                if matrix_filter.filter_type in ['DescriptiveTextAndImagesFilter', 'TextOnlyFilter']:

                    spaces = matrix_filter.get_space()

                    for space in spaces:
                        locale[space.encoded_space] = space.encoded_space

        
        return locale


    # return crosslink dict {parent_nuid:[child_1_nuid,]}
    def crosslinks(self):

        crosslinks_dic = {}
        
        # construct the crosslink lookup dict
        crosslinks = NatureGuideCrosslinks.objects.filter(parent__nature_guide=self)
        
        for crosslink in crosslinks:

            if crosslink.parent.taxon_nuid not in crosslinks_dic:
                crosslinks_dic[crosslink.parent.taxon_nuid] = []

            crosslinks_dic[crosslink.parent.taxon_nuid].append(crosslink.child.taxon_nuid)   

        return crosslinks_dic


    def crosslink_list(self):

        query = NatureGuideCrosslinks.objects.filter(parent__nature_guide=self)
        
        crosslinks = []

        for crosslink in query:
            crosslink_tuple = (crosslink.parent.taxon_nuid, crosslink.child.taxon_nuid)
            crosslinks.append(crosslink_tuple)

        return crosslinks

    def get_inactive_nuids(self):

        inactive_nuids = set([])

        for node in NatureGuidesTaxonTree.objects.filter(nature_guide=self):
            if node.additional_data and node.additional_data.get('is_active', True) == False:
                inactive_nuids.add(node.taxon_nuid)
        
        return inactive_nuids

    # return a LazyTaxonList instance
    def taxa(self):
        
        queryset = MetaNode.objects.filter(nature_guide=self, node_type='result',
                                           taxon_latname__isnull=False).distinct('taxon_latname')
        
        taxonlist = LazyTaxonList(queryset)

        fallback_nodes = MetaNode.objects.filter(nature_guide=self, node_type='result',
                                                 taxon_latname__isnull=True)

        fallback_query = NatureGuidesTaxonTree.objects.filter(nature_guide=self, meta_node__in=fallback_nodes)
        taxonlist.add(fallback_query)

        return taxonlist
    

    def higher_taxa(self):
        return LazyTaxonList()
    

    class Meta:
        verbose_name = _('Nature Guide')
        verbose_name_plural = _('Nature Guides')


FeatureModel = NatureGuide


'''
    ChildrenCacheManager
    - manage the children_json attribute (=cache) of a node

    CACHE UPDATING:
    - when a node is inserted (NatureGuideTaxonTree.save)
    - when a node is deleted (NatureGuideTaxonTree.delete)
    - when the Color of a ColorTrait is changed (parent_node) (ManageColorValue VIEW)
    - when the space of a Node is altered (ManageMatrixNodelink VIEW)
    

    CACHE IS NOT UPDATED FOR THE FOLLOWING:
    - removing a trait_property or _value from parent_node
    - adding a trait_property or _value to parent_node
    - altering parent_node space for anything else than color
    -- explanation: TextAndImages do not change encoded_space, but localization
    -- for Range/Numbers false values are acceptable, numbers are never changed - only added or deleted

    When building the app, the json is rebuilt
'''

class ChildrenCacheManager:

    def __init__(self, meta_node):
        self.meta_node = meta_node

    # rebuild the whole cache for this node from scratch
    def rebuild_cache(self):

        data = self.get_data(empty=True)

        identification_mode = IDENTIFICATION_MODE_STRICT

        if self.meta_node.settings:
            identification_mode = self.meta_node.settings.get('identification_mode', IDENTIFICATION_MODE_STRICT)

        data['identification_mode'] = identification_mode
        
        # add all matrix filters
        matrix_filters = MatrixFilter.objects.filter(meta_node=self.meta_node)
        for matrix_filter in matrix_filters:
            data = self.add_matrix_filter_to_cache(data, matrix_filter)

            # add all restrictions
            restrictions = MatrixFilterRestriction.objects.filter(restricted_matrix_filter=matrix_filter)

            for restriction in restrictions:
                data = self.add_matrix_filter_restriction_to_cache(data, restriction)
            
        
        # get all children of this meta_node, including crosslinks
        children = NatureGuidesTaxonTree.objects.filter(parent__meta_node=self.meta_node)

        for child in children:

            child_json = self.child_as_json(child)
            data['items'].append(child_json)


        crosslink_children = NatureGuideCrosslinks.objects.filter(parent__meta_node=self.meta_node)
        for crosslink in crosslink_children:
            child_json = self.child_as_json(crosslink.child, crosslink=crosslink)
            data['items'].insert(crosslink.position, child_json)

        self.meta_node.children_cache = data
        self.meta_node.save()
        

    def get_data(self, empty=False):

        data = self.meta_node.children_cache

        if not data or empty == True:
            
            data = {
                'items' : [],
                'matrix_filters' : {},
            }
        
        return data


    def child_as_json(self, child, crosslink=None):

        matrix_filters = MatrixFilter.objects.filter(meta_node=self.meta_node)

        # there is only one NodeFilterSpace per matrix_filter/node combination
        space_query = NodeFilterSpace.objects.filter(node=child, matrix_filter__in=matrix_filters)

        max_points = 0
        space = {}

        for node_filter_space in space_query:

            # get the matrix_filter for this specific space
            matrix_filter = node_filter_space.matrix_filter

            matrix_filter_uuid = str(matrix_filter.uuid)

            # a list of spaces applicable for this entry/matrix_filter combination
            # is added to the cache
            space[matrix_filter_uuid] = matrix_filter.matrix_filter_type.get_filter_space_as_list(
                node_filter_space)

            weight = matrix_filter.weight
            max_points = max_points + weight


        # apply taxon filters
        taxon_filters = matrix_filters.filter(filter_type='TaxonFilter')
        for matrix_filter in taxon_filters:
            
            matrix_filter_uuid = str(matrix_filter.uuid)
            
            taxon_filter = matrix_filter.matrix_filter_type
            node_taxon_space = taxon_filter.get_space_for_node(child)
            space[matrix_filter_uuid] = node_taxon_space

            weight = matrix_filter.weight
            max_points = max_points + weight
            

        decision_rule = child.decision_rule

        if crosslink:
            decision_rule = crosslink.decision_rule
            
        child_json = {
            'id' : child.id,
            'meta_node_id' : child.meta_node.id,
            'node_type' : child.meta_node.node_type,
            'image_url' : child.meta_node.image_url(), 
            'uuid' : str(child.name_uuid),
            'space' : space,
            'max_points' : max_points,
            'is_visible' : True,
            'name' : child.meta_node.name,
            'morphotype': child.meta_node.morphotype,
            'decision_rule' : decision_rule,
            'taxon' : None,
        }

        if child.meta_node.taxon:
            child_json['taxon'] = child.meta_node.taxon.as_json()

        return child_json

    '''
        CHILD MANAGEMENT
    '''
    def add_or_update_child(self, child_node, crosslink=None):

        data = self.get_data()

        items = data['items']

        child_json = self.child_as_json(child_node, crosslink=crosslink)

        found_child = False
        for item in items:

            if item['uuid'] == str(child_node.name_uuid):
                found_child = True
                items[items.index(item)] = child_json
                break

        if not found_child:
            position = child_node.position
            if crosslink:
                position = crosslink.position
                
            items.insert(position, child_json)
            
        data['items'] = items

        self.meta_node.children_cache = data
        self.meta_node.save()        

        
    def remove_child(self, child_node):
        
        data = self.get_data()

        items = data['items']

        for item in items:

            if item['uuid'] == str(child_node.name_uuid):
                del items[items.index(item)]
                break

        data['items'] = items

        self.meta_node.children_cache = data
        self.meta_node.save()

    '''
    MATRIX FILTER MANAGEMENT
    - MatrixFilterSpaces are stored in the cache with minimal required information
    '''
    def add_matrix_filter_to_cache(self, data, matrix_filter):

        allow_multiple_values = False

        if matrix_filter.definition:
            allow_multiple_values = matrix_filter.definition.get('allow_multiple_values', False)

        data['matrix_filters'][str(matrix_filter.uuid)] = {
            'type' : matrix_filter.filter_type,
            'name' : matrix_filter.name,
            'weight' : matrix_filter.weight,
            'allow_multiple_values' : allow_multiple_values, # do not just remove this, this is tied to IdentificationMatrix.js
            'definition': matrix_filter.definition,
        }
            
        return data
        
        
    def add_matrix_filter(self, matrix_filter):
        data = self.get_data()

        data = self.add_matrix_filter_to_cache(data, matrix_filter)

        self.meta_node.children_cache = data
        self.meta_node.save()

        
    def remove_matrix_filter(self, matrix_filter):
        data = self.get_data()

        matrix_filter_uuid = str(matrix_filter.uuid)

        if matrix_filter_uuid in data['matrix_filters']:
            del data['matrix_filters'][matrix_filter_uuid]

        self.meta_node.children_cache = data
        self.meta_node.save()
        

    def add_matrix_filter_restriction_to_cache(self, data, matrix_filter_restriction):

        restricted_matrix_filter = matrix_filter_restriction.restricted_matrix_filter
        restrictive_matrix_filter = matrix_filter_restriction.restrictive_matrix_filter

        restrictive_matrix_filter_uuid = str(restrictive_matrix_filter.uuid)
        restricted_matrix_filter_uuid = str(restricted_matrix_filter.uuid)

        space = restrictive_matrix_filter.matrix_filter_type.get_filter_space_as_list(
            matrix_filter_restriction)
        
        if restricted_matrix_filter_uuid not in data['matrix_filters']:
            data = self.add_matrix_filter_to_cache(data, restricted_matrix_filter)

        if 'restrictions' not in data['matrix_filters'][restricted_matrix_filter_uuid]:
            data['matrix_filters'][restricted_matrix_filter_uuid]['restrictions'] = {}

        data['matrix_filters'][restricted_matrix_filter_uuid]['restrictions'][restrictive_matrix_filter_uuid] = space
    

        return data
    
        
    def update_matrix_filter_restrictions(self, matrix_filter):

        data = self.get_data()
        data = self.add_matrix_filter_to_cache(data, matrix_filter)

        matrix_filter_uuid = str(matrix_filter.uuid)

        restrictions = MatrixFilterRestriction.objects.filter(restricted_matrix_filter=matrix_filter)

        '''
        {
            '<matrix_filter_uuid>' : <space>,
        }
        '''

        for restriction in restrictions:
            data = self.add_matrix_filter_restriction_to_cache(data, restriction)
        
        self.meta_node.children_cache = data
        self.meta_node.save()

    '''
    update matrix filter
    '''
    def update_matrix_filter(self, matrix_filter):

        data = self.get_data()
        data = self.add_matrix_filter_to_cache(data, matrix_filter)
        self.meta_node.children_cache = data
        self.meta_node.save()
        

    '''
    MATRIX FILTER SPACE MANAGEMENT
    '''
    # do nothing, matrix_filter_spaces are not covered by children_cache
    def add_matrix_filter_space(self, matrix_filter_space):
        pass
    
    # update a single value
    # - this is triggered if a user changes ColorFilter or DescriptiveTextAndImagesFilter
    # - if a user changes a color/dtai, the children's space (NodeFilterSpace) has to be adjusted accordingly
    def update_matrix_filter_space(self, matrix_filter_uuid, old_value, new_value):

        data = self.get_data()

        items = data['items']

        # this will update the items space
        for item in items:

            if matrix_filter_uuid in item['space'] and old_value in item['space'][matrix_filter_uuid]:
                index = item['space'][matrix_filter_uuid].index(old_value)
                item['space'][matrix_filter_uuid][index] = new_value

        self.meta_node.children_cache = data
        self.meta_node.save()


    # if a Color or DescriptiveText is removed, remove that space from children
    def remove_matrix_filter_space(self, matrix_filter_space):

        matrix_filter = matrix_filter_space.matrix_filter

        if matrix_filter.filter_type in ['ColorFilter', 'DescriptiveTextAndImagesFilter', 'TextOnlyFilter']:

            data = self.get_data()

            items = data['items']

            matrix_filter_uuid = str(matrix_filter.uuid)
            value = matrix_filter_space.encoded_space

            # this will update the items space
            for item in items:

                if matrix_filter_uuid in item['space'] and value in item['space'][matrix_filter_uuid]:
                    index = item['space'][matrix_filter_uuid].index(value)
                    del item['space'][matrix_filter_uuid][index]


            self.meta_node.children_cache = data
            self.meta_node.save()


    '''
    NODE FILTER SPACE MANAGEMENT
    - cache.update_child is triggered every time a child is saved, this covers all matrix filters
    '''


'''
    MetaNodes
    - contain children_cache, which includes crosslink children
    - necessary for clean crosslink data
    - contain information independant of the parent node like name and image
    - MetaNode is also necessary for assigning a taxon to the node, because the node itself is a taxon
      in the NatureGuidesTaxonTree
'''
NODE_TYPES = (
    ('root', _('Start')),
    ('node', _('Node')),
    ('result', _('Identification result')),
)

class MetaNode(UpdateContentImageTaxonMixin, ContentImageMixin, ModelWithTaxon):
    
    # for unique_together constraint only
    nature_guide = models.ForeignKey(NatureGuide, on_delete=models.CASCADE)
    name = models.CharField(max_length=TEXT_LENGTH_RESTRICTIONS['MetaNode']['name'], null=True)

    morphotype = models.CharField(max_length=355, null=True)

    node_type = models.CharField(max_length=30, choices=NODE_TYPES)

    description = models.TextField(null=True)

    settings = models.JSONField(null=True)

    children_cache = models.JSONField(null=True)


    def get_content_image_restrictions(self, image_type='image'):

        if image_type == 'overview':
            restrictions = {
                'allow_features' : False,
                'allow_cropping' : False,
            }

        else:
            restrictions = {
                'allow_features' : True,
                'allow_cropping' : True,
            }
        
        return restrictions


    def add_setting(self, key, value):
        if not self.settings:
            self.settings = {}
            
        self.settings[key] = value

    def rebuild_cache(self):
        cache_manager = ChildrenCacheManager(self)
        cache_manager.rebuild_cache()

    def delete(self, *args, **kwargs):
        self.delete_images()
        super().delete(*args, **kwargs)

    @property
    def identification_mode(self):
        if self.settings:
            return self.settings.get('identification_mode', IDENTIFICATION_MODE_STRICT)
        return IDENTIFICATION_MODE_STRICT

    def __str__(self):
        if self.name:
            return '{0}'.format(self.name)
        
        if self.taxon_latname:
            return '{0}'.format(self.taxon_latname)
        
        return 'Entry {0}'.format(self.pk)

    # the requirement of copying tree branches makes unique meta node names impossible
    #class Meta:
    #    unique_together=('nature_guide', 'name')

'''
    NatureGuide as a TaxonTree
    - makes LazyTaxon work, e.g. for listing taxa in the backbone taxonomy
    - without cross references
    - if a branch has cross references, query the tree for multiple subtrees to get all results
    - acts as a taxonomic tree and as an identification tree
    - if a node has a taxon assigned, it will occur in 2 taxonomies: NatureGuidesTaxonTree and the source taxonomy
'''
from taxonomy.utils import NuidManager
from localcosmos_server.slugifier import create_unique_slug

# activate Length lookup
from django.db.models import CharField
from django.db.models.functions import Length
CharField.register_lookup(Length, 'length')

    
'''
    NatureGuidesTaxonTree also is the identification key without crosslinks
    - ContentImagemixin is only if the user wants different images depending on  where in the tree a
      MetaNode appears
'''
class NatureGuidesTaxonTreeManager(models.Manager):

    def next_sibling(self, node):

        nuidmanager = NuidManager()
        next_nuid = nuidmanager.next_nuid(node.taxon_nuid)

        return self.filter(taxon_nuid=next_nuid).first()
        
    
from taxonomy.models import TaxonTree, TaxonSynonym, TaxonNamesView, TaxonLocale
class NatureGuidesTaxonTree(ContentImageMixin, TaxonTree):

    taxon_source = 'app_kit.features.nature_guides'
    
    # NatureGuide specific fields
    nature_guide = models.ForeignKey(NatureGuide, on_delete=models.CASCADE)
    
    # see MetaNode for explanation
    meta_node = models.OneToOneField(MetaNode, on_delete=models.CASCADE)

    # child specific, can be overridden by NatureGuideCrosslinks.decision_rule
    decision_rule = models.CharField(max_length=TEXT_LENGTH_RESTRICTIONS['NatureGuidesTaxonTree']['decision_rule'], null=True)

    position = models.IntegerField(default=1)

    objects = NatureGuidesTaxonTreeManager()

    @property
    def name(self):
        return self.meta_node.name

    @property
    def tree_descendants(self):

        children = NatureGuidesTaxonTree.objects.filter(nature_guide=self.nature_guide,
                    taxon_nuid__startswith=self.taxon_nuid).exclude(taxon_nuid=self.taxon_nuid)

        return children

    @property
    def tree_children(self):

        children_nuid_length = len(self.taxon_nuid) + 3
        
        children = NatureGuidesTaxonTree.objects.filter(nature_guide=self.nature_guide,
                            taxon_nuid__startswith=self.taxon_nuid,
                            taxon_nuid__length=children_nuid_length).exclude(taxon_nuid=self.taxon_nuid)

        return children
        
    @property
    def crosslink_children(self):

        children = []
        
        position_map = {}
        
        crosslinks = NatureGuideCrosslinks.objects.filter(parent=self)
        for crosslink in crosslinks:
            position_map[crosslink.child.id] = crosslink.position


        children_ids = crosslinks.values_list('child_id', flat=True)
        tree_entries = NatureGuidesTaxonTree.objects.filter(pk__in=children_ids)
        for entry in tree_entries:
            entry.position = position_map[entry.id]
            entry.is_crosslink = True
            children.append(entry)
            
        return children

    # respect crosslink positioning
    @property
    def children(self):
        # children are tree children and crosslinked children
        children = list(self.tree_children) + list(self.crosslink_children)

        children.sort(key=lambda c: c.position)
        
        return children


    @property
    def children_count(self):
        return len(self.children)

    ''' parent not unique due to crosslinks
    @property
    def parent(self):
        if self.meta_node.node_type == 'root':
            return None
        
        parent_nuid = self.taxon_nuid[:-3]
        return NatureGuidesTaxonTree.objects.get(nature_guide=self.nature_guide, taxon_nuid=parent_nuid)
    '''

    @property
    def has_children(self):
        return NatureGuidesTaxonTree.objects.filter(nature_guide=self.nature_guide,
                                                    taxon_nuid__startswith=self.taxon_nuid).exclude(
            pk=self.pk)


    @property
    def lazy_taxon(self):
        return LazyTaxon(instance=self)

    # nodes are active unless they have been actively set to inactive
    @property
    def is_active(self):

        if self.additional_data:
            return self.additional_data.get('is_active', True)
        
        return True

    def get_taxon_profiles(self, meta_app):
        taxon_profiles_content_type = ContentType.objects.get_for_model(TaxonProfiles)
        taxon_profiles_link = MetaAppGenericContent.objects.get(meta_app=meta_app,
                                                content_type=taxon_profiles_content_type)
        
        return taxon_profiles_link.generic_content
        
    # in the future, a nature guide might appear in more than one app
    def get_taxon_profile(self, meta_app):

        taxon_profiles = self.get_taxon_profiles(meta_app)
        
        taxon_profile = TaxonProfile.objects.filter(taxon_profiles=taxon_profiles,
                taxon_source='app_kit.features.nature_guides', taxon_latname=self.taxon_latname).first()

        return taxon_profile
    

    def get_taxon_tree_fields(self, parent=None):

        if self.pk:
            raise ValueError('cannot assign nuid to already saved tree entry')
        
        nuidmanager = NuidManager()

        is_root_taxon = False

        # if parent is None, it is a root node
        if parent is None:
            is_root_taxon = True
            
            nature_guide_nuid = nuidmanager.decimal_to_nuid(self.nature_guide.id)
            root_node_nuid = nuidmanager.decimal_to_nuid(1)
            nuid = '{0}{1}'.format(nature_guide_nuid, root_node_nuid)

        else:
            # get the new child nuid
            parent_nuid = parent.taxon_nuid
            children_nuid_length = len(parent_nuid) + 3
            last_child = NatureGuidesTaxonTree.objects.filter(nature_guide=parent.nature_guide,
                    taxon_nuid__startswith=parent_nuid, taxon_nuid__length=children_nuid_length).order_by(
                        'taxon_nuid').last()

            if last_child:
                nuid = nuidmanager.next_nuid(last_child.taxon_nuid)
            else:
                nuid = '{0}{1}'.format(parent_nuid, nuidmanager.decimal_to_nuid(1))

        # create other TaxonTree fields
        if self.meta_node.name:
            taxon_latname = self.meta_node.name
        else:
            taxon_latname = self.decision_rule
            
        slug = create_unique_slug(taxon_latname, 'slug', NatureGuidesTaxonTree)            

        taxon_tree_fields = {
            'taxon_nuid' : nuid,
            'taxon_latname' : taxon_latname,
            'is_root_taxon' : is_root_taxon,
            'rank' : None, # no ranks for NG TaxonTree entries
            'slug' : slug,
            'author' : None, # no author for NG TaxonTree entries
            'source_id' : nuid, # obsolete in this case, only necessary for taxonomies like col
        }

        return taxon_tree_fields

    # parent is only used on create, not on update
    # during copyin of a node, taxon_tree_fields are partially supplied
    def save(self, parent, taxon_tree_fields={}, *args, **kwargs):

        self.parent = parent

        if parent and parent.meta_node.node_type == 'result':
            raise ValueError('Result nodes cannt have children')

        if not self.meta_node.name and not self.decision_rule:
            raise ValueError('A tree node either needs a name or a decision rule')

        if taxon_tree_fields:
            required_keys = set(['taxon_nuid', 'taxon_latname', 'is_root_taxon', 'rank', 'slug', 'author',
                             'source_id'])

            for key in required_keys:
                if key not in taxon_tree_fields:
                    raise ValueError('You supplied invalid taxon_tree_fields. The key {0} is required.'.format(
                        key))

        if self.pk:
            self.taxon_latname = self.meta_node.name
        else:
            # create nuid etc on first save
            if not taxon_tree_fields:
                taxon_tree_fields = self.get_taxon_tree_fields(parent)

            for key, value in taxon_tree_fields.items():
                setattr(self, key, value)

        # security: check self.parent.taxon_nuid is start of self.taxon_nuid
        if self.parent and not self.taxon_nuid.startswith(self.parent.taxon_nuid):
            raise ValueError('taxon_nuid does not start with parent.taxon_nuid')
        
        super().save(*args, **kwargs)

        linked_profile = TaxonProfile.objects.filter(
            taxon_source='app_kit.features.nature_guides', name_uuid=self.name_uuid).first()
        if linked_profile and linked_profile.taxon_latname != self.taxon_latname:
            linked_profile.taxon_latname = self.taxon_latname
            linked_profile.save()



    # user should call delete_branch, not delete() directly
    def delete(self, from_delete_branch=False, *args, **kwargs):

        if from_delete_branch != True:
            raise PermissionError('Use NatureGuidesTaxonTree.delete_branch to avoid tree inconsistencies.')

        if self.has_children:
            raise PermissionError('Cannot remove node from the tree if it has children')

        self.delete_images()

        # remove from cache
        cache = ChildrenCacheManager(self.parent.meta_node)
        cache.remove_child(self)

        self.meta_node.delete()

        super().delete(*args, **kwargs)
            
        
    # deleting a higher node has to delete all nodes below itself
    # delete() also triggers the deletion of crosslinks
    def delete_branch(self):

        descendants = list(self.tree_descendants.order_by('taxon_nuid'))
        descendants.reverse()

        for descendant in descendants:

            '''
            if the deleted node is a result, and is references as a crosslink child,
            preserve it by moving it to the first crosslink.parent
            '''

            delete_node = True
            
            if descendant.meta_node.node_type == 'result':

                crosslink = NatureGuideCrosslinks.objects.filter(child=descendant).first()

                if crosslink:
                    descendant.move_to(crosslink.parent)
                    crosslink.delete()
                    delete_node = False

            if delete_node == True:
                descendant.delete(from_delete_branch=True)

        self.delete(from_delete_branch=True)


    '''
    MOVING a taxon to a new parent
    - set new parent_id
    - new nuids for self and all descendants of self
    - rebuild cache of old parent and of new parent
    - before save: check if circular connection would occur
    '''
    def get_nuid_depending_on_new_parent(self, new_parent):

        # ordering is extremely important
        
        new_parent_children = NatureGuidesTaxonTree.objects.filter(parent=new_parent).order_by('taxon_nuid')

        last_child = new_parent_children.last()

        nuidmanager = NuidManager()

        if last_child:
            next_nuid = nuidmanager.next_nuid(last_child.taxon_nuid)

        else:
            next_nuid = '{0}{1}'.format(new_parent.taxon_nuid, nuidmanager.decimal_to_nuid(1))

        return next_nuid
        
        
    def move_to_check_crosslinks(self, new_parent):

        old_self_nuid = self.taxon_nuid
        old_self_nuid_len = len(old_self_nuid)

        old_parent = self.parent
        old_parent_nuid_len = len(old_parent.taxon_nuid)

        # new nuid depends on the children of the new parent
        new_self_nuid = self.get_nuid_depending_on_new_parent(new_parent)

        # get all crosslinks of the nature guide
        all_crosslinks = NatureGuideCrosslinks.objects.filter(parent__nature_guide=self.nature_guide)
        crosslink_tuples = []
        
        for crosslink in all_crosslinks:

            crosslink_parent_nuid = crosslink.parent.taxon_nuid
            crosslink_child_nuid = crosslink.child.taxon_nuid

            # if the crosslink is an descendant of self, adjust the nuid
            if crosslink_parent_nuid.startswith(old_self_nuid):
                crosslink_parent_nuid_tail = crosslink_parent_nuid[old_self_nuid_len:]
                crosslink_parent_nuid = '{0}{1}'.format(new_self_nuid, crosslink_parent_nuid_tail)

            elif crosslink_child_nuid.startswith(old_self_nuid):
                crosslink_child_nuid_tail = crosslink_child_nuid[old_self_nuid_len:]
                crosslink_child_nuid = '{0}{1}'.format(new_self_nuid, crosslink_child_nuid_tail)

            crosslink_tuple = tuple([crosslink_parent_nuid, crosslink_child_nuid])
            crosslink_tuples.append(crosslink_tuple)


        crosslink_manager = CrosslinkManager()

        is_circular = crosslink_manager.check_circularity(crosslink_tuples)

        return is_circular


    def move_to_is_valid(self, new_parent):

        if new_parent == self.parent:
            return False

        # before saving anything, perform a circularity check for the new stuff        
        is_circular = self.move_to_check_crosslinks(new_parent)

        if is_circular:
            return False

        # do not allow moving if new_parent is a descendant of self
        if new_parent.taxon_nuid.startswith(self.taxon_nuid):
            return False

        return True
            
    
    '''
        also supports moving to another nature_guide
    '''
    def move_to(self, new_parent):

        old_parent = self.parent

        old_nature_guide = self.nature_guide
        new_nature_guide = new_parent.nature_guide

        old_self_nuid = self.taxon_nuid
        old_self_nuid_len = len(self.taxon_nuid)

        is_valid = self.move_to_is_valid(new_parent)

        if not is_valid:
            raise ValueError('Moving {0} to {1} would result in an invalid tree'.format(
                self, new_parent))


        new_self_nuid = self.get_nuid_depending_on_new_parent(new_parent)

        self.taxon_nuid = new_self_nuid

        self.source_id = new_self_nuid
        self.nature_guide = new_nature_guide
        
        self.save(new_parent)

        self.meta_node.nature_guide = new_nature_guide
        self.meta_node.save()

        # update all nuids, parent stays the same
        descendants_and_self = NatureGuidesTaxonTree.objects.filter(nature_guide=old_nature_guide,
            taxon_nuid__startswith=old_self_nuid).order_by('taxon_nuid')
        
        for descendant in descendants_and_self:
            
            new_descendant_nuid_tail = descendant.taxon_nuid[old_self_nuid_len:]
            new_descendant_nuid = '{0}{1}'.format(new_self_nuid, new_descendant_nuid_tail)
            descendant.taxon_nuid = new_descendant_nuid

            descendant.source_id = new_descendant_nuid
            descendant.nature_guide = new_nature_guide

            descendant.save(descendant.parent)

            descendant.meta_node.nature_guide = new_nature_guide
            descendant.meta_node.save()

            # update nuid in TaxonProfiles
            if descendant.meta_node.node_type == 'result':
                taxon_profile = TaxonProfile.objects.filter(name_uuid=descendant.name_uuid).first()
                if taxon_profile:
                    lazy_taxon = LazyTaxon(instance=descendant)
                    taxon_profile.set_taxon(lazy_taxon)
                    taxon_profile.save()
                    

        # currently, the nuid is not present in child_json. child_json['taxon'] can not be a taxon of
        # NatureGuidesTaxonTree
        # cycle two times. rebuild_cache required all children of a descendant to be updated
        #for descendant in descendants_and_self:
        #    children_cache_manager = ChildrenCacheManager(descendant.meta_node)
        #    children_cache_manager.rebuild_cache()

        # rebuild cache of new parent
        new_parent_cache_manager = ChildrenCacheManager(new_parent.meta_node)
        new_parent_cache_manager.rebuild_cache()

        # rebuild cache of old parent
        old_parent_cache_manager = ChildrenCacheManager(old_parent.meta_node)
        old_parent_cache_manager.rebuild_cache()
        

    def __str__(self):
        if self.name:
            return '{0}'.format(self.name)
        
        return '{0}'.format(self.decision_rule)
    

    class Meta:
        unique_together = (('nature_guide', 'taxon_nuid',))
        ordering = ('position',)


'''
    CrosslinkManager
    - nuid based
    - a crosslink is a (parent_nuid, child_nuid) tuple
'''
class CrosslinkManager:

    # check a single crosslink
    def check_crosslink(self, crosslink):

        is_circular = False

        if crosslink[0].startswith(crosslink[1]):
            is_circular = True

        return is_circular

    '''
    circular connections can be detected ONLY using the crosslink nuid
    - build a crosslink chain:
    - check for each crosslink child: does a crosslink exists BELOW that child in the tree.
      this means you can travel from that crosslink to the crosslink below
    - check if the nuid of the first element in the chain starts with the nuid of the last element
    '''
    def check_circularity(self, crosslinks):

        is_circular = False               
        
        for single_crosslink in crosslinks:

            is_circular = self.check_crosslink(single_crosslink)

            if is_circular == True:
                break


        if is_circular == False:

            found_connection = True

            for crosslink in crosslinks:

                # start a new chain
                chain = [crosslink]
            
                while found_connection == True and is_circular == False:
                    
                    for crosslink_2 in crosslinks:

                        chain_end = chain[-1][1]

                        found_connection = False

                        if crosslink_2 not in chain:

                            if crosslink_2[0].startswith(chain_end):
                                chain.append(crosslink_2)

                                found_connection = True

                                if chain[0][0].startswith(chain[-1][1]):
                                    is_circular = True

        return is_circular



class NatureGuideCrosslinks(models.Model):

    parent = models.ForeignKey(NatureGuidesTaxonTree, related_name='parent_node', on_delete=models.CASCADE)
    child = models.ForeignKey(NatureGuidesTaxonTree, related_name='child_node', on_delete=models.CASCADE)

    decision_rule = models.CharField(
        max_length=TEXT_LENGTH_RESTRICTIONS['NatureGuidesTaxonTree']['decision_rule'], null=True)

    position = models.IntegerField(default=0)

    def save(self, *args, **kwargs):

        # only used by moving a crosslink, the old connection has to be ignored
        exclude_from_check = kwargs.pop('exclude_from_check', None)

        all_crosslinks = [tuple([self.parent.taxon_nuid, self.child.taxon_nuid])]

        nature_guide = self.parent.nature_guide
        for crosslink in NatureGuideCrosslinks.objects.filter(parent__nature_guide=nature_guide):

            crosslink_tuple = tuple([crosslink.parent.taxon_nuid, crosslink.child.taxon_nuid])

            if exclude_from_check and crosslink_tuple == exclude_from_check:
                continue
            
            all_crosslinks.append(crosslink_tuple)

        crosslink_manager =  CrosslinkManager()
        is_circular = crosslink_manager.check_circularity(all_crosslinks)

        if is_circular:
            raise ValueError('Cannot save crosslink because it ould result in a circular connection')

        super().save(*args, **kwargs)

        cache = ChildrenCacheManager(self.parent.meta_node)
        cache.add_or_update_child(self.child, crosslink=self)


    def delete(self, *args, **kwargs):

        cache = ChildrenCacheManager(self.parent.meta_node)
        cache.remove_child(self.child)

        super().delete(*args, **kwargs)


    '''
    MOVING a crosslink child to a new parent
    - set new parent_id
    - rebuild cache of old parent and new parent
    '''
    def move_to(self, new_parent):

        old_parent = self.parent

        # update parent of crosslink
        self.parent = new_parent

        exclude_from_check = tuple([old_parent.taxon_nuid, self.child.taxon_nuid])
        self.save(exclude_from_check=exclude_from_check) # triggers error if crosslink

        # rebuild cache of new parent
        new_parent_cache_manager = ChildrenCacheManager(new_parent.meta_node)
        new_parent_cache_manager.add_or_update_child(self.child)

        # rebuild cache of old parent
        old_parent_cache_manager = ChildrenCacheManager(old_parent.meta_node)
        old_parent_cache_manager.remove_child(self.child)
        

    class Meta:
        unique_together = ('parent', 'child')
        ordering=('position', )


'''
    TaxonTree Models
'''
class NatureGuidesTaxonSynonym(TaxonSynonym):
    taxon = models.ForeignKey(NatureGuidesTaxonTree, on_delete=models.CASCADE, to_field='name_uuid')

    class Meta:
        unique_together = ('taxon', 'taxon_latname', 'taxon_author')


class NatureGuidesTaxonLocale(TaxonLocale):
    taxon = models.ForeignKey(NatureGuidesTaxonTree, on_delete=models.CASCADE, to_field='name_uuid')

    class Meta:
        indexes = [
            models.Index(fields=['taxon', 'language']),
        ]


NatureGuidesTaxonNamesView = NatureGuidesTaxonTree

    
'''
    MATRICES AND TRAITS -> = FILTERS (Model: MatrixFilter)

    - in biology, traits are a feature of an organism

    - a trait/filter consists of an MatrixFilter (e.g. length of fur) and the property values/range (eg 10-20cm)

    - values/range of values are interpreted as SPACE
    
    - "everything is a range paradigm"
    - when numbers are used in trait-/filtervalues 1.00 is different than 1 (-> slider intermediate values)
    - MatrixFilter models are above the Node model

    - every trait/filter has a "space" depending on the node it is attached to
'''

'''
    Matrix Identification Keys (simplified version) -> MatrixFilters
    - Filters are tied to a node
    - multiple types available
    - e.g. 'color of skin' as a ColorFilter
'''

from .matrix_filters import MATRIX_FILTER_TYPES

def get_matrix_filter_class(filter_type):
    m = __import__('app_kit.features.nature_guides.matrix_filters', globals(), locals(), [filter_type])
    return getattr(m, filter_type)

class MatrixFilter(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    meta_node = models.ForeignKey(MetaNode, on_delete=models.CASCADE) # a "parent" node
    name = models.CharField(max_length=150)
    description = models.TextField(null=True)

    filter_type = models.CharField(max_length=50, choices=MATRIX_FILTER_TYPES)
    
    # definition is never referenced and can be a JSONB field
    # things like unit etc
    # also eg 'allow_multiple_values' - allow the user to select multiple values
    definition = models.JSONField(null=True)

    # moved to definition
    # multiple spaces in the user input, makes no sense for range of numbers
    # allow_multiple_values = models.BooleanField(default=False)

    position = models.IntegerField(default=0)
    weight = models.IntegerField(default=1) # 0-10: how discriminative the trait is for this node

    additional_data = models.JSONField(null=True)

    ### NON_MODEL_FIELD ATTRIBUTES
    # the class from .matrix_filters - the type of the filter as a class
    matrix_filter_type = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # the spacemodel can be accessed by MatrixFilterTypeClass
        self.space_model = MatrixFilterSpace
        self._load_filter_type()

    def get_space(self):
        # bug in django 5: matrix_filter=self throws error in testing
        return MatrixFilterSpace.objects.filter(matrix_filter_id=self.pk)


    def _load_filter_type(self):
        
        if not self.filter_type:
            raise ValueError('You cannot instantiate a MatrixFilter without setting the filter_type attribute')
        
        MatrixFilterTypeClass = get_matrix_filter_class(self.filter_type)

        # this adds
        # a) the definition parameters
        # b) the methods get_form_field
        # to the MatrixFilter instance
        self.matrix_filter_type = MatrixFilterTypeClass(self)
        # MatrixFilter.encoded_space as a list [] is now available
        # this differs from MatrixFilterSpace.encoded_space


    ### STANDARD METHODS - TRIGGER CACHING
    def save(self):

        created = True
        if self.pk:
            created = False
        
        super().save()
        self._load_filter_type()

        if created == True:
            cache = ChildrenCacheManager(self.meta_node)
            cache.add_matrix_filter(self)

    def delete(self):
        cache = ChildrenCacheManager(self.meta_node)
        cache.remove_matrix_filter(self)
        super().delete()

    @property
    def is_restricted(self):
        if self.pk:
            return MatrixFilterRestriction.objects.filter(restricted_matrix_filter=self).exists()
        return False

    @property
    def is_active(self):

        if self.additional_data:
            return self.additional_data.get('is_active', True)
        
        return True
    
    def __str__(self):
        return '{0}'.format(self.name)
    

    class Meta:
        unique_together = ('meta_node', 'name')
        ordering=('position', )


'''
    MatrixFilterSpace
    - needed for e.g. TextAndImages type, which is an 1:n relation
    - other filter types like range contain all values in the encoded_space column, 1:1 relation
    - Values of Filter entries
    - mandatory for all MatrixFilters
    - possible spaces of a matrix trait, all spaces together create the Hyperspace
    
    - the space of the filter is saved in an encoded form (compressed)
    - the space can influence how widgets are rendered
'''
class MatrixFilterSpace(ContentImageMixin, models.Model):

    matrix_filter = models.ForeignKey(MatrixFilter, on_delete=models.CASCADE)

    # space can contain multiple values. values can be multidimensional themselves
    # space can have an image
    # space can be just a word (encoded==decoded) or
    # an encoded range, encoded set of numbers, encoded set of colors, ...
    encoded_space = models.JSONField()

    # make it future safe, eg. provide color names ?
    additional_information = models.JSONField(null=True)

    position = models.IntegerField(default=0)

    
    '''
        if save receives old_encoded_space in kwargs, the childrenjson cache has to be updated
    '''
    def save(self, *args, **kwargs):

        old_encoded_space = kwargs.pop('old_encoded_space', None)

        is_valid = self.matrix_filter.matrix_filter_type.validate_encoded_space(self.encoded_space)

        if not is_valid:
            raise ValueError('Invalid space for {0}: {1}'.format(self.matrix_filter.filter_type,
                                                                 json.dumps(self.encoded_space)))

        super().save(*args, **kwargs)

        # update cache if old_encoded_space is passed (ColorFilter, DescriptiveTextAndImagesFilter)
        if old_encoded_space:
            cache = ChildrenCacheManager(self.matrix_filter.meta_node)
            cache.update_matrix_filter_space(str(self.matrix_filter.uuid), old_encoded_space,
                                             self.encoded_space)


        self.matrix_filter._load_filter_type()


    def delete(self, *args, **kwargs):

        # update cache
        cache = ChildrenCacheManager(self.matrix_filter.meta_node)
        cache.remove_matrix_filter_space(self)

        super().delete(*args, **kwargs)
        
        
    # decode the encoded_space into an html readable string, e.g. color to rgba
    # not all matrix filter types can be decoded into html
    def decode(self):
        return self.matrix_filter.matrix_filter_type.decode(self.encoded_space)


    def get_image_suggestions(self):
        suggestions = []
        content_type = ContentType.objects.get_for_model(self)
        matrix_filter_space_images = ContentImage.objects.filter(content_type=content_type)

        for content_image in matrix_filter_space_images:

            matrix_filter_space = content_image.content

            # there might not be an instance of content_image.content
            if not matrix_filter_space:
                suggestions.append(content_image)
            elif matrix_filter_space.encoded_space == self.encoded_space:
                suggestions.append(content_image)

        return suggestions


    @classmethod
    def search_image_suggestions(cls, searchtext):
        suggestions = []

        content_type = ContentType.objects.get_for_model(cls)

        json_searchtext = '"{0}'.format(searchtext)
        matrix_filter_spaces = MatrixFilterSpace.objects.filter(encoded_space__istartswith=json_searchtext)

        if matrix_filter_spaces:
            matrix_filter_space_ids = matrix_filter_spaces.values_list('id', flat=True)
            suggestions = ContentImage.objects.filter(content_type=content_type,
                                                      object_id__in=matrix_filter_space_ids)

        return suggestions


    def get_content_image_restrictions(self, image_type='image'):
        restrictions = {
            'allow_features' : True,
            'allow_cropping' : True,
        }
        
        return restrictions
    

    def __str__(self):
        if self.pk:
            return '{0}'.format(self.matrix_filter.matrix_filter_type.verbose_space_name)
        return self.__class__.__name__

    class Meta:
        ordering=('position', )
    


'''
    Assign spaces to single nodes (=possible results of a matrix key)
    - this does NOT depend on the parent_node. A node has a trait value or it has not
    - localization not required. encoded_space is for numbers etc, value for FKs to translated spaces

    "Select-from-the-defined"-Paradigm:
    - assigning NodeSpaces are selections of defined hyperspaces (MatrixFilterSpace)
    - the hyperspace (allowed values) are set by an expert
    - this allows mediocre users to assign values, they cant go "out-of-bounds"

    Cache Updating us done using a view
'''
class NodeFilterSpace(models.Model):
    
    node = models.ForeignKey(NatureGuidesTaxonTree, on_delete=models.CASCADE) # a "child" node

    matrix_filter = models.ForeignKey(MatrixFilter, on_delete=models.CASCADE)

    '''
    ASSIGNED VALUES
    '''
    encoded_space = models.JSONField(null=True) # for ranges [2,4] and numbers only

    # for DescriptiveTextAndImages values, (Number values ??), Colors
    # there can be more than 1 encoded space
    values = models.ManyToManyField(MatrixFilterSpace)

    weight = models.IntegerField(null=True, default=None) # 0-10: how discriminative the trait is for this node, overrides MatrixFilter.weight


    def save(self, *args, **kwargs):

        if self.matrix_filter.filter_type in ['RangeFilter', 'NumberFilter']:
             if not self.encoded_space:
                 raise ValueError('{0} Node space requires encoded_space to be set'.format(self.matrix_filter.filter_type))

        else:
            if self.encoded_space:
                raise ValueError('{0} Node space do not support .encoded_space. Use values instead.'.format(self.matrix_filter.filter_type))


        super().save(*args, **kwargs)


    class Meta:
        unique_together = ('node', 'matrix_filter')



'''
    MatrixFilterRestrictions
    - a matrix filter may depend on a value
'''
class MatrixFilterRestriction(models.Model):

    # the matrix filter which is restricted
    restricted_matrix_filter = models.ForeignKey(MatrixFilter, on_delete=models.CASCADE,
                                                 related_name='restricted_matrix_filter')

    # the filter which restricts restricted_matrix_filter
    restrictive_matrix_filter = models.ForeignKey(MatrixFilter, on_delete=models.CASCADE)

    values = models.ManyToManyField(MatrixFilterSpace)
    encoded_space = models.JSONField(null=True) # for ranges [2,4] and numbers only
    


def get_vernacular_name_from_nature_guides(meta_app, lazy_taxon):

    installed_taxonomic_sources = [s[0] for s in settings.TAXONOMY_DATABASES]

    if lazy_taxon.taxon_source in installed_taxonomic_sources:

        nature_guide_links = meta_app.get_generic_content_links(NatureGuide)
        nature_guide_ids = nature_guide_links.values_list('object_id', flat=True)

        meta_node = MetaNode.objects.filter(nature_guide_id__in=nature_guide_ids,
            name_uuid=lazy_taxon.name_uuid).first()

        if meta_node:
            return meta_node.name

    return None