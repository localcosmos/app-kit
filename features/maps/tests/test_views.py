from django.test import TestCase, RequestFactory
from django_tenants.test.cases import TenantTestCase
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from app_kit.tests.common import test_settings

from app_kit.tests.mixins import (WithMetaApp, WithTenantClient, WithUser, WithLoggedInUser, WithAjaxAdminOnly,
                                  WithAdminOnly, WithFormTest, ViewTestMixin)

from localcosmos_server.taxonomy.forms import AddSingleTaxonForm

from .mixins import WithMap, WithMapTaxonomicFilter


from app_kit.features.maps.views import (ManageMaps, ManageProjectArea, ManageTaxonomicFilter, GetTaxonomicFilters,
    DeleteFilterTaxon)
from app_kit.features.maps.models import Map, MapGeometries, MapTaxonomicFilter, FilterTaxon
from app_kit.features.maps.forms import ProjectAreaForm, TaxonomicFilterForm

from app_kit.models import MetaAppGenericContent

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon

import json


class WithMaps:

    def setUp(self):
        super().setUp()
        self.content_type = ContentType.objects.get_for_model(Map)
        
        # create link
        generic_content_name = '{0} {1}'.format(self.meta_app.name, Map.__class__.__name__)
        self.generic_content = Map.objects.create(generic_content_name, self.meta_app.primary_language)

        self.link = MetaAppGenericContent(
            meta_app=self.meta_app,
            content_type=self.content_type,
            object_id=self.generic_content.id
        )

        self.link.save()
        

class TestManageMaps(WithMaps, ViewTestMixin, WithAdminOnly, WithUser, WithLoggedInUser, WithMetaApp,
                     WithTenantClient, TenantTestCase):


    url_name = 'manage_map'
    view_class = ManageMaps


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'content_type_id' : self.content_type.id,
            'object_id' : self.generic_content.id,
        }
        return url_kwargs



class TestManageProjectArea(WithMaps, ViewTestMixin, WithAdminOnly, WithUser, WithLoggedInUser, WithMetaApp,
                     WithTenantClient, TenantTestCase):


    url_name = 'manage_project_area'
    view_class = ManageProjectArea


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
        view.map = self.generic_content
        view.project_area = None
        return view


    def get_geojson(self):

        geojson = {
            "type":"FeatureCollection",
            "features": [
                {
                    "type":"Feature",
                    "properties":{},
                    "geometry":{
                        "type":"Polygon",
                        "coordinates":[
                            [[5.097656,48.004625],[5.097656,50.541363],[10.83252,50.541363],[10.83252,48.004625],[5.097656,48.004625]]
                        ]
                    }
                },
            ]
        }

        return geojson
    

    def create_project_area(self):

        geojson = self.get_geojson()

        polygons = []

        for feature in geojson['features']:
            polygon = GEOSGeometry(json.dumps(feature['geometry']), srid=4326)
            polygons.append(polygon)
            
        multipoly = MultiPolygon(tuple(polygons), srid=4326)

        project_area = MapGeometries(
            map = self.generic_content,
            geometry_type = 'project_area',
            geometry = multipoly,
        )

        project_area.save()
        
        return project_area


    @test_settings
    def test_get_context_data(self):
        # no area
        view = self.get_view()
        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['map'], self.generic_content)
        self.assertEqual(context['project_area'], None)
        self.assertEqual(context['success'], False)

        # with area
        project_area = self.create_project_area()
        
        view.project_area = project_area
        serialized_project_area = view.serialize_project_area()

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['map'], self.generic_content)
        self.assertEqual(context['project_area'], serialized_project_area)
        self.assertEqual(context['success'], False)


    @test_settings
    def test_serialize_project_area(self):

        view = self.get_view()
        project_area = self.create_project_area()
        
        view.project_area = project_area
        serialized_project_area = view.serialize_project_area()

        self.assertEqual(serialized_project_area['type'], 'FeatureCollection')
        self.assertEqual(len(serialized_project_area['features']), 1)
        self.assertEqual(serialized_project_area['features'][0]['type'], 'Feature')
        self.assertIn('geometry', serialized_project_area['features'][0])


    @test_settings
    def test_get_initial(self):
        
        # no area
        view = self.get_view()

        initial = view.get_initial()
        self.assertFalse('area' in initial)

        project_area = self.create_project_area()
        view.project_area = project_area

        initial = view.get_initial()

        self.assertTrue('area' in initial)
        self.assertEqual(type(initial['area']), str)


    @test_settings
    def test_remove_project_area(self):

        view = self.get_view()
        view.remove_project_area()

        project_area = self.create_project_area()
        project_area_pk = project_area.pk

        qry = MapGeometries.objects.filter(pk=project_area_pk)

        self.assertTrue(qry.exists())
        view.project_area = project_area

        view.remove_project_area()
        self.assertFalse(qry.exists())


    @test_settings
    def test_form_valid(self):

        view = self.get_view()

        area = self.get_geojson()

        data = {
            'area' : json.dumps(area),
        }

        form = ProjectAreaForm(data=data)
        form.is_valid()

        self.assertEqual(form.errors, {})

        response = view.form_valid(form)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['success'], True)
        self.assertEqual(response.context_data['form'].__class__, ProjectAreaForm)

        qry = MapGeometries.objects.filter(map=self.generic_content)
        self.assertTrue(qry.exists())

        # remove area
        data_2 = {}
        form_2 = ProjectAreaForm(data=data_2)
        form_2.is_valid()

        self.assertEqual(form_2.errors, {})
        response_2 = view.form_valid(form_2)

        self.assertEqual(response_2.status_code, 200)
        self.assertFalse(qry.exists())


        # remove area, #2
        project_area = self.create_project_area()
        view.project_area = project_area
        self.assertTrue(qry.exists())

        data_3 = {
            "type":"FeatureCollection",
            "features":[],
        }
        form_3 = ProjectAreaForm(data=data_3)
        form_3.is_valid()

        self.assertEqual(form_3.errors, {})
        response_3 = view.form_valid(form_3)

        self.assertEqual(response_3.status_code, 200)
        self.assertFalse(qry.exists())


      
class TestCreateTaxonomicFilter(WithMapTaxonomicFilter, WithMap, WithMaps, ViewTestMixin, WithAjaxAdminOnly,
    WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):
    
    
    url_name = 'create_map_taxonomic_filter'
    view_class = ManageTaxonomicFilter

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'map_id' : self.generic_content.id,
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        view.set_taxonomic_filter(**view.kwargs)
        return view


    @test_settings
    def test_set_taxonomic_filter(self):
        view = super().get_view()
        self.assertFalse(hasattr(view, 'map'))
        view.set_taxonomic_filter(**self.get_url_kwargs())

        self.assertEqual(view.map, self.generic_content)
        self.assertEqual(view.taxonomic_filter, None)
        self.assertEqual(view.content_type, self.content_type)


    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['taxonomic_filter'], None)
        self.assertEqual(context['map'], self.generic_content)
        self.assertEqual(context['content_type'], self.content_type)
        self.assertFalse(context['success'])
        self.assertEqual(context['add_taxon_form'].__class__, AddSingleTaxonForm)

    @test_settings
    def test_get_initial(self):
        view = self.get_view()
        initial = view.get_initial()
        self.assertFalse('name' in initial)

    @test_settings
    def test_get_form_kwargs(self):
        view = self.get_view()
        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs['taxonomic_filter'], None)

    @test_settings
    def test_form_valid(self):
        
        view = self.get_view()

        post_data = {
            'name': 'test name',
            'input_language': 'de',
        }

        form = TaxonomicFilterForm(data=post_data)

        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        query = MapTaxonomicFilter.objects.filter(name='test name')

        self.assertFalse(query.exists())

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data['success'])
        self.assertTrue(query.exists())

    @test_settings 
    def test_form_valid_with_taxon(self):
        
        view = self.get_view()

        post_data = {
            'name': 'test name',
            'input_language': 'de',
        }

        lazy_lacerta = self.get_taxon()
        taxon_post_data = self.get_taxon_post_data(lazy_lacerta)
        post_data.update(taxon_post_data)

        form = TaxonomicFilterForm(data=post_data)

        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        query = MapTaxonomicFilter.objects.filter(name='test name')

        self.assertFalse(query.exists())

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data['success'])
        self.assertTrue(query.exists())

        taxon_query = FilterTaxon.objects.filter(taxonomic_filter=query.first())
        self.assertTrue(taxon_query.exists())
        self.assertEqual(taxon_query.first().taxon, lazy_lacerta)


class TestManageTaxonomicFilter(WithMapTaxonomicFilter, WithMap, WithMaps, ViewTestMixin, WithAjaxAdminOnly,
    WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):
    
    
    url_name = 'manage_map_taxonomic_filter'
    view_class = ManageTaxonomicFilter

    def setUp(self):
        super().setUp()
        self.taxonomic_filter = self.create_taxonomic_filter()
        

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'map_id' : self.generic_content.id,
            'taxonomic_filter_id': self.taxonomic_filter.id,
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        view.set_taxonomic_filter(**view.kwargs)
        return view


    @test_settings
    def test_set_taxonomic_filter(self):
        view = super().get_view()
        self.assertFalse(hasattr(view, 'map'))
        view.set_taxonomic_filter(**self.get_url_kwargs())

        self.assertEqual(view.map, self.generic_content)
        self.assertEqual(view.taxonomic_filter, self.taxonomic_filter)
        self.assertEqual(view.content_type, self.content_type)


    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()

        context = view.get_context_data(**view.kwargs)
        self.assertEqual(context['taxonomic_filter'], self.taxonomic_filter)
        self.assertEqual(context['map'], self.generic_content)
        self.assertEqual(context['content_type'], self.content_type)
        self.assertFalse(context['success'])
        self.assertEqual(context['add_taxon_form'].__class__, AddSingleTaxonForm)

    @test_settings
    def test_get_initial(self):
        view = self.get_view()
        initial = view.get_initial()
        self.assertEqual(initial['name'], self.taxonomic_filter.name)

    @test_settings
    def test_get_form_kwargs(self):
        view = self.get_view()
        form_kwargs = view.get_form_kwargs()
        self.assertEqual(form_kwargs['taxonomic_filter'], self.taxonomic_filter)

    @test_settings
    def test_form_valid(self):
        
        view = self.get_view()

        query_1 = MapTaxonomicFilter.objects.filter(name='test filter')
        self.assertTrue(query_1.exists())

        post_data = {
            'name': 'test name updated',
            'input_language': 'de',
        }

        form = TaxonomicFilterForm(data=post_data)

        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        query = MapTaxonomicFilter.objects.filter(name='test name updated')

        self.assertFalse(query.exists())

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data['success'])
        self.assertTrue(query.exists())

    @test_settings 
    def test_form_valid_with_taxon(self):
        
        view = self.get_view()

        query_1 = MapTaxonomicFilter.objects.filter(name='test filter')
        self.assertTrue(query_1.exists())

        post_data = {
            'name': 'test name updated',
            'input_language': 'de',
        }

        lazy_lacerta = self.get_taxon()
        taxon_post_data = self.get_taxon_post_data(lazy_lacerta)
        post_data.update(taxon_post_data)

        form = TaxonomicFilterForm(data=post_data)

        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        query = MapTaxonomicFilter.objects.filter(name='test name updated')

        self.assertFalse(query.exists())

        response = view.form_valid(form)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data['success'])
        self.assertTrue(query.exists())

        taxon_query = FilterTaxon.objects.filter(taxonomic_filter=query.first())
        self.assertTrue(taxon_query.exists())
        self.assertEqual(taxon_query.first().taxon, lazy_lacerta)


class TestGetTaxonomicFilters(WithMapTaxonomicFilter, WithMap, WithMaps, ViewTestMixin, WithAjaxAdminOnly,
    WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'get_map_taxonomic_filters'
    view_class = GetTaxonomicFilters

    def setUp(self):
        super().setUp()
        self.taxonomic_filter = self.create_taxonomic_filter()
        self.map = self.taxonomic_filter.map

    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'map_id' : self.map.id,
        }
        return url_kwargs


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        return view

    @test_settings
    def test_get_context_data(self):

        view = self.get_view()

        context = view.get_context_data(**view.kwargs)

        mtf_ctype = ContentType.objects.get_for_model(self.taxonomic_filter)

        self.assertEqual(list(context['taxonomic_filters']), [self.taxonomic_filter])
        self.assertEqual(context['map_taxonomic_filter_content_type'], mtf_ctype)
        self.assertEqual(context['generic_content'], self.map)


class TestDeleteFilterTaxon(WithMapTaxonomicFilter, WithMap, WithMaps, ViewTestMixin, WithAjaxAdminOnly,
    WithUser, WithLoggedInUser, WithMetaApp, WithTenantClient, TenantTestCase):

    url_name = 'delete_map_filter_taxon'
    view_class = DeleteFilterTaxon

    def setUp(self):
        super().setUp()
        self.taxonomic_filter = self.create_taxonomic_filter()
        self.map = self.taxonomic_filter.map
        
        self.filter_taxon = FilterTaxon(
            taxonomic_filter=self.taxonomic_filter,
        )

        lazy_lacerta = self.get_taxon()

        self.filter_taxon.set_taxon(lazy_lacerta)
        self.filter_taxon.save()


    def get_view(self):
        view = super().get_view()
        view.meta_app = self.meta_app
        view.object = self.filter_taxon
        return view


    def get_url_kwargs(self):
        url_kwargs = {
            'meta_app_id' : self.meta_app.id,
            'map_id' : self.map.id,
            'taxonomic_filter_id': self.taxonomic_filter.id,
            'pk': self.filter_taxon.pk,
        }
        return url_kwargs

    @test_settings
    def test_get_context_data(self):
        
        view = self.get_view()

        context = view.get_context_data(**self.get_url_kwargs())
        self.assertEqual(context['map'], self.map)
        self.assertEqual(context['taxonomic_filter'], self.taxonomic_filter)