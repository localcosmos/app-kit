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
        NodeAnalysis, GetIdentificationMatrix, MoveNatureGuideNode, SearchMoveToGroup,
        ManageMatrixFilterRestrictions, CopyTreeBranch, ManageAdditionalMatrixFilterSpaceImage,
        DeleteAdditionalMatrixFilterSpaceImage)


from app_kit.features.nature_guides.models import (NatureGuide, NatureGuidesTaxonTree, NatureGuideCrosslinks,
                MetaNode, MatrixFilter, NodeFilterSpace, MatrixFilterSpace, MatrixFilterRestriction)

from app_kit.features.nature_guides.forms import (NatureGuideOptionsForm, SearchForNodeForm, MoveNodeForm,
                        IdentificationMatrixForm, ManageNodelinkForm, ManageMatrixFilterRestrictionsForm,
                        CopyTreeBranchForm)


from app_kit.features.nature_guides.tests.common import WithNatureGuide, WithMatrixFilters

from app_kit.features.nature_guides.matrix_filters import MATRIX_FILTER_TYPES

from content_licencing.models import ContentLicenceRegistry


from taxonomy.lazy import LazyTaxon
from taxonomy.models import TaxonomyModelRouter

from app_kit.multi_tenancy.models import TenantUserRole

from app_kit.tests.test_views import ContentImagePostData

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
        self.assertEqual(view.submitted_parent_node, self.start_node)
        self.assertEqual(view.tree_parent_node, self.start_node)
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

        form = ManageNodelinkForm(self.meta_app, view.submitted_parent_node, view.submitted_parent_node, data=data,
                                  from_url=view.request.path)

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

        form = ManageNodelinkForm(self.meta_app, view.submitted_parent_node, view.submitted_parent_node, data=data,
                                  from_url=view.request.path)

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
            'parent_node_id' : self.view_node.parent.id,
            'node_id' : self.view_node.id,
        }
        return url_kwargs


    @test_settings
    def test_set_node(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        self.assertEqual(view.node, self.view_node)
        self.assertEqual(view.submitted_parent_node, self.start_node)
        self.assertEqual(view.tree_parent_node, self.start_node)
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

        form = ManageNodelinkForm(self.meta_app, view.submitted_parent_node, view.submitted_parent_node, data=data,
                                  from_url=view.request.path)

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

        form = ManageNodelinkForm(self.meta_app, view.submitted_parent_node, view.submitted_parent_node, data=data,
                                  from_url=view.request.path)

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

                elif matrix_filter.filter_type == 'TextOnlyFilter':
                    self.assertEqual(node_space.values.count(), 1)

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

        form_2 = ManageNodelinkForm(self.meta_app, view.submitted_parent_node, view.submitted_parent_node, data=data_2,
                                    from_url=view.request.path)

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


class TestManageNodelinkAsManageWithCrosslinkParent(WithNatureGuideLink, WithMatrixFilters, ViewTestMixin,
                WithAjaxAdminOnly, WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'manage_nodelink'
    view_class = ManageNodelink
    

    def setUp(self):
        super().setUp()

        self.nodes = []
        
        self.create_nodes()
        # crosslink:
        # parent=self.child_node,
        # child=self.nodes[1],
        self.matrix_filters = self.create_all_matrix_filters(self.child_node)

        self.view_node = self.nodes[1]
        self.submitted_parent_node = self.child_node
        self.tree_parent_node = self.view_node.parent

        self.assertTrue(self.submitted_parent_node != self.tree_parent_node)
        self.assertTrue(self.view_node.parent != self.submitted_parent_node)
        self.assertEqual(self.view_node.parent, self.tree_parent_node)


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app

        return view
    

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'parent_node_id' : self.submitted_parent_node.id,
            'node_id' : self.view_node.id,
        }
        return url_kwargs


    @test_settings
    def test_set_node_with_crosslink_parent(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        self.assertEqual(view.node, self.view_node)
        self.assertEqual(view.node_type, 'node')
        self.assertEqual(view.submitted_parent_node, self.submitted_parent_node)
        self.assertEqual(view.tree_parent_node, self.tree_parent_node)
        self.assertEqual(view.nature_guide, self.generic_content)

        
    @test_settings
    def test_get_initial_with_crosslink_parent(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        initial = view.get_initial()

        self.assertEqual(initial['node_type'], 'node')
        self.assertEqual(initial['name'], 'node 2')
        self.assertEqual(initial['decision_rule'], 'node 2 decision rule')
        self.assertEqual(initial['node_id'], self.view_node.id)
        self.assertEqual(initial['taxon'], None)
        self.assertEqual(initial['is_active'], True)
        

    @test_settings
    def test_get_context_data_with_crosslink_parent(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        context = view.get_context_data(**view.kwargs)

        self.assertEqual(context['node_type'], 'node')
        self.assertEqual(context['parent_node'], self.submitted_parent_node)
        self.assertEqual(context['node'], self.view_node)
        self.assertEqual(context['content_type'], ContentType.objects.get_for_model(self.generic_content))
        
    @test_settings
    def test_get_form_kwargs_with_crosslink_parent(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs['node'], self.view_node)
        self.assertIn('/app-kit/nature-guides/manage-natureguide-node/', form_kwargs['from_url'])
        
    @test_settings
    def test_get_form_with_crosslink_parent(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        form = view.get_form()
        self.assertEqual(form.submitted_parent_node, self.submitted_parent_node)
        self.assertEqual(form.tree_parent_node, self.tree_parent_node)
        
    @test_settings
    def test_save_nodelink_with_crosslink_parent(self):
        view = self.get_view()
        view.set_node(**view.kwargs)

        # does not contain matrix filters
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

        form = ManageNodelinkForm(self.meta_app, view.tree_parent_node, view.submitted_parent_node, data=data,
                                  from_url=view.request.path)

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
        
    # also covers matrix filters
    @test_settings
    def test_form_valid_with_crosslink_parent(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        data = self.get_nodelink_form_data(**view.get_initial())
        
        # update data with matrixfilter data
        matrix_filters_data = {}

        matrix_filters = MatrixFilter.objects.filter(meta_node=self.submitted_parent_node.meta_node)

        for matrix_filter in matrix_filters:

            matrix_filter_post_data = self.get_matrix_filter_post_data(matrix_filter)
            matrix_filters_data.update(matrix_filter_post_data)


        data.update(matrix_filters_data)

        form = ManageNodelinkForm(self.meta_app, view.tree_parent_node, view.submitted_parent_node, data=data,
                                  from_url=view.request.path)

        matrix_filter_field_count = 0
        for field in form:
            if getattr(field.field, 'matrix_filter', None) != None:
                matrix_filter_field_count += 1
                self.assertEqual(field.field.matrix_filter.meta_node, self.submitted_parent_node.meta_node)

        # -1, TaxonFilter is skipped
        self.assertEqual(matrix_filter_field_count, len(self.matrix_filters) - 1)

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

                elif matrix_filter.filter_type == 'TextOnlyFilter':
                    self.assertEqual(node_space.values.count(), 1)

                else:
                    raise ValueError('Invalid filter: {0}'.format(matrix_filter.filter_type))

        
        # test removal of spaces
        view_2 = self.get_view()
        view_2.set_node(**view_2.kwargs)
        
        data_2 = self.get_nodelink_form_data(**view_2.get_initial())

        dtai_filter = MatrixFilter.objects.get(meta_node=self.submitted_parent_node.meta_node,
                                                  filter_type='DescriptiveTextAndImagesFilter')

        old_space = NodeFilterSpace.objects.get(matrix_filter=dtai_filter, node=self.view_node)

        matrix_filter_post_data_2 = {}
        new_space = dtai_filter.get_space()[1]

        old_encoded_space = old_space.values.first().encoded_space
        new_encoded_space = new_space.encoded_space
        self.assertTrue(old_encoded_space != new_encoded_space)
        
        matrix_filter_post_data_2[str(dtai_filter.uuid)] = [new_space.id]

        data_2.update(matrix_filter_post_data_2)

        form_2 = ManageNodelinkForm(self.meta_app, view.tree_parent_node, view.submitted_parent_node, data=data_2,
                                    from_url=view.request.path)

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
    def test_post(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        view.request.method = 'POST'

        response = view.post(view.request, **view.kwargs)
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
    def test_post(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        view.request.method = 'POST'

        response = view.post(view.request, **view.kwargs)
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
        view.set_node(**view.kwargs)

        return view

    @test_settings
    def test_set_node(self):
        view = self.get_view()
        view.set_node(**view.kwargs)

        self.assertEqual(view.parent_node, self.view_node)
        self.assertEqual(view.nature_guide, self.generic_content)
        self.assertEqual(view.selected_node_ids, [])


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
        self.assertEqual(set(nodes), set([self.nodes[0].id, self.nodes[1].id]))


    @test_settings
    def test_get(self):

        view = self.get_view()

        self.assertTrue(view.request.headers.get('x-requested-with') == 'XMLHttpRequest')
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
        view.set_parent_node(**view.kwargs)
        
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
            'meta_app_id' : self.meta_app.id,
            'meta_node_id' : self.start_node.meta_node.id,
        }
        return url_kwargs

    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        view.meta_node = self.start_node.meta_node
        view.meta_app = self.meta_app

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
            'meta_app_id': self.meta_app.id,
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
        view.meta_app = self.meta_app

        return view


    def get_post_data(self, filter_type):
        
        post_data = {
            'input_language' : self.generic_content.primary_language,
            'name' : '{0} filter'.format(filter_type),
            'filter_type' : filter_type,
            'weight' : 5,
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
            created_matrix_filter = MatrixFilter.objects.all().order_by('pk').last()
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
            'meta_app_id' : self.meta_app.id,
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
            



class TestDeleteMatrixFilter(WithNatureGuideLink, ViewTestMixin, WithUser, WithMedia, WithMatrixFilters,
                WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'delete_matrix_filter'
    view_class = DeleteMatrixFilter


    def setUp(self):
        super().setUp()

        self.matrix_filters = self.create_all_matrix_filters(self.start_node)

        self.view_node = self.start_node


    def get_url_kwargs(self, matrix_filter):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'pk' : matrix_filter.id,
        }
        return url_kwargs

    def get_url(self, matrix_filter):
        url_kwargs = self.get_url_kwargs(matrix_filter)
        url = reverse(self.url_name, kwargs=url_kwargs)
        
        return url
    

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
        view.meta_app = self.meta_app

        return view



    @test_settings
    def test_post(self):

        for matrix_filter in self.matrix_filters:

            view = self.get_view(matrix_filter)

            meta_node = matrix_filter.meta_node
            
            matrix_filter_id = matrix_filter.pk
            qry = MatrixFilter.objects.filter(pk=matrix_filter_id)

            view = self.get_view(matrix_filter)

            self.assertTrue(qry.exists())

            view.request.method = 'POST'
            response = view.post(view.request, **view.kwargs)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context_data['meta_app'], self.meta_app)
            self.assertEqual(response.context_data['meta_node'], meta_node)
            self.assertEqual(response.context_data['deleted'], True)

            self.assertFalse(qry.exists())


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
            'meta_app_id' : self.meta_app.id,
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
        view.meta_app = self.meta_app

        return view


    def get_post_data(self, matrix_filter, source_image=True, referred_image=False):

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

            elif referred_image == True:
                image_store = self.create_image_store()
                
                space = MatrixFilterSpace(
                    matrix_filter=matrix_filter,
                    encoded_space='Test space',
                )

                space.save()


                self.referred_content_image = ContentImage(
                    content_type = ContentType.objects.get_for_model(space),
                    object_id = space.id,
                    image_store = image_store,
                )

                self.referred_content_image.save()

                post_data.update({
                    'referred_content_image_id' : self.referred_content_image.id,
                })

        elif matrix_filter.filter_type == 'ColorFilter':
            post_data.update({
                'color' : '#ff00ff',
                'color_type' : 'single',
            })

        return post_data
    
    
class TestCreateMatrixFilterSpace(ManageMatrixFilterSpaceCommon, WithFormTest, WithNatureGuideLink, WithUser,
                WithImageStore, WithMedia, WithMatrixFilters, WithLoggedInUser, WithMetaApp, WithTenantClient,
                TenantTestCase):


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

                created_space = MatrixFilterSpace.objects.filter(
                    matrix_filter=matrix_filter).order_by('pk').last()
                self.assertEqual(created_space.matrix_filter, matrix_filter)


    @test_settings
    def test_form_valid_color_gradient(self):
        for matrix_filter in self.matrix_filters:

            if matrix_filter.filter_type == 'ColorFilter':

                view = self.get_view(matrix_filter)
                view.set_space(**view.kwargs)
                view.set_primary_language()

                post_data = self.get_post_data(matrix_filter)

                # include gradient in post_data
                post_data.update({
                    'gradient' : True,
                    'color_2' : '#f1f1f1',
                    'description' : 'red',
                })

                form_kwargs = view.get_form_kwargs()
                form_kwargs['data'] = post_data
                form_class = view.get_form_class()
                form = form_class(**form_kwargs)

                form.is_valid()
                self.assertEqual(form.errors, {})

                response = view.form_valid(form)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context_data['success'], True)

                created_space = MatrixFilterSpace.objects.filter(
                    matrix_filter=matrix_filter).order_by('pk').last()
                self.assertEqual(created_space.matrix_filter, matrix_filter)


    @test_settings
    def test_form_valid_referred_image(self):
        
        for matrix_filter in self.matrix_filters:

            if matrix_filter.filter_type == 'DescriptiveTextAndImagesFilter':

                view = self.get_view(matrix_filter)
                view.set_space(**view.kwargs)
                view.set_primary_language()

                # do not supply a source_image as a file
                # instead, use an existing content_image
                post_data = self.get_post_data(matrix_filter, source_image=False, referred_image=True)

                form_kwargs = view.get_form_kwargs()
                form_kwargs['data'] = post_data
                form_class = view.get_form_class()
                form = form_class(**form_kwargs)

                form.is_valid()
                self.assertEqual(form.errors, {})

                response = view.form_valid(form)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context_data['success'], True)

                created_space = MatrixFilterSpace.objects.filter(
                    matrix_filter=matrix_filter).order_by('pk').last()
                self.assertEqual(created_space.matrix_filter, matrix_filter)
                self.assertEqual(created_space.encoded_space, post_data['text'])

                content_image = created_space.image()
                self.assertEqual(content_image.image_store, self.referred_content_image.image_store)


class TestManageMatrixFilterSpace(ManageMatrixFilterSpaceCommon, WithFormTest, WithNatureGuideLink, WithUser,
        WithImageStore, WithMedia, WithMatrixFilters, WithLoggedInUser, WithMetaApp, WithTenantClient,
        TenantTestCase):


    url_name = 'manage_matrix_filter_space'
    view_class = ManageMatrixFilterSpace


    def setUp(self):
        super().setUp()


    def get_url_kwargs(self, space):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
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
            view.meta_app = self.meta_app
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
            'meta_app_id' : self.meta_app.id,
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
    def test_post(self):

        self.create_matrix_filter_spaces()

        for filter_type, space in self.spaces.items():

            meta_node = space.matrix_filter.meta_node
            
            space_id = space.pk
            qry = MatrixFilterSpace.objects.filter(pk=space_id)

            view = self.get_view(space)

            self.assertTrue(qry.exists())

            view.request.method = 'POST'
            response = view.post(view.request, **view.kwargs)

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
    view_class = GetIdentificationMatrix


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


class TestMoveNatureGuideNode(WithNatureGuideLink, WithAjaxAdminOnly, ViewTestMixin, WithUser,
                            WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'move_natureguide_node'
    view_class = MoveNatureGuideNode


    def setUp(self):
        super().setUp()

        self.left = self.create_node(self.start_node, 'Left')
        self.middle = self.create_node(self.start_node, 'Middle')
        self.right = self.create_node(self.start_node, 'Right')
        
        self.left_1 = self.create_node(self.left, 'Left child')
        self.right_1 = self.create_node(self.right, 'Right child')

        self.crosslink = NatureGuideCrosslinks(
            parent = self.middle,
            child = self.right_1,
        )

        self.crosslink.save()
        

    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'parent_node_id' : self.right_1.parent.id,
            'child_node_id' : self.right_1.id,
        }

        return url_kwargs


    @test_settings
    def test_set_nodes(self):

        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_nodes(**view.kwargs)

        self.assertEqual(view.child_node, self.right_1)
        self.assertEqual(view.old_parent_node, self.right_1.parent)


    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_nodes(**view.kwargs)

        context = view.get_context_data(**view.kwargs)

        self.assertEqual(context['meta_app'], self.meta_app)
        self.assertEqual(context['old_parent_node'], self.right_1.parent)
        self.assertEqual(context['child_node'], self.right_1)
        self.assertEqual(context['form'].__class__, MoveNodeForm)
        self.assertEqual(context['success'], False)


    @test_settings
    def test_post_valid(self):

        self.assertEqual(self.right_1.parent, self.right)

        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_nodes(**view.kwargs)

        # move right_1 to left
        post_data = {
            'input_language' : 'en',
            'new_parent_node_id' : self.left.id,
        }

        form_kwargs = view.get_form_kwargs()
        form_kwargs['data'] = post_data
        form_class = view.get_form_class()
        form = form_class(self.right_1, self.right_1.parent, **form_kwargs)

        form.is_valid()
        self.assertEqual(form.errors, {})

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'], True)

        self.right_1.refresh_from_db()
        self.assertEqual(self.right_1.parent, self.left)
        self.assertTrue(self.right_1.taxon_nuid.startswith(self.left.taxon_nuid))


    @test_settings
    def test_post_invalid(self):

        self.assertEqual(self.right_1.parent, self.right)

        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_nodes(**view.kwargs)

        view.request.POST = QueryDict('new_parent_node_id={0}'.format(self.right.id))

        response = view.post(view.request, **view.kwargs)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'], False)



class TestMoveNatureGuideNodeCrosslink(WithNatureGuideLink, WithAjaxAdminOnly, ViewTestMixin, WithUser,
                            WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):


    url_name = 'move_natureguide_node'
    view_class = MoveNatureGuideNode


    def setUp(self):
        super().setUp()

        self.left = self.create_node(self.start_node, 'Left')
        self.middle = self.create_node(self.start_node, 'Middle')
        self.right = self.create_node(self.start_node, 'Right')
        
        self.left_1 = self.create_node(self.left, 'Left child')
        self.right_1 = self.create_node(self.right, 'Right child')

        self.crosslink = NatureGuideCrosslinks(
            parent = self.middle,
            child = self.right_1,
        )

        self.crosslink.save()
        

    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'parent_node_id' : self.middle.id, # middle is parent of crosslink
            'child_node_id' : self.right_1.id,
        }

        return url_kwargs
        
    @test_settings
    def test_post_valid_crosslink(self):

        self.assertEqual(self.right_1.parent, self.right)

        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_nodes(**view.kwargs)

        # move right_1 to left
        post_data = {
            'input_language' : 'en',
            'new_parent_node_id' : self.left.id,
        }

        form_kwargs = view.get_form_kwargs()
        form_kwargs['data'] = post_data
        form_class = view.get_form_class()
        form = form_class(self.right_1, self.right_1.parent, **form_kwargs)

        form.is_valid()
        self.assertEqual(form.errors, {})

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'], True)

        self.crosslink.refresh_from_db()
        self.assertEqual(self.crosslink.parent, self.left)
    

class TestSearchMoveToGroup(WithNatureGuideLink, WithAjaxAdminOnly, ViewTestMixin, WithUser,
                            WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):


    url_name = 'search_move_to_group'
    view_class = SearchMoveToGroup


    def setUp(self):
        super().setUp()

        self.left = self.create_node(self.start_node, 'Left')
        self.middle = self.create_node(self.start_node, 'Middle')
        self.right = self.create_node(self.start_node, 'Right')
        
        self.left_1 = self.create_node(self.left, 'Left child')
        self.right_1 = self.create_node(self.right, 'Right child')

        self.crosslink = NatureGuideCrosslinks(
            parent = self.middle,
            child = self.right_1,
        )

        self.crosslink.save()


    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'nature_guide_id' : self.left.nature_guide.id,
        }

        return url_kwargs

    @test_settings
    def test_get_queryset(self):
        
        view = self.get_view()
        view.meta_app = self.meta_app

        view.request.GET = {
            'name' : 'lEft',
        }

        queryset = view.get_queryset(view.request, **view.kwargs)

        self.assertEqual(len(queryset), 2)



class TestManageMatrixFilterRestrictionsCreate(WithMatrixFilters, WithNatureGuideLink, WithAjaxAdminOnly,
            ViewTestMixin, WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):


    url_name = 'manage_matrix_filter_restrictions'
    view_class = ManageMatrixFilterRestrictions


    def setUp(self):
        super().setUp()

        self.nature_guide = self.generic_content
        self.matrix_filters = self.create_all_matrix_filters(self.start_node)
        self.meta_node = self.start_node.meta_node
        


    def get_url_kwargs(self, matrix_filter):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'meta_node_id' : self.meta_node.id,
            'matrix_filter_id' : matrix_filter.id,
        }

        return url_kwargs


    def get_url(self, matrix_filter):
        url_kwargs = self.get_url_kwargs(matrix_filter)
        url = reverse(self.url_name, kwargs=url_kwargs)
        
        return url
    

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
        view.meta_app = self.meta_app
        view.kwargs = self.get_url_kwargs(matrix_filter)

        return view

    # matrix filters that theoretically can become a restrictivee filter for a given filter
    def get_restrictive_matrix_filters(self, restricted_matrix_filter):

        restrictive_matrix_filters = MatrixFilter.objects.all().exclude(
            pk=restricted_matrix_filter.pk).exclude(filter_type='TaxonFilter')

        return restrictive_matrix_filters


    @test_settings
    def test_dispatch(self):

        for restricted_matrix_filter in self.matrix_filters:
            
            role = TenantUserRole.objects.filter(user=self.user, tenant=self.tenant).first()
            if role:
                role.delete()

            url = self.get_url(restricted_matrix_filter)
            
            url_kwargs = {
                'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
            }

            response = self.tenant_client.get(url, **url_kwargs)
            self.assertEqual(response.status_code, 403)

            # test with admin role
            self.make_user_tenant_admin(self.user, self.tenant)
            response = self.tenant_client.get(url, **url_kwargs)
            self.assertEqual(response.status_code, 200)


    @test_settings
    def test_get(self):

        self.make_user_tenant_admin(self.user, self.tenant)

        for restricted_matrix_filter in self.matrix_filters:

            url = self.get_url(restricted_matrix_filter)

            get_kwargs = {
                'HTTP_X_REQUESTED_WITH':'XMLHttpRequest'
            }

            response = self.tenant_client.get(url, **get_kwargs)
            self.assertEqual(response.status_code, 200)


    @test_settings
    def test_set_node(self):

        for restricted_matrix_filter in self.matrix_filters:

            view = self.get_view(restricted_matrix_filter)
            view.set_node(**view.kwargs)
            self.assertEqual(view.meta_node, self.meta_node)
            self.assertEqual(view.matrix_filter, restricted_matrix_filter)
            

    @test_settings
    def test_get_form(self):

        for restricted_matrix_filter in self.matrix_filters:

            view = self.get_view(restricted_matrix_filter)
            view.set_node(**view.kwargs)
            form = view.get_form()
            self.assertEqual(form.__class__, ManageMatrixFilterRestrictionsForm)
            

    @test_settings
    def test_get_form_kwargs(self):

        for restricted_matrix_filter in self.matrix_filters:

            view = self.get_view(restricted_matrix_filter)
            view.set_node(**view.kwargs)

            form_kwargs = view.get_form_kwargs()
            self.assertEqual(form_kwargs['from_url'], view.request.path)
            

    @test_settings
    def test_get_context_data(self):

        for restricted_matrix_filter in self.matrix_filters:
            
            view = self.get_view(restricted_matrix_filter)
            view.set_node(**view.kwargs)

            context = view.get_context_data(**view.kwargs)
            self.assertEqual(context['meta_node'], self.meta_node)
            self.assertEqual(context['matrix_filter'], restricted_matrix_filter)
            self.assertFalse(context['success'])
            

    @test_settings
    def test_get_existing_space_link(self):

        for restricted_matrix_filter in self.matrix_filters:

            restrictive_matrix_filters = self.get_restrictive_matrix_filters(restricted_matrix_filter)

            view = self.get_view(restricted_matrix_filter)
            view.set_node(**view.kwargs)

            for restrictive_matrix_filter in restrictive_matrix_filters:
                space = view.get_existing_space_link(restrictive_matrix_filter)
                self.assertEqual(space, None)
            

    @test_settings
    def test_get_all_existing_space_links(self):

        for restricted_matrix_filter in self.matrix_filters:

            restrictive_matrix_filters = self.get_restrictive_matrix_filters(restricted_matrix_filter)

            view = self.get_view(restricted_matrix_filter)
            view.set_node(**view.kwargs)

            for restrictive_matrix_filter in restrictive_matrix_filters:
                spaces = view.get_all_existing_space_links(restrictive_matrix_filter)
                self.assertEqual(list(spaces), [])


    @test_settings
    def test_instantiate_new_space_link(self):

        for restricted_matrix_filter in self.matrix_filters:

            restrictive_matrix_filters = self.get_restrictive_matrix_filters(restricted_matrix_filter)

            view = self.get_view(restricted_matrix_filter)
            view.set_node(**view.kwargs)

            for restrictive_matrix_filter in restrictive_matrix_filters:
                space = view.instantiate_new_space_link(restrictive_matrix_filter)
                self.assertEqual(space.restricted_matrix_filter, restricted_matrix_filter)
                self.assertEqual(space.restrictive_matrix_filter, restrictive_matrix_filter)


    def check_restriction_existence(self, created_restriction):

        self.assertFalse(created_restriction.exists())
        

    @test_settings
    def test_form_valid(self):

        for restricted_matrix_filter in self.matrix_filters:

            restrictive_matrix_filters = self.get_restrictive_matrix_filters(restricted_matrix_filter)

            for restrictive_matrix_filter in restrictive_matrix_filters:

                created_restriction = MatrixFilterRestriction.objects.filter(
                    restricted_matrix_filter=restricted_matrix_filter,
                    restrictive_matrix_filter=restrictive_matrix_filter)

                self.check_restriction_existence(created_restriction)

                view = self.get_view(restricted_matrix_filter)
                view.set_node(**view.kwargs)

                post_data = {}
                matrix_filter_post_data = self.get_matrix_filter_post_data(restrictive_matrix_filter)
                post_data.update(matrix_filter_post_data)

                form = view.form_class(self.meta_app, restricted_matrix_filter, self.meta_node, data=post_data,
                                        from_url='/')

                form.is_valid()
                self.assertEqual(form.errors, {})

                response = view.form_valid(form)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context_data['success'])

                # check if restrictoin exists, check cache
                self.assertTrue(created_restriction.exists())

                created_restriction = created_restriction.first()

                if restrictive_matrix_filter.filter_type == 'RangeFilter':
                    self.assertEqual(created_restriction.encoded_space, [0.5, 4])
                    
                elif restrictive_matrix_filter.filter_type == 'DescriptiveTextAndImagesFilter':
                    self.assertEqual(created_restriction.values.count(), 1)

                elif restrictive_matrix_filter.filter_type == 'ColorFilter':
                    self.assertEqual(created_restriction.values.count(), 1)

                elif restrictive_matrix_filter.filter_type == 'NumberFilter':
                    self.assertEqual(created_restriction.encoded_space, [2.0, 3.0])

                elif restrictive_matrix_filter.filter_type == 'TextOnlyFilter':
                    self.assertEqual(created_restriction.values.count(), 1)

                else:
                    raise ValueError('Invalid filter: {0}'.format(matrix_filter.filter_type))

                

class TestManageMatrixFilterRestrictionsManage(TestManageMatrixFilterRestrictionsCreate):

    url_name = 'manage_matrix_filter_restrictions'
    view_class = ManageMatrixFilterRestrictions


    def setUp(self):
        super().setUp()

        for matrix_filter in self.matrix_filters:

            restrictive_matrix_filters = MatrixFilter.objects.all().exclude(pk=matrix_filter.pk).exclude(
                filter_type='TaxonFilter')

            for restrictive_filter in restrictive_matrix_filters:
                restriction = MatrixFilterRestriction(
                    restricted_matrix_filter = matrix_filter,
                    restrictive_matrix_filter = restrictive_filter,
                )

                filter_type = restrictive_filter.filter_type

                if filter_type == 'RangeFilter':
                    restriction.encoded_space = [0.6, 3]
                    restriction.save()
                    
                elif filter_type == 'NumberFilter':
                    restriction.encoded_space = [3.0]
                    restriction.save()

                else:
                    space = restrictive_filter.get_space().first()
                    restriction.save()
                    restriction.values.add(space)


    def check_restriction_existence(self, created_restriction):
        pass


    @test_settings
    def test_instantiate_new_space_link(self):
        pass
    

    @test_settings
    def test_get_existing_space_link(self):

        for restricted_matrix_filter in self.matrix_filters:

            restrictive_matrix_filters = self.get_restrictive_matrix_filters(restricted_matrix_filter)

            view = self.get_view(restricted_matrix_filter)
            view.set_node(**view.kwargs)

            for restrictive_matrix_filter in restrictive_matrix_filters:
                space = view.get_existing_space_link(restrictive_matrix_filter)

                filter_type = restrictive_matrix_filter.filter_type
                
                if filter_type == 'RangeFilter':
                    self.assertEqual(space.encoded_space, [0.6, 3])
                    
                elif filter_type == 'NumberFilter':
                    self.assertEqual(space.encoded_space, [3.0])
                    
                else:
                    expected_space = restrictive_matrix_filter.get_space().first()
                    self.assertEqual(space.values.all().first(), expected_space)
            

    @test_settings
    def test_get_all_existing_space_links(self):

        for restricted_matrix_filter in self.matrix_filters:

            restrictive_matrix_filters = self.get_restrictive_matrix_filters(restricted_matrix_filter)

            view = self.get_view(restricted_matrix_filter)
            view.set_node(**view.kwargs)

            for restrictive_matrix_filter in restrictive_matrix_filters:
                spaces = view.get_all_existing_space_links(restrictive_matrix_filter)

                filter_type = restrictive_matrix_filter.filter_type

                if filter_type == 'RangeFilter':
                    self.assertEqual(spaces[0].encoded_space, [0.6, 3])
                    
                elif filter_type == 'NumberFilter':
                    self.assertEqual(spaces[0].encoded_space, [3.0])
                    
                else:
                    self.assertEqual(spaces.values().all().count(), 1)
                    
            


class TestCopyTreeBranch(WithImageStore, WithMedia, WithNatureGuideLink, WithMatrixFilters, WithAjaxAdminOnly,
                    ViewTestMixin, WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):


    url_name = 'copy_tree_branch'
    view_class = CopyTreeBranch


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'node_id' : self.copy_node.id,
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view


    def set_content_image(self, node):

        content_image = ContentImage(
            content_type = ContentType.objects.get_for_model(MetaNode),
            object_id = node.meta_node.id,
            image_store = self.image_store,
        )

        content_image.save()

        return content_image


    def setUp(self):
        super().setUp()

        self.image_store = self.create_image_store()

        self.tree = {
            'node 1' : {
                'node 1.1' : {
                    '1.1.1' : 'result 1.1.1',
                    '1.1.2' : 'result 1.1.2',
                },
                'node 1.2' : {
                    '1.2.1' : 'result 1.2.1',
                    'node 1.2.2' : {
                        '1.2.2' : 'result 1.2.2',
                    }
                },
            },
            'node 2' : {
                'node 2.1' : 'result 2'
            },
        }


        self.crosslinks = {
            'node 2' : 'node 1.1', # parent outside, child inside
            'node 1.1' : 'node 1.2.2', # parent inside, child inside
            'node 1.2' : 'node 2', # parent inside, child outside            
        }

        # for accessing specific nodes on tests
        self.nodes = self.create_tree(self.start_node, self.tree)
        self.copy_node = self.nodes['node 1']
        

        self.node_1_matrix_filters = self.create_all_matrix_filters(self.copy_node)
        self.fill_matrix_filters_nodes(self.copy_node, [self.nodes['node 1'], self.nodes['node 2']])
        
        self.node_1_parent_matrix_filters = self.create_all_matrix_filters(self.copy_node.parent)
        self.fill_matrix_filters_nodes(self.copy_node.parent, [self.copy_node])

        # create filters a for non root nodes
        self.node_1_1_matrix_filters = self.create_all_matrix_filters(self.nodes['node 1.1'])
        self.fill_matrix_filters_nodes(self.nodes['node 1.1'], [self.nodes['1.1.1'], self.nodes['1.1.2']])

        self.create_crosslinks(self.crosslinks)
        

    def create_crosslinks(self, crosslinks):
        
        for parent_name, child_name in self.crosslinks.items():
            
            parent = self.nodes[parent_name]
            child = self.nodes[child_name]
            
            crosslink = NatureGuideCrosslinks(
                parent=parent,
                child=child,
            )

            crosslink.save()


    def create_tree(self, parent_node, tree):

        node_dict = {}

        for level_1_node_name, level_1_children in tree.items():

            # no result on the first level
            level_1_node = self.create_node(parent_node, level_1_node_name)

            node_dict[level_1_node_name] = level_1_node

            for level_2_node_name, level_2_children in level_1_children.items():

                if type(level_2_children) == dict:

                    level_2_node = self.create_node(level_1_node, level_2_node_name)

                    node_dict[level_2_node_name] = level_2_node


                    for level_3_node_name, level_3_children in level_2_children.items():

                        if type(level_3_children) == dict:

                            level_3_node = self.create_node(level_2_node, level_3_node_name)

                            node_dict[level_3_node_name] = level_3_node

                        else:
                            level_3_result_name = level_3_children
                            level_3_result = self.create_node(level_2_node, level_3_result_name,
                                                              node_type='result')
                            
                            node_dict[level_3_node_name] = level_3_result
                        
                else:
                    level_2_result_name = level_2_children
                    level_2_node = self.create_node(level_1_node, level_2_result_name, node_type='result')

                    node_dict[level_2_node_name] = level_2_node

        return node_dict
            
    @test_settings    
    def test_set_node(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        self.assertEqual(view.node, self.copy_node)
        self.assertEqual(view.parent_node, self.copy_node.parent)

    @test_settings
    def test_get_new_taxon_nuid(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        old_parent_nuid = self.copy_node.parent.taxon_nuid
        new_parent_nuid = '00a00a'
        new_taxon_nuid = view.get_new_taxon_nuid(old_parent_nuid, new_parent_nuid, self.copy_node)
        
        expected_nuid = self.copy_node.taxon_nuid.replace(old_parent_nuid,new_parent_nuid)
        
        self.assertEqual(new_taxon_nuid, expected_nuid)

    @test_settings
    def test_copy_meta_node(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        meta_node = self.copy_node.meta_node

        copied_meta_node = view.copy_meta_node(meta_node)

        self.assertEqual(meta_node.nature_guide, copied_meta_node.nature_guide)
        self.assertEqual(meta_node.node_type, copied_meta_node.node_type)
        self.assertEqual(meta_node.name, copied_meta_node.name)

    @test_settings
    def test_copy_meta_node_with_taxon(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        meta_node = self.copy_node.meta_node

        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lazy_taxon = LazyTaxon(instance=lacerta_agilis)
        
        meta_node.set_taxon(lazy_taxon)

        copied_meta_node = view.copy_meta_node(meta_node)

        self.assertEqual(meta_node.nature_guide, copied_meta_node.nature_guide)
        self.assertEqual(meta_node.node_type, copied_meta_node.node_type)
        self.assertEqual(meta_node.name, copied_meta_node.name)
        self.assertEqual(meta_node.taxon, copied_meta_node.taxon)

        self.assertEqual(lazy_taxon, copied_meta_node.taxon)

    @test_settings
    def test_copy_content_image(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        content_image = self.set_content_image(self.copy_node)

        # mock a copied node
        copied_node = self.nodes['node 2']

        copied_image = view.copy_content_image(content_image, copied_node)

        content_image.refresh_from_db()
        copied_image.refresh_from_db()
        
        self.assertTrue(copied_image.pk != content_image.pk)

        self.assertEqual(copied_image.image_store, content_image.image_store)
        self.assertEqual(copied_image.crop_parameters, content_image.crop_parameters)
        self.assertEqual(copied_image.content_type, content_image.content_type)
        self.assertEqual(copied_image.image_type, content_image.image_type)
        self.assertEqual(copied_image.position, content_image.position)
        self.assertEqual(copied_image.is_primary, content_image.is_primary)
        self.assertEqual(copied_image.text, content_image.text)

    @test_settings
    def test_copy_matrix_filter(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        copied_node = self.nodes['node 2']

        for matrix_filter in self.node_1_matrix_filters:

            copied_matrix_filter = view.copy_matrix_filter(matrix_filter, copied_node.meta_node)

            self.assertIn(str(matrix_filter.pk), view.copy_map['matrix_filters'])
            self.assertEqual(view.copy_map['matrix_filters'][str(matrix_filter.pk)],
                             str(copied_matrix_filter.pk))

            copy_fields = ['name', 'description', 'filter_type', 'definition', 'position', 'weight']

            for field in copy_fields:
                self.assertEqual(getattr(matrix_filter, field), getattr(copied_matrix_filter, field))

            self.assertEqual(matrix_filter.meta_node, self.copy_node.meta_node)
            self.assertEqual(copied_matrix_filter.meta_node, copied_node.meta_node)

            space = matrix_filter.get_space()
            space.order_by('pk')

            copied_space = copied_matrix_filter.get_space()
            copied_space.order_by('pk')

            self.assertEqual(len(space), len(copied_space))

            for counter, mfs in enumerate(space, 0):

                copied_mfs = copied_space[counter]

                self.assertEqual(len(mfs.images()), len(copied_mfs.images()))

                self.assertEqual(mfs.matrix_filter, matrix_filter)
                self.assertEqual(copied_mfs.matrix_filter, copied_matrix_filter)

                space_copy_fields = ['encoded_space', 'additional_information', 'position']

                for space_field in space_copy_fields:
                    self.assertEqual(getattr(mfs, space_field), getattr(copied_mfs, space_field))
                
        
    # does NOT create new values/ matrix filters
    @test_settings
    def test_copy_node_filter_space_root_node(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        copied_node = self.nodes['node 2']

        original_filter_count = len(self.node_1_parent_matrix_filters)

        self.assertTrue(original_filter_count >0)

        for matrix_filter in self.node_1_parent_matrix_filters:

            if matrix_filter.filter_type != 'TaxonFilter':

                spaces = NodeFilterSpace.objects.filter(matrix_filter=matrix_filter, node=self.copy_node)

                self.assertTrue(spaces.count() > 0)

                for node_filter_space in spaces:
                    copied_node_filter_space = view.copy_node_filter_space(node_filter_space, copied_node,
                                                                           matrix_filter)

                    self.assertEqual(copied_node_filter_space.matrix_filter, matrix_filter)

                    self.assertEqual(copied_node_filter_space.encoded_space, node_filter_space.encoded_space)
                    self.assertEqual(set(copied_node_filter_space.values.all().values_list('pk', flat=True)),
                                     set(node_filter_space.values.all().values_list('pk', flat=True)))
        
        new_filter_count = MatrixFilter.objects.filter(meta_node=self.copy_node.parent.meta_node).count()
        self.assertEqual(original_filter_count, new_filter_count)
        
    # does create new values/ matrix filters
    @test_settings
    def test_copy_node_filter_space_subnode(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        copy_node = self.nodes['1.1.1']
        copied_node = self.nodes['node 2.1']

        for matrix_filter in self.node_1_1_matrix_filters:

            matrix_filter_copy = view.copy_matrix_filter(matrix_filter, copied_node.meta_node)

            if matrix_filter.filter_type != 'TaxonFilter':

                spaces = NodeFilterSpace.objects.filter(matrix_filter=matrix_filter, node=copy_node)

                self.assertTrue(spaces.count() > 0)

                for space in matrix_filter.get_space():
                    self.assertTrue(str(space.pk) in view.copy_map['matrix_filter_space'])

                for node_filter_space in spaces:
                    copied_node_filter_space = view.copy_node_filter_space(node_filter_space, copied_node,
                                                                           matrix_filter_copy)

                    self.assertEqual(copied_node_filter_space.matrix_filter, matrix_filter_copy)

                    self.assertEqual(copied_node_filter_space.encoded_space, node_filter_space.encoded_space)

                    # there shpuld be new pks
                    copied_values = []
                    for mfs in node_filter_space.values.all():
                        mfs_copy_pk = view.copy_map['matrix_filter_space'][str(mfs.pk)]
                        mfs_copy = MatrixFilterSpace.objects.get(pk=mfs_copy_pk)

                        self.assertEqual(mfs_copy.matrix_filter, matrix_filter_copy)
                        self.assertEqual(mfs.matrix_filter, matrix_filter)

                        self.assertEqual(mfs.encoded_space, mfs_copy.encoded_space)

                    original_values = node_filter_space.values.all()
                    original_values_pks = original_values.values_list('pk', flat=True)

                    new_values = copied_node_filter_space.values.all()
                    new_values_pks = new_values.values_list('pk', flat=True)
                    
                    for value_pk in original_values_pks:
                        self.assertFalse(value_pk in new_values_pks)

                    for original_value in original_values:
                        new_value = new_values.get(
                            pk=view.copy_map['matrix_filter_space'][str(original_value.pk)])

                        self.assertEqual(new_value.encoded_space, original_value.encoded_space)
                        self.assertEqual(new_value.additional_information,
                                         original_value.additional_information)
                        self.assertEqual(new_value.position, original_value.position)

    
    # copy the root node of the brancht which should be copied
    # toplevel copy does not pass taxon_tree_fields
    # also check conten images
    @test_settings
    def test_copy_toplevel_node(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        new_parent_node = self.copy_node.parent

        copied_node = view.copy_node(self.copy_node, new_parent_node, taxon_tree_fields={})

        self.assertEqual(len(copied_node.taxon_nuid), len(self.copy_node.taxon_nuid))

        self.assertFalse(copied_node.meta_node.pk == self.copy_node.meta_node.pk)

        self.assertTrue(copied_node.taxon_nuid.startswith(new_parent_node.taxon_nuid))
        self.assertEqual(copied_node.parent, new_parent_node)
        self.assertEqual(copied_node.meta_node.name, self.copy_node.meta_node.name)

        matrix_filters = MatrixFilter.objects.filter(meta_node=self.copy_node.meta_node)
        copied_matrix_filters = MatrixFilter.objects.filter(meta_node=copied_node.meta_node)

        self.assertEqual(matrix_filters.count(), copied_matrix_filters.count())


    @test_settings
    def test_copy_subnode_with_taxontree_fields(self):

        # copy single node
        view = self.get_view()
        view.set_node(**view.kwargs)

        # self.copy_node == node 1
        new_root = view.copy_node(self.copy_node, self.copy_node.parent, taxon_tree_fields={})

        # copy a subnode of self.copy_node: node 1.1
        copy_node = self.nodes['node 1.1']
        new_taxon_nuid = view.get_new_taxon_nuid(self.copy_node.taxon_nuid, new_root.taxon_nuid,
                                                 copy_node)

        #print(self.copy_node.taxon_nuid)
        #print(new_root.taxon_nuid)
        #print(copy_node.taxon_nuid)
        #print(new_taxon_nuid)

        self.assertTrue(new_taxon_nuid.startswith(new_root.taxon_nuid))

        taxon_tree_fields = {
            'taxon_nuid' : new_taxon_nuid,
            'taxon_latname' : copy_node.taxon_latname,
            'is_root_taxon' : False,
            'rank' : None,
            'slug' : 'test slug {0}'.format(copy_node.id),
            'author' : None,
            'source_id' : new_taxon_nuid,
        }

        copied_node = view.copy_node(copy_node, new_root, taxon_tree_fields=taxon_tree_fields)

        self.assertEqual(len(copied_node.taxon_nuid), len(copy_node.taxon_nuid))
        self.assertEqual(len(copied_node.taxon_nuid) -3, len(new_root.taxon_nuid))
        self.assertEqual(len(copied_node.taxon_nuid) -3, len(self.copy_node.taxon_nuid))

        for key, value in taxon_tree_fields.items():
            self.assertEqual(getattr(copied_node, key), taxon_tree_fields[key])

        self.assertEqual(copied_node.parent, new_root)

        matrix_filters = MatrixFilter.objects.filter(meta_node=self.copy_node.meta_node)
        copied_matrix_filters = MatrixFilter.objects.filter(meta_node=new_root.meta_node)

        self.assertEqual(matrix_filters.count(), copied_matrix_filters.count())

    @test_settings
    def test_copy_crosslinks(self):

        # 3 cases :
        # (a) parent and child within copied branch
        # (b) parent outside, child inside
        # (c) parent inside, child outside
        '''
        self.crosslinks = {
            'node 2' : 'node 1.1', # parent outside, child inside
            'node 1.1' : 'node 1.2.2', # parent inside, child inside
            'node 1.2' : 'node 2', # parent inside, child outside            
        }
        '''

        view = self.get_view()
        view.set_node(**view.kwargs)

        # create the copied tree
        copied_tree = {
            'node 1 copy' : {
                'node 1.1 copy' : {
                    '1.1.1 copy' : 'result 1.1.1 copy',
                    '1.1.2 copy' : 'result 1.1.2 copy',
                },
                'node 1.2 copy' : {
                    '1.2.1 copy' : 'result 1.2.1 copy',
                    'node 1.2.2 copy' : {
                        '1.2.2 copy' : 'result 1.2.2 copy',
                    }
                },
            },
        }

        copied_nodes = self.create_tree(self.start_node, copied_tree)

        '''
        self.crosslinks = {
            'node 2' : 'node 1.1', # parent outside, child inside
            'node 1.1' : 'node 1.2.2', # parent inside, child inside
            'node 1.2' : 'node 2', # parent inside, child outside            
        }
        '''

        # node 1 copy as parent. crosslink points to node 1.1
        # case 1: node 2 --> node 1.1.
        case_1_old_parent = self.nodes['node 1']
        case_1_new_parent = copied_nodes['node 1 copy']

        created_case_1_crosslinks = view.copy_crosslinks(case_1_old_parent, case_1_new_parent)

        self.assertEqual(created_case_1_crosslinks, [])

        # case 2 node 1.1 --> node 1.2.2
        old_case_2_parent = self.nodes['node 1.1']
        new_case_2_parent = copied_nodes['node 1.1 copy']

        case_2_child = self.nodes['node 1.2.2']

        created_case_2_crosslinks = view.copy_crosslinks(old_case_2_parent, new_case_2_parent)
        case_2_qry = NatureGuideCrosslinks.objects.filter(parent=new_case_2_parent, child=case_2_child)

        self.assertTrue(case_2_qry.exists())
        self.assertEqual(created_case_2_crosslinks, [case_2_qry.first()])


        # case 3: 'node 1.2' --> 'node 2'
        case_3_old_parent = self.nodes['node 1.2']
        case_3_new_parent = copied_nodes['node 1.2 copy']

        # mock copy map
        view.copy_map['nodes'][str(case_3_old_parent.pk)] = str(case_3_new_parent.pk) 

        created_case_3_crosslinks = view.copy_crosslinks(case_3_old_parent, case_3_new_parent)

        self.assertEqual(len(created_case_3_crosslinks), 1)

        case_3_child = self.nodes['node 2']

        # parent should not create a crosslink
        case_3_qry = NatureGuideCrosslinks.objects.filter(parent=case_3_new_parent, child=case_3_child)
        self.assertTrue(case_3_qry.exists())
        self.assertEqual(case_3_qry.count(), 1)
        self.assertEqual(case_3_qry.first(), created_case_3_crosslinks[0])
        
        
        '''
        old_node = self.nodes['node 1.1']
        new_node = copied_nodes['node 1.1 copy']

        
        self.assertEqual(len(created_case_1_crosslinks), 1)

        # expected new crosslink: node 2 --> node 1.1 copy
        case_1_parent = self.nodes['node 2']
        case_1_child = new_node

        case_1_qry = NatureGuideCrosslinks.objects.filter(parent=case_1_parent, child=case_1_child)
        self.assertTrue(case_1_qry.exists())
        self.assertEqual(case_1_qry.count(), 1)
        self.assertEqual(created_case_1_crosslinks[0], case_1_qry.first())

        # case 2 node 1.1 --> node 1.2.2
        case_2_old_node = self.nodes['node 1.2.2']
        case_2_new_node = copied_nodes['node 1.2.2 copy']

        # mock copy map
        old_crosslink_parent = self.nodes['node 1.1']
        view.copy_map['nodes'][str(old_crosslink_parent.pk)] = str(new_node.pk) 

        created_case_2_crosslinks = view.copy_crosslinks(case_2_old_node, case_2_new_node)

        self.assertEqual(len(created_case_2_crosslinks), 1)

        case_2_parent = copied_nodes['node 1.1 copy']
        case_2_child = copied_nodes['node 1.2.2 copy']

        # parent should not create a crosslink
        case_2_qry = NatureGuideCrosslinks.objects.filter(parent=case_2_parent, child=case_2_child)
        self.assertTrue(case_2_qry.exists())
        self.assertEqual(case_2_qry.count(), 1)
        self.assertEqual(case_2_qry.first(), created_case_2_crosslinks[0])

        
        # case 3: 'node 1.2' --> 'node 2'
        case_3_old_node = self.nodes['node 1.2']
        case_3_new_node = copied_nodes['node 1.2 copy']

        # mock copy map
        
        view.copy_map['nodes'][str(case_3_old_node.pk)] = str(case_3_new_node.pk) 

        created_case_3_crosslinks = view.copy_crosslinks(case_3_old_node, case_3_new_node)

        self.assertEqual(len(created_case_3_crosslinks), 1)

        case_3_parent = copied_nodes['node 1.2 copy']
        case_3_child = self.nodes['node 2']

        # parent should not create a crosslink
        case_3_qry = NatureGuideCrosslinks.objects.filter(parent=case_3_parent, child=case_3_child)
        self.assertTrue(case_3_qry.exists())
        self.assertEqual(case_3_qry.count(), 1)
        self.assertEqual(case_3_qry.first(), created_case_3_crosslinks[0])
        '''

    
    # copy branch
    @test_settings
    def test_form_valid(self):

        view = self.get_view()
        view.set_node(**view.kwargs)

        data = {
            'branch_name' : 'node 1 copy',
        }
        
        form = CopyTreeBranchForm(data=data)

        form.is_valid()

        self.assertEqual(form.errors, {})

        response = view.form_valid(form)

        matrix_filters = MatrixFilter.objects.filter(
            meta_node=response.context_data['node'].meta_node)
        copied_matrix_filters = MatrixFilter.objects.filter(
            meta_node=response.context_data['node_copy'].meta_node)

        self.assertEqual(matrix_filters.count(), copied_matrix_filters.count())

        self.assertEqual(response.status_code, 200)

        # check copies
        root_copy = NatureGuidesTaxonTree.objects.get(meta_node__name=data['branch_name'])
        orig_root = view.node

        self.assertEqual(root_copy.parent, orig_root.parent)

        for level_2_node_name, level_2_children in self.tree['node 1'].items():

            if type(level_2_children) == str:
                level_2_node_name = level_2_children

            orig_level_2_node = NatureGuidesTaxonTree.objects.get(parent=orig_root,
                                                                meta_node__name=level_2_node_name)


            if type(level_2_children) == dict:

                copied_level_2_node = NatureGuidesTaxonTree.objects.get(parent=root_copy,
                                                                  meta_node__name=level_2_node_name)

                for level_3_node_name, level_3_children in self.tree['node 1'][level_2_node_name].items():

                    if type(level_3_children) == str:
                        level_3_node_name = level_3_children
                        

                    orig_level_3_node = NatureGuidesTaxonTree.objects.get(parent=orig_level_2_node,
                                                                meta_node__name=level_3_node_name)

                    if type(level_3_children) == dict:
                        
                        copied_level_3_node = NatureGuidesTaxonTree.objects.get(parent=copied_level_2_node,
                                                                  meta_node__name=level_3_node_name)

                    else:

                        result_node = NatureGuidesTaxonTree.objects.get(parent=orig_level_2_node,
                                                                        meta_node__name=level_3_node_name)

                        result_link = NatureGuideCrosslinks.objects.get(parent=copied_level_2_node,
                                                                        child=result_node)

            else:

                result_link = NatureGuideCrosslinks.objects.get(parent=root_copy, child=orig_child_node)

    @test_settings
    def test_copy_and_delete_old(self):
        pass
        



class TestManageAdditionalMatrixFilterSpaceImage(ContentImagePostData, WithMedia, WithFormTest, WithMatrixFilters, WithNatureGuideLink, ViewTestMixin,
                            WithAjaxAdminOnly, WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):
    
    url_name = 'manage_additional_matrix_filter_space_image'
    view_class = ManageAdditionalMatrixFilterSpaceImage

    def setUp(self):
        super().setUp()

        self.content_type = ContentType.objects.get_for_model(MatrixFilterSpace)

        parent_node = self.start_node
        filter_type = 'DescriptiveTextAndImagesFilter'
        encoded_space = 'description'
        self.matrix_filter = self.create_matrix_filter_with_space(parent_node, filter_type, encoded_space)
        self.space = MatrixFilterSpace.objects.filter(matrix_filter=self.matrix_filter).first()

        self.image_type = 'secondary'

    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_type_id' : self.content_type.id,
            'object_id' : self.space.id,
            'image_type' : self.image_type,
        }

        return url_kwargs

    def get_view(self):
        view = super().get_view()
        url_kwargs = self.get_url_kwargs()
        view.meta_app=self.meta_app
        view.set_content_image(**url_kwargs)

        if view.content_image:
            view.set_licence_registry_entry(view.content_image.image_store, 'source_image')

        self.assertEqual(view.image_type, self.image_type)
        view.set_taxon(view.request)
        return view

    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        kwargs = self.get_url_kwargs()
        context = view.get_context_data(**kwargs)

        self.assertEqual(context['content_type'], self.content_type)
        self.assertEqual(context['content_instance'], self.space)
        self.assertEqual(context['content_image'], None)
        self.assertEqual(context['content_image_taxon'], None)
        self.assertEqual(context['new'], True)

    @test_settings
    def test_post(self):
        
        post_data, file_data = self.get_post_form_data()

        view = self.get_view()

        initial = view.get_initial()
        self.assertEqual(initial['image_type'], self.image_type)

        post_data['image_type'] = self.image_type

        form = view.form_class(initial=initial, data=post_data, files=file_data)
        
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})
        
        view.set_content_image(**view.kwargs)
        view.licence_registry_entry = None

        content_image_qry = ContentImage.objects.filter(content_type=self.content_type,
                                                object_id=self.space.id, image_type=self.image_type)
        self.assertFalse(content_image_qry.exists())


        self.assertEqual(view.image_type, self.image_type)

        response = view.form_valid(form)
        
        self.assertEqual(response.status_code, 200)

        # check image existance
        # check if the content image has been created
        self.assertTrue(content_image_qry.exists())
        
        # check if the licence has been stored
        content_image = content_image_qry.first()

        licence = content_image.image_store.licences.first()
        licencing_data = self.get_licencing_post_data()
        
        self.assertEqual(licence.creator_name, licencing_data['creator_name'])
        self.assertEqual(licence.licence, 'CC0')

        # check response context data
        self.assertEqual(response.context_data['content_image'], content_image)

        # test new context data from GET
        kwargs = self.get_url_kwargs()
        view = self.get_view()
        
        context = view.get_context_data(**kwargs)
        self.assertEqual(context['content_type'], self.content_type)
        self.assertEqual(context['content_instance'], self.space)
        self.assertEqual(context['content_image'], content_image)
        self.assertEqual(context['content_image_taxon'], None)
        self.assertEqual(context['new'], False)


class TestDeleteAdditionalMatrixFilterSpaceImage(WithImageStore, WithMedia, WithMatrixFilters, WithNatureGuideLink, ViewTestMixin,
                            WithAjaxAdminOnly, ContentImagePostData, WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):
    
    url_name = 'delete_additional_matrix_filter_space_image'
    view_class = DeleteAdditionalMatrixFilterSpaceImage

    def setUp(self):
        super().setUp()

        self.content_type = ContentType.objects.get_for_model(MatrixFilterSpace)

        parent_node = self.start_node
        filter_type = 'DescriptiveTextAndImagesFilter'
        encoded_space = 'description'
        self.matrix_filter = self.create_matrix_filter_with_space(parent_node, filter_type, encoded_space)
        self.space = MatrixFilterSpace.objects.filter(matrix_filter=self.matrix_filter).first()

        self.generic_content = self.space

    def get_url_kwargs(self):
        content_image = self.create_content_image()
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'pk' : content_image.pk,
        }
        return url_kwargs

    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        view.object = view.get_object()
        view.meta_app = self.meta_app
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['image_type'], 'image')
        self.assertEqual(context['content_instance'], self.space)