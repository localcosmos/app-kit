from app_kit.tests.common import test_settings
from django.conf import settings

from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import tenant_context

from rest_framework import status
from rest_framework.test import APIClient
from django.urls import reverse

from app_kit.tests.mixins import WithTenantClient, WithUser

from app_kit.app_kit_api.tests.mixins import WithAppKitApiUser

from app_kit.multi_tenancy.models import Tenant, Domain


from localcosmos_server.tests.mixins import WithApp, WithObservationForm

import json, subprocess, time


class TestObtainLCAuthToken(WithAppKitApiUser, WithUser, WithTenantClient, TenantTestCase):

    def setUp(self):
        super().setUp()
        self.superuser = self.create_superuser()

    def get_post_data(self):

        post_data = {
            'username': self.username,
            'password': self.password,
        }

        return post_data


    @test_settings
    def test_post(self):
        
        post_data = self.get_post_data()

        url = '/api/building/auth-token/' #reverse('get_appkit_api_token')

        response = self.client.post(url, post_data, follow=True, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestCreateAppKit(WithAppKitApiUser, WithUser, WithTenantClient, TenantTestCase):
    client_class = APIClient
    
    def setUp(self):
        super().setUp()
        self.superuser = self.create_superuser()
        
    @test_settings
    def test_post(self):
        
        subdomain = 'testkit'
        
        post_data = {
            'tenant_admin_user_id': self.superuser.id,
            'number_of_apps': 1,
            'subdomain': subdomain,
        }
        
        url = '/api/building/create-appkit/' #reverse('api_create_appkit')

        response = self.client.post(url, post_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # log in
        self.client.force_authenticate(user=self.app_kit_api_user)
        
        self.assertFalse(Tenant.objects.filter(schema_name=subdomain).exists())
        
        response = self.client.post(url, post_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        time.sleep(120)
        
        self.assertTrue(Tenant.objects.filter(schema_name=subdomain).exists())
        
    
    @test_settings
    def test_post_invalid(self):
        
        subdomain = 'testkit'
        
        post_data = {
            'tenant_admin_user_id': self.superuser.id,
            'number_of_apps': 1,
        }
        
        url = '/api/building/create-appkit/' #reverse('api_create_appkit')

        self.client.force_authenticate(user=self.app_kit_api_user)
        
        response = self.client.post(url, post_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


'''
APP KIT JOBS API
'''



'''
    Test anycluster schema urls
'''
from localcosmos_server.datasets.api.tests.test_views import WithDatasetPostData, CreatedUsersMixin
from localcosmos_server.datasets.models import Dataset
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
            'app_uuid': self.ao_app.uuid,
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
            'geojson' : GEOJSON_RECTANGLE,
            'geometry_type': GEOMETRY_TYPE_VIEWPORT,
        }

        response = self.tenant_client.post(url, post_data, content_type="application/json", format='json')
        if response.status_code != status.HTTP_200_OK:
            print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 1)


    @test_settings
    def test_grid(self):
        pass