from app_kit.tests.common import test_settings
from django.conf import settings
from rest_framework.test import APIRequestFactory, APITestCase
from django_tenants.test.cases import TenantTestCase
from rest_framework import status
from django.urls import reverse

from app_kit.tests.mixins import WithTenantClient, WithUser
from django_tenants.utils import tenant_context

import json, subprocess


from app_kit.app_kit_api.views import ObtainLCAuthToken

class TestObtainLCAuthToken(APITestCase):

    @test_settings
    def test_post(self):
        pass


'''
    Test anycluster schema urls
'''
from localcosmos_server.datasets.api.tests.test_views import WithDatasetPostData, CreatedUsersMixin
from localcosmos_server.datasets.models import Dataset
from localcosmos_server.tests.mixins import WithApp, WithObservationForm
from anycluster.tests.common import GEOJSON_RECTANGLE
from anycluster.definitions import GEOMETRY_TYPE_VIEWPORT



MAP_TILESIZE = 256
GRID_SIZE = 256
ZOOM = 10


class WithKmeans:

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        test_database_name = settings.DATABASES['default']['NAME']

        if not test_database_name.startswith('test_'):
            raise ValueError('Not a test database, aborting')
        #psql -f /usr/share/postgresql15/extension/kmeans.sql -d YOURGEODJANGODATABASE
        subprocess.run(['psql', '-f', '/usr/share/postgresql15/extension/kmeans.sql', '-d', test_database_name])

class TestAnyclusterViews(WithDatasetPostData, WithObservationForm, WithUser, WithApp, CreatedUsersMixin,
    WithTenantClient, WithKmeans, TenantTestCase):

    def get_anycluster_url_kwargs(self):

        url_kwargs = {
            'zoom': ZOOM,
            'grid_size': GRID_SIZE,
        }

        return url_kwargs

    @test_settings
    def test_create_dataset(self):
        
        observation_form = self.create_observation_form()
        dataset = self.create_dataset(observation_form)

        url_kwargs = {
            'app_uuid' : self.ao_app.uuid,
            'uuid' : str(dataset.uuid),
        }

        url = reverse('api_manage_dataset', kwargs=url_kwargs)

        response = self.tenant_client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(response.data['uuid'], str(dataset.uuid))

        with tenant_context(self.tenant):
            tenant_dataset = Dataset.objects.all().last()
            self.assertEqual(tenant_dataset, dataset)
        

    @test_settings
    def test_kmeans(self):
        
        observation_form = self.create_observation_form(observation_form_json=self.observation_form_point_json)
        dataset = self.create_dataset(observation_form)

        url_kwargs = self.get_anycluster_url_kwargs()

        url = reverse('schema_kmeans_cluster', kwargs=url_kwargs)

        post_data = {
            'geojson' : json.dumps(GEOJSON_RECTANGLE),
            'geometry_type': GEOMETRY_TYPE_VIEWPORT,
        }

        response = self.tenant_client.post(url, post_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 1)


    @test_settings
    def test_grid(self):
        pass