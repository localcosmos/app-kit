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


class NatureGuide(GenericContent):

    zip_import_supported = True

    objects = NatureGuideManager()

    @property
    def zip_import_class(self):
        from .zip_import import NatureGuideZipImporter
        return NatureGuideZipImporter


    @property
    def root_node(self):
        return NatureGuidesTaxonTree.objects.get(nature_guide=self, meta_node__node_type='root')


    def get_primary_localization(self):
        locale = {}

        locale[self.name] = self.name

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

                if matrix_filter.filter_type in ['DescriptiveTextAndImagesFilter']:

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
        verbose_name = _('Nature guide')
        verbose_name_plural = _('Nature guides')


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
    -- explanation: TestAndImages do not change encoded_space, but localization
    -- for Range/Numbers false values are acceptable, numbers are never changed - only added or deleted

    When building the app, the json is rebuilt
'''

class ChildrenCacheManager:

    def __init__(self, meta_node):
        self.meta_node = meta_node

    def get_data(self):

        data = self.meta_node.children_cache

        if not data:
            
            data = {
                'items' : [],
                'matrix_filter_types' : {},
            }
        
        return data


    def child_as_json(self, child):

        matrix_filters = MatrixFilter.objects.filter(meta_node=self.meta_node)

        # there is only one NodeFilterSpace per matrix_filter/node combination
        space_query = NodeFilterSpace.objects.filter(node=child, matrix_filter__in=matrix_filters)
        
        space = {}

        for node_filter_space in space_query:

            # get the matrix_filter for this specific space
            matrix_filter = node_filter_space.matrix_filter

            matrix_filter_uuid = str(matrix_filter.uuid)

            # a list of spaces applicable for this entry/matrix_filter combination
            # is added to the cache
            space[matrix_filter_uuid] = matrix_filter.matrix_filter_type.get_node_filter_space_as_list(
                node_filter_space)


        child_json = {
            'id' : child.id,
            'meta_node_id' : child.meta_node.id,
            'node_type' : child.meta_node.node_type,
            'image_url' : child.meta_node.image_url(), 
            'uuid' : str(child.name_uuid),
            'space' : space,
            'is_visible' : True,
            'name' : child.meta_node.name,
            'decision_rule' : child.decision_rule,
            'taxon' : None,
        }

        if child.meta_node.taxon:
            child_json['taxon'] = child.meta_node.taxon.as_json()

        return child_json

    '''
        CHILD MANAGEMENT
    '''
    def add_or_update_child(self, child_node):

        data = self.get_data()

        items = data['items']

        child_json = self.child_as_json(child_node)

        found_child = False
        for item in items:

            if item['uuid'] == str(child_node.name_uuid):
                found_child = True
                items[items.index(item)] = child_json
                break

        if not found_child:
            items.append(child_json)
            
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
    - MatrixFilterSpaces are not stored in the cache, it is only a uuid -> type map
    '''
    def add_matrix_filter(self, matrix_filter):
        data = self.get_data()

        data['matrix_filter_types'][str(matrix_filter.uuid)] = matrix_filter.filter_type

        self.meta_node.children_cache = data
        self.meta_node.save()

        
    def remove_matrix_filter(self, matrix_filter):
        data = self.get_data()

        matrix_filter_uuid = str(matrix_filter.uuid)

        if matrix_filter_uuid in data['matrix_filter_types']:
            del data['matrix_filter_types'][matrix_filter_uuid]

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
    MetaNodes contain information shared by several nodes across a Tree, like name and image
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
    node_type = models.CharField(max_length=30, choices=NODE_TYPES)

    children_cache = models.JSONField(null=True)

    def delete(self, *args, **kwargs):
        self.delete_images()
        super().delete(*args, **kwargs)

    def __str__(self):
        return '{0}'.format(self.name)

    class Meta:
        unique_together=('nature_guide', 'name')

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
from django.template.defaultfilters import slugify

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
    
    # NatureGuide specific fields
    nature_guide = models.ForeignKey(NatureGuide, on_delete=models.CASCADE)
    
    # meta_node contains shared data across nodes
    meta_node = models.ForeignKey(MetaNode, on_delete=models.CASCADE)

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

    '''
    @property
    def parent(self):
        if self.meta_node.node_type == 'root':
            return None
        
        parent_nuid = self.taxon_nuid[:-3]
        return NatureGuidesTaxonTree.objects.get(taxon_nuid=parent_nuid)
    '''

    @property
    def has_children(self):
        return NatureGuidesTaxonTree.objects.filter(taxon_nuid__startswith=self.taxon_nuid).exclude(
            pk=self.pk)


    @property
    def lazy_taxon(self):
        return LazyTaxon(instance=self)

    # in the future, a nature guide might appear in more than one app
    def get_taxon_profile(self, meta_app):

        taxon_profiles_content_type = ContentType.objects.get_for_model(TaxonProfiles)
        taxon_profiles_link = MetaAppGenericContent.objects.get(meta_app=meta_app,
                                                content_type=taxon_profiles_content_type)
        taxon_profiles = taxon_profiles_link.generic_content
        
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
    def save(self, parent, *args, **kwargs):

        self.parent = parent

        if parent and parent.meta_node.node_type == 'result':
            raise ValueError('Result nodes cannt have children')

        if not self.meta_node.name and not self.decision_rule:
            raise ValueError('A tree node either needs a name or a decision rule')

        if self.pk:
            self.taxon_latname = self.meta_node.name
        else:
            # create nuid etc on first save
            taxon_tree_fields = self.get_taxon_tree_fields(parent)

            for key, value in taxon_tree_fields.items():
                setattr(self, key, value)

            
        super().save(*args, **kwargs)


    # delete the MetaNode if it does not occur in the tree anymore
    # user should call delete_branch, not delete() irectly
    def delete(self, from_delete_branch=False, *args, **kwargs):

        if from_delete_branch != True:
            raise PermissionError('Use NatureGuidesTaxonTree.delete_branch to avoid tree inconsistencies.')

        if self.has_children:
            raise PermissionError('Cannot remove node from the tree if it has children')

        meta_node = self.meta_node

        self.delete_images()

        # remove from cache
        cache = ChildrenCacheManager(self.parent.meta_node)
        cache.remove_child(self)

        super().delete(*args, **kwargs)

        meta_node_occurs = NatureGuidesTaxonTree.objects.filter(meta_node=meta_node).exists()

        if not meta_node_occurs:
            meta_node.delete()
            
        
    # deleting a higher node has to delete all nodes below itself
    # delete() also triggers the deletion of crosslinks
    def delete_branch(self):

        descendants = list(self.tree_descendants)
        descendants.reverse()

        for descendant in descendants:
            descendant.delete(from_delete_branch=True)

        self.delete(from_delete_branch=True)
            

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

        all_crosslinks = [tuple([self.parent.taxon_nuid, self.child.taxon_nuid])]

        nature_guide = self.parent.nature_guide
        for crosslink in NatureGuideCrosslinks.objects.filter(parent__nature_guide=nature_guide):
            all_crosslinks.append(tuple([crosslink.parent.taxon_nuid, crosslink.child.taxon_nuid]))

        crosslink_manager =  CrosslinkManager()
        is_circular = crosslink_manager.check_circularity(all_crosslinks)

        if is_circular:
            raise ValueError('Cannot save crosslink because it ould result in a circular connection')

        super().save(*args, **kwargs)

        cache = ChildrenCacheManager(self.parent.meta_node)
        cache.add_or_update_child(self.child)


    def delete(self, *args, **kwargs):

        cache = ChildrenCacheManager(self.parent.meta_node)
        cache.remove_child(self.child)

        super().delete(*args, **kwargs)
        

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
        index_together = [
            ['taxon', 'language'],
        ]
    
class NatureGuidesTaxonNamesView(TaxonNamesView):
    pass

    
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
    weight = models.IntegerField(default=50) # 0-100: how discriminative the trait is for this node

    ### NON_MODEL_FIELD ATTRIBUTES
    # the class from .matrix_filters - the type of the filter as a class
    matrix_filter_type = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # the spacemodel can be accessed by MatrixFilterTypeClass
        self.space_model = MatrixFilterSpace
        self._load_filter_type()

    def get_space(self):
        return MatrixFilterSpace.objects.filter(matrix_filter=self)


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

            if matrix_filter_space.encoded_space == self.encoded_space:
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

    weight = models.IntegerField(default=50) # 0-100: how discriminative the trait is for this node


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
