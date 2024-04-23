from django.test import TestCase, RequestFactory
from django_tenants.test.cases import TenantTestCase
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from app_kit.tests.common import test_settings

from app_kit.tests.mixins import (WithMetaApp, WithTenantClient, WithUser, WithLoggedInUser, WithAjaxAdminOnly,
                                  WithAdminOnly, WithFormTest, ViewTestMixin)


from app_kit.features.backbonetaxonomy.views import (ManageBackboneTaxonomy, BackboneFulltreeUpdate,
            AddMultipleBackboneTaxa, AddBackboneTaxon, RemoveBackboneTaxon, SearchBackboneTaxonomy) 

from app_kit.features.backbonetaxonomy.forms import (AddSingleTaxonForm, AddMultipleTaxaForm,
                                                     ManageFulltreeForm, SearchTaxonomicBackboneForm)

from app_kit.features.backbonetaxonomy.models import BackboneTaxonomy, BackboneTaxa

from taxonomy.lazy import LazyTaxon
from taxonomy.models import TaxonomyModelRouter

import json

class WithBackboneTaxonomy:

    def setUp(self):
        super().setUp()
        self.link = self.get_generic_content_link(BackboneTaxonomy)
        self.generic_content = self.link.generic_content
        self.content_type = ContentType.objects.get_for_model(BackboneTaxonomy)
        

class TestManageBackboneTaxonomy(ViewTestMixin, WithAdminOnly, WithLoggedInUser, WithUser, WithBackboneTaxonomy,
                                 WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'manage_backbonetaxonomy'
    view_class = ManageBackboneTaxonomy

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_type_id' : self.content_type.id,
            'object_id' : self.generic_content.id,
        }
        return url_kwargs


    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        self.assertFalse(view.request.headers.get('x-requested-with') == 'XMLHttpRequest')
        view.meta_app = self.meta_app
        view.generic_content = self.generic_content
        view.generic_content_type = self.content_type

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['alltaxa'], True)
        self.assertIn('taxa', context)
        self.assertEqual(context['form'].__class__, AddSingleTaxonForm)
        self.assertEqual(context['taxaform'].__class__, AddMultipleTaxaForm)
        self.assertEqual(context['fulltreeform'].__class__, ManageFulltreeForm)
        self.assertEqual(context['searchbackboneform'].__class__, SearchTaxonomicBackboneForm)


    @test_settings
    def test_context_data_ajax(self):

        view = self.get_view(ajax=True)
        self.assertTrue(view.request.headers.get('x-requested-with') == 'XMLHttpRequest')

        view.meta_app = self.meta_app
        view.generic_content = self.generic_content
        view.generic_content_type = self.content_type
        view.request.GET = {
            'contenttypeid' : self.content_type.id,
            'objectid' : self.generic_content.id,
        }

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['alltaxa'], False)
        self.assertIn('taxa', context)


class TestAddMultipleBackboneTaxa(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithBackboneTaxonomy,
                           WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'add_backbone_taxa'
    view_class = AddMultipleBackboneTaxa

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'backbone_id' : self.generic_content.id,
        }
        return url_kwargs

    def get_view(self):
        view = super().get_view()
        view.backbone = self.generic_content
        view.meta_app = self.meta_app
        return view

    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['meta_app'], self.meta_app)
        self.assertEqual(context['backbone'], self.generic_content)
        self.assertEqual(context['taxaform'].__class__, AddMultipleTaxaForm)
        self.assertEqual(context['content_type'], self.content_type)

    @test_settings
    def test_form_valid(self):

        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)
        

        post_data = {
            'taxa' : ' Lacerta agilis, Viola, Nothing',
            'source' : 'taxonomy.sources.col',
        }

        form = AddMultipleTaxaForm(post_data)
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        view = self.get_view()
        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['form'].__class__, AddMultipleTaxaForm)
        self.assertEqual(response.context_data['added'][0].name_uuid, lacerta_agilis.name_uuid)
        self.assertEqual(len(response.context_data['unambiguous']), 1)
        self.assertEqual(len(response.context_data['not_found']), 1)

        # test existed and not found
        post_data = {
            'taxa' : ' Lacerta agilis',
            'source' : 'taxonomy.sources.col',
        }

        form = AddMultipleTaxaForm(post_data)
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        view = self.get_view()
        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.context_data['existed'][0].name_uuid), str(lacerta_agilis.name_uuid))

        

class TestAddBackboneTaxon(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithBackboneTaxonomy,
                           WithMetaApp, WithTenantClient, TenantTestCase):


    url_name = 'add_backbone_taxon'
    view_class = AddBackboneTaxon

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'backbone_id' : self.generic_content.id,
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.backbone = self.generic_content
        view.meta_app = self.meta_app
        return view


    @test_settings
    def test_get_context_data(self):

        view = self.get_view()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['backbone'], self.generic_content)
        self.assertEqual(context['content_type'], self.content_type)
        self.assertEqual(context['meta_app'], self.meta_app)
        

    @test_settings
    def get_form_kwargs(self):

        view = self.get_view()
        form_kwargs = view.get_form_kwargs(**view.kwargs)
        self.assertIn('taxon_search_url', form_kwargs)
        self.assertIn('descendants_choice', True)
        

    @test_settings
    def test_get_required_form_kwargs(self):

        view = self.get_view()
        form_kwargs = view.get_required_form_kwargs()
        self.assertIn('taxon_search_url', form_kwargs)
        self.assertEqual(form_kwargs['descendants_choice'], True)
        

    @test_settings
    def test_form_valid(self):

        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)

        post_data = {
            'taxon_0' : 'taxonomy.sources.col', # taxon_source
            'taxon_1' : lacerta_agilis.taxon_latname, # taxon_latname
            'taxon_2' : lacerta_agilis.taxon_author, # taxon_author
            'taxon_3' : str(lacerta_agilis.name_uuid), # name_uuid
            'taxon_4' : lacerta_agilis.taxon_nuid, # taxon_nuid
        }

        view = self.get_view()

        form_kwargs = view.get_form_kwargs(**view.kwargs)
        form_kwargs['data'] = post_data
        form = AddSingleTaxonForm(**form_kwargs)
        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['exists'], False)
        self.assertEqual(response.context_data['form'].__class__, AddSingleTaxonForm)
        self.assertEqual(response.context_data['taxon'].name_uuid, lacerta_agilis.name_uuid)

        backbone_taxon = BackboneTaxa.objects.get(backbonetaxonomy=self.generic_content)
        self.assertEqual(str(backbone_taxon.name_uuid), str(lacerta_agilis.name_uuid))

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['exists'], True)
        


class TestRemoveBackboneTaxon(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithBackboneTaxonomy,
                           WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'remove_backbone_taxon'
    view_class = RemoveBackboneTaxon

    def get_taxon(self):

        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)

        return lacerta_agilis


    def get_view(self):
        view = super().get_view()
        view.backbone = self.generic_content
        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        view.models = models
        return view
    

    def get_backbone_taxon(self):
    
        link = BackboneTaxa(
            backbonetaxonomy = self.generic_content,
            taxon = self.get_taxon(),
        )
        link.save()

        return link
        

    def get_url_kwargs(self):
        taxon = self.get_taxon()
        
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'backbone_id' : self.generic_content.id,
            'name_uuid' : str(taxon.name_uuid),
            'source' : str(taxon.taxon_source),
        }
        return url_kwargs

    @test_settings
    def get_context_data(self):

        view = self.get_view(**view.kwargs)
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['taxon'].name_uuid, self.taxon.name_uuid)
        self.assertEqual(context['backbone'], self.generic_content)
        self.assertEqual(context['meta_app'], self.meta_app)

    @test_settings
    def test_post(self):

        taxon = self.get_taxon()
        exists_qry = BackboneTaxa.objects.filter(backbonetaxonomy=self.generic_content,
                                                 name_uuid=str(taxon.name_uuid))

        self.assertFalse(exists_qry.exists())

        view = self.get_view()
        response = view.post(view.request, **view.kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(exists_qry.exists())
        self.assertEqual(response.context_data['deleted'], True)

        link = self.get_backbone_taxon()
        self.assertTrue(exists_qry.exists())
        response = view.post(view.request, **view.kwargs)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(exists_qry.exists())
        self.assertEqual(response.context_data['deleted'], True)
        

class TestSearchBackboneTaxonomy(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithBackboneTaxonomy,
                           WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'search_backbonetaxonomy'
    view_class = SearchBackboneTaxonomy

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
        }
        return url_kwargs


    @test_settings
    def test_get(self):
        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)

        link = BackboneTaxa(
            backbonetaxonomy = self.generic_content,
            taxon = lacerta_agilis,
        )
        link.save()
        
        view = self.get_view()

        response = view.get(view.request, **view.kwargs)
        self.assertEqual(response.status_code, 200)

        view_2 = self.get_view()
        view_2.request.GET = {
            'searchtext' : 'lacerta ag',
        }

        response_2 = view.get(view_2.request, **view.kwargs)
        self.assertEqual(response_2.status_code, 200)

        content = json.loads(response_2.content)
        self.assertEqual(len(content), 1)
