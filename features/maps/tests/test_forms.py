from django.test import TestCase
from django_tenants.test.cases import TenantTestCase

from django import forms

from app_kit.tests.common import test_settings, powersetdic
from app_kit.tests.mixins import WithMetaApp, WithFormTest

from app_kit.features.maps.forms import (MapsOptionsForm, ProjectAreaForm)
from app_kit.features.maps.models import Map

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
        
