from django.shortcuts import render, redirect, reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, FormView
from django.contrib.contenttypes.models import ContentType
from django.db.models.query import QuerySet # needed for saving node matrix filter values
from django.http import JsonResponse # NodeSearch

from .models import (NatureGuide, MetaNode, MatrixFilter, MatrixFilterSpace, NodeFilterSpace,
                     NatureGuidesTaxonTree, CrosslinkManager, NatureGuideCrosslinks, ChildrenCacheManager,
                     MatrixFilterRestriction)

from .forms import (NatureGuideOptionsForm, IdentificationMatrixForm, SearchForNodeForm, ManageNodelinkForm,
                    MoveNodeForm, ManageMatrixFilterRestrictionsForm, CopyTreeBranchForm)

# do not delete these imports, they are generically read
from .matrix_filter_forms import (MatrixFilterManagementForm, DescriptiveTextAndImagesFilterManagementForm,
                            RangeFilterManagementForm, ColorFilterManagementForm, NumberFilterManagementForm,
                            TaxonFilterManagementForm, TextOnlyFilterManagementForm)

from .matrix_filter_space_forms import (DescriptiveTextAndImagesFilterSpaceForm, ColorFilterSpaceForm,
                                        TextOnlyFilterSpaceForm)


from app_kit.views import ManageGenericContent, ManageContentImage, DeleteContentImage
from app_kit.view_mixins import MetaAppMixin, FormLanguageMixin, MetaAppFormLanguageMixin

from app_kit.features.taxon_profiles.models import TaxonProfile


from app_kit.utils import copy_model_instance

from localcosmos_server.decorators import ajax_required
from django.utils.decorators import method_decorator

from .matrix_filters import MATRIX_FILTER_TYPES

from localcosmos_server.generic_views import AjaxDeleteView

import json


class ManageNatureGuide(ManageGenericContent):
    
    template_name = 'nature_guides/manage_nature_guide.html'

    options_form_class = NatureGuideOptionsForm

    def dispatch(self, request, *args, **kwargs):
        self.parent_node = self.get_parent_node(**kwargs)
        return super().dispatch(request, *args, **kwargs)
        

    def get_parent_node(self, **kwargs):

        parent_node_id = kwargs.get('parent_node_id', None)
        
        if parent_node_id:
            parent_node = NatureGuidesTaxonTree.objects.get(pk=parent_node_id)
        else:
            nature_guide = NatureGuide.objects.get(pk=kwargs['object_id'])
            parent_node = NatureGuidesTaxonTree.objects.get(nature_guide=nature_guide,
                                                            meta_node__node_type='root')

        # EXPERIMENTAL: if service gets too slow, do not rebuild cache
        parent_node.meta_node.rebuild_cache()

        return parent_node


    def get_tree_path(self):

        path = []
        
        parent_node = self.parent_node
        
        while parent_node.meta_node.node_type != 'root':

            if parent_node != self.parent_node:
                path.insert(0, parent_node)

            parent_node = parent_node.parent

        path.insert(0, parent_node)

        return path
        

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['parent_node'] = self.parent_node
        context['meta_node'] = self.parent_node.meta_node
        context['natureguides_taxontree_content_type'] = ContentType.objects.get_for_model(
            NatureGuidesTaxonTree)
        context['nature_guide'] = self.generic_content
        context['children_count'] = self.parent_node.children_count
        
        context['form'] = IdentificationMatrixForm(self.meta_app, self.parent_node.meta_node)
        context['search_for_node_form'] = SearchForNodeForm(language=self.primary_language)

        # add the parents to the context for tree browsing
        
        context['parent_crosslinks'] = NatureGuideCrosslinks.objects.filter(child=self.parent_node)

        # add filters button
        context['matrix_filter_types'] = MATRIX_FILTER_TYPES

        context['tree_path'] = self.get_tree_path()

        return context


class MultipleTraitValuesIterator:

    def get_existing_space_link(self, matrix_filter):
        raise NotImplementedError('MultipleTraitValuesIterator requires a get_space method')

    def get_all_existing_space_links(self, matrix_filter):
        raise NotImplementedError('MultipleTraitValuesIterator requires a get_all_existing_space_links method')

    def instantiate_new_space_link(self, matrix_filter):
        raise NotImplementedError('MultipleTraitValuesIterator requires a instantiate_space method')
    
    def iterate_matrix_form_fields(self, form):

        # save matrix filters if any
        # now save all inserted trait values
        for field in form:
            
            is_matrix_filter = getattr(field.field, 'is_matrix_filter', False)

            if is_matrix_filter == True:
                
                matrix_filter_uuid = field.name
                matrix_filter = MatrixFilter.objects.get(uuid=matrix_filter_uuid)
                
                # add posted, remove unposted
                if matrix_filter_uuid in form.cleaned_data and form.cleaned_data[matrix_filter_uuid]:
                    
                    space_value = form.cleaned_data[matrix_filter_uuid]
                    is_new_space_link = False

                    space_link = self.get_existing_space_link(matrix_filter)

                    if not space_link:
                        is_new_space_link = True

                        space_link = self.instantiate_new_space_link(matrix_filter)
                        

                    # Color, TextAndImages
                    if isinstance(space_value, QuerySet):
                        
                        if is_new_space_link == True:
                            space_link.save()

                        # remove existing
                        available_spaces = MatrixFilterSpace.objects.filter(matrix_filter=matrix_filter)
                        
                        for matrix_filter_space in available_spaces:
                            if matrix_filter_space in space_value:
                                space_link.values.add(matrix_filter_space)
                                
                            else:
                                space_link.values.remove(matrix_filter_space)

                    # Range, Numbers
                    else:
                        # the value needs to be encoded correctly by the TraitProperty Subclass
                        encoded_space = matrix_filter.matrix_filter_type.encode_entity_form_value(space_value)
                        
                        space_link.encoded_space = encoded_space
                        space_link.save()

                # remove filter which uuids are not present in the posted data
                else:
                    existing_space_links = self.get_all_existing_space_links(matrix_filter)

                    if existing_space_links.exists():

                        for space_link in existing_space_links:
                            space_link.delete()
        

'''
    Manage a Node(link)
    - also define which filters apply for an entry
    - if a taxon is added to a NatureGuideTaxonTree, the TaxonProfile referring taxon has to be updated
    - the submitted parent can be a crosslink parent or a tree parent
    - the NatureGuidestaxonTree.save() method always requires the tree parent
    - matrix filters always require the submitted parent
'''
class ManageNodelink(MultipleTraitValuesIterator, MetaAppFormLanguageMixin, MetaAppMixin, FormView):

    template_name = 'nature_guides/ajax/manage_nodelink_form.html'

    form_class = ManageNodelinkForm

    # create the node and close the modal
    # or display errors in modal
    # return two different htmls for success and error
    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_node(**kwargs)
        return super().dispatch(request, *args, **kwargs)


    def set_node(self, **kwargs):

        self.is_crosslink = False

        # it might be a crosslink
        if 'node_id' in kwargs:
            self.node = NatureGuidesTaxonTree.objects.get(pk=kwargs['node_id'])
            self.node_type = self.node.meta_node.node_type

            # the parent node from the url, might be the crosslink parent
            self.submitted_parent_node = NatureGuidesTaxonTree.objects.get(pk=kwargs['parent_node_id'])

            # the parent of the node in the tree, no crosslink
            self.tree_parent_node = self.node.parent            
            
        else:
            self.node = None
            self.node_type = kwargs['node_type']

            # the parent node from the url, might be the crosslink parent
            self.submitted_parent_node = NatureGuidesTaxonTree.objects.get(pk=kwargs['parent_node_id'])

            # the parent of the node in the tree, no crosslink
            self.tree_parent_node = self.submitted_parent_node


        if self.node:

            if self.submitted_parent_node != self.tree_parent_node:
                exists = NatureGuideCrosslinks.objects.filter(parent=self.submitted_parent_node,
                                                              child=self.node).exists()

                if exists:
                    self.is_crosslink = True


        self.nature_guide = self.submitted_parent_node.nature_guide
        

    def get_initial(self):
        initial = super().get_initial()
        
        if self.node:
            initial['node_type'] = self.node.meta_node.node_type
            initial['name'] = self.node.meta_node.name
            initial['morphotype'] = self.node.meta_node.morphotype
            initial['decision_rule'] = self.node.decision_rule
            initial['node_id'] = self.node.id
            initial['taxon'] = self.node.meta_node.taxon
            initial['is_active'] = self.node.is_active
            initial['description'] = self.node.meta_node.description

        else:
            initial['node_type'] = self.node_type
            initial['is_active'] = True
        
        return initial
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.node != None:
            self.node.is_crosslink = self.is_crosslink

        context['node_type'] = self.node_type
        context['parent_node'] = self.submitted_parent_node
        context['node'] = self.node
        context['content_type'] = ContentType.objects.get_for_model(self.nature_guide)

        return context

    
    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        if self.node:
            form_kwargs['node'] = self.node

        form_kwargs['from_url'] = self.request.path
        return form_kwargs
    

    def get_form(self, form_class=None):

        if form_class is None:
            form_class = self.get_form_class()

        # submitted parent node is for matrix filters
        return form_class(self.meta_app, self.tree_parent_node, self.submitted_parent_node, **self.get_form_kwargs())
    
    # if a taxon is added to a meta_node without taxon, there could have been a taxon profile referencing
    # app_kit.features.nature_guides as taxon_source. this taxon profile has to be updated to reference
    # the new taxon of the meta node
    def save_nodelink(self, form):
        node_id = form.cleaned_data.get('node_id', None)

        if not node_id:
            meta_node = MetaNode(
                nature_guide=self.nature_guide,
                node_type = form.cleaned_data['node_type'],
                name = form.cleaned_data['name']
            )

            meta_node.save()
            
            self.node = NatureGuidesTaxonTree(
                nature_guide = self.nature_guide,
                meta_node = meta_node,
                position=self.submitted_parent_node.children_count,
            )
            
        else:
            self.node = NatureGuidesTaxonTree.objects.get(pk=node_id)
            meta_node = self.node.meta_node

        is_active = form.cleaned_data['is_active']

        if not self.node.additional_data:
            self.node.additional_data = {}
            
        self.node.additional_data['is_active'] = is_active

        
        if 'taxon' in form.cleaned_data and form.cleaned_data['taxon']:

            new_taxon = form.cleaned_data['taxon']
            
            # if the meta_node had no taxon, a taxon profile with a fallback taxon might exist
            if not meta_node.taxon and not meta_node.taxon_source and not meta_node.taxon_latname:
                
                taxon_profile = self.node.get_taxon_profile(self.meta_app)

                if taxon_profile:
                    # update taxon_profile taxon
                    # check if profile for this taxon already exists
                    existing_new_taxon_profile = TaxonProfile.objects.filter(taxon_source=new_taxon.taxon_source,
                        taxon_latname=new_taxon.taxon_latname, taxon_author=new_taxon.taxon_author).first()

                    if not existing_new_taxon_profile:
                        taxon_profile.set_taxon(new_taxon)
                        taxon_profile.save()
                
            self.node.meta_node.set_taxon(new_taxon)
        else:
            self.node.meta_node.remove_taxon()

        self.node.meta_node.name = form.cleaned_data['name']
        self.node.meta_node.morphotype = form.cleaned_data['morphotype']
        self.node.meta_node.description = form.cleaned_data['description']  
        self.node.meta_node.save()

        self.node.decision_rule = form.cleaned_data['decision_rule']
        self.node.save(self.tree_parent_node)

        self.node.is_crosslink = self.is_crosslink


    def form_valid(self, form):

        # save nodelink, make self.nodelink available
        self.save_nodelink(form)

        self.iterate_matrix_form_fields(form)
        
        # update cache, cannot be done in .models because the node is saved BEFORE the spaces are added
        cache = ChildrenCacheManager(self.submitted_parent_node.meta_node)
        cache.add_or_update_child(self.node)
        
        context = self.get_context_data(**self.kwargs)
        context['form'] = form
        context['success'] = True
        
        return self.render_to_response(context)


    # methods for iterating over selected traits
    def get_existing_space_link(self, matrix_filter):
        node_filter_space = NodeFilterSpace.objects.filter(node=self.node, matrix_filter=matrix_filter).first()
        return node_filter_space

    def get_all_existing_space_links(self, matrix_filter):
        node_filter_spaces = NodeFilterSpace.objects.filter(node=self.node, matrix_filter=matrix_filter)
        return node_filter_spaces

    def instantiate_new_space_link(self, matrix_filter):
        node_filter_space = NodeFilterSpace(node=self.node, matrix_filter=matrix_filter)
        return node_filter_space


'''
    DeleteNodelink has to respect the deletion of crosslinks
    - if a crosslink is deleted, the node remains in the tree
    - if a true node is deleted, all its crosslinks are deleted
'''
class DeleteNodelink(AjaxDeleteView):

    template_name = 'nature_guides/ajax/delete_nodelink.html'

    def dispatch(self, request, *args, **kwargs):
        self.set_node(**kwargs)
        return super().dispatch(request, *args, **kwargs)


    def set_node(self, **kwargs):
        child_id = self.kwargs['child_node_id']
        parent_id = self.kwargs['parent_node_id']

        # first, check if it is a crosslink
        self.crosslink = NatureGuideCrosslinks.objects.filter(parent_id=parent_id, child_id=child_id).first()
        
        if self.crosslink:
            self.model = NatureGuideCrosslinks
            self.child = self.crosslink.child
            self.node = None
        else:
            self.model = NatureGuidesTaxonTree
            self.node = NatureGuidesTaxonTree.objects.get(pk=child_id)
            self.child = self.node


    def get_verbose_name(self):
        return self.child.name
        

    def get_object(self):
        if self.crosslink:
            return self.crosslink

        return self.node


    def get_deletion_message(self):

        if self.crosslink:
            message = _('Do you really want to remove the crosslink to {0}?'.format(self.child.name))
        else:
            message = _('Do you really want to remove {0}?'.format(self.child.name))

        return message

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['crosslink'] = self.crosslink
        context['node'] = self.node
        context['deleted_object_child_uuid'] = str(self.child.name_uuid)
        context['deletion_message'] = self.get_deletion_message()
        return context


    def form_valid(self, form):
        if self.crosslink:
            return super().form_valid(form)

        context = self.get_context_data(**self.kwargs)
        context['deleted_object_id'] = self.object.pk
        context['deleted'] = True
        self.object.delete_branch()
        return self.render_to_response(context)


# get nodes that can be added to the current parent
class AddExistingNodes(MetaAppMixin, TemplateView):

    template_name = 'nature_guides/ajax/add_existing_nodes.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_node(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_node(self, **kwargs):
        self.parent_node = NatureGuidesTaxonTree.objects.get(pk=kwargs['parent_node_id'])
        self.nature_guide = self.parent_node.nature_guide
        self.selected_node_ids = []

    def get_queryset(self):
        # exclude is_root_node and all uplinks
        nodes = NatureGuidesTaxonTree.objects.filter(nature_guide=self.nature_guide).exclude(
            meta_node__node_type='root').exclude(taxon_nuid__startswith=self.parent_node.taxon_nuid).order_by(
                'meta_node__name')
        
        return nodes

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_node'] = self.parent_node
        context['content_type'] = ContentType.objects.get_for_model(self.parent_node.nature_guide)
        
        nodes = self.get_queryset()
        context['nodes'] = nodes

        parsed_selected_node_ids = [int(i) for i in self.selected_node_ids]
        context['selected_node_ids'] = parsed_selected_node_ids
        context['selected_nodes'] = NatureGuidesTaxonTree.objects.filter(pk__in=parsed_selected_node_ids)
        
        return context


    def get(self, request, *args, **kwargs):

        if 'selected' in request.GET:
            self.selected_node_ids = request.GET.getlist('selected')
        
        context = self.get_context_data(**kwargs)

        if request.headers.get('x-requested-with') == 'XMLHttpRequest' and 'page' in request.GET:
            self.template_name = 'nature_guides/ajax/add_existing_nodes_page.html'

        return self.render_to_response(context)
    

    @method_decorator(ajax_required)
    def post(self, request, *args, **kwargs):

        success = False

        context = self.get_context_data(**kwargs)

        added_children = []

        crosslinks = self.parent_node.nature_guide.crosslink_list()
        
        crosslinkmanager = CrosslinkManager()

        nodelist = request.POST.getlist('node', [])
        nodelist_db = []

        for node_id in nodelist:

            # check circularity for each node
            node = NatureGuidesTaxonTree.objects.get(pk=node_id)
            nodelist_db.append(node)

            crosslink = (self.parent_node.taxon_nuid, node.taxon_nuid)
            crosslinks.append(crosslink)


        is_circular = crosslinkmanager.check_circularity(crosslinks)

        if not is_circular:

            for node in nodelist_db:

                # if it is a dangling node: add it directly to the parent
                

                crosslink = NatureGuideCrosslinks(
                    parent=self.parent_node,
                    child=node,
                )

                crosslink.save()

                added_children.append(node)

            success = True


        context['is_circular'] = is_circular
        context['added_children'] = added_children
        context['success'] = success
        
        return self.render_to_response(context)    


class LoadKeyNodes(MetaAppMixin, TemplateView):
    
    template_name = 'nature_guides/ajax/nodelist.html'


    def dispatch(self, request, *args, **kwargs):
        self.set_parent_node(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_parent_node(self, **kwargs):

        parent_node_id = kwargs.get('parent_node_id', None)

        if parent_node_id:
            self.parent_node = NatureGuidesTaxonTree.objects.get(pk=parent_node_id)
        else:
            self.parent_node = NatureGuidesTaxonTree.objects.get(nature_guide=self.generic_content,
                                                                 meta_node__node_type='root')
        

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_node'] = self.parent_node
        context['content_type'] = ContentType.objects.get_for_model(self.parent_node.nature_guide)
        return context


from localcosmos_server.generic_views import StoreObjectOrder
class StoreNodeOrder(StoreObjectOrder):

    def get_save_args(self, node):
        return [node.parent]

    @method_decorator(ajax_required)
    def post(self, request, *args, **kwargs):

        success = False

        order = request.POST.get('order', None)

        if order:

            parent_node = NatureGuidesTaxonTree.objects.get(pk=kwargs['parent_node_id'])
            
            self.order = json.loads(order)

            for child_id in self.order:
                # check if a crosslink exists
                position = self.order.index(child_id) + 1
                child = NatureGuidesTaxonTree.objects.get(pk=child_id)

                crosslink = NatureGuideCrosslinks.objects.filter(parent=parent_node, child=child).first()

                if crosslink:
                    crosslink.position = position
                    crosslink.save()
                else:
                    child.position = position
                    child.save(parent_node)

            self._on_success()

            success = True
        
        return JsonResponse({'success':success})


class LoadNodeManagementMenu(MetaAppMixin, TemplateView):

    template_name = 'nature_guides/ajax/node_management_menu.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_node(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_node(self, **kwargs):
        self.content_type = ContentType.objects.get_for_model(NatureGuide)
        self.node = NatureGuidesTaxonTree.objects.get(pk=self.kwargs['node_id'])
        self.parent_node = NatureGuidesTaxonTree.objects.get(pk=self.kwargs['parent_node_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['node'] = self.node
        context['parent_node'] = self.parent_node
        context['content_type'] = self.content_type
        return context


'''
    Search a node of a key for quick access
'''
class SearchForNode(MetaAppFormLanguageMixin, TemplateView):


    def get_on_click_url(self, node):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'meta_node_id' : node.meta_node.id
        }

        url = reverse('node_analysis', kwargs=url_kwargs)

        return url


    def get_queryset(self, request, **kwargs):

        nodes = []

        searchtext = request.GET.get('name', '')
        
        if len(searchtext) > 2:

            nodes = NatureGuidesTaxonTree.objects.filter(
                nature_guide=self.nature_guide,
                meta_node__name__istartswith=searchtext).exclude(
                meta_node__node_type='root')[:15]

        return nodes


    def get_displayed_name(self, node):
        return node.meta_node.name
        
        
    @method_decorator(ajax_required)
    def get(self, request, *args, **kwargs):

        self.nature_guide = NatureGuide.objects.get(pk=kwargs['nature_guide_id'])

        results = []

        nodes = self.get_queryset(request, **kwargs)
        
        for node in nodes:

            url = self.get_on_click_url(node)

            displayed_name = self.get_displayed_name(node)

            choice = {
                'name' : displayed_name,
                'id' : node.id,
                'url' : url,
            }
            
            results.append(choice)

        return JsonResponse(results, safe=False) 


'''
    Matrix
'''
class LoadMatrixFilters(MetaAppMixin, TemplateView):

    template_name = 'nature_guides/ajax/matrix_filters.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.meta_node = MetaNode.objects.get(pk=kwargs['meta_node_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = IdentificationMatrixForm(self.meta_app, self.meta_node)
        context['meta_node'] = self.meta_node
        context['meta_node_has_matrix_filters'] = MatrixFilter.objects.filter(
            meta_node=self.meta_node).exists()
        context['matrix_filter_ctype'] = ContentType.objects.get_for_model(MatrixFilter)
        context['matrix_filter_types'] = MATRIX_FILTER_TYPES
        return context


'''
    Superclass for creating and managing matrix filters
    - no appmixin due to horizontal_choices
'''
class ManageMatrixFilter(FormLanguageMixin, MetaAppMixin, FormView):

    template_name = 'nature_guides/ajax/manage_matrix_filter.html'
    form_class = MatrixFilterManagementForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_matrix_filter(**kwargs)
        return super().dispatch(request, *args, **kwargs)


    def set_matrix_filter(self, **kwargs):
        
        if 'matrix_filter_id' in kwargs:
            self.matrix_filter = MatrixFilter.objects.get(pk=kwargs['matrix_filter_id'])
            self.meta_node = self.matrix_filter.meta_node
            self.filter_type = self.matrix_filter.filter_type
        else:
            self.matrix_filter = None
            self.meta_node = MetaNode.objects.get(pk=kwargs['meta_node_id'])
            self.filter_type = kwargs['filter_type']


    def set_primary_language(self):
        tree_node = NatureGuidesTaxonTree.objects.filter(meta_node=self.meta_node).first()
        self.primary_language = tree_node.nature_guide.primary_language
        

    def get_form_class(self):
        form_class_name = '{0}ManagementForm'.format(self.filter_type)
        return globals()[form_class_name]


    def get_form(self, form_class=None):

        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.meta_node, self.matrix_filter, **self.get_form_kwargs())


    def get_initial(self):
        initial = super().get_initial()
        initial['filter_type'] = self.filter_type

        initial['is_active'] = True

        if self.matrix_filter is not None:
            initial['matrix_filter_id'] = self.matrix_filter.id
            initial['name'] = self.matrix_filter.name

            initial['is_active'] = self.matrix_filter.is_active

            if self.matrix_filter.definition:
                for key in self.matrix_filter.definition:
                    initial[key] = self.matrix_filter.definition[key]

            # for some cases, the encoded space can be decoded into initial values
            space_initial = self.matrix_filter.matrix_filter_type.get_space_initial()
            initial.update(space_initial)
            
        return initial
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_node'] = self.meta_node
        context['filter_type'] = self.filter_type
        context['matrix_filter'] = self.matrix_filter

        # fallback
        verbose_filter_name = self.filter_type

        # get verbose filter name
        for tup in MATRIX_FILTER_TYPES:
            if tup[0] == self.filter_type:
                verbose_filter_name = tup[1]
                break
        context['verbose_filter_name'] = verbose_filter_name
        return context

    # create a definition dictionary from the form values
    def set_definition(self, form, matrix_filter):

        definition = {}

        for key in matrix_filter.matrix_filter_type.definition_parameters:
            if key in form.cleaned_data:
                definition[key] = form.cleaned_data[key]

        matrix_filter.definition = definition

    # for some filters, the space can be encoded directly from the form
    # only applies for 1:1 space relations (e.g. RangeFilter)
    def save_encoded_space(self, form, matrix_filter):

        if matrix_filter.matrix_filter_type.is_multispace == False:

            space = MatrixFilterSpace.objects.filter(matrix_filter=matrix_filter).first()
            if not space:
                space = MatrixFilterSpace(
                    matrix_filter = matrix_filter,
                )

            encoded_space = matrix_filter.matrix_filter_type.get_encoded_space_from_form(form)

            if encoded_space:
                space.encoded_space = encoded_space
                space.save()
    

    def form_valid(self, form):

        if not self.matrix_filter:

            position = 0

            last_filter = MatrixFilter.objects.filter(meta_node=self.meta_node).order_by('position').last()

            if last_filter:
                position = last_filter.position + 1
            
            self.matrix_filter = MatrixFilter(
                meta_node = self.meta_node,
                filter_type = form.cleaned_data['filter_type'],
                position = position,
            )

        self.matrix_filter.name = form.cleaned_data['name']

        if not self.matrix_filter.additional_data:
            self.matrix_filter.additional_data = {}

        self.matrix_filter.additional_data['is_active'] = form.cleaned_data.get('is_active', True)

        self.set_definition(form, self.matrix_filter)

        self.matrix_filter.save()

        if self.matrix_filter.filter_type == 'RangeFilter':
            cache_manager = ChildrenCacheManager(self.meta_node)
            cache_manager.update_matrix_filter(self.matrix_filter)

        # matrix filter needs to be saved first, encoded_space is stored on MatrixFilterSpace Model
        # with FK to MatrixFilter
        self.save_encoded_space(form, self.matrix_filter)

        # redirect to management view
        context = self.get_context_data(**self.kwargs)
        context['success'] = True
        return self.render_to_response(context)


'''
    A View to add/edit one single MatrixFilterSpace of a MatrixFilter that is_multispace==True
    - e.g. ColorFilter, DescriptiveTextAndImagesFilter and TaxonFilter
    - the form_class depends on the type of the matrix_filter
'''
from app_kit.views import ManageContentImageMixin
from localcosmos_server.forms import ManageContentImageFormCommon
class ManageMatrixFilterSpace(FormLanguageMixin, ManageContentImageMixin, FormView):

    form_class = None
    template_name = 'nature_guides/ajax/manage_matrix_filter_space.html'

    template_names = {
        'ColorFilter' : 'nature_guides/ajax/manage_color_filter_space.html',
    }

    # ContentImageTaxon
    taxon = None

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):        
        self.set_space(**kwargs)
        self.set_template_name()
        return super().dispatch(request, *args, **kwargs)


    def set_template_name(self):
        if self.matrix_filter.filter_type in self.template_names:
            self.template_name = self.template_names[self.matrix_filter.filter_type]

    def set_space(self, **kwargs):

        # content image mixin
        self.new = False

        # content image specific
        self.object_content_type = ContentType.objects.get_for_model(MatrixFilterSpace)

        if 'space_id' in kwargs:
            self.matrix_filter_space = MatrixFilterSpace.objects.get(pk=kwargs['space_id'])
            self.matrix_filter = self.matrix_filter_space.matrix_filter

            # set the content image specific stuff
            self.content_image = self.matrix_filter_space.image()
            self.content_instance = self.matrix_filter_space
            
        else:
            self.matrix_filter_space = None
            self.matrix_filter = MatrixFilter.objects.get(pk=kwargs['matrix_filter_id'])

            # content image specific
            self.content_image = None
            self.content_instance = None


        # matrix_filter is available

        # meet requirements of ManageContentImageMixin
        if self.content_image:
            self.image_type = self.content_image.image_type
            self.set_licence_registry_entry(self.content_image.image_store, 'source_image')
        else:
            self.image_type = None
            self.licence_registry_entry = None
        

    def set_primary_language(self):
        meta_node = self.matrix_filter.meta_node
        tree_node = NatureGuidesTaxonTree.objects.filter(meta_node=meta_node).first()
        self.primary_language = tree_node.nature_guide.primary_language
        

    def get_form_class(self):
        form_class_name = '{0}SpaceForm'.format(self.matrix_filter.filter_type)
        return globals()[form_class_name]
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['matrix_filter'] = self.matrix_filter
        context['matrix_filter_space'] = self.matrix_filter_space
        context['meta_node'] = self.matrix_filter.meta_node
        
        # paramters if the create space was called from a node management modal
        context['from_url'] = self.request.GET.get('from_url', None)
        return context

    def get_initial(self):
        initial = super().get_initial()
        if self.matrix_filter_space:
            initial['matrix_filter_space_id'] = self.matrix_filter_space.id
            initial.update(self.matrix_filter.matrix_filter_type.get_single_space_initial(
                self.matrix_filter_space))
            
        return initial


    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        
        form_class = self.get_form_class()

        if not issubclass(form_class, ManageContentImageFormCommon):
            if 'content_instance' in form_kwargs:
                del form_kwargs['content_instance']
        return form_kwargs


    def form_valid(self, form):

        self.matrix_filter_space = self.matrix_filter.matrix_filter_type.save_single_space(form)

        self.content_instance = self.matrix_filter_space

        # save the image, if any
        if 'source_image' in form.cleaned_data and form.cleaned_data['source_image']:
            self.save_image(form)
        elif 'referred_content_image_id' in form.cleaned_data and form.cleaned_data['referred_content_image_id']:
            self.save_image(form)

        context = self.get_context_data(**self.kwargs)
        context['success'] = True
        return self.render_to_response(context)


class ManageAdditionalMatrixFilterSpaceImage(ManageContentImage):
    
    template_name = 'nature_guides/ajax/manage_additional_matrix_filter_space_image.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_node'] = self.content_instance.matrix_filter.meta_node
        return context


class DeleteAdditionalMatrixFilterSpaceImage(DeleteContentImage):
    
    template_name = 'nature_guides/ajax/delete_additional_matrix_filter_space_image.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_node'] = self.object.content.matrix_filter.meta_node
        return context


class DeleteMatrixFilter(MetaAppMixin, AjaxDeleteView):
    model = MatrixFilter

    template_name = 'nature_guides/ajax/delete_matrix_filter_value.html'


    def form_valid(self, form):
        self.object = self.get_object()
        meta_node = self.object.meta_node
        self.object.delete()

        context = {
            'meta_app' : self.meta_app,
            'meta_node' : meta_node,
            'deleted' : True,
        }
        return self.render_to_response(context)
        

# parent_node_id needed for reload matrix
class DeleteMatrixFilterSpace(MetaAppMixin, AjaxDeleteView):
    model = MatrixFilterSpace

    template_name = 'nature_guides/ajax/delete_matrix_filter_value.html'

    def get_verbose_name(self):
        return self.object
            
    def form_valid(self, form):
        meta_node = self.object.matrix_filter.meta_node
        self.object.delete()

        context = {
            'meta_app' : self.meta_app,
            'meta_node' : meta_node,
            'deleted':True,
        }
        return self.render_to_response(context)


'''
    Node analysis View
    - this should support nodes that are not added to a parent node
    (all node have fk to key, but not necessarily a NodeToNode entry)
'''
class NodeAnalysis(MetaAppMixin, TemplateView):

    template_name = 'nature_guides/node_analysis.html'

    def dispatch(self, request, *args, **kwargs):
        self.set_node(**kwargs)
        return super().dispatch(request, *args, **kwargs)


    def set_node(self, **kwargs):
        self.meta_node = MetaNode.objects.get(pk=kwargs['meta_node_id'])
        self.nodelinks = []
        for node in NatureGuidesTaxonTree.objects.filter(meta_node=self.meta_node):
            self.nodelinks.append((node.parent, node))

            crosslinks = NatureGuideCrosslinks.objects.filter(child=node)
            for crosslink in crosslinks:
                self.nodelinks.append((crosslink.parent, crosslink.child))
        

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_node'] = self.meta_node
        context['nodelinks'] = self.nodelinks
        context['content_type'] = ContentType.objects.get_for_model(NatureGuide)
        context['is_analysis'] = True
        context['search_for_node_form'] = SearchForNodeForm(
            language=self.meta_node.nature_guide.primary_language)
        return context


'''
    GetIdentificationMatrix
    - space is a list of length n, except for range space
    - range space is a list of length 2
'''
class GetIdentificationMatrix(TemplateView):

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):

        self.meta_node = MetaNode.objects.get(pk=kwargs['meta_node_id'])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not self.meta_node.children_cache or 'matrix_filters' not in self.meta_node.children_cache:
            manager = ChildrenCacheManager(self.meta_node)
            manager.rebuild_cache()
        return JsonResponse(self.meta_node.children_cache, safe=False)



'''
    move a NatureGuidesTaxonTree node or a NatureGuideCrosslinks.child
    - node_id and parent_node id are required to determine if it is a crosslink or not
'''
class MoveNatureGuideNode(MetaAppFormLanguageMixin, FormView):

    template_name = 'nature_guides/ajax/move_natureguide_node.html'
    form_class = MoveNodeForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_nodes(**kwargs)
        # new parent is fetched using the form
        return super().dispatch(request, *args, **kwargs)

    def set_nodes(self, **kwargs):
        self.old_parent_node = NatureGuidesTaxonTree.objects.get(pk=kwargs['parent_node_id'])
        self.child_node = NatureGuidesTaxonTree.objects.get(pk=kwargs['child_node_id'])


    def get_form(self, form_class=None):

        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.child_node, self.old_parent_node, **self.get_form_kwargs())


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['old_parent_node'] = self.old_parent_node
        context['child_node'] = self.child_node
        context['success'] = False
        return context

    def form_valid(self, form):

        new_parent_node_id = form.cleaned_data['new_parent_node_id']
        new_parent_node = NatureGuidesTaxonTree.objects.get(pk=new_parent_node_id)

        # check if it is a crosslink
        crosslink = NatureGuideCrosslinks.objects.filter(parent=self.old_parent_node,
                                                         child=self.child_node).first()
        
        if crosslink:
            crosslink.move_to(new_parent_node)

        else:
            self.child_node.move_to(new_parent_node)

        context = self.get_context_data(**self.kwargs)
        context['form'] = form
        context['new_parent_node'] = new_parent_node
        context['success'] = True

        return self.render_to_response(context)


class SearchMoveToGroup(SearchForNode):

    def get_displayed_name(self, node):
        displayed_name = '{0} ({1})'.format(node.meta_node.name, node.nature_guide)
        return displayed_name

    def get_queryset(self, request, **kwargs):

        nodes = []

        searchtext = request.GET.get('name', '')
        
        if len(searchtext) > 2:
            node_types = ['node', 'root']
            nodes = NatureGuidesTaxonTree.objects.filter(meta_node__name__istartswith=searchtext).filter(
                meta_node__node_type__in=node_types)[:15]

        return nodes

    def get_on_click_url(self, meta_node):
        return None


class ManageMatrixFilterRestrictions(MultipleTraitValuesIterator, MetaAppMixin, FormView):

    template_name = 'nature_guides/ajax/manage_matrix_filter_restrictions.html'
    form_class = ManageMatrixFilterRestrictionsForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_node(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_node(self, **kwargs):
        self.meta_node = MetaNode.objects.get(pk=kwargs['meta_node_id'])
        self.matrix_filter = MatrixFilter.objects.get(pk=kwargs['matrix_filter_id'])

    def get_form(self, form_class=None):

        if form_class is None:
            form_class = self.get_form_class()
        return form_class(self.meta_app, self.matrix_filter, self.meta_node, **self.get_form_kwargs())


    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['from_url'] = self.request.path
        return form_kwargs


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['meta_node'] = self.meta_node
        context['matrix_filter'] = self.matrix_filter
        context['success'] = False
        return context


    def form_valid(self, form):
        self.iterate_matrix_form_fields(form)

        cache_manager = ChildrenCacheManager(self.meta_node)
        cache_manager.update_matrix_filter_restrictions(self.matrix_filter)

        context = self.get_context_data(**self.kwargs)
        context['form'] = form
        context['success'] = True
        
        return self.render_to_response(context)
    

    # methods for iterating over selected traits
    # use self.matrix_filter, which is the restricted filter
    # the passed 'matrix_filter' argument is the filter which restricts self.matrix_filter
    def get_existing_space_link(self, restrictive_matrix_filter):
        restriction_space = MatrixFilterRestriction.objects.filter(restricted_matrix_filter=self.matrix_filter,
                                                restrictive_matrix_filter=restrictive_matrix_filter).first()
        
        return restriction_space


    def get_all_existing_space_links(self, restrictive_matrix_filter):
        restriction_spaces = MatrixFilterRestriction.objects.filter(restricted_matrix_filter=self.matrix_filter,
                    restrictive_matrix_filter=restrictive_matrix_filter)
        
        return restriction_spaces

        
    def instantiate_new_space_link(self, restrictive_matrix_filter):
        restriction_space = MatrixFilterRestriction(restricted_matrix_filter=self.matrix_filter,
                                                    restrictive_matrix_filter=restrictive_matrix_filter)
        return restriction_space


'''
    Add the ability to copy a tree branch as a copy to work on without making changes to the existing one
    - ask the user to add a name
    - copy all descendants
    - also copy all matrix filter data
    - always copies in place, same parent node
'''
from localcosmos_server.slugifier import create_unique_slug

class CopyTreeBranch(MetaAppMixin, FormView):

    template_name = 'nature_guides/ajax/copy_tree_branch.html'
    form_class = CopyTreeBranchForm

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.set_node(**kwargs)
        return super().dispatch(request, *args, **kwargs)

    def set_node(self, **kwargs):
        self.node = NatureGuidesTaxonTree.objects.get(pk=kwargs['node_id'])
        self.parent_node = self.node.parent

        # look up copies if their source is given
        self.copy_map = {
            'nodes' : {},
            'matrix_filters' : {},
            'matrix_filter_space' : {},
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['node'] = self.node
        context['success'] = False
        return context


    def copy_content_image(self, content_image, new_object):

        copy_fields = ['image_store', 'crop_parameters', 'features', 'content_type', 'image_type', 'position',
                       'is_primary', 'text']

        overwrite_values = {
            'object_id' : new_object.id,
        }

        copied_content_image = copy_model_instance(content_image, copy_fields, overwrite_values)

        return copied_content_image


    def copy_meta_node(self, meta_node, new_name=None):

        copy_fields = ['nature_guide', 'node_type', 'name']
        overwrite_values = {}

        if new_name:
            overwrite_values['name'] = new_name

        copied_meta_node = copy_model_instance(meta_node, copy_fields, overwrite_values)

        if meta_node.taxon:

            copied_meta_node.set_taxon(meta_node.taxon)
            copied_meta_node.save()

        return copied_meta_node


    def copy_node(self, node, new_parent_node, taxon_tree_fields={}, copied_node_name=None):

        if copied_node_name == None:
            copied_node_name = node.meta_node.name

        # for MetaNode and NatureGuidesTaxonTree do not use meta_node.pk = None meta_node.save()
        # due to inhertance this does not work
        # create a copy of meta node
        new_meta_node = self.copy_meta_node(node.meta_node, copied_node_name)

        # taxon tree nodes are more complex, create a new one instead of setting pk to None
        # eg trigger
        copied_node = NatureGuidesTaxonTree(
            nature_guide = new_parent_node.nature_guide,
            meta_node = new_meta_node,
            position = node.position,
        )

        copied_node.save(new_parent_node, taxon_tree_fields=taxon_tree_fields)

        # copy node images
        images = node.meta_node.images()

        for image in images:
            copied_image = self.copy_content_image(image, copied_node.meta_node)


        # copy matrix filters
        matrix_filters = MatrixFilter.objects.filter(meta_node=node.meta_node)
        for matrix_filter in matrix_filters:
            copied_matrix_filter = self.copy_matrix_filter(matrix_filter, new_meta_node)


        # copy node filter space - the space of node in relation to node.parent
        parent_matrix_filters = MatrixFilter.objects.filter(meta_node=node.parent.meta_node)

        for parent_matrix_filter in parent_matrix_filters:

            if node == self.node:
                copied_parent_matrix_filter = parent_matrix_filter

            else:
                copied_parent_matrix_filter_pk = self.copy_map['matrix_filters'][str(parent_matrix_filter.pk)]
                copied_parent_matrix_filter = MatrixFilter.objects.get(pk=copied_parent_matrix_filter_pk)

            node_filter_spaces = NodeFilterSpace.objects.filter(node=node, matrix_filter=parent_matrix_filter)

            for node_filter_space in node_filter_spaces:
                copied_node_filter_space = self.copy_node_filter_space(node_filter_space, copied_node,
                                                                       copied_parent_matrix_filter)

        self.copy_map['nodes'][str(node.pk)] = str(copied_node.pk) 
        return copied_node


    def copy_matrix_filter(self, matrix_filter, new_meta_node):

        copy_fields = ['name', 'description', 'filter_type', 'definition', 'position', 'weight']
        
        overwrite_values = {
            'meta_node' : new_meta_node,
        }
        
        copied_matrix_filter = copy_model_instance(matrix_filter, copy_fields, overwrite_values)

        self.copy_map['matrix_filters'][str(matrix_filter.pk)] = str(copied_matrix_filter.pk)

        spaces = matrix_filter.get_space()

        for space in spaces:

            space_copy_fields = ['encoded_space', 'additional_information', 'position']
            space_overwrite_values = {
                'matrix_filter' : copied_matrix_filter,
            }

            copied_space = copy_model_instance(space, space_copy_fields, space_overwrite_values)

            self.copy_map['matrix_filter_space'][str(space.pk)] = str(copied_space.pk)

            if space.images().exists():

                for content_image in space.images():
                    self.copy_content_image(content_image, copied_space)

        return copied_matrix_filter


    def copy_node_filter_space(self, node_filter_space, new_node, new_matrix_filter):

        copy_fields = ['encoded_space', 'weight']

        '''
        for the copy of self.node simply copy all values of NodeFilterSpace
        '''
        if node_filter_space.node == self.node:
            copy_fields.append('values')

        overwrite_values = {
            'node' : new_node,
            'matrix_filter' : new_matrix_filter,
        }

        copied_node_filter_space = copy_model_instance(node_filter_space, copy_fields, overwrite_values)

        '''
        the copy of self.node uses the matrix filters of self.node.parent - which have not been copied
        '''
        if node_filter_space.node != self.node:

            # set the new values of copied_node_filter_space - these are the copies of the old values
            old_values = node_filter_space.values.all().values_list('pk', flat=True)

            if old_values:
                new_values_pks = []
                for matrix_filter_space_pk in old_values:
                    new_values_pks.append(self.copy_map['matrix_filter_space'][str(matrix_filter_space_pk)])

                new_values_qry = MatrixFilterSpace.objects.filter(pk__in=new_values_pks)

                copied_node_filter_space.values.set(new_values_qry)

        return copied_node_filter_space

    # old_node is a descendant of the original node. new_node is th copied node
    # search crosslinks using the parent
    # only crosslinks that point from the original branch to an outside node are copied
    def copy_crosslinks(self, old_parent_node, copied_node):

        created_crosslinks = []

        old_crosslinks = NatureGuideCrosslinks.objects.filter(parent=old_parent_node)

        for old_crosslink in old_crosslinks:

            new_child = old_crosslink.child

            new_parent = copied_node

            new_crosslink = NatureGuideCrosslinks(
                parent = new_parent,
                child = new_child,
                position = old_crosslink.position,
            )
            new_crosslink.save()

            created_crosslinks.append(new_crosslink)

        return created_crosslinks
        

    def get_new_taxon_nuid(self, old_root_nuid, new_root_nuid, old_node):

        new_taxon_nuid_tail = old_node.taxon_nuid[len(old_root_nuid):]
        new_taxon_nuid = '{0}{1}'.format(new_root_nuid, new_taxon_nuid_tail)

        return new_taxon_nuid
        

    def form_valid(self, form):

        # copy the node
        copied_node_name = form.cleaned_data['branch_name']
        prevent_crosslinks = form.cleaned_data['prevent_crosslinks']

        # the new root node has the new root nuid
        new_root_node = self.copy_node(self.node, self.parent_node, taxon_tree_fields={},
                                       copied_node_name=copied_node_name)

        created_root_crosslinks = self.copy_crosslinks(self.node, new_root_node)

        old_root_nuid = self.node.taxon_nuid
        new_root_nuid = new_root_node.taxon_nuid
        
        # copy all descendants, travelling down the tree
        descendants = self.node.tree_descendants.order_by('taxon_nuid')

        # it is sufficient to replace the old_root_nuid with new_root_nuid for each taxon
        for descendant in descendants:

            copy_node = True

            # the taxon_nuid field is calculated here and not using the .save() method of
            # NatureGuidesTaxonTree
            new_taxon_nuid = self.get_new_taxon_nuid(old_root_nuid, new_root_nuid, descendant)
            new_parent_nuid = new_taxon_nuid[:-3]

            new_parent_node = NatureGuidesTaxonTree.objects.get(taxon_nuid=new_parent_nuid)

            if descendant.meta_node.node_type == 'result' and prevent_crosslinks == False:
                # if the result is backed by a taxonomic database, copy it
                # if the result is NOT backed by a taxonomic database, create a crosslink
                if not descendant.meta_node.taxon_latname:
                    copy_node = False
            
            else:
                copy_node = True


            if copy_node == True:

                # create the taxon tree fields
                slug = create_unique_slug(descendant.taxon_latname, 'slug', NatureGuidesTaxonTree)            

                taxon_tree_fields = {
                    'taxon_nuid' : new_taxon_nuid,
                    'taxon_latname' : descendant.taxon_latname,
                    'is_root_taxon' : False,
                    'rank' : None, # no ranks for NG TaxonTree entries
                    'slug' : slug,
                    'author' : None, # no author for NG TaxonTree entries
                    'source_id' : new_taxon_nuid, # obsolete in this case, only necessary for taxonomies like col
                }
                
                copied_node = self.copy_node(descendant, new_parent_node, taxon_tree_fields=taxon_tree_fields)

                created_crosslinks = self.copy_crosslinks(descendant, copied_node)

            else:
                # create a crosslink instead of a copy
                crosslink = NatureGuideCrosslinks(
                    parent = new_parent_node,
                    child = descendant,
                    position = descendant.position,
                )

                crosslink.save()

        # rebuild cache
        self.parent_node.meta_node.rebuild_cache()
        
        context = self.get_context_data(**self.kwargs)
        context['form'] = form
        context['node_copy'] = new_root_node
        context['success'] = True

        # add required context for rendering a node
        context['content_type'] = ContentType.objects.get_for_model(self.node.nature_guide)
        context['parent_node'] = self.node.parent

        return self.render_to_response(context)


class StoreIdentificationMode(TemplateView):
    
    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):

        self.meta_node = MetaNode.objects.get(pk=kwargs['meta_node_id'])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        mode = kwargs['identification_mode']

        self.meta_node.add_setting('identification_mode', mode)
        self.meta_node.save()

        response = {
            'meta_node_id' : self.meta_node.id,
            'identification_mode' : mode,
        }
        
        return JsonResponse(response, safe=False)


'''
    overview images are attached to a MetaNode
'''
class ManageOverviewImage(ManageContentImage):
    template_name = 'nature_guides/ajax/manage_overview_image.html'


class DeleteOverviewImage(DeleteContentImage):
    template_name = 'nature_guides/ajax/delete_overview_image.html'