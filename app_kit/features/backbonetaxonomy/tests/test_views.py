from django_tenants.test.cases import TenantTestCase
from django.contrib.contenttypes.models import ContentType

from app_kit.models import MetaAppGenericContent

from app_kit.tests.common import test_settings

from app_kit.tests.mixins import (WithMetaApp, WithTenantClient, WithUser, WithLoggedInUser, WithAjaxAdminOnly,
                                  WithAdminOnly, WithFormTest, ViewTestMixin)


from app_kit.features.backbonetaxonomy.views import (ManageBackboneTaxonomy, BackboneFulltreeUpdate,
            AddMultipleBackboneTaxa, AddBackboneTaxon, RemoveBackboneTaxon, SearchBackboneTaxonomy,
            ManageBackboneTaxon, SwapTaxon, AnalyzeTaxon, UpdateTaxonReferences,
            TaxonRelationships, ManageTaxonRelationshipType, DeleteTaxonRelationshipType,
            ManageTaxonRelationship, DeleteTaxonRelationship)

from app_kit.features.backbonetaxonomy.forms import (AddSingleTaxonForm, AddMultipleTaxaForm,
    ManageFulltreeForm, SearchTaxonomicBackboneForm, TaxonRelationshipForm)

from app_kit.features.backbonetaxonomy.models import BackboneTaxonomy, BackboneTaxa, TaxonRelationshipType, TaxonRelationship

from app_kit.features.taxon_profiles.models import TaxonProfiles, TaxonProfile
from app_kit.features.nature_guides.models import NatureGuide, NatureGuidesTaxonTree
from app_kit.features.nature_guides.tests.common import WithNatureGuide

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
        view.meta_app = self.meta_app

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



class TestManageTaxon(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser, WithNatureGuide,
                      WithBackboneTaxonomy, WithMetaApp, WithTenantClient, TenantTestCase):
    
    url_name = 'manage_backbone_taxon'
    view_class = ManageBackboneTaxon
    
    def setUp(self):
        super().setUp()
        
        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)
        
        self.taxon = lacerta_agilis
        

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'taxon_source' : self.taxon.taxon_source,
            'name_uuid' : self.taxon.name_uuid,
        }
        return url_kwargs
    
    
    @test_settings
    def test_set_taxon(self):
        
        view = self.get_view()
        view.set_taxon(**view.kwargs)
        view.meta_app = self.meta_app
        self.assertEqual(view.lazy_taxon, self.taxon)
        
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        view.set_taxon(**view.kwargs)
        view.meta_app = self.meta_app
        
        context_data = view.get_context_data(**view.kwargs)
        
        taxon_profiles_link = self.meta_app.get_generic_content_links(TaxonProfiles).first()
        taxon_profiles = taxon_profiles_link.generic_content
        
        ng_ctype = ContentType.objects.get_for_model(NatureGuide)
        
        self.assertEqual(context_data['taxon'], self.taxon)
        self.assertEqual(context_data['nature_guides'], [])
        self.assertEqual(context_data['taxon_profiles'], taxon_profiles)
        self.assertEqual(context_data['taxon_profile'], None)
        self.assertEqual(context_data['nature_guides_content_type'], ng_ctype)
        
        nature_guide = self.create_nature_guide()
        ng_link = MetaAppGenericContent(
            meta_app=self.meta_app,
            content_type=ng_ctype,
            object_id=nature_guide.id,
        )
        ng_link.save()
        
        node = self.create_node(nature_guide.root_node, 'First')
        node.meta_node.set_taxon(self.taxon)
        node.meta_node.save()
                
        taxon_profile = TaxonProfile(
            taxon_profiles=taxon_profiles,
            taxon=self.taxon,
        )
        
        taxon_profile.save()
    
    
        context_data = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context_data['taxon'], self.taxon)
        self.assertEqual(context_data['nature_guides'], [node])
        self.assertEqual(context_data['taxon_profiles'], taxon_profiles)
        self.assertEqual(context_data['taxon_profile'], taxon_profile)
        self.assertEqual(context_data['nature_guides_content_type'], ng_ctype)
        

class TestSwapTaxon(ViewTestMixin, WithAdminOnly, WithLoggedInUser, WithUser, WithBackboneTaxonomy,
                           WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'swap_taxon'
    view_class = SwapTaxon
    
    def setUp(self):
        super().setUp()
        
        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)
        
        self.taxon = lacerta_agilis
        
        picea_abies = models.TaxonTreeModel.objects.get(taxon_latname='Picea abies')
        picea_abies = LazyTaxon(instance=picea_abies)
        self.taxon_2 = picea_abies
        
        taxon_profiles_link = self.meta_app.get_generic_content_links(TaxonProfiles).first()
        taxon_profiles = taxon_profiles_link.generic_content
        
        self.taxon_profile = TaxonProfile(
            taxon_profiles=taxon_profiles,
            taxon=self.taxon,
        )
        
        self.taxon_profile.save()
        

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
        }
        return url_kwargs
    
    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view
    
    def get_post_data(self):
        
        post_data = {
            'from_taxon_0' : 'taxonomy.sources.col',
            'from_taxon_1' : self.taxon.taxon_latname,
            'from_taxon_2' : self.taxon.taxon_author,
            'from_taxon_3' : str(self.taxon.name_uuid),
            'from_taxon_4' : self.taxon.taxon_nuid,
            'to_taxon_0' : 'taxonomy.sources.col',
            'to_taxon_1' : self.taxon_2.taxon_latname,
            'to_taxon_2' : self.taxon_2.taxon_author,
            'to_taxon_3' : str(self.taxon_2.name_uuid),
            'to_taxon_4' : self.taxon_2.taxon_nuid,
        }
        
        return post_data
        
    
    @test_settings
    def test_analyze_taxon(self):
        view = self.get_view()
        
        analysis = view.analyze_taxon(self.taxon, self.taxon_2)
        analysis[0]['occurrences'] = list(analysis[0]['occurrences'])
        expected_analysis = [
            {
                'model': TaxonProfile,
                'occurrences': [self.taxon_profile],
                'verbose_model_name': 'Taxon Profile',
                'verbose_occurrences': ['exists as a Taxon Profile'],
                'is_swappable': True
            }
        ]
        
        self.assertEqual(analysis, expected_analysis)

    
    @test_settings
    def test_get_taxon_occurrences(self):
        view = self.get_view()
        occurrences = view.get_taxon_occurrences(self.taxon)
        
        occurrences[0]['occurrences'] = list(occurrences[0]['occurrences'])
        
        expected_occurrences = [
            {
                'model': TaxonProfile,
                'occurrences': [self.taxon_profile],
                'verbose_model_name': 'Taxon Profile',
                'verbose_occurrences': ['exists as a Taxon Profile'],
            }
        ]
        
        self.assertEqual(occurrences, expected_occurrences)
        
        occurrences_2 = view.get_taxon_occurrences(self.taxon_2)
        self.assertEqual(occurrences_2, [])
        
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        context_data = view.get_context_data(**view.kwargs)
        self.assertEqual(context_data['from_taxon'], None)
        self.assertEqual(context_data['to_taxon'], None)
        self.assertEqual(context_data['analyzed'], False)
        self.assertEqual(context_data['swapped'], False)
        self.assertEqual(context_data['verbose_from_taxon_occurrences'], [])
        self.assertEqual(context_data['verbose_to_taxon_occurrences'], [])
        
    
    @test_settings
    def test_get_form_valid_context_data(self):
        
        view = self.get_view()
        
        post_data = self.get_post_data()
        
        form = view.form_class(data=post_data)
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        occurrences = view.get_taxon_occurrences(self.taxon_2)
        analysis = view.analyze_taxon(self.taxon, self.taxon_2)
        analysis[0]['occurrences'] = list(analysis[0]['occurrences'])
        
        context_data = view.get_form_valid_context_data(form)
        context_data['verbose_from_taxon_occurrences'][0]['occurrences'] = list(context_data['verbose_from_taxon_occurrences'][0]['occurrences'])
        
        self.assertEqual(context_data['from_taxon'], self.taxon)
        self.assertEqual(context_data['to_taxon'], self.taxon_2)
        self.assertEqual(context_data['analyzed'], True)
        self.assertEqual(context_data['swapped'], False)
        self.assertEqual(context_data['verbose_from_taxon_occurrences'], analysis)
        self.assertEqual(context_data['verbose_to_taxon_occurrences'], occurrences)
    
    @test_settings
    def test_form_valid(self):
        
        view = self.get_view()
        
        post_data = self.get_post_data()
        
        form = view.form_class(data=post_data)
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['analyzed'], True)
        
        tp = TaxonProfile.objects.get(pk=self.taxon_profile.pk)
        self.assertEqual(tp.taxon, self.taxon_2)
        
        
    @test_settings
    def test_swap_TaxonRelationship(self):
        
        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)
        pica_pica = models.TaxonTreeModel.objects.get(taxon_latname='Pica pica')
        pica_pica = LazyTaxon(instance=pica_pica)
        
        #swap to
        larix_decidua = models.TaxonTreeModel.objects.get(taxon_latname='Larix decidua')
        larix_decidua = LazyTaxon(instance=larix_decidua)
        
        turdus_merula = models.TaxonTreeModel.objects.get(taxon_latname='Turdus merula')
        turdus_merula = LazyTaxon(instance=turdus_merula)
        
        relationship_type = TaxonRelationshipType(
            backbonetaxonomy = self.generic_content,
            relationship_name = 'Predation',
            taxon_role = 'Predator',
            related_taxon_role = 'Prey',
        )

        relationship_type.save()

        relationship = TaxonRelationship(
            backbonetaxonomy = self.generic_content,
            taxon = lacerta_agilis,
            relationship_type = relationship_type,
        )

        relationship.set_related_taxon(pica_pica)
        relationship.save()
        
        
        
        post_data = {
            'from_taxon_0' : 'taxonomy.sources.col',
            'from_taxon_1' : lacerta_agilis.taxon_latname,
            'from_taxon_2' : lacerta_agilis.taxon_author,
            'from_taxon_3' : str(lacerta_agilis.name_uuid),
            'from_taxon_4' : lacerta_agilis.taxon_nuid,
            'to_taxon_0' : 'taxonomy.sources.col',
            'to_taxon_1' : larix_decidua.taxon_latname,
            'to_taxon_2' : larix_decidua.taxon_author,
            'to_taxon_3' : str(larix_decidua.name_uuid),
            'to_taxon_4' : larix_decidua.taxon_nuid,
        }
        
        view = self.get_view()
        
        form = view.form_class(data=post_data)
        form.is_valid()
        
        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['analyzed'], True)
        
        updated_relationship = TaxonRelationship.objects.get(pk=relationship.pk)
        self.assertEqual(updated_relationship.taxon, larix_decidua)
        
        
        # update related taxon
        post_data = {
            'from_taxon_0' : 'taxonomy.sources.col',
            'from_taxon_1' : pica_pica.taxon_latname,
            'from_taxon_2' : pica_pica.taxon_author,
            'from_taxon_3' : str(pica_pica.name_uuid),
            'from_taxon_4' : pica_pica.taxon_nuid,
            'to_taxon_0' : 'taxonomy.sources.col',
            'to_taxon_1' : turdus_merula.taxon_latname,
            'to_taxon_2' : turdus_merula.taxon_author,
            'to_taxon_3' : str(turdus_merula.name_uuid),
            'to_taxon_4' : turdus_merula.taxon_nuid,
        }
        
        form = view.form_class(data=post_data)
        form.is_valid()
        self.assertEqual(form.errors, {})
        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['analyzed'], True)
        updated_relationship = TaxonRelationship.objects.get(pk=relationship.pk)
        self.assertEqual(updated_relationship.related_taxon, turdus_merula)

class TestAnalyzeTaxon(ViewTestMixin, WithAdminOnly, WithLoggedInUser, WithUser, WithBackboneTaxonomy,
                           WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'analyze_taxon'
    view_class = AnalyzeTaxon
    
    def setUp(self):
        super().setUp()
        
        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)
        
        self.taxon = lacerta_agilis
        
        picea_abies = models.TaxonTreeModel.objects.get(taxon_latname='Picea abies')
        picea_abies = LazyTaxon(instance=picea_abies)
        self.taxon_2 = picea_abies
        
        taxon_profiles_link = self.meta_app.get_generic_content_links(TaxonProfiles).first()
        taxon_profiles = taxon_profiles_link.generic_content
        
        self.taxon_profile = TaxonProfile(
            taxon_profiles=taxon_profiles,
            taxon=self.taxon,
        )
        
        self.taxon_profile.save()

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
        }
        return url_kwargs
    
    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view
    
    def get_post_data(self):
        
        post_data = {
            'from_taxon_0' : 'taxonomy.sources.col',
            'from_taxon_1' : self.taxon.taxon_latname,
            'from_taxon_2' : self.taxon.taxon_author,
            'from_taxon_3' : str(self.taxon.name_uuid),
            'from_taxon_4' : self.taxon.taxon_nuid,
            'to_taxon_0' : 'taxonomy.sources.col',
            'to_taxon_1' : self.taxon_2.taxon_latname,
            'to_taxon_2' : self.taxon_2.taxon_author,
            'to_taxon_3' : str(self.taxon_2.name_uuid),
            'to_taxon_4' : self.taxon_2.taxon_nuid,
        }
        
        return post_data
    
    @test_settings
    def test_form_valid(self):
        
        view = self.get_view()
        post_data = self.get_post_data()
        form = view.form_class(data=post_data)
        form.is_valid()
        self.assertEqual(form.errors, {})
        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['analyzed'], True)
        self.assertEqual(response.context_data['swapped'], False)
        
        
class TestUpdateTaxonReferences(ViewTestMixin, WithAdminOnly, WithLoggedInUser, WithUser, WithBackboneTaxonomy,
                           WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'analyze_taxon'
    view_class = UpdateTaxonReferences
    
    def setUp(self):
        super().setUp()
        
        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        
        picea_abies = models.TaxonTreeModel.objects.get(taxon_latname='Picea abies')
        self.picea_abies = LazyTaxon(instance=picea_abies)
        
        taxon_profiles_link = self.meta_app.get_generic_content_links(TaxonProfiles).first()
        taxon_profiles = taxon_profiles_link.generic_content
        
        self.taxon_profile = TaxonProfile(
            taxon_profiles=taxon_profiles,
        )
        
        self.taxon_profile.set_taxon(self.picea_abies)
        
        self.taxon_profile.save()
        
        self.reference_lazy_taxon = LazyTaxon(instance=self.taxon_profile)
        
        outdated_taxon_kwargs = {
            'taxon_source': self.picea_abies.taxon_source,
            'taxon_latname': self.picea_abies.taxon_latname,
            'taxon_author': self.picea_abies.taxon_author,
            'taxon_nuid': '001002003',
            'name_uuid': 'aaaaaaaa-47ac-4ad4-bd6a-4158c78165be', # a uuid v4
        }
        
        self.outdated_lazy_taxon = LazyTaxon(**outdated_taxon_kwargs)
        self.taxon_profile.set_taxon(self.outdated_lazy_taxon)
        self.taxon_profile.save()
        
    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
        }
        return url_kwargs
    
    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view
    
    @test_settings
    def test_analyze(self):
        view = self.get_view()
        result = view.analyze()
        
        expected_result = [
            {
                'instance': self.taxon_profile,
                'taxon': self.outdated_lazy_taxon,
                'errors': [
                    'Taxon Picea abies (L.) H. Karst. has changed its position in Catalogue Of Life 2019',
                    'Taxon Picea abies (L.) H. Karst. has changed its identifier in Catalogue Of Life 2019'
                ],
                'updated': False
            }
        ]
        
        self.assertEqual(result, expected_result)
    
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        result = view.analyze()
        
        context_data = view.get_context_data(**view.kwargs)
        
        self.assertEqual(context_data['analyzed'], True)
        self.assertEqual(context_data['updated'], False)
        self.assertEqual(context_data['result'], result)
        
    
    @test_settings
    def test_post(self):
        
        view = self.get_view()
        
        view.request.method = 'POST'
        
        response = view.post(view.request, **view.kwargs)
        
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(response.context_data['analyzed'], False)
        self.assertEqual(response.context_data['updated'], True)
        
        
        expected_result = [
            {
                'instance': self.taxon_profile,
                'taxon': self.reference_lazy_taxon,
                'errors': [
                    'Taxon Picea abies (L.) H. Karst. has changed its position in Catalogue Of Life 2019',
                    'Taxon Picea abies (L.) H. Karst. has changed its identifier in Catalogue Of Life 2019'
                ],
                'updated': True
            }
        ]
        
        self.assertEqual(response.context_data['result'], expected_result)
        
        


class WithTaxonRelationship:
    
    def setUp(self):
        super().setUp()
        
        
        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lacerta_agilis = LazyTaxon(instance=lacerta_agilis)
        pica_pica = models.TaxonTreeModel.objects.get(taxon_latname='Pica pica')
        pica_pica = LazyTaxon(instance=pica_pica)
        
        self.relationship_type = TaxonRelationshipType(
            backbonetaxonomy = self.generic_content,
            relationship_name = 'Predation',
            taxon_role = 'Predator',
            related_taxon_role = 'Prey',
        )

        self.relationship_type.save()

        self.relationship = TaxonRelationship(
            backbonetaxonomy = self.generic_content,
            taxon = lacerta_agilis,
            relationship_type = self.relationship_type,
        )

        self.relationship.set_related_taxon(pica_pica)
        self.relationship.save()


class TestTaxonRelationships(ViewTestMixin, WithTaxonRelationship, WithAdminOnly, WithLoggedInUser, WithUser,
                             WithBackboneTaxonomy, WithMetaApp, WithTenantClient, TenantTestCase):


    url_name = 'taxon_relationships'
    view_class = TaxonRelationships       
        
        
    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'backbone_id' : self.generic_content.id,
        }
        return url_kwargs
    
    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()
        view.backbone = self.generic_content
        view.meta_app = self.meta_app
        
        context_data = view.get_context_data(**view.kwargs)
        
        existing_types = TaxonRelationshipType.objects.filter(backbonetaxonomy=self.generic_content)
        existing_relationships = TaxonRelationship.objects.filter(backbonetaxonomy=self.generic_content)
        
        self.assertEqual(context_data['generic_content'], self.generic_content)
        self.assertEqual(context_data['meta_app'], self.meta_app)
        self.assertEqual(list(context_data['taxon_relationship_types']), list(existing_types))
        self.assertEqual(list(context_data['taxon_relationships']), list(existing_relationships))
        
        
class TestCreateTaxonRelationshipType(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser,
                                     WithBackboneTaxonomy, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'create_taxon_relationship_type'
    view_class = ManageTaxonRelationshipType

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id': self.meta_app.id,
            'backbone_id': self.generic_content.id,
        }
        return url_kwargs

    @test_settings
    def test_set_instances(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        self.assertEqual(view.backbonetaxonomy, self.generic_content)
        self.assertEqual(view.meta_app, self.meta_app)
        self.assertEqual(view.relationship_type, None)

    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        context_data = view.get_context_data(**view.kwargs)
        self.assertEqual(context_data['backbone_taxonomy'], self.generic_content)
        self.assertEqual(context_data['meta_app'], self.meta_app)
        self.assertEqual(context_data['relationship_type'], None)
        
        
    @test_settings
    def test_get_initial(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        initial = view.get_initial()
        self.assertEqual(initial, {})
    
    
    @test_settings
    def test_form_valid(self):
        
        post_data = {
            'input_language' : self.meta_app.primary_language,
            'relationship_name' : 'Predation',
            'taxon_role' : 'Predator',
            'related_taxon_role' : 'Prey',
        }
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        
        form = view.form_class(data=post_data)
        form.is_valid()
        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'], True)
        
        create_relationship_type = TaxonRelationshipType.objects.filter(
            backbonetaxonomy=self.generic_content,
            relationship_name='Predation').first()
        
        self.assertIsNotNone(create_relationship_type)
        self.assertEqual(create_relationship_type.taxon_role, 'Predator')
        self.assertEqual(create_relationship_type.related_taxon_role, 'Prey')
        
        
class TestUpdateTaxonRelationshipType(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser,
            WithTaxonRelationship, WithBackboneTaxonomy, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'update_taxon_relationship_type'
    view_class = ManageTaxonRelationshipType
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'meta_app_id': self.meta_app.id,
            'backbone_id': self.generic_content.id,
            'relationship_type_id': self.relationship_type.id,
        }
        return url_kwargs
    
    @test_settings
    def test_set_instances(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        self.assertEqual(view.backbonetaxonomy, self.generic_content)
        self.assertEqual(view.meta_app, self.meta_app)
        self.assertEqual(view.relationship_type, self.relationship_type)
        
    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        context_data = view.get_context_data(**view.kwargs)
        self.assertEqual(context_data['backbone_taxonomy'], self.generic_content)
        self.assertEqual(context_data['meta_app'], self.meta_app)
        self.assertEqual(context_data['relationship_type'], self.relationship_type)
        
    @test_settings
    def test_get_initial(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        initial = view.get_initial()
                
        expected_initial = {
            'relationship_name' : self.relationship_type.relationship_name,
            'taxon_role' : self.relationship_type.taxon_role,
            'related_taxon_role' : self.relationship_type.related_taxon_role,
        }
        
        self.assertEqual(initial, expected_initial)


    @test_settings
    def test_form_valid(self):
        
        post_data = {
            'input_language' : self.meta_app.primary_language,
            'relationship_name' : 'New name',
            'taxon_role' : 'New taxon role',
            'related_taxon_role' : 'New related taxon role',
        }
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        
        form = view.form_class(data=post_data)
        form.is_valid()
        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'], True)
        
        self.relationship_type.refresh_from_db()

        self.assertIsNotNone(self.relationship_type)
        self.assertEqual(self.relationship_type.relationship_name, 'New name')
        self.assertEqual(self.relationship_type.taxon_role, 'New taxon role')
        self.assertEqual(self.relationship_type.related_taxon_role, 'New related taxon role')
        
        
class TestDeleteTaxonRelationshipType(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser,
            WithTaxonRelationship, WithBackboneTaxonomy, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'delete_taxon_relationship_type'
    view_class = DeleteTaxonRelationshipType
    
    def get_url_kwargs(self):
        
        url_kwargs = {
            'meta_app_id': self.meta_app.id,
            'pk': self.relationship_type.id,
        }
        return url_kwargs
        
    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.object = self.relationship_type
        
        context_data = view.get_context_data(**view.kwargs)
        self.assertEqual(context_data['backbone_taxonomy'], self.generic_content)
        self.assertEqual(context_data['meta_app'], self.meta_app)
        
    @test_settings
    def test_post(self):
        
        self.make_user_tenant_admin(self.user, self.tenant)
        
        view = self.get_view()
        view.meta_app = self.meta_app
        
        relationship_type_id = self.relationship_type.id
        
        relationship_type_qry = TaxonRelationshipType.objects.filter(id=relationship_type_id)
        self.assertTrue(relationship_type_qry.exists())
        
        response = self.tenant_client.post(view.request.path, data={}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['deleted'], True)
        
        self.assertFalse(relationship_type_qry.exists())
        
        
class TestCreateTaxonRelationship(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser,
                             WithBackboneTaxonomy, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'create_taxon_relationship'
    view_class = ManageTaxonRelationship

    def setUp(self):
        super().setUp()

        taxon_source = 'taxonomy.sources.col'
        models = TaxonomyModelRouter(taxon_source)
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        self.lacerta_agilis = LazyTaxon(instance=lacerta_agilis)
        pica_pica = models.TaxonTreeModel.objects.get(taxon_latname='Pica pica')
        self.pica_pica = LazyTaxon(instance=pica_pica)

        self.relationship_type = TaxonRelationshipType(
            backbonetaxonomy=self.generic_content,
            relationship_name='Predation',
            taxon_role='Predator',
            related_taxon_role='Prey',
        )

        self.relationship_type.save()
        
    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id': self.meta_app.id,
            'backbone_id': self.generic_content.id,
            'relationship_type_id': self.relationship_type.id,
        }
        return url_kwargs
    
    @test_settings
    def test_set_instances(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        self.assertEqual(view.backbone_taxonomy, self.generic_content)
        self.assertEqual(view.meta_app, self.meta_app)
        self.assertEqual(view.relationship_type, self.relationship_type)
        self.assertEqual(view.relationship, None)
        
    @test_settings
    def test_get_form(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        form = view.get_form()
        self.assertEqual(form.__class__, TaxonRelationshipForm)
        self.assertEqual(form.relationship_type, self.relationship_type)
        
    @test_settings
    def test_get_initial(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        initial = view.get_initial()
        self.assertEqual(initial, {})


    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        context_data = view.get_context_data(**view.kwargs)
        self.assertEqual(context_data['backbone_taxonomy'], self.generic_content)
        self.assertEqual(context_data['meta_app'], self.meta_app)
        self.assertEqual(context_data['relationship_type'], self.relationship_type)
        self.assertEqual(context_data['relationship'], None)
        
        
    @test_settings
    def test_form_valid(self):
        
        post_data = {
            'input_language' : self.meta_app.primary_language,
            'taxon_0' : self.lacerta_agilis.taxon_source,
            'taxon_1' : self.lacerta_agilis.taxon_latname,
            'taxon_2' : self.lacerta_agilis.taxon_author,
            'taxon_3' : str(self.lacerta_agilis.name_uuid),
            'taxon_4' : self.lacerta_agilis.taxon_nuid,
            'related_taxon_0' : self.pica_pica.taxon_source,
            'related_taxon_1' : self.pica_pica.taxon_latname,
            'related_taxon_2' : self.pica_pica.taxon_author,
            'related_taxon_3' : str(self.pica_pica.name_uuid),
            'related_taxon_4' : self.pica_pica.taxon_nuid,
            'description' : 'A description of the relationship',
        }
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        
        form = view.form_class(data=post_data, relationship_type=self.relationship_type)
        form.is_valid()
        self.assertEqual(form.errors, {})
        
        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'], True)
        
        create_relationship = TaxonRelationship.objects.filter(
            backbonetaxonomy=self.generic_content,
            name_uuid=self.lacerta_agilis.name_uuid,
            relationship_type=self.relationship_type).first()
        
        self.assertIsNotNone(create_relationship)
        self.assertEqual(create_relationship.taxon, self.lacerta_agilis)
        self.assertEqual(create_relationship.related_taxon, self.pica_pica)
        self.assertEqual(create_relationship.description, 'A description of the relationship')
        
        
class TestUpdateTaxonRelationship(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser,
                             WithTaxonRelationship, WithBackboneTaxonomy, WithMetaApp, WithTenantClient, TenantTestCase):
    
    url_name = 'update_taxon_relationship'
    view_class = ManageTaxonRelationship
    
    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id': self.meta_app.id,
            'backbone_id': self.generic_content.id,
            'relationship_type_id': self.relationship_type.id,
            'relationship_id': self.relationship.id,
        }
        return url_kwargs
    
    @test_settings
    def test_set_instances(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        self.assertEqual(view.backbone_taxonomy, self.generic_content)
        self.assertEqual(view.meta_app, self.meta_app)
        self.assertEqual(view.relationship_type, self.relationship_type)
        self.assertEqual(view.relationship, self.relationship)
        
    @test_settings
    def test_get_form(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        form = view.get_form()
        self.assertEqual(form.__class__, TaxonRelationshipForm)
        self.assertEqual(form.relationship_type, self.relationship_type)

    @test_settings
    def test_get_initial(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        initial = view.get_initial()
        
        expected_initial = {
            'taxon' : self.relationship.taxon,
            'related_taxon' : self.relationship.related_taxon,
            'description' : self.relationship.description,
        }
                
        self.assertEqual(initial, expected_initial)
        
        
    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)
        context_data = view.get_context_data(**view.kwargs)
        self.assertEqual(context_data['backbone_taxonomy'], self.generic_content)
        self.assertEqual(context_data['meta_app'], self.meta_app)
        self.assertEqual(context_data['relationship_type'], self.relationship_type)
        self.assertEqual(context_data['relationship'], self.relationship)
        
    @test_settings
    def test_form_valid(self):
        
        models = TaxonomyModelRouter('taxonomy.sources.col')
        turdus_merula = models.TaxonTreeModel.objects.get(taxon_latname='Turdus merula')
        turdus_merula = LazyTaxon(instance=turdus_merula)

        larix_decidua = models.TaxonTreeModel.objects.get(taxon_latname='Larix decidua')
        larix_decidua = LazyTaxon(instance=larix_decidua)

        post_data = {
            'input_language' : self.meta_app.primary_language,
            'taxon_0' : turdus_merula.taxon_source,
            'taxon_1' : turdus_merula.taxon_latname,
            'taxon_2' : turdus_merula.taxon_author,
            'taxon_3' : str(turdus_merula.name_uuid),
            'taxon_4' : turdus_merula.taxon_nuid,
            'related_taxon_0' : larix_decidua.taxon_source,
            'related_taxon_1' : larix_decidua.taxon_latname,
            'related_taxon_2' : larix_decidua.taxon_author,
            'related_taxon_3' : str(larix_decidua.name_uuid),
            'related_taxon_4' : larix_decidua.taxon_nuid,
            'description' : 'An updated description of the relationship',
        }
        
        view = self.get_view()
        view.meta_app = self.meta_app
        view.set_instances(**view.kwargs)

        self.assertEqual(view.relationship, self.relationship)

        form = view.form_class(data=post_data, relationship_type=self.relationship_type)
        form.is_valid()
        self.assertEqual(form.errors, {})

        self.assertEqual(form.cleaned_data['taxon'], turdus_merula)
        self.assertEqual(form.cleaned_data['related_taxon'], larix_decidua)
        self.assertEqual(form.cleaned_data['description'], 'An updated description of the relationship')

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'], True)
        
        self.relationship = TaxonRelationship.objects.get(id=self.relationship.id)
                
        self.assertIsNotNone(self.relationship)
        self.assertEqual(self.relationship.related_taxon.taxon_latname, larix_decidua.taxon_latname)
        self.assertEqual(self.relationship.taxon.taxon_latname, turdus_merula.taxon_latname)
        self.assertEqual(self.relationship.description, 'An updated description of the relationship')
        
        
class TestDeleteTaxonRelationship(ViewTestMixin, WithAjaxAdminOnly, WithLoggedInUser, WithUser,
            WithTaxonRelationship, WithBackboneTaxonomy, WithMetaApp, WithTenantClient, TenantTestCase):
    
    url_name = 'delete_taxon_relationship'
    view_class = DeleteTaxonRelationship
    
    def get_url_kwargs(self):
        return {
            'meta_app_id': self.meta_app.id,
            'pk': self.relationship.id
        }
        
    @test_settings
    def test_get_context_data(self):
        view = self.get_view()
        view.meta_app = self.meta_app
        view.object = self.relationship
        
        context_data = view.get_context_data(**view.kwargs)
        self.assertEqual(context_data['backbone_taxonomy'], self.generic_content)
        self.assertEqual(context_data['meta_app'], self.meta_app)
        
    @test_settings
    def test_post(self):
        
        self.make_user_tenant_admin(self.user, self.tenant)
        
        view = self.get_view()
        view.meta_app = self.meta_app
        
        relationship_id = self.relationship.id
        
        relationship_qry = TaxonRelationship.objects.filter(id=relationship_id)
        self.assertTrue(relationship_qry.exists())
        
        response = self.tenant_client.post(view.request.path, data={}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['deleted'], True)
        
        self.assertFalse(relationship_qry.exists())