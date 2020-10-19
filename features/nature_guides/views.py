from django.shortcuts import render, redirect, reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, FormView
from django.contrib.contenttypes.models import ContentType
from django.db.models.query import QuerySet # needed for saving node matrix filter values
from django.http import JsonResponse # NodeSearch

from .models import (NatureGuide, MetaNode, MatrixFilter, MatrixFilterSpace, NodeFilterSpace,
                     NatureGuidesTaxonTree, CrosslinkManager, NatureGuideCrosslinks, ChildrenCacheManager)

from .forms import (NatureGuideOptionsForm, IdentificationMatrixForm, SearchForNodeForm, ManageNodelinkForm,
                    MoveNodeForm)

from .matrix_filter_forms import (MatrixFilterManagementForm, DescriptiveTextAndImagesFilterManagementForm,
                            RangeFilterManagementForm, ColorFilterManagementForm, NumberFilterManagementForm,
                            TaxonFilterManagementForm, TextOnlyFilterManagementForm)

from .matrix_filter_space_forms import (DescriptiveTextAndImagesFilterSpaceForm, ColorFilterSpaceForm,
                                        TextOnlyFilterSpaceForm)

from app_kit.views import ManageGenericContent
from app_kit.view_mixins import MetaAppMixin, FormLanguageMixin, MetaAppFormLanguageMixin

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

        return parent_node
        

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['parent_node'] = self.parent_node
        context['meta_node'] = self.parent_node.meta_node
        context['natureguides_taxontree_content_type'] = ContentType.objects.get_for_model(
            NatureGuidesTaxonTree)
        context['nature_guide'] = self.generic_content
        context['children_count'] = self.parent_node.children_count
        
        context['form'] = IdentificationMatrixForm(self.parent_node.meta_node)
        context['search_for_node_form'] = SearchForNodeForm(language=self.primary_language)

        # add the parents to the context for tree browsing
        
        context['parent_crosslinks'] = NatureGuideCrosslinks.objects.filter(child=self.parent_node)

        return context



'''
    Manage a Node(link)
    - also define which filters apply for an entry
    - if a taxon is added to a NatureGuideTaxonTree, the TaxonProfile referring taxon has to be updated
'''
class ManageNodelink(MetaAppFormLanguageMixin, FormView):

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
        
        if 'node_id' in kwargs:
            self.node = NatureGuidesTaxonTree.objects.get(pk=kwargs['node_id'])
            self.parent_node = self.node.parent
            self.node_type = self.node.meta_node.node_type
            
        else:
            self.node = None
            self.parent_node = NatureGuidesTaxonTree.objects.get(pk=kwargs['parent_node_id'])
            self.node_type = kwargs['node_type']
        

    def get_initial(self):
        initial = super().get_initial()
        
        if self.node:
            initial['node_type'] = self.node.meta_node.node_type
            initial['name'] = self.node.meta_node.name
            initial['decision_rule'] = self.node.decision_rule
            initial['node_id'] = self.node.id
            initial['taxon'] = self.node.meta_node.taxon

        else:
            initial['node_type'] = self.node_type
        
        return initial
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['node_type'] = self.node_type
        context['parent_node'] = self.parent_node
        context['node'] = self.node
        context['content_type'] = ContentType.objects.get_for_model(self.parent_node.nature_guide)

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
        return form_class(self.parent_node, **self.get_form_kwargs())
    
    # if a taxon is added to a meta_node without taxon, there could have been a taxon profile referencing
    # app_kit.features.nature_guides as taxon_source. this taxon profile has to be updated to reference
    # the new taxon of the meta node
    def save_nodelink(self, form):
        node_id = form.cleaned_data.get('node_id', None)

        if not node_id:
            meta_node = MetaNode(
                nature_guide=self.parent_node.nature_guide,
                node_type = form.cleaned_data['node_type'],
                name = form.cleaned_data['name']
            )

            meta_node.save()
            
            self.node = NatureGuidesTaxonTree(
                nature_guide = self.parent_node.nature_guide,
                meta_node = meta_node,
                position=self.parent_node.children_count,
            )
            
        else:
            self.node = NatureGuidesTaxonTree.objects.get(pk=node_id)
            meta_node = self.node.meta_node

        
        if 'taxon' in form.cleaned_data and form.cleaned_data['taxon']:

            new_taxon = form.cleaned_data['taxon']
            
            # if the meta_node had no taxon, a taxon profile with a fallback taxon might exist
            if not meta_node.taxon and not meta_node.taxon_source and not meta_node.taxon_latname:
                
                taxon_profile = self.node.get_taxon_profile(self.meta_app)

                if taxon_profile:
                    # update taxon_profile taxon
                    taxon_profile.set_taxon(new_taxon)
                    taxon_profile.save()
                
            self.node.meta_node.set_taxon(new_taxon)
        else:
            self.node.meta_node.remove_taxon()

        self.node.meta_node.name = form.cleaned_data['name']  
        self.node.meta_node.save()

        self.node.decision_rule = form.cleaned_data['decision_rule']
        self.node.save(self.parent_node)


    def form_valid(self, form):

        # save nodelink, make self.nodelink available
        self.save_nodelink(form)

        
        # save matrix filters if any
        # now save all inserted trait values
        for field in form:
            
            is_matrix_filter = getattr(field.field, 'is_matrix_filter', False)

            if is_matrix_filter == True:

                matrix_filter_uuid = field.name
                matrix_filter = MatrixFilter.objects.get(uuid=matrix_filter_uuid)

                # add posted, remove unposted
                if matrix_filter_uuid in form.cleaned_data and form.cleaned_data[matrix_filter_uuid]:

                    is_new_node_filter_space = False
                    node_filter_space = NodeFilterSpace.objects.filter(node=self.node,
                                                                       matrix_filter=matrix_filter).first()

                    if not node_filter_space:
                        is_new_node_filter_space = True
                        node_filter_space = NodeFilterSpace(node=self.node, matrix_filter=matrix_filter)
                        

                    value = form.cleaned_data[matrix_filter_uuid]

                    # Color, TextAndImages
                    if isinstance(value, QuerySet):

                        if is_new_node_filter_space == True:
                            node_filter_space.save()
                        
                        # remove existing
                        available_spaces = MatrixFilterSpace.objects.filter(matrix_filter=matrix_filter)
                        
                        for space in available_spaces:
                            if space in value:
                                node_filter_space.values.add(space)
                            else:
                                node_filter_space.values.remove(space)

                    # Range, Numbers
                    else:
                        # the value needs to be encoded correctly by the TraitProperty Subclass
                        encoded_space = matrix_filter.matrix_filter_type.encode_entity_form_value(value)
                        
                        node_filter_space.encoded_space = encoded_space
                        node_filter_space.save()

                # remove filter which uuids are not present in the posted data
                else:
                    node_filter_space = NodeFilterSpace.objects.filter(node=self.node,
                                                                       matrix_filter=matrix_filter)

                    if node_filter_space.exists():

                        for space in node_filter_space:
                            space.delete()

        # update cache, cannot be done in .models because the node is saved BEFORE the spaces are added
        cache = ChildrenCacheManager(self.node.parent.meta_node)
        cache.add_or_update_child(self.node)
        
        context = self.get_context_data(**self.kwargs)
        context['form'] = form
        context['success'] = True
        
        return self.render_to_response(context)



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


    def delete(self, request, *args, **kwargs):
        if self.crosslink:
            return super().delete(request, *args, **kwargs)

        self.object = self.get_object()
        context = self.get_context_data(**kwargs)
        context['deleted_object_id'] = self.object.pk
        context['deleted'] = True
        self.object.delete_branch()
        return self.render_to_response(context)


# get nodes that can be added to the current parent
class AddExistingNodes(MetaAppMixin, TemplateView):

    template_name = 'nature_guides/ajax/add_existing_nodes.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.parent_node = NatureGuidesTaxonTree.objects.get(pk=kwargs['parent_node_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # exclude is_root_node and all uplinks
        nodes = NatureGuidesTaxonTree.objects.all().exclude(meta_node__node_type='root').exclude(
            taxon_nuid__startswith=self.parent_node.taxon_nuid)
        
        return nodes

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_node'] = self.parent_node
        context['content_type'] = ContentType.objects.get_for_model(self.parent_node.nature_guide)
        
        nodes = self.get_queryset()
        context['nodes'] = nodes
        
        return context


    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)

        if request.is_ajax() and 'page' in request.GET:
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


from app_kit.views import StoreObjectOrder
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


    def get_on_click_url(self, meta_node):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'meta_node_id' : meta_node.id
        }

        url = reverse('node_analysis', kwargs=url_kwargs)

        return url


    def get_queryset(self, request, **kwargs):

        meta_nodes = []

        searchtext = request.GET.get('name', '')
        
        if len(searchtext) > 2:

            meta_nodes = MetaNode.objects.filter(name__istartswith=searchtext).exclude(node_type='root')[:15]

        return meta_nodes
        

    @method_decorator(ajax_required)
    def get(self, request, *args, **kwargs):

        nature_guide = NatureGuide.objects.get(pk=kwargs['nature_guide_id'])

        results = []

        meta_nodes = self.get_queryset(request, **kwargs)
        
        for meta_node in meta_nodes:

            url = self.get_on_click_url(meta_node)

            choice = {
                'name' : meta_node.name,
                'id' : meta_node.id,
                'url' : url,
            }
            
            results.append(choice)

        return JsonResponse(results, safe=False) 


'''
    Matrix
'''
class LoadMatrixFilters(TemplateView):

    template_name = 'nature_guides/ajax/matrix_filters.html'

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):
        self.meta_node = MetaNode.objects.get(pk=kwargs['meta_node_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = IdentificationMatrixForm(self.meta_node)
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
class ManageMatrixFilter(FormLanguageMixin, FormView):

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

        if self.matrix_filter is not None:
            initial['matrix_filter_id'] = self.matrix_filter.id
            initial['name'] = self.matrix_filter.name

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

        self.set_definition(form, self.matrix_filter)

        self.matrix_filter.save()

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
class ManageMatrixFilterSpace(FormLanguageMixin, ManageContentImageMixin, FormView):

    form_class = None
    template_name = 'nature_guides/ajax/manage_matrix_filter_space.html'

    # ContentImageTaxon
    taxon = None

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):        
        self.set_space(**kwargs)
        return super().dispatch(request, *args, **kwargs)


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


class DeleteMatrixFilter(AjaxDeleteView):
    model = MatrixFilter

    template_name = 'nature_guides/ajax/delete_matrix_filter_value.html'


    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        meta_node = self.object.meta_node
        self.object.delete()

        context = {
            'meta_node' : meta_node,
            'deleted' : True,
        }
        return self.render_to_response(context)
        

# parent_node_id needed for reload matrix
class DeleteMatrixFilterSpace(AjaxDeleteView):
    model = MatrixFilterSpace

    template_name = 'nature_guides/ajax/delete_matrix_filter_value.html'

    def get_verbose_name(self):
        return self.object
            
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        meta_node = self.object.matrix_filter.meta_node
        self.object.delete()

        context = {
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
    - granular space is a list of length n
    - range space is a list of length 2
'''
class GetIdentificationMatrix(TemplateView):

    @method_decorator(ajax_required)
    def dispatch(self, request, *args, **kwargs):

        self.meta_node = MetaNode.objects.get(pk=kwargs['meta_node_id'])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):        
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
        return form_class(self.child_node, **self.get_form_kwargs())


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

    def get_queryset(self, request, **kwargs):

        meta_nodes = []

        searchtext = request.GET.get('name', '')
        
        if len(searchtext) > 2:
            node_types = ['node', 'root']
            meta_nodes = MetaNode.objects.filter(name__istartswith=searchtext).filter(
                node_type__in=node_types)[:15]

        return meta_nodes

    def get_on_click_url(self, meta_node):
        return None
