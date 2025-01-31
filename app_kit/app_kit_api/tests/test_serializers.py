from app_kit.tests.common import test_settings

from django_tenants.test.cases import TenantTestCase

from rest_framework.serializers import ValidationError

from app_kit.tests.common import TEST_IPA_FILEPATH

from app_kit.app_kit_api.serializers import (ApiTokenSerializer, AppKitJobSerializer,
                        AppKitJobAssignSerializer, AppKitJobStatusSerializer, RESERVED_SUBDOMAINS,
                        AppKitJobCompletedSerializer, CreateAppKitSerializer)

from app_kit.tests.mixins import (WithMetaApp, WithUser)
from app_kit.app_kit_api.tests.mixins import WithAppKitJob

from django.core.files.uploadedfile import SimpleUploadedFile

from localcosmos_cordova_builder.MetaAppDefinition import MetaAppDefinition

from app_kit.multi_tenancy.models import Domain


class TestAppKitJobSerializer(WithAppKitJob, WithMetaApp, TenantTestCase):
    
    @test_settings
    def test_serialize(self):
        
        job = self.create_job(self.meta_app, 'ios', 'build')

        serializer = AppKitJobSerializer(job)

        meta_app_definition = MetaAppDefinition.meta_app_to_dict(self.meta_app)

        expected_data = {
            'id': job.id,
            'uuid': str(job.uuid),
            'meta_app_uuid': str(self.meta_app.uuid),
            'meta_app_definition': meta_app_definition, 
            'app_version': job.app_version,
            'job_type': job.job_type,
            'platform': job.platform,
            'assigned_to': None,
            'assigned_at': None,
            'finished_at': None,
            'job_status': 'waiting_for_assignment',
            'job_result': None
        }

        for key, value in expected_data.items():
            self.assertEqual(serializer.data[key], value)


'''
    only used in PATCH requests
'''
class TestAppKitJobAssignSerializer(WithAppKitJob, WithMetaApp, TenantTestCase):

    @test_settings
    def test_deserialize(self):
        
        job = self.create_job(self.meta_app, 'ios', 'build')

        post_data = {
            'pk': job.id,
            'assigned_to': 'Mac',
            'job_status': 'in_progress',
        }

        serializer = AppKitJobAssignSerializer(data=post_data)

        is_valid = serializer.is_valid()

        self.assertEqual(serializer.errors, {})

    @test_settings
    def test_update(self):
        
        job = self.create_job(self.meta_app, 'ios', 'build')

        post_data = {
            'pk': job.id,
            'assigned_to': 'Mac',
            'job_status': 'in_progress',
        }

        serializer = AppKitJobAssignSerializer(data=post_data)

        is_valid = serializer.is_valid()

        self.assertEqual(serializer.errors, {})

        self.assertEqual(job.assigned_to, None)
        self.assertEqual(job.job_status, 'waiting_for_assignment')

        serializer.update(job, serializer.validated_data)

        job.refresh_from_db()
        self.assertEqual(job.assigned_to, 'Mac')
        self.assertEqual(job.job_status, 'in_progress')


'''
    only used in patch requests
'''
class TestAppKitJobStatusSerializer(WithAppKitJob, WithMetaApp, TenantTestCase):

    @test_settings
    def test_deserialize(self):

        job = self.create_job(self.meta_app, 'ios', 'build')

        post_data = {
            'pk': job.id,
            'job_status': 'success',
        }

        serializer = AppKitJobStatusSerializer(data=post_data)

        is_valid = serializer.is_valid()

        self.assertEqual(serializer.errors, {})


class TestAppKitJobCompletedSerializer(WithAppKitJob, WithMetaApp, TenantTestCase):

    def get_valid_job_result(self):
        valid_job_result = {
            'errors': [],
            'warnings': [],
            'success': True
        }

        return valid_job_result
    
    def get_ipa_file(self):
        upload_file = open(TEST_IPA_FILEPATH, 'rb')
        ipa = SimpleUploadedFile('AppName.ipa', upload_file.read())
        return ipa


    @test_settings
    def test_deserialize(self):

        job = self.create_job(self.meta_app, 'ios', 'build')
        
        post_data = {
            'pk': job.id,
            'job_result': self.get_valid_job_result(),
            'ipa_file': self.get_ipa_file(),
        }

        serializer = AppKitJobCompletedSerializer(data=post_data)

        is_valid = serializer.is_valid()

        self.assertEqual(serializer.errors, {})


    @test_settings
    def test_validate_job_result(self):

        job = self.create_job(self.meta_app, 'ios', 'build')

        post_data = {
            'pk': job.id,
            'ipa_file': self.get_ipa_file(),
        }
        
        # missing errors
        invalid_job_result = {
            'warnings': [],
            'success': True
        }

        serializer = AppKitJobCompletedSerializer(data=post_data)

        with self.assertRaises(ValidationError):
            serializer.validate_job_result(invalid_job_result)

        
        # missing warnings
        invalid_job_result_2 = {
            'errors': [],
            'success': True
        }

        with self.assertRaises(ValidationError):
            serializer.validate_job_result(invalid_job_result_2)

       
        # missing success
        invalid_job_result_3 = {
            'errors': [],
            'warnings': [],
        }

        with self.assertRaises(ValidationError):
            serializer.validate_job_result(invalid_job_result_3)

        # success not bool
        invalid_job_result_4 = {
            'errors': [],
            'warnings': [],
            'success': 'true'
        }
        
        with self.assertRaises(ValidationError):
            serializer.validate_job_result(invalid_job_result_4)


    @test_settings
    def test_validate(self):
        
        job = self.create_job(self.meta_app, 'ios', 'build')

        post_data = {
            'pk': job.id,
            'job_result': self.get_valid_job_result(),
        }

        serializer = AppKitJobCompletedSerializer(instance=job, data=post_data)

        with self.assertRaises(ValidationError):
            serializer.validate(post_data)


    @test_settings
    def update(self):
        
        job = self.create_job(self.meta_app, 'ios', 'build')

        post_data = {
            'pk': job.id,
            'job_result': self.get_valid_job_result(),
            'ipa_file': self.get_ipa_file(),
        }

        serializer = AppKitJobCompletedSerializer(data=post_data)

        is_valid = serializer.is_valid()

        self.assertEqual(serializer.errors, {})

        self.assertEqual(job.job_status, 'waiting_for_assignment')
        self.assertEqual(job.finished_at, None)
        self.assertEqual(job.job_result, None)
        serializer.update(job, serializer.validated_data)

        job.refresh_from_db()

        self.assertEqual(job.job_status, 'success')
        self.assertTrue(job.finished_at != None)
        self.assertEqual(job.job_result, post_data['job_result'])
        

class TestCreateAppKitSerializer(WithUser, WithMetaApp, TenantTestCase):
    
    @test_settings
    def test_wrong_encoding(self):
        
        subdomain = 'Á É Í Ó Ú Ý Ć Ǵ Ḱ Ĺ Ḿ Ń Ṕ Ŕ Ś Ẃ Ź'
        
        post_data = {
            'subdomain': subdomain,
            'number_of_apps': 1,
        }

        with self.assertRaises(UnicodeEncodeError):
            subdomain.encode('ascii')
            
        serializer = CreateAppKitSerializer(data=post_data)

        with self.assertRaises(ValidationError):
            subdomain = serializer.validate_subdomain(subdomain)
        
    @test_settings
    def test_in_reserved(self):

        subdomain = RESERVED_SUBDOMAINS[0]
        
        post_data = {
            'subdomain': subdomain,
            'number_of_apps': 1,
        }
        
        serializer = CreateAppKitSerializer(data=post_data)

        with self.assertRaises(ValidationError):
            subdomain = serializer.validate_subdomain(subdomain)

    @test_settings
    def test_0_unalpha(self):
        subdomain = '1test'

        post_data = {
            'subdomain': subdomain,
            'number_of_apps': 1,
        }
        
        serializer = CreateAppKitSerializer(data=post_data)

        with self.assertRaises(ValidationError):
            subdomain = serializer.validate_subdomain(subdomain)

    @test_settings
    def test_is_not_alphanumeric(self):

        subdomain = 'test!'

        post_data = {
            'subdomain': subdomain,
            'number_of_apps': 1,
        }
        
        serializer = CreateAppKitSerializer(data=post_data)

        with self.assertRaises(ValidationError):
            subdomain = serializer.validate_subdomain(subdomain)
            
    @test_settings
    def test_already_exists(self):

        domain = Domain(
            domain='test.lc.org',
            tenant=self.tenant,
            app=self.meta_app.app,
        )

        domain.save()

        subdomain = 'test'

        post_data = {
            'subdomain': subdomain,
            'number_of_apps': 1,
        }
        
        serializer = CreateAppKitSerializer(data=post_data)

        with self.assertRaises(ValidationError):
            subdomain = serializer.validate_subdomain(subdomain)

    @test_settings
    def test_valid(self):
        
        user = self.create_user()

        subdomain = 'test2'
        post_data = {
            'subdomain': subdomain,
            'number_of_apps': 1,
            'tenant_admin_user_id': user.id,
        }
        
        serializer = CreateAppKitSerializer(data=post_data)
        
        subdomain_valid = serializer.validate_subdomain(subdomain)
        self.assertEqual(subdomain, subdomain_valid)
        
        is_valid = serializer.is_valid()
        self.assertEqual(serializer.errors, {})