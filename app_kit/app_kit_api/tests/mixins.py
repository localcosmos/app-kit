from django.conf import settings

from localcosmos_server.models import LocalcosmosUser

from app_kit.app_kit_api.models import AppKitJobs

from localcosmos_cordova_builder.MetaAppDefinition import MetaAppDefinition

class WithAppKitApiUser:

    def setUp(self):
        super().setUp()

        # create the app kit api user
        self.username = settings.APP_KIT_APIUSER_USERNAME
        self.password = settings.APP_KIT_APIUSER_PASSWORD
        self.email = settings.APP_KIT_APIUSER_EMAIL = 'api@localcosmos.org'

        self.app_kit_api_user = LocalcosmosUser.objects.create_user(self.username, self.email, self.password)



class WithAppKitJob:

    def create_job(self, meta_app, platform, job_type):

        meta_app_definition = MetaAppDefinition.meta_app_to_dict(meta_app)

        job = AppKitJobs(
            meta_app_uuid=meta_app.uuid,
            meta_app_definition=meta_app_definition,
            app_version=meta_app.current_version,
            platform=platform,
            job_type=job_type,
        )

        job.save()

        return job
