from django_tenants.test.cases import TenantTestCase

from app_kit.tests.common import test_settings
from app_kit.features.maps.models import Map, MapGeometries

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon

from taxonomy.lazy import LazyTaxonList

import json


class WithMap:

    def create_map(self):
        app_map = Map.objects.create('Test Map', 'en')
        return app_map



class TestMap(WithMap, TenantTestCase):

    @test_settings
    def test_get_primary_localization(self):

        app_map = self.create_map()

        locale = app_map.get_primary_localization()
        self.assertEqual(locale[app_map.name], app_map.name)


    @test_settings
    def test_taxa(self):
        app_map = self.create_map()

        taxa = app_map.taxa()
        self.assertTrue(isinstance(taxa, LazyTaxonList))
        self.assertEqual(taxa.count(), 0)


    @test_settings
    def test_higher_taxa(self):
        app_map = self.create_map()

        higher_taxa = app_map.higher_taxa()
        self.assertTrue(isinstance(higher_taxa, LazyTaxonList))
        self.assertEqual(higher_taxa.count(), 0)


class TestMapGeometries(WithMap, TenantTestCase):

    def get_multipolygon(self):

        geojson = {
            "type":"FeatureCollection","features":[
                    {
                        "type":"Feature",
                        "properties":{},
                        "geometry":{"type":"Polygon","coordinates":[[[5.097656,48.004625],[5.097656,50.541363],[10.83252,50.541363],[10.83252,48.004625],[5.097656,48.004625]]]}
                    },
                    {
                        "type":"Feature",
                        "properties":{},
                        "geometry":{"type":"Polygon","coordinates":[[[1.40625,46.649436],[1.40625,48.034019],[3.779297,48.034019],[3.779297,46.649436],[1.40625,46.649436]]]}
                    }
                ]
            }

        polygons = []

        for feature in geojson['features']:
            polygon = GEOSGeometry(json.dumps(feature['geometry']), srid=4326)
            polygons.append(polygon)
                    
        multipoly = MultiPolygon(tuple(polygons), srid=4326)

        return multipoly
            

    @test_settings
    def test_create(self):

        app_map = self.create_map()

        geometry = self.get_multipolygon()

        map_geometry = MapGeometries(
            map=app_map,
            geometry_type='project_area',
            geometry=geometry,
        )

        map_geometry.save()

        geometry_db = MapGeometries.objects.get(map=app_map)
        self.assertEqual(geometry_db.map, app_map)
        self.assertEqual(geometry_db.geometry_type, 'project_area')        

