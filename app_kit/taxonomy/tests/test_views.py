from django_tenants.test.cases import TenantTestCase

from taxonomy.lazy import LazyTaxon
from taxonomy.models import TaxonomyModelRouter

from taxonomy.forms import ManageMetaVernacularNameForm
from taxonomy.views import ManageMetaVernacularName

from taxonomy.models import MetaVernacularNames

from app_kit.tests.common import test_settings
from app_kit.tests.mixins import (WithMetaApp, )

from app_kit.tests.mixins import (WithMetaApp, WithTenantClient, WithUser, WithLoggedInUser, WithAjaxAdminOnly,
                                  ViewTestMixin)


class TestCreateMetaVernacularName(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser,
                                   WithTenantClient, WithMetaApp, TenantTestCase):

    url_name = 'create_meta_vernacular_name'
    view_class = ManageMetaVernacularName

    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_source' : self.lazy_taxon.taxon_source,
            'name_uuid' : self.lazy_taxon.name_uuid,
        }

        return url_kwargs
    
    
    def setUp(self):
        super().setUp()
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        taxon = models.TaxonTreeModel.objects.get(taxon_latname='Natrix natrix')
        
        self.lazy_taxon = LazyTaxon(instance=taxon)
    
    def get_view(self):
        view = super().get_view(ajax=True)
        view.meta_app = self.meta_app
        return view
    

    @test_settings
    def test_set_taxon_and_name(self):
        
        view = self.get_view()
        
        view.set_taxon_and_name(**view.kwargs)
        
        self.assertEqual(view.lazy_taxon, self.lazy_taxon)
        self.assertEqual(view.meta_vernacular_name, None)
    
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        view.set_taxon_and_name(**view.kwargs)
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['taxon'], self.lazy_taxon)
        self.assertEqual(context['meta_vernacular_name'], None)
        self.assertEqual(context['success'], False)
      
      
    @test_settings
    def test_form_valid(self):
        
        post_data = {
            'name': 'Snake',
            'input_language': 'en',
            'preferred': True,
        }
        
        view = self.get_view()
        view.set_taxon_and_name(**view.kwargs)
        
        form = view.form_class(self.lazy_taxon, data=post_data, language='en')
        
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)
        
        self.assertEqual(response.status_code, 200)
        
        name = MetaVernacularNames.objects.get(name_uuid=self.lazy_taxon.name_uuid)
        
        self.assertEqual(name.name, 'Snake')
        self.assertEqual(name.language, 'en')
        self.assertEqual(name.preferred, True)
        
        self.assertEqual(response.context_data['success'], True)
        self.assertEqual(response.context_data['meta_vernacular_name'], name)
        
        
        

class TestManageMetaVernacularName(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser,
                                   WithTenantClient, WithMetaApp, TenantTestCase):

    url_name = 'manage_meta_vernacular_name'
    view_class = ManageMetaVernacularName

    def get_url_kwargs(self):

        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'meta_vernacular_name_id': self.name.id,
        }

        return url_kwargs
    
    
    def setUp(self):
        super().setUp()
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        taxon = models.TaxonTreeModel.objects.get(taxon_latname='Natrix natrix')
        
        self.lazy_taxon = LazyTaxon(instance=taxon)
        
        self.name = self.create_name()
    
    def get_view(self):
        view = super().get_view(ajax=True)
        view.meta_app = self.meta_app
        return view
    
    
    def create_name(self):
        name = MetaVernacularNames(
            taxon_latname=self.lazy_taxon.taxon_latname,
            taxon_author=self.lazy_taxon.taxon_author,
            taxon_source=self.lazy_taxon.taxon_source,
            taxon_nuid=self.lazy_taxon.taxon_nuid,
            name_uuid=self.lazy_taxon.name_uuid,
            name='Snake',
            language='en',
        )
        
        name.save()
        
        return name

    @test_settings
    def test_set_taxon_and_name(self):
        
        view = self.get_view()
        
        view.set_taxon_and_name(**view.kwargs)
        
        self.assertEqual(view.lazy_taxon, self.lazy_taxon)
        self.assertEqual(view.meta_vernacular_name, self.name)
    
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        view.set_taxon_and_name(**view.kwargs)
        
        context = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context['taxon'], self.lazy_taxon)
        self.assertEqual(context['meta_vernacular_name'], self.name)
        self.assertEqual(context['success'], False)
      
    
    @test_settings
    def test_get_initial(self):
        
        view = self.get_view()
        view.set_taxon_and_name(**view.kwargs)
        
        initial = view.get_initial()
        
        self.assertEqual(initial['name'], 'Snake')
        self.assertEqual(initial['preferred'], view.meta_vernacular_name.preferred)
        
        
    @test_settings
    def test_form_valid(self):
        
        post_data = {
            'name': 'Snake 2',
            'input_language': 'en',
            'preferred': True,
        }
        
        view = self.get_view()
        view.set_taxon_and_name(**view.kwargs)
        
        form = view.form_class(self.lazy_taxon, meta_vernacular_name=self.name,
                               data=post_data, language='en')
        
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)
        
        self.assertEqual(response.status_code, 200)
        
        name = MetaVernacularNames.objects.get(name_uuid=self.lazy_taxon.name_uuid)
        
        self.assertEqual(name.name, 'Snake 2')
        self.assertEqual(name.language, 'en')
        self.assertEqual(name.preferred, True)
        
        self.assertEqual(response.context_data['success'], True)
        
        
