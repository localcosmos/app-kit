from django.test import TestCase
from django_tenants.test.cases import TenantTestCase

from django import forms

from app_kit.tests.common import test_settings, powersetdic
from app_kit.tests.mixins import WithMetaApp, WithFormTest

from app_kit.features.maps.forms import (MapsOptionsForm, ProjectAreaForm, TaxonomicFilterForm)
from app_kit.features.maps.models import Map, FilterTaxon

from taxonomy.lazy import LazyTaxon
from taxonomy.models import TaxonomyModelRouter

from .mixins import WithMap, WithMapTaxonomicFilter


import json

class TestMapOptionsForm(WithMetaApp, WithFormTest, TenantTestCase):

    @test_settings
    def test_init(self):


        post_data = {
            'initial_latitude' : '11',
            'initial_longitude' : '49',
            'initial_zoom' : '3',
        }

        maps = Map.objects.create('Test maps', self.meta_app.primary_language)

        form_kwargs = {
            'meta_app' : self.meta_app,
            'generic_content' : maps,
        }

        form = MapsOptionsForm(**form_kwargs)

        self.perform_form_test(MapsOptionsForm, post_data, form_kwargs=form_kwargs)


class TestProjectAreaForm(WithFormTest, TenantTestCase):

    @test_settings
    def test_form(self):

        form = ProjectAreaForm()

        geojson = { "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [ [100.0, 0.0], [101.0, 0.0], [101.0, 1.0], [100.0, 1.0], [100.0, 0.0] ]
                        ]
                    },
                }
            ]
        }

        post_data = {
            'area' : json.dumps(geojson),
        }

        self.perform_form_test(ProjectAreaForm, post_data)


    @test_settings
    def test_clean_area(self):

        geojson = 'wrong { }'

        post_data = {
            'area' : geojson,
        }

        form = ProjectAreaForm()
        form.cleaned_data = post_data

        with self.assertRaises(forms.ValidationError):
            form.clean_area()
        


class TestTaxonomicFilterForm(WithMapTaxonomicFilter, WithMap, WithMetaApp, WithFormTest, TenantTestCase):

    @test_settings
    def test_form_no_filter(self):
        
        map = self.create_map()

        form = TaxonomicFilterForm()
        self.assertEqual(form.taxonomic_filter, None)

        lazy_lacerta = self.get_taxon()

        post_data = {
            'name': 'test name',
            'input_language': 'de',
        }

        self.perform_form_test(TaxonomicFilterForm, post_data)

        taxon_post_data = self.get_taxon_post_data(lazy_lacerta)
        post_data.update(taxon_post_data)

        form = TaxonomicFilterForm(data=post_data)

        form.is_valid()
        self.assertEqual(form.errors, {})


    @test_settings
    def test_form_with_filter(self):
        
        taxonomic_filter = self.create_taxonomic_filter()

        form = TaxonomicFilterForm(taxonomic_filter=taxonomic_filter)
        self.assertEqual(form.taxonomic_filter, taxonomic_filter)


    @test_settings
    def test_clean_taxon(self):
        
        # test create
        lazy_lacerta = self.get_taxon()

        post_data = {
            'name': 'test name',
            'input_language': 'de',
        }

        taxon_post_data = self.get_taxon_post_data(lazy_lacerta)
        post_data.update(taxon_post_data)

        form = TaxonomicFilterForm(data=post_data)

        is_valid = form.is_valid()
        self.assertEqual(form.errors, {})

        self.assertIn('taxon', form.cleaned_data)

        taxon = form.clean_taxon()

        self.assertEqual(taxon, lazy_lacerta)

        # add Lacerta
        taxonomic_filter = self.create_taxonomic_filter()
        form_w_filter = TaxonomicFilterForm(data=post_data, taxonomic_filter=taxonomic_filter)

        is_valid = form_w_filter.is_valid()
        self.assertEqual(form_w_filter.errors, {})

        self.assertIn('taxon', form_w_filter.cleaned_data)

        taxon = form_w_filter.clean_taxon()

        self.assertEqual(taxon, lazy_lacerta)

        filter_taxon = FilterTaxon(
            taxonomic_filter=taxonomic_filter,
        )

        filter_taxon.set_taxon(lazy_lacerta)
        filter_taxon.save()

        form_w_filter_2 = TaxonomicFilterForm(data=post_data, taxonomic_filter=taxonomic_filter)
        form_w_filter_2.cleaned_data = {
            'taxon': lazy_lacerta
        }

        with self.assertRaises(forms.ValidationError):
            form_w_filter_2.clean_taxon()


        # test subtaxon
        models = TaxonomyModelRouter('taxonomy.sources.col')
        lacerta_agilis = models.TaxonTreeModel.objects.get(taxon_latname='Lacerta agilis')
        lazy_lacerta_agilis = LazyTaxon(instance=lacerta_agilis)
        form_w_filter_3 = TaxonomicFilterForm(data=post_data, taxonomic_filter=taxonomic_filter)
        form_w_filter_3.cleaned_data = {
            'taxon': lazy_lacerta_agilis
        }

        with self.assertRaises(forms.ValidationError):
            form_w_filter_3.clean_taxon()


