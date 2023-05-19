from django_tenants.test.cases import TenantTestCase

from app_kit.tests.common import test_settings
from app_kit.features.maps.models import Map, MapGeometries, MapTaxonomicFilter, FilterTaxon

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon

from taxonomy.lazy import LazyTaxonList, LazyTaxon
from taxonomy.models import TaxonomyModelRouter

from .mixins import WithMap, WithMapTaxonomicFilter

import json


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



class TestMapTaxonomicFilter(WithMapTaxonomicFilter, WithMap, TenantTestCase):

    @test_settings
    def test_create(self):

        app_map = self.create_map()

        taxonfilter = MapTaxonomicFilter(
            map=app_map,
            name='test filter',
        )

        taxonfilter.save()

        self.assertEqual(taxonfilter.map, app_map)
        self.assertEqual(taxonfilter.name, 'test filter')
        self.assertEqual(taxonfilter.position, 0)


    @test_settings
    def test_taxa(self):
        
        map_taxonomic_filter = self.create_taxonomic_filter()
        self.assertEqual(list(map_taxonomic_filter.taxa), [])

        filter_taxon = FilterTaxon(
            taxonomic_filter=map_taxonomic_filter,
        )

        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta')
        lazy_lacerta = LazyTaxon(instance=lacerta)

        filter_taxon.set_taxon(lazy_lacerta)
        filter_taxon.save()

        self.assertEqual(list(map_taxonomic_filter.taxa), [filter_taxon])

    @test_settings
    def test_str(self):
        
        map_taxonomic_filter = self.create_taxonomic_filter()
        self.assertEqual(str(map_taxonomic_filter), 'test filter')


class TestFilterTaxon(WithMapTaxonomicFilter, WithMap, TenantTestCase):

    @test_settings
    def test_create(self):
        
        map_taxonomic_filter = self.create_taxonomic_filter()

        filter_taxon = FilterTaxon(
            taxonomic_filter=map_taxonomic_filter,
        )

        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta')
        lazy_lacerta = LazyTaxon(instance=lacerta)

        filter_taxon.set_taxon(lazy_lacerta)
        filter_taxon.save()

        filter_taxon = FilterTaxon.objects.all().last()
        self.assertEqual(filter_taxon.taxon, lazy_lacerta)
        self.assertEqual(filter_taxon.taxonomic_filter, map_taxonomic_filter)

        # test str
        self.assertEqual(str(filter_taxon), 'Lacerta')

