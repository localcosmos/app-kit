###################################################################################################################
#
# LOCAL COSMOS APPKIT API
# - build ios apps on a mac
# - mac queries this api for jobs
# - mac builds app and informs the server about the status
#
###################################################################################################################
from django.db import connection
from django.contrib.contenttypes.models import ContentType

from rest_framework.views import APIView
from rest_framework.exceptions import ParseError, NotFound, APIException
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.generics import GenericAPIView
from rest_framework import status, mixins
from rest_framework.parsers import MultiPartParser, JSONParser

from .serializers import (AppKitJobSerializer, AppKitJobAssignSerializer, AppKitJobCompletedSerializer,
                          AppKitJobStatusSerializer, ApiTokenSerializer, CreateAppKitSerializer)

from django_filters.rest_framework import DjangoFilterBackend

from .models import AppKitJobs
from app_kit.models import MetaApp
from localcosmos_cordova_builder.MetaAppDefinition import MetaAppDefinition
from app_kit.appbuilder import  AppReleaseBuilder

from localcosmos_server.models import App
from rest_framework_simplejwt.authentication import JWTAuthentication

from app_kit.multi_tenancy.models import Domain, Tenant

from .permissions import IsApiUser

from django.contrib.auth import get_user_model

User = get_user_model()

import os, threading


class AppKitApiMixin:
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsApiUser,)


class APIHome(AppKitApiMixin, APIView):

    def get(self, request, *args, **kwargs):
        context = {
            'api_status' : 'online',
            'api_type' : 'building',
        }
        return Response(context)



from rest_framework_simplejwt.views import TokenObtainPairView
class ObtainLCAuthToken(TokenObtainPairView):
    serializer_class = ApiTokenSerializer


###################################################################################################################
# LIST JOBS
# - GET
# - View to list all open jobs in the system.
# - allow filtering

class AppKitJobList(AppKitApiMixin, mixins.ListModelMixin, GenericAPIView):

    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)
    serializer_class = AppKitJobSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['platform']

    def get_queryset(self):
        queryset = AppKitJobs.objects.filter(job_status='waiting_for_assignment')
        assigned_to = self.request.query_params.get('assigned_to', None)
        
        queryset = queryset.filter(assigned_to=assigned_to)
        return queryset

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


###################################################################################################################
# JOB DETAIL
# - GET
# - allow filtering

### STILL NEEDS AUTH

class AppKitJobDetail(AppKitApiMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, GenericAPIView):

    queryset = AppKitJobs.objects.all()
    serializer_class = AppKitJobSerializer

    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


###################################################################################################################
#
# ASSIGN JOB
# - PATCH
# - jobs/{job_id}/assign
# - mac calls this api to assign a job to itself
# - response: link to zip file
# - mac ID is linked to the job, started_at is set


class AlreadyAssigned(APIException):
    status_code = status.HTTP_406_NOT_ACCEPTABLE
    default_detail = 'This job is already assigned.'


class AssignAppKitJob(AppKitApiMixin, mixins.UpdateModelMixin, GenericAPIView):

    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)

    queryset = AppKitJobs.objects.all()
    serializer_class = AppKitJobAssignSerializer

    # only allow patching if the job has no machine assigned yet 
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.assigned_to:
            raise AlreadyAssigned()
        instance.job_status = 'assigned'
        instance.save()
        return self.partial_update(request, *args, **kwargs)


class UpdateAppKitJobStatus(AppKitApiMixin, mixins.UpdateModelMixin, GenericAPIView):

    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)
    
    queryset = AppKitJobs.objects.all()
    serializer_class = AppKitJobStatusSerializer

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
    
###################################################################################################################
#
# COMPLETED JOB
# - PATCH
# - jobs/{job_id}/completed
# - mac calls this api if it completed a job
# - post body: the result as json
# - appkit api server stores the result in db

class CompletedAppKitJob(AppKitApiMixin, mixins.UpdateModelMixin, GenericAPIView):

    queryset = AppKitJobs.objects.all()
    serializer_class = AppKitJobCompletedSerializer
    parser_classes = (MultiPartParser, )
    renderer_classes =(JSONRenderer,)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        app_kit_job = self.get_object()

        # get the app
        app = App.objects.get(uuid=app_kit_job.meta_app_uuid)

        # get the domain
        domain = Domain.objects.filter(app=app).first()

        if not domain:
            raise ValueError('No domain found for app {0}'.format(app.uid))
        
        # switch to correct db schema, and refetch the instance
        connection.set_tenant(domain.tenant)
        app_kit_job = self.get_object()
        
        serializer = self.get_serializer(app_kit_job, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(app_kit_job, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            app_kit_job._prefetched_objects_cache = {}

        response_data = serializer.data.copy()

        # save the ipa file if necessary
        if app_kit_job.platform == 'ios' and app_kit_job.job_type == 'build' and app_kit_job.job_result['success'] == True:
            
            # The MetaApp db instance might already be the next version
            meta_app_definition_json = app_kit_job.meta_app_definition
            meta_app_definition = MetaAppDefinition(meta_app_definition = meta_app_definition_json)
            
            meta_app = MetaApp.objects.get(app__uuid=app_kit_job.meta_app_uuid)
            app_release_builder = meta_app.get_release_builder()

            cordova_builder = app_release_builder.get_cordova_builder()

            # the cordova builder defines where to upload the .ipa file to
            # the cordova builder also defines where the android .aab is located, which is where cordova itself creates it
            # /{AppReleaseBuilder._cordova_build_path}/{MetaApp.package_name}/platforms/ios/build/device/
            ipa_folder = cordova_builder._ipa_folder
            if not os.path.isdir(ipa_folder):
                os.makedirs(ipa_folder)
                
            ipa_filepath = cordova_builder._ipa_filepath

            with open(ipa_filepath, 'wb') as ipa_file:
                ipa_file.write(app_kit_job.ipa_file.read())

            # make the ipa preview available, use instance.app_version
            app_release_builder.serve_review_ipa(ipa_filepath)

            response_data['ipa_file'] = os.path.basename(ipa_filepath)

        if app_kit_job.job_result['success'] == True:
            app_kit_job.job_status = 'success'
        else:
            app_kit_job.job_status = 'failed'

        app_kit_job.save()

        return Response(response_data)

    # only allow patching if the job has not been completed yet
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class CreateAppKit(AppKitApiMixin, APIView):
    
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsApiUser,)
    
    def post(self, request, *args, **kwargs):
        
        serializer = CreateAppKitSerializer(data=self.request.data)
        
        if serializer.is_valid():
            tenant_admin_user = User.objects.get(pk=serializer.data['tenant_admin_user_id'])
            number_of_apps = serializer.data['number_of_apps']
            tenant_schema_name = serializer.data['subdomain']
            
            def run_in_thread():
                
                extra_fields = {
                    'number_of_apps' : number_of_apps,
                }
                
                tenant = Tenant.objects.create(tenant_admin_user, tenant_schema_name, **extra_fields)

                public_domain = Domain.objects.get(tenant__schema_name='public', is_primary=True)
                tenant_domain_name = '{0}.{1}'.format(tenant_schema_name, public_domain.domain)

                tenant_domain = Domain(
                    tenant=tenant,
                    domain=tenant_domain_name,
                    is_primary=True,
                )

                tenant_domain.save()

                connection.close()

            # create tenant schema async
            thread = threading.Thread(target=run_in_thread)
            thread.start()
            
            return Response(status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
