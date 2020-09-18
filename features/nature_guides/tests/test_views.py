from django.test import TestCase, RequestFactory
from django_tenants.test.cases import TenantTestCase
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from django.http import QueryDict

from app_kit.tests.common import test_settings

from app_kit.tests.mixins import (WithMetaApp, WithTenantClient, WithUser, WithLoggedInUser, WithAjaxAdminOnly,
                                  WithAdminOnly, WithFormTest, ViewTestMixin, WithImageStore, WithMedia)

from app_kit.models import MetaAppGenericContent, ContentImage


from app_kit.features.nature_guides.views import (ManageNatureGuide, ManageNodelink, DeleteNodelink,
        AddExistingNodes, LoadKeyNodes, StoreNodeOrder, LoadNodeManagementMenu, DeleteMatrixFilter,
        SearchForNode, LoadMatrixFilters, ManageMatrixFilter, ManageMatrixFilterSpace, DeleteMatrixFilterSpace,
        NodeAnalysis, GetIdentificationMatrix)


from app_kit.features.nature_guides.models import (NatureGuide, NatureGuidesTaxonTree, NatureGuideCrosslinks,
                                        MetaNode, MatrixFilter, NodeFilterSpace, MatrixFilterSpace)

from app_kit.features.nature_guides.forms import (NatureGuideOptionsForm, SearchForNodeForm,
                                                  IdentificationMatrixForm, ManageNodelinkForm)


from app_kit.features.nature_guides.tests.common import WithNatureGuide, WithMatrixFilters

from app_kit.features.nature_guides.matrix_filters import MATRIX_FILTER_TYPES

from content_licencing.models import ContentLicenceRegistry


from taxonomy.lazy import LazyTaxon
from taxonomy.models import TaxonomyModelRouter


import json


class WithNatureGuideLink(WithNatureGuide):

    def setUp(self):
        super().setUp()
        self.content_type = ContentType.objects.get_for_model(NatureGuide)

        self.natureguides_taxontree_content_type = ContentType.objects.get_for_model(
            NatureGuidesTaxonTree)

        self.create_nature_guide()


    def create_nature_guide(self):
        
        # create link
        generic_content_name = '{0} {1}'.format(self.meta_app.name, NatureGuide.__class__.__name__)
        self.generic_content = NatureGuide.objects.create(generic_content_name, self.meta_app.primary_language)

        self.link = MetaAppGenericContent(
            meta_app=self.meta_app,
            content_type=self.content_type,
            object_id=self.generic_content.id
        )

        self.link.save()

        self.start_node = NatureGuidesTaxonTree.objects.get(nature_guide=self.generic_content,
                                                            meta_node__node_type='root')


    def create_nodes(self, create_crosslink=True):

        # create nodes with crosslinks
        for c in range(1,3):

            node_name = 'node {}'.format(c)

            extra = {
                'decision_rule' : '{0} decision rule'.format(node_name)
            }

            node = self.create_node(self.start_node, node_name, **extra)

            self.nodes.append(node)


        self.child_node = self.create_node(self.nodes[0], 'child node')

        if create_crosslink == True:
            self.crosslink = NatureGuideCrosslinks(
                parent=self.child_node,
                child=self.nodes[1],
            )

            self.crosslink.save()


    def get_nodelink_form_data(self, **extra_data):
        data = {
            'input_language' : self.meta_app.primary_language,
            'node_type' : 'node',
            'name' : 'formtest node',
            'decision_rule' : 'test rule',
        }

        data.update(extra_data)

        return data


class TestManageNatureGuide(WithNatureGuideLink, ViewTestMixin, WithAdminOnly, WithUser, WithLoggedInUser,
                            WithMetaApp, WithTenantClient, TenantTestCase):


    url_name = 'manage_natureguide'
    view_class = ManageNatureGuide


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_type_id' : self.content_type.id,
            'object_id' : self.generic_content.id,
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        view.generic_content = self.generic_content
        view.generic_content_type = self.content_type
        return view
        

    @test_settings
    def test_get_parent_node(self):
        # no parent node id in kwargs
        view = self.get_view()
        parent_node = view.get_parent_node(**view.kwargs)
        self.assertEqual(parent_node, self.start_node)

    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.parent_node = self.start_node

        context = view.get_context_data(**view.kwargs)

        self.assertEqual(context['parent_node'], self.start_node)
        self.assertEqual(context['meta_node'], self.start_node.meta_node)
        self.assertEqual(context['natureguides_taxontree_content_type'],
                         self.natureguides_taxontree_content_type)
        self.assertEqual(context['nature_guide'], self.generic_content)
        self.assertEqual(context['children_count'], 0)
        self.assertEqual(context['options_form'].__class__, NatureGuideOptionsForm)
        self.assertEqual(context['form'].__class__, IdentificationMatrixForm)
        self.assertEqual(context['search_for_node_form'].__class__, SearchForNodeForm)

        self.assertIn('parent_crosslinks', context)


 
class TestManageNatureGuideComplex(WithNatureGuideLink, ViewTestMixin, WithAdminOnly, WithUser,
                                   WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'manage_natureguide'
    view_class = ManageNatureGuide

    def setUp(self):
        super().setUp()

        self.nodes = []
        self.create_nodes()
    

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_type_id' : self.content_type.id,
            'object_id' : self.generic_content.id,
            'parent_node_id' : self.child_node.id,
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        view.generic_content = self.generic_content
        view.generic_content_type = self.content_type
        return view
    

    @test_settings
    def test_get_parent_node(self):

        view = self.get_view()
        parent_node = view.get_parent_node(**view.kwargs)
        self.assertEqual(parent_node, self.child_node)


    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.parent_node = self.start_node

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['parent_node'], self.start_node)
        self.assertEqual(context['children_count'], 2)

        # crosslink as child
        view.parent_node = self.child_node

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['parent_node'], self.child_node)
        self.assertEqual(context['children_count'], 1)
        self.assertEqual(context['parent_crosslinks'].count(), 0)

        # crosslink as parent
        view.parent_node = self.nodes[1]

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['parent_node'], self.nodes[1])
        self.assertEqual(context['children_count'], 0)
        self.assertEqual(context['parent_crosslinks'].count(), 1)
        self.assertEqual(context['parent_crosslinks'][0], self.crosslink)

        

class TestManageNodelinkAsCreate(WithNatureGuideLink, ViewTestMixin, WithAjaxAdminOnly, WithUser,
                                 WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'create_nodelink'
    view_class = ManageNodelink

    
    def get_url_kwargs(self):
        url_kwargs = {
            'node_type' : 'node',
            'meta_app_id' : self.meta_app.id,
            'parent_node_id' : self.start_node.id,
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app

        return view


    @test_settings
    def test_set_node(self):

        view = self.get_view()
        view.set_node(**view.kwargs)
        self.assertEqual(view.node, None)
        self.assertEqual(view.parent_node, self.start_node)
        self.assertEqual(view.node_type, 'node')


    @test_settings
    def test_get_initial(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        initial = view.get_initial()
        self.assertEqual(initial['node_type'], 'node')
        self.assertFalse('name' in initial)
        self.assertFalse('decision_rule' in initial)
        self.assertFalse('node_id' in initial)
        self.assertFalse('taxon' in initial)


    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        context = view.get_context_data(**view.kwargs)

        self.assertEqual(context['node_type'], 'node')
        self.assertEqual(context['parent_node'], self.start_node)
        self.assertEqual(context['node'], None)
        self.assertEqual(context['content_type'], self.content_type)


    @test_settings
    def test_get_form_kwargs(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        form_kwargs = view.get_form_kwargs()
        self.assertFalse('node' in form_kwargs)
        self.assertEqual(form_kwargs['from_url'], view.request.path)


    @test_settings
    def test_get_form(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        form = view.get_form()
        self.assertEqual(form.__class__, ManageNodelinkForm)


    @test_settings
    def test_save_nodelink(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        data = self.get_nodelink_form_data()

        form = ManageNodelinkForm(view.parent_node, data=data, from_url=view.request.path)

        form.is_valid()
        self.assertEqual(form.errors, {})

        view.save_nodelink(form)

        node = self.start_node.children[0]
        self.assertEqual(node.decision_rule, data['decision_rule'])
        self.assertEqual(node.parent, self.start_node)
        self.assertEqual(node.meta_node.node_type, 'node')
        self.assertEqual(node.meta_node.name, data['name'])
        self.assertEqual(node.nature_guide, self.generic_content)
        self.assertEqual(node.meta_node.nature_guide, self.generic_content)


    @test_settings
    def test_form_valid(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        data = self.get_nodelink_form_data()

        form = ManageNodelinkForm(view.parent_node, data=data, from_url=view.request.path)

        form.is_valid()
        self.assertEqual(form.errors, {})

        node_name = data['name']
        qry = NatureGuidesTaxonTree.objects.filter(meta_node__name=node_name)

        self.assertFalse(qry.exists())

        response = view.form_valid(form)

        self.assertTrue(qry.exists())

        self.start_node.refresh_from_db()
        cache = self.start_node.meta_node.children_cache

        self.assertEqual(cache['items'][0]['name'], node_name)


    
class TestManageNodelinkAsManage(WithNatureGuideLink, WithMatrixFilters, ViewTestMixin, WithAjaxAdminOnly,
                        WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'manage_nodelink'
    view_class = ManageNodelink
    

    def setUp(self):
        super().setUp()

        self.nodes = []
        
        self.create_nodes()
        self.create_all_matrix_filters(self.start_node)

        self.view_node = self.nodes[0]


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app

        return view
    

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'node_id' : self.view_node.id,
        }
        return url_kwargs


    @test_settings
    def test_set_node(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        self.assertEqual(view.node, self.view_node)
        self.assertEqual(view.parent_node, self.start_node)
        self.assertEqual(view.node_type, 'node')


    @test_settings
    def test_get_initial(self):

        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lazy_taxon = LazyTaxon(instance=lacerta_agilis)

        self.view_node.meta_node.set_taxon(lazy_taxon)
        self.view_node.meta_node.save()
        
        view = self.get_view()
        view.set_node(**view.kwargs)

        initial = view.get_initial()
        self.assertEqual(initial['node_type'], 'node')
        self.assertEqual(initial['name'], 'node 1')
        self.assertEqual(initial['decision_rule'], 'node 1 decision rule')
        self.assertEqual(initial['node_id'], self.view_node.id)
        self.assertEqual(initial['taxon'], lazy_taxon)
        

    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        view.set_node(**view.kwargs)

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['node_type'], 'node')
        self.assertEqual(context['parent_node'], self.start_node)
        self.assertEqual(context['node'], self.view_node)
        self.assertEqual(context['content_type'], self.content_type)


    @test_settings
    def test_get_form_kwargs(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs['node'], self.view_node)
        self.assertEqual(form_kwargs['from_url'], view.request.path)


    @test_settings
    def test_save_nodelink(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        data = self.get_nodelink_form_data(**view.get_initial())

        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lazy_taxon = LazyTaxon(instance=lacerta_agilis)

        taxon_post_data = {
            'taxon_0' : lazy_taxon.taxon_source, # source
            'taxon_1' : lazy_taxon.taxon_latname, # latname
            'taxon_2' : lazy_taxon.taxon_author, # author
            'taxon_3' : str(lazy_taxon.name_uuid), # uuid
            'taxon_4' : lazy_taxon.taxon_nuid, # nuid
        }

        data.update(taxon_post_data)

        form = ManageNodelinkForm(view.parent_node, data=data, from_url=view.request.path)

        form.is_valid()
        self.assertEqual(form.errors, {})

        view.save_nodelink(form)

        node = self.view_node
        node.refresh_from_db()
        self.assertEqual(node.decision_rule, data['decision_rule'])
        self.assertEqual(node.parent, self.start_node)
        self.assertEqual(node.meta_node.node_type, 'node')
        self.assertEqual(node.meta_node.name, data['name'])
        self.assertEqual(node.nature_guide, self.generic_content)
        self.assertEqual(node.meta_node.nature_guide, self.generic_content)
        self.assertEqual(node.meta_node.taxon, lazy_taxon)


    @test_settings
    def test_form_valid(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        data = self.get_nodelink_form_data(**view.get_initial())
        
        # update data with matrixfilter data
        matrix_filters_data = {}

        matrix_filters = MatrixFilter.objects.filter(meta_node=self.start_node.meta_node)

        for matrix_filter in matrix_filters:

            matrix_filter_post_data = self.get_matrix_filter_post_data(matrix_filter)
            matrix_filters_data.update(matrix_filter_post_data)


        data.update(matrix_filters_data)

        form = ManageNodelinkForm(view.parent_node, data=data, from_url=view.request.path)

        form.is_valid()
        self.assertEqual(form.errors, {})

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)

        # check if all nodefilterspaces have been created
        for matrix_filter in matrix_filters:

            if matrix_filter.filter_type != 'TaxonFilter':
                
                node_space = NodeFilterSpace.objects.get(matrix_filter=matrix_filter, node=self.view_node)

                if matrix_filter.filter_type == 'RangeFilter':
                    self.assertEqual(node_space.encoded_space, [0.5, 4])
                    
                elif matrix_filter.filter_type == 'DescriptiveTextAndImagesFilter':
                    self.assertEqual(node_space.values.count(), 1)

                elif matrix_filter.filter_type == 'ColorFilter':
                    self.assertEqual(node_space.values.count(), 1)

                elif matrix_filter.filter_type == 'NumberFilter':
                    self.assertEqual(node_space.encoded_space, [2.0, 3.0])

                else:
                    raise ValueError('Invalid filter: {0}'.format(matrix_filter.filter_type))

        
        # test removal of spaces
        view_2 = self.get_view()
        view_2.set_node(**view_2.kwargs)
        
        data_2 = self.get_nodelink_form_data(**view_2.get_initial())

        dtai_filter = MatrixFilter.objects.get(meta_node=self.start_node.meta_node,
                                                  filter_type='DescriptiveTextAndImagesFilter')

        old_space = NodeFilterSpace.objects.get(matrix_filter=dtai_filter, node=self.view_node)

        matrix_filter_post_data_2 = {}
        new_space = dtai_filter.get_space()[1]

        old_encoded_space = old_space.values.first().encoded_space
        new_encoded_space = new_space.encoded_space
        self.assertTrue(old_encoded_space != new_encoded_space)
        
        matrix_filter_post_data_2[str(dtai_filter.uuid)] = [new_space.id]

        data_2.update(matrix_filter_post_data_2)

        form_2 = ManageNodelinkForm(view.parent_node, data=data_2, from_url=view.request.path)

        form_2.is_valid()
        self.assertEqual(form_2.errors, {})

        response_2 = view_2.form_valid(form_2)
        self.assertEqual(response_2.status_code, 200)

        for matrix_filter in matrix_filters:

            if matrix_filter.filter_type != 'TaxonFilter':
                
                node_space = NodeFilterSpace.objects.filter(matrix_filter=matrix_filter, node=self.view_node)


                if matrix_filter.filter_type == 'DescriptiveTextAndImagesFilter':

                    space = node_space.first()
                    self.assertEqual(space.values.first(), new_space)
                    self.assertEqual(space.values.count(), 1)

                else:
                    self.assertFalse(node_space.exists())



class TestDeleteNodelink(WithNatureGuideLink, ViewTestMixin, WithAjaxAdminOnly, WithUser, WithLoggedInUser,
                         WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'delete_nodelink'
    view_class = DeleteNodelink


    def setUp(self):
        super().setUp()

        self.nodes = []
        self.create_nodes()
        self.view_node = self.nodes[0]


    def get_url_kwargs(self):
        url_kwargs = {
            'parent_node_id' : self.start_node.id,
            'child_node_id' : self.view_node.id,
        }
        return url_kwargs
    

    @test_settings
    def test_set_node(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        self.assertEqual(view.model, NatureGuidesTaxonTree)
        self.assertEqual(view.node, self.view_node)
        self.assertEqual(view.child, self.view_node)
        self.assertEqual(view.crosslink, None)
        

    @test_settings
    def test_get_verbose_name(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        verbose_name = view.get_verbose_name()
        self.assertEqual(verbose_name, self.view_node.name)


    @test_settings
    def test_get_object(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        obj = view.get_object()
        self.assertEqual(obj, self.view_node)
        

    @test_settings
    def test_get_deletion_message(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        message = view.get_deletion_message()

    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.set_node(**view.kwargs)
        view.object = view.get_object()

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['crosslink'], None)
        self.assertEqual(context['node'], self.view_node)
        self.assertEqual(context['deleted_object_child_uuid'], str(self.view_node.name_uuid))
        self.assertIn('deletion_message', context)
        

    @test_settings
    def test_delete(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        response = view.delete(view.request, **view.kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['deleted_object_id'], self.view_node.id)
        self.assertEqual(response.context_data['deleted'], True)

        qry = NatureGuidesTaxonTree.objects.filter(pk=self.view_node.id)
        self.assertFalse(qry.exists())



class TestDeleteCrosslink(WithNatureGuideLink, ViewTestMixin, WithAjaxAdminOnly, WithUser, WithLoggedInUser,
                         WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'delete_nodelink'
    view_class = DeleteNodelink


    def setUp(self):
        super().setUp()

        self.nodes = []
        self.create_nodes()
        
        self.crosslink = NatureGuideCrosslinks.objects.get(child=self.nodes[1])


    def get_url_kwargs(self):
        url_kwargs = {
            'parent_node_id' : self.crosslink.parent.id,
            'child_node_id' : self.crosslink.child.id,
        }
        return url_kwargs
    

    @test_settings
    def test_set_node(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        self.assertEqual(view.model, NatureGuideCrosslinks)
        self.assertEqual(view.node, None)
        self.assertEqual(view.child, self.crosslink.child)
        self.assertEqual(view.crosslink, self.crosslink)


    @test_settings
    def test_get_object(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        obj = view.get_object()
        self.assertEqual(obj, self.crosslink)


    @test_settings
    def test_get_deletion_message(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        message = view.get_deletion_message()


    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.set_node(**view.kwargs)
        view.object = view.get_object()

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['crosslink'], self.crosslink)
        self.assertEqual(context['node'], None)
        self.assertEqual(context['deleted_object_child_uuid'], str(self.crosslink.child.name_uuid))
        self.assertIn('deletion_message', context)
        

    @test_settings
    def test_delete(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        response = view.delete(view.request, **view.kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['deleted_object_id'], self.crosslink.id)
        self.assertEqual(response.context_data['deleted'], True)

        qry = NatureGuideCrosslinks.objects.filter(pk=self.crosslink.id)
        self.assertFalse(qry.exists())

    
class TestAddExistingNodes(WithNatureGuideLink, ViewTestMixin, WithAjaxAdminOnly, WithUser, WithLoggedInUser,
                         WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'add_existing_nodes'
    view_class = AddExistingNodes


    def setUp(self):
        super().setUp()

        self.nodes = []
        self.create_nodes(create_crosslink=False)

        # child of first child of root
        self.view_node = self.child_node
        self.lower_child = self.create_node(self.view_node, 'Lower child')
        

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'parent_node_id' : self.view_node.id,
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view(ajax=True)
        view.meta_app = self.meta_app
        view.parent_node = self.view_node

        return view


    @test_settings
    def test_get_queryset(self):

        view = self.get_view()

        queryset = view.get_queryset()
        self.assertEqual(queryset.count(), 2)
        allowed_node_ids = set([node.id for node in queryset])
        expected_node_ids = set([self.nodes[0].id, self.nodes[1].id])
        self.assertEqual(allowed_node_ids, expected_node_ids)
        

    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['parent_node'], self.view_node)
        self.assertEqual(context['content_type'], self.content_type)
        nodes = list(context['nodes'].values_list('id', flat=True))
        self.assertEqual(nodes, [self.nodes[0].id, self.nodes[1].id])


    @test_settings
    def test_get(self):

        view = self.get_view()

        self.assertTrue(view.request.is_ajax())
        response = view.get(view.request, **view.kwargs)
        self.assertEqual(response.status_code, 200)


    @test_settings
    def test_post(self):

        view = self.get_view()

        # this is the parent node and thus would result in a crosslink
        view.request.POST = QueryDict('node={0}'.format(self.nodes[0].id))

        response = view.post(view.request, **view.kwargs)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['is_circular'], True)
        self.assertEqual(response.context_data['added_children'], [])
        self.assertEqual(response.context_data['success'], False)

        # allowed node
        allowed_node = self.nodes[1]
        view.request.POST = QueryDict('node={0}'.format(allowed_node.id))

        response = view.post(view.request, **view.kwargs)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['is_circular'], False)
        self.assertEqual(response.context_data['added_children'], [allowed_node])
        self.assertEqual(response.context_data['success'], True)

    

class TestLoadKeyNodes(WithNatureGuideLink, ViewTestMixin, WithAjaxAdminOnly, WithUser, WithLoggedInUser,
                   WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'load_keynodes'
    view_class = LoadKeyNodes


    def setUp(self):
        super().setUp()

        self.nodes = []
        self.create_nodes()


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view
        

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'parent_node_id' : self.start_node.id,
        }
        return url_kwargs


    @test_settings
    def test_get_context_data(self):

        view = self.get_view()

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['content_type'], self.content_type)
        self.assertEqual(context['parent_node'], self.start_node)


class TestStoreNodeOrder(WithNatureGuideLink, ViewTestMixin, WithAjaxAdminOnly, WithUser, WithLoggedInUser,
                   WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'store_node_order'
    view_class = StoreNodeOrder
    

    def setUp(self):
        super().setUp()

        self.nodes = []
        self.create_nodes(create_crosslink=False)


    @test_settings
    def test_dispatch(self):
        pass


    def get_url_kwargs(self):
        url_kwargs = {
            'parent_node_id' : self.start_node.id,
        }
        return url_kwargs
        

    @test_settings
    def test_get_save_args(self):

        view = self.get_view(ajax=True)

        save_args = view.get_save_args(self.nodes[0])
        self.assertEqual(save_args, [self.start_node])
        

    @test_settings
    def test_post(self):

        view = self.get_view(ajax=True)

        node_1 = self.nodes[0]
        node_2 = self.nodes[1]

        node_2.position = 2
        node_2.save(self.start_node)

        self.assertEqual(node_1.position, 1)
        self.assertEqual(node_2.position, 2)

        post_data = {
            'order' : json.dumps([node_2.id, node_1.id]),
        }

        view.request.POST = post_data

        response = view.post(view.request, **view.kwargs)
        self.assertEqual(response.status_code, 200)

        node_1.refresh_from_db()
        node_2.refresh_from_db()

        self.assertEqual(node_1.position, 2)
        self.assertEqual(node_2.position, 1)


class TestStoreNodeOrderCrosslink(WithNatureGuideLink, ViewTestMixin, WithAjaxAdminOnly, WithUser,
                    WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'store_node_order'
    view_class = StoreNodeOrder
    

    def setUp(self):
        super().setUp()

        self.nodes = []
        self.create_nodes()

        self.view_node = self.child_node
        self.lower_child = self.create_node(self.view_node, 'Lower child')
        self.crosslink.position = 2
        self.crosslink.save()


    def get_url_kwargs(self):
        url_kwargs = {
            'parent_node_id' : self.child_node.id,
        }
        return url_kwargs


    @test_settings
    def test_dispatch(self):
        pass
        

    @test_settings
    def test_post(self):

        view = self.get_view(ajax=True)

        self.assertEqual(self.lower_child.position, 1)
        self.assertEqual(self.crosslink.position, 2)

        post_data = {
            'order' : json.dumps([self.crosslink.child.id, self.lower_child.id]),
        }

        view.request.POST = post_data

        response = view.post(view.request, **view.kwargs)
        self.assertEqual(response.status_code, 200)

        self.crosslink.refresh_from_db()
        self.lower_child.refresh_from_db()

        self.assertEqual(self.lower_child.position, 2)
        self.assertEqual(self.crosslink.position, 1)



class TestLoadNodeManagementMenu(WithNatureGuideLink, ViewTestMixin, WithAjaxAdminOnly, WithUser,
                    WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):


    url_name = 'load_nodemenu'
    view_class = LoadNodeManagementMenu


    def setUp(self):
        super().setUp()

        self.nodes = []
        self.create_nodes()

        self.view_node = self.nodes[0]
        self.parent_node = self.start_node


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'parent_node_id' : self.parent_node.id,
            'node_id' : self.view_node.id,
        }
        return url_kwargs


    @test_settings
    def test_set_node(self):

        view = self.get_view()
        view.set_node(**view.kwargs)
        self.assertEqual(view.node, self.view_node)
        self.assertEqual(view.parent_node, self.parent_node)
        self.assertEqual(view.content_type, self.content_type)
        
    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_node(**view.kwargs)

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['node'], self.view_node)
        self.assertEqual(context['parent_node'], self.parent_node)
        self.assertEqual(context['content_type'], self.content_type)


class TestSearchForNode(WithNatureGuideLink, ViewTestMixin, WithAjaxAdminOnly, WithUser,
                    WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):


    url_name = 'search_for_node'
    view_class = SearchForNode


    def setUp(self):
        super().setUp()

        self.nodes = []
        self.create_nodes()


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'nature_guide_id' : self.generic_content.id,
        }
        return url_kwargs


    @test_settings
    def test_get(self):

        view = self.get_view(ajax=True)
        view.meta_app=self.meta_app

        view.request.GET = {
            'name' : 'NoDe',
        }

        response = view.get(view.request, **view.kwargs)
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content)

        self.assertEqual(len(content), 2)

        names = set([choice['name'] for choice in content])
        self.assertEqual(names, set(['node 1', 'node 2']))
    


class TestLoadMatrixFilters(WithNatureGuideLink, ViewTestMixin, WithAjaxAdminOnly, WithUser, WithMatrixFilters,
                    WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):


    url_name = 'load_matrix_filters'
    view_class = LoadMatrixFilters


    def setUp(self):
        super().setUp()

        self.nodes = []
        self.create_nodes()
        self.create_all_matrix_filters(self.start_node)
        self.fill_matrix_filters_nodes(self.start_node, self.nodes)
        

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_node_id' : self.start_node.meta_node.id,
        }
        return url_kwargs

    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        view.meta_node = self.start_node.meta_node

        matrix_filter_type = ContentType.objects.get_for_model(MatrixFilter)

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['form'].__class__, IdentificationMatrixForm)
        self.assertEqual(context['meta_node'], self.start_node.meta_node)
        self.assertEqual(context['meta_node_has_matrix_filters'], True)
        self.assertEqual(context['matrix_filter_ctype'], matrix_filter_type)
        self.assertEqual(context['matrix_filter_types'], MATRIX_FILTER_TYPES)



class ManageMatrixFilterCommon:

    def setUp(self):
        super().setUp()

        self.nodes = []
        self.create_nodes()

        self.view_node = self.start_node

        self.make_user_tenant_admin(self.user, self.tenant)


    def get_url_kwargs(self, filter_type):
        url_kwargs = {
            'meta_node_id' : self.view_node.meta_node.id,
            'filter_type' : filter_type,
        }
        return url_kwargs
    

    def get_url(self, filter_type):
        url_kwargs = self.get_url_kwargs(filter_type)
        url = reverse(self.url_name, kwargs=url_kwargs)
        
        return url

    def get_request(self, filter_type):
        factory = RequestFactory()
        url = self.get_url(filter_type)

        url_kwargs = {
            'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
        }
        request = factory.get(url, **url_kwargs)
        
        request.user = self.user
        request.session = self.client.session
        request.tenant = self.tenant

        return request


    def get_view(self, filter_type):

        request = self.get_request(filter_type)

        view = self.view_class()        
        view.request = request
        view.kwargs = self.get_url_kwargs(filter_type)

        return view


    def get_post_data(self, filter_type):
        
        post_data = {
            'input_language' : self.generic_content.primary_language,
            'name' : '{0} filter'.format(filter_type),
            'filter_type' : filter_type,
        }

        if filter_type in ['RangeFilter', 'NumberFilter']:
            post_data.update({
                'unit' : 'cm',
                'unit_verbose' : 'centimeters',
            })


        if filter_type == 'RangeFilter':
            post_data.update({
                'min_value' : 1,
                'max_value' : 4,
                'step' : 0.5,
            })


        if filter_type == 'NumberFilter':
            post_data.update({
                'numbers' : '1,2,3,4,5',
            })


        return post_data
    
    
class TestCreateMatrixFilter(ManageMatrixFilterCommon, WithNatureGuideLink, WithUser, WithMatrixFilters,
                             WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):


    url_name = 'create_matrix_filter'
    view_class = ManageMatrixFilter
    

    @test_settings
    def test_get(self):

        for tup in MATRIX_FILTER_TYPES:

            filter_type = tup[0]

            url = self.get_url(filter_type)

            get_kwargs = {
                'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
            }

            response = self.tenant_client.get(url, **get_kwargs)
            self.assertEqual(response.status_code, 200)


    @test_settings
    def test_set_matrix_filter(self):

        for tup in MATRIX_FILTER_TYPES:

            filter_type = tup[0]

            view = self.get_view(filter_type)

            view.set_matrix_filter(**view.kwargs)
            self.assertEqual(view.matrix_filter, None)
            self.assertEqual(view.meta_node, self.start_node.meta_node)
            self.assertEqual(view.filter_type, filter_type)
            

    @test_settings
    def test_set_primary_language(self):

        for tup in MATRIX_FILTER_TYPES:

            filter_type = tup[0]

            view = self.get_view(filter_type)

            view.set_matrix_filter(**view.kwargs)
            view.set_primary_language()
            self.assertEqual(view.primary_language, self.generic_content.primary_language)
            

    @test_settings
    def test_get_form_class(self):

        for tup in MATRIX_FILTER_TYPES:

            filter_type = tup[0]

            view = self.get_view(filter_type)
            view.set_matrix_filter(**view.kwargs)
            view.set_primary_language()

            form_class = view.get_form_class()

            self.assertEqual(form_class.__name__, '{0}ManagementForm'.format(filter_type))
            

    @test_settings
    def test_get_form(self):
        
        for tup in MATRIX_FILTER_TYPES:

            filter_type = tup[0]

            view = self.get_view(filter_type)
            view.set_matrix_filter(**view.kwargs)
            view.set_primary_language()

            form = view.get_form()

            self.assertEqual(form.__class__.__name__,  '{0}ManagementForm'.format(filter_type))
            

    @test_settings
    def test_get_initial(self):

        for tup in MATRIX_FILTER_TYPES:

            filter_type = tup[0]

            view = self.get_view(filter_type)
            view.set_matrix_filter(**view.kwargs)
            view.set_primary_language()

            initial = view.get_initial()
            self.assertEqual(initial['filter_type'], filter_type)
            self.assertFalse('matrix_filter_id' in initial)
            self.assertFalse('name' in initial)


    @test_settings
    def test_get_context_data(self):

        for tup in MATRIX_FILTER_TYPES:

            filter_type = tup[0]

            view = self.get_view(filter_type)
            view.set_matrix_filter(**view.kwargs)
            view.set_primary_language()

            context = view.get_context_data(**view.kwargs)

            self.assertEqual(context['meta_node'], self.start_node.meta_node)
            self.assertEqual(context['filter_type'], filter_type)
            self.assertEqual(context['matrix_filter'], None)
            self.assertIn('verbose_filter_name', context)
            

    @test_settings
    def test_set_definition(self):
        # tested in TestManage...
        pass

    @test_settings
    def test_save_encoded_space(self):
        # tested in TestManage...
        pass


    @test_settings
    def test_form_valid(self):

        for tup in MATRIX_FILTER_TYPES:

            filter_type = tup[0]

            view = self.get_view(filter_type)
            view.set_matrix_filter(**view.kwargs)
            view.set_primary_language()

            post_data = self.get_post_data(filter_type)

            form_kwargs = view.get_form_kwargs()
            form_kwargs['data'] = post_data
            form_class = view.get_form_class()
            form = form_class(self.view_node.meta_node, None, **form_kwargs)

            form.is_valid()
            self.assertEqual(form.errors, {})

            response = view.form_valid(form)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context_data['success'], True)
            created_matrix_filter = MatrixFilter.objects.all().last()
            self.assertEqual(created_matrix_filter.name, post_data['name'])
            self.assertEqual(created_matrix_filter.filter_type, filter_type)

            if filter_type in ['RangeFilter', 'NumberFilter']:

                self.assertEqual(created_matrix_filter.definition['unit'], 'cm')
                self.assertEqual(created_matrix_filter.definition['unit_verbose'], 'centimeters')

            if filter_type == 'RangeFilter':
                space = created_matrix_filter.get_space()[0]
                self.assertEqual(space.encoded_space, [1,4])

            elif filter_type == 'NumberFilter':
                space = created_matrix_filter.get_space()[0]
                self.assertEqual(space.encoded_space, [1,2,3,4,5])



class TestManageMatrixFilter(ManageMatrixFilterCommon,  WithNatureGuideLink, WithUser, WithMatrixFilters,
                             WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):


    url_name = 'manage_matrix_filter'
    view_class = ManageMatrixFilter


    def setUp(self):
        super().setUp()

        self.matrix_filters = self.create_all_matrix_filters(self.start_node)

        self.view_node = self.start_node


    def get_url_kwargs(self, matrix_filter):
        url_kwargs = {
            'matrix_filter_id' : matrix_filter.id,
        }
        return url_kwargs


    @test_settings
    def test_get(self):

        for matrix_filter in self.matrix_filters:

            url = self.get_url(matrix_filter)

            get_kwargs = {
                'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
            }

            response = self.tenant_client.get(url, **get_kwargs)
            self.assertEqual(response.status_code, 200)


    @test_settings
    def test_set_matrix_filter(self):

        for matrix_filter in self.matrix_filters:

            view = self.get_view(matrix_filter)
            view.set_matrix_filter(**view.kwargs)

            self.assertEqual(view.matrix_filter, matrix_filter)
            self.assertEqual(view.meta_node, self.view_node.meta_node)
            self.assertEqual(view.filter_type, matrix_filter.filter_type)


    @test_settings
    def test_get_form(self):

        for matrix_filter in self.matrix_filters:

            view = self.get_view(matrix_filter)

            view.set_matrix_filter(**view.kwargs)
            view.set_primary_language()

            form = view.get_form()

            self.assertEqual(form.__class__.__name__,  '{0}ManagementForm'.format(matrix_filter.filter_type))


    @test_settings
    def test_get_initial(self):

        for matrix_filter in self.matrix_filters:

            view = self.get_view(matrix_filter)

            view.set_matrix_filter(**view.kwargs)
            view.set_primary_language()

            initial = view.get_initial()
            self.assertEqual(initial['matrix_filter_id'], matrix_filter.id)
            self.assertEqual(initial['filter_type'], matrix_filter.filter_type)
            self.assertEqual(initial['name'], matrix_filter.name)

            if matrix_filter.filter_type in ['RangeFilter', 'NumberFilter']:

                self.assertEqual(initial['unit'], matrix_filter.definition['unit'])
                self.assertEqual(initial['unit_verbose'], matrix_filter.definition['unit_verbose'])

                if matrix_filter.filter_type == 'RangeFilter':
                    self.assertEqual(initial['min_value'], 4)
                    self.assertEqual(initial['max_value'], 7)
            

    @test_settings
    def test_get_context_data(self):

        for matrix_filter in self.matrix_filters:

            view = self.get_view(matrix_filter)

            view.set_matrix_filter(**view.kwargs)
            view.set_primary_language()

            context = view.get_context_data(**view.kwargs)

            self.assertEqual(context['meta_node'], self.view_node.meta_node)
            self.assertEqual(context['filter_type'], matrix_filter.filter_type)
            self.assertEqual(context['matrix_filter'], matrix_filter)
            self.assertIn('verbose_filter_name', context)
            
            

    @test_settings
    def test_set_definition(self):

        for matrix_filter in self.matrix_filters:

            view = self.get_view(matrix_filter)
            view.set_matrix_filter(**view.kwargs)
            view.set_primary_language()

            post_data = self.get_post_data(matrix_filter.filter_type)

            form_kwargs = view.get_form_kwargs()
            form_kwargs['data'] = post_data
            form_class = view.get_form_class()
            form = form_class(self.view_node.meta_node, matrix_filter, **form_kwargs)

            form.is_valid()
            self.assertEqual(form.errors, {})

            view.set_definition(form, matrix_filter)

            if matrix_filter.filter_type in ['RangeFilter', 'NumberFilter']:

                self.assertEqual(matrix_filter.definition['unit'], post_data['unit'])
                self.assertEqual(matrix_filter.definition['unit_verbose'], post_data['unit_verbose'])


    @test_settings
    def test_save_encoded_space(self):

        for matrix_filter in self.matrix_filters:

            view = self.get_view(matrix_filter)
            view.set_matrix_filter(**view.kwargs)
            view.set_primary_language()

            post_data = self.get_post_data(matrix_filter.filter_type)

            form_kwargs = view.get_form_kwargs()
            form_kwargs['data'] = post_data
            form_class = view.get_form_class()
            form = form_class(self.view_node.meta_node, matrix_filter, **form_kwargs)

            form.is_valid()
            self.assertEqual(form.errors, {})

            view.save_encoded_space(form, matrix_filter)

            if matrix_filter.filter_type in ['RangeFilter', 'NumberFilter']:

                space = matrix_filter.get_space()[0]

                if matrix_filter.filter_type == 'RangeFilter':
                    self.assertEqual(space.encoded_space, [1,4])

                elif matrix_filter.filter_type == 'NumberFilter':
                    self.assertEqual(space.encoded_space, [1,2,3,4,5])


    @test_settings
    def test_form_valid(self):

        for matrix_filter in self.matrix_filters:

            view = self.get_view(matrix_filter)
            view.set_matrix_filter(**view.kwargs)
            view.set_primary_language()

            post_data = self.get_post_data(matrix_filter.filter_type)

            form_kwargs = view.get_form_kwargs()
            form_kwargs['data'] = post_data
            form_class = view.get_form_class()
            form = form_class(self.view_node.meta_node, matrix_filter, **form_kwargs)

            form.is_valid()
            self.assertEqual(form.errors, {})

            response = view.form_valid(form)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context_data['success'], True)
            



class ManageMatrixFilterSpaceCommon:


    def setUp(self):
        super().setUp()

        self.nodes = []
        self.create_nodes()

        self.view_node = self.start_node

        self.make_user_tenant_admin(self.user, self.tenant)

        self.matrix_filters = self.create_all_matrix_filters(self.view_node)


    def create_matrix_filter_spaces(self):
        
        self.image_store = self.create_image_store()

        # set licence
        licence_kwargs = {
            'creator_name' : 'Bond',
        }
        
        ContentLicenceRegistry.objects.register(self.image_store, 'source_image', self.user, 'CC0', '1.0',
                                        **licence_kwargs)

        self.spaces = {}

        for matrix_filter in self.matrix_filters:

            if matrix_filter.filter_type == 'DescriptiveTextAndImagesFilter':

                space = MatrixFilterSpace(
                    matrix_filter=matrix_filter,
                    encoded_space='Test space',
                )

                space.save()


                self.content_image = ContentImage(
                    content_type = ContentType.objects.get_for_model(space),
                    object_id = space.id,
                    image_store = self.image_store,
                )

                self.content_image.save()

                self.spaces[matrix_filter.filter_type] = space


            elif matrix_filter.filter_type == 'ColorFilter':

                space = MatrixFilterSpace(
                    matrix_filter=matrix_filter,
                    encoded_space=[0,0,0,1],
                )

                space.save()

                self.spaces[matrix_filter.filter_type] = space


    def get_url(self, matrix_filter):
        url_kwargs = self.get_url_kwargs(matrix_filter)
        url = reverse(self.url_name, kwargs=url_kwargs)
        
        return url


    def get_url_kwargs(self, matrix_filter):
        url_kwargs = {
            'matrix_filter_id' : matrix_filter.id,
        }
        return url_kwargs
    

    def get_request(self, matrix_filter):
        factory = RequestFactory()
        url = self.get_url(matrix_filter)

        url_kwargs = {
            'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
        }
        request = factory.get(url, **url_kwargs)
        
        request.user = self.user
        request.session = self.client.session
        request.tenant = self.tenant

        return request


    def get_view(self, matrix_filter):

        request = self.get_request(matrix_filter)

        view = self.view_class()        
        view.request = request
        view.kwargs = self.get_url_kwargs(matrix_filter)

        return view


    def get_post_data(self, matrix_filter, source_image=True):

        post_data = {
            'input_language' : self.generic_content.primary_language,
        }

        if matrix_filter.filter_type == 'DescriptiveTextAndImagesFilter':
        
            post_data.update({
                'text' : 'test text',
            })

            if source_image == True:
                post_data.update({
                    'source_image' : self.get_image(),
                })

                post_data.update(self.get_licencing_post_data())

        elif matrix_filter.filter_type == 'ColorFilter':
            post_data.update({
                'color' : '#ff00ff',
            })

        return post_data
    
    
class TestCreateMatrixFilterSpace(ManageMatrixFilterSpaceCommon, WithFormTest, WithNatureGuideLink, WithUser,
                WithMedia, WithMatrixFilters, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):


    url_name = 'create_matrix_filter_space'
    view_class = ManageMatrixFilterSpace


    @test_settings
    def test_get(self):

        for matrix_filter in self.matrix_filters:

            if matrix_filter.filter_type in ['DescriptiveTextAndImagesFilter', 'ColorFilter']:

                url = self.get_url(matrix_filter)

                get_kwargs = {
                    'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
                }

                response = self.tenant_client.get(url, **get_kwargs)
                self.assertEqual(response.status_code, 200)
    

    @test_settings
    def test_set_space(self):

        for matrix_filter in self.matrix_filters:

            if matrix_filter.filter_type in ['DescriptiveTextAndImagesFilter', 'ColorFilter']:

                view = self.get_view(matrix_filter)

                view.set_space(**view.kwargs)

                ctype = ContentType.objects.get_for_model(MatrixFilterSpace)
                self.assertEqual(view.object_content_type, ctype)
                self.assertEqual(view.matrix_filter_space, None)
                self.assertEqual(view.matrix_filter, matrix_filter)
                self.assertEqual(view.content_image, None)
                self.assertEqual(view.content_instance, None)
                self.assertEqual(view.image_type, None)
                self.assertEqual(view.licence_registry_entry, None)


    @test_settings
    def test_set_primary_language(self):

        for matrix_filter in self.matrix_filters:

            if matrix_filter.filter_type in ['DescriptiveTextAndImagesFilter', 'ColorFilter']:

                view = self.get_view(matrix_filter)

                view.set_space(**view.kwargs)

                view.set_primary_language()
                self.assertEqual(view.primary_language, self.generic_content.primary_language)
                

    @test_settings
    def test_get_form_class(self):
        for matrix_filter in self.matrix_filters:

            if matrix_filter.filter_type in ['DescriptiveTextAndImagesFilter', 'ColorFilter']:

                view = self.get_view(matrix_filter)
                view.set_space(**view.kwargs)
                view.set_primary_language()

                form_class = view.get_form_class()
                self.assertEqual(form_class.__name__, '{0}SpaceForm'.format(matrix_filter.filter_type))

    @test_settings
    def test_get_context_data(self):

        for matrix_filter in self.matrix_filters:

            if matrix_filter.filter_type in ['DescriptiveTextAndImagesFilter', 'ColorFilter']:

                view = self.get_view(matrix_filter)
                view.set_space(**view.kwargs)
                view.set_primary_language()

                context = view.get_context_data(**view.kwargs)
                self.assertEqual(context['matrix_filter'], matrix_filter)
                self.assertEqual(context['matrix_filter_space'], None)
                self.assertEqual(context['meta_node'], self.view_node.meta_node)
                self.assertIn('from_url', context)


    @test_settings
    def test_get_initial(self):

        for matrix_filter in self.matrix_filters:

            if matrix_filter.filter_type in ['DescriptiveTextAndImagesFilter', 'ColorFilter']:

                view = self.get_view(matrix_filter)
                view.set_space(**view.kwargs)
                view.set_primary_language()

                initial = view.get_initial()
                self.assertFalse('matrix_filter_space_id' in initial)
                

    @test_settings
    def test_form_valid(self):

        for matrix_filter in self.matrix_filters:

            if matrix_filter.filter_type in ['DescriptiveTextAndImagesFilter', 'ColorFilter']:

                view = self.get_view(matrix_filter)
                view.set_space(**view.kwargs)
                view.set_primary_language()

                post_data = self.get_post_data(matrix_filter)

                form_kwargs = view.get_form_kwargs()
                form_kwargs['data'] = post_data
                form_class = view.get_form_class()
                form = form_class(**form_kwargs)

                form.is_valid()
                self.assertEqual(form.errors, {})

                response = view.form_valid(form)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context_data['success'], True)

                created_space = MatrixFilterSpace.objects.filter(matrix_filter=matrix_filter).last()
                self.assertEqual(created_space.matrix_filter, matrix_filter)



class TestManageMatrixFilterSpace(ManageMatrixFilterSpaceCommon, WithFormTest, WithNatureGuideLink, WithUser,
        WithImageStore, WithMedia, WithMatrixFilters, WithLoggedInUser, WithMetaApp, WithTenantClient,
        TenantTestCase):


    url_name = 'manage_matrix_filter_space'
    view_class = ManageMatrixFilterSpace


    def setUp(self):
        super().setUp()


    def get_url_kwargs(self, space):
        url_kwargs = {
            'space_id' : space.id,
        }
        return url_kwargs
    

    @test_settings
    def test_get(self):

        self.create_matrix_filter_spaces()

        for filter_type, space in self.spaces.items():

            url = self.get_url(space)

            get_kwargs = {
                'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
            }

            response = self.tenant_client.get(url, **get_kwargs)
            self.assertEqual(response.status_code, 200)


    @test_settings
    def test_set_space(self):

        self.create_matrix_filter_spaces()

        for filter_type, space in self.spaces.items():

            view = self.get_view(space)
            view.set_space(**view.kwargs)
            self.assertEqual(view.matrix_filter_space, space)
            self.assertEqual(view.matrix_filter, space.matrix_filter)

            if filter_type == 'DescriptiveTextAndImagesFilter':
                self.assertEqual(view.content_image, self.content_image)
                self.assertEqual(view.content_instance, space)
                self.assertEqual(view.image_type, 'image')
                self.assertTrue(view.licence_registry_entry != None)


    @test_settings
    def test_get_initial(self):

        self.create_matrix_filter_spaces()

        for filter_type, space in self.spaces.items():

            view = self.get_view(space)
            view.set_space(**view.kwargs)
            view.set_primary_language()
            
            initial = view.get_initial()
            self.assertEqual(initial['matrix_filter_space_id'], space.id)

            if filter_type == 'DescriptiveTextAndImagesFilter':
                self.assertEqual(initial['text'], space.encoded_space)

            elif filter_type == 'ColorFilter':
                self.assertEqual(initial['color'], '#000000')

    @test_settings
    def test_form_valid(self):

        self.create_matrix_filter_spaces()

        for filter_type, space in self.spaces.items():

            old_encoded_space = space.encoded_space

            view = self.get_view(space)
            view.set_space(**view.kwargs)
            view.set_primary_language()

            post_data = self.get_post_data(space.matrix_filter, source_image=False)
            self.assertFalse('source_image' in post_data)
            post_data['matrix_filter_space_id'] = space.id

            form_kwargs = view.get_form_kwargs()
            form_class = view.get_form_class()
            form = form_class(data=post_data)

            form.is_valid()
            self.assertEqual(form.errors, {})

            response = view.form_valid(form)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context_data['success'], True)

            space.refresh_from_db()
            self.assertTrue(space.encoded_space != old_encoded_space)

            if filter_type == 'DescriptiveTextAndImagesFilter':
                self.assertEqual(space.encoded_space, post_data['text'])

            elif filter_type == 'ColorFilter':
                self.assertEqual(space.encoded_space, [255,0,255,1])



class TestDeleteMatrixFilterSpace(ManageMatrixFilterSpaceCommon, WithFormTest, WithNatureGuideLink, WithUser,
        WithImageStore, WithMedia, WithMatrixFilters, WithLoggedInUser, WithMetaApp, WithTenantClient,
        TenantTestCase):

    url_name = 'delete_matrix_filter_space'
    view_class = DeleteMatrixFilterSpace


    def setUp(self):
        super().setUp()

    def get_url_kwargs(self, space):
        url_kwargs = {
            'pk' : space.id,
        }
        return url_kwargs


    @test_settings
    def test_verbose_name(self):

        self.create_matrix_filter_spaces()

        for filter_type, space in self.spaces.items():

            view = self.get_view(space)
            view.object = view.get_object()

            name = view.get_verbose_name()
            self.assertEqual(name, space)


    @test_settings
    def test_delete(self):

        self.create_matrix_filter_spaces()

        for filter_type, space in self.spaces.items():

            meta_node = space.matrix_filter.meta_node
            
            space_id = space.pk
            qry = MatrixFilterSpace.objects.filter(pk=space_id)

            view = self.get_view(space)

            self.assertTrue(qry.exists())

            response = view.delete(view.request, **view.kwargs)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context_data['meta_node'], meta_node)
            self.assertEqual(response.context_data['deleted'], True)

            self.assertFalse(qry.exists())

            
        
class TestNodeAnalysis(WithNatureGuideLink, WithAdminOnly, ViewTestMixin, WithUser, WithLoggedInUser,
                        WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'node_analysis'
    view_class = NodeAnalysis


    def setUp(self):
        super().setUp()
        self.nodes = []
        self.create_nodes()
        self.view_node  = self.nodes[1]

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'meta_node_id' : self.view_node.meta_node.id,
        }
        return url_kwargs


    @test_settings
    def test_set_node(self):
        
        view = self.get_view()
        view.set_node(**view.kwargs)

        self.assertEqual(view.meta_node, self.view_node.meta_node)
        self.assertEqual(len(view.nodelinks), 2)
        self.assertEqual(view.nodelinks[0], (self.start_node, self.view_node))
        self.assertEqual(view.nodelinks[1], (self.child_node, self.view_node))
        

    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.set_node(**view.kwargs)
        view.meta_app = self.meta_app

        context = view.get_context_data(**view.kwargs)

        self.assertEqual(context['meta_node'], self.view_node.meta_node)
        self.assertEqual(len(context['nodelinks']), 2)
        self.assertEqual(context['content_type'], self.content_type)
        self.assertEqual(context['is_analysis'], True)
        self.assertEqual(context['search_for_node_form'].__class__, SearchForNodeForm)
    


class TestGetIdentificationMatrix(WithNatureGuideLink, WithAjaxAdminOnly, ViewTestMixin, WithUser,
                            WithLoggedInUser, WithMatrixFilters, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'get_identification_matrix'
    view_name = GetIdentificationMatrix


    def setUp(self):
        super().setUp()

        self.nodes = []
        self.create_nodes()

        self.view_node = self.start_node

        self.matrix_filters = self.create_all_matrix_filters(self.view_node)


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_node_id' : self.view_node.meta_node.id,
        }
        return url_kwargs
