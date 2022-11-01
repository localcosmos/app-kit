
###################################################################################################################
#
# LOCAL COSMOS APPKIT API
# - build ios apps on a mac
# - mac queries this api for jobs
# - mac builds app and informs the server about the status
#
###################################################################################################################
from django.db import connection

from rest_framework.views import APIView
from rest_framework.exceptions import ParseError, NotFound, APIException
from rest_framework.response import Response
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.generics import GenericAPIView
from rest_framework import status, mixins
from rest_framework.parsers import MultiPartParser

from .serializers import (AppKitJobSerializer, AppKitJobAssignSerializer, AppKitJobCompletedSerializer,
                          AppKitJobStatusSerializer, ApiTokenSerializer)

from django_filters.rest_framework import DjangoFilterBackend

from .models import AppKitJobs
from app_kit.models import MetaApp
from localcosmos_cordova_builder.MetaAppDefinition import MetaAppDefinition
from app_kit.appbuilder import  AppReleaseBuilder

from localcosmos_server.models import App
from rest_framework_simplejwt.authentication import JWTAuthentication

from app_kit.multi_tenancy.models import Domain

from .permissions import IsApiUser

import os


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



from rest_framework.authtoken.views import ObtainAuthToken
class ObtainLCAuthToken(ObtainAuthToken):
    serializer_class = ApiTokenSerializer


###################################################################################################################
# LIST JOBS
# - GET
# - View to list all jobs in the system.
# - allow filtering

class AppKitJobList(AppKitApiMixin, mixins.ListModelMixin, GenericAPIView):

    serializer_class = AppKitJobSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['platform']

    def get_queryset(self):
        """
        Optionally restricts the returned purchases to a given user,
        by filtering against a `username` query parameter in the URL.
        """
        queryset = AppKitJobs.objects.all()
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


    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # get the app
        app = App.objects.get(uuid=instance.meta_app_uuid)

        # get the domain
        domain = Domain.objects.filter(app=app).first()

        if not domain:
            raise ValueError('No domain found for app {0}'.format(app.uid))
        
        # switch to correct db schema, and refetch the instance
        connection.set_tenant(domain.tenant)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}


        response_data = serializer.data.copy()

        
        # save the ipa file if necessary
        if instance.platform == 'ios' and instance.job_type == 'build' and instance.job_result['success'] == True:
            
            # The MetaApp db instance might already be the next version
            meta_app_definition_json = instance.meta_app_definition
            meta_app_definition = MetaAppDefinition(meta_app_definition_json['current_version'],
                                                    meta_app_definition = meta_app_definition_json)
            

            app_release_builder = AppReleaseBuilder()

            meta_app = MetaApp.objects.get(app__uuid=instance.meta_app_uuid)
            
            cordova_builder = app_release_builder.get_cordova_builder(meta_app, instance.app_version)

            # the cordova builder defines where to upload the .ipa file to
            ipa_folder = cordova_builder.get_ipa_folder()
            if not os.path.isdir(ipa_folder):
                os.makedirs(ipa_folder)
                
            ipa_filepath = cordova_builder.get_ipa_filepath()

            with open(ipa_filepath, 'wb') as ipa_file:
                ipa_file.write(instance.ipa_file.read())

            # make the ipa preview available, use instance.app_version
            app_release_builder.serve_preview_ipa(meta_app, instance.app_version, ipa_filepath)

            response_data['ipa_file'] = os.path.basename(ipa_filepath)

        if instance.job_result['success'] == True:
            instance.job_status = 'success'
        else:
            instance.job_status = 'failed'

        instance.save()

        return Response(response_data)

    # only allow patching if the job has not been completed yet
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
