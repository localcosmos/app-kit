from rest_framework import serializers
from django.conf import settings

from django.utils import timezone

from .models import AppKitJobs
from rest_framework import exceptions
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()

from app_kit.multi_tenancy.models import Domain

RESERVED_SUBDOMAINS = getattr(settings, 'RESERVED_SUBDOMAINS', [])

import json

class ApiTokenSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        username = attrs[self.username_field]

        if username != settings.APP_KIT_APIUSER_USERNAME:

            error_message = 'No valid account given'

            raise exceptions.AuthenticationFailed(
                error_message,
                "invalid_account",
            )

        return super().validate(attrs)

    

class AppKitJobSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = AppKitJobs
        fields = '__all__'


# assigned_to has to be set by the machine doing the job
class AppKitJobAssignSerializer(serializers.ModelSerializer):

    def update(self, instance, validated_data):
        instance.assigned_at = timezone.now()
        instance = super().update(instance, validated_data)
        return instance

    class Meta:
        model = AppKitJobs
        fields = ('pk','assigned_to', 'job_status')
        extra_kwargs = {
            'assigned_to' : {
                'required' : True,
                'trim_whitespace' : True,
            }
        }


class AppKitJobStatusSerializer(serializers.ModelSerializer):

    class Meta:
        model = AppKitJobs
        fields = ('pk','job_status')



class AppKitJobCompletedSerializer(serializers.ModelSerializer):

    ipa_file = serializers.FileField(required=False)

    def update(self, instance, validated_data):
        instance.finished_at = timezone.now()
        instance = super().update(instance, validated_data)
        return instance

    def validate_job_result(self, value):

        if type(value) == str:
            value = json.loads(value)

        if 'errors' not in value:
            raise serializers.ValidationError('Incomplete JSON: key "errors" not in job_result. If there were no errors, add an empty list.')
        
        if 'warnings' not in value:
            raise serializers.ValidationError('Incomplete JSON: key "warnings" not in job_result. If there were no warnings, add an empty list.')

        if 'success' not in value:
            raise serializers.ValidationError('Incomplete JSON: key "success" not in job_result.')

        elif type(value['success']) != bool:
            raise serializers.ValidationError('Invalid JSON: key "success" has to be of type bool.')
                  
        return value
            
    def validate(self, data):
        """
        if the job type was "build" and the platform "ios" a ipa file is required
        """

        if self.instance and self.instance.platform == 'ios' and self.instance.job_type == 'build':
            if data.get('job_result', None) and data['job_result'].get('success', False) == True:
                if not data.get('ipa_file', None):
                    raise serializers.ValidationError({'ipa_file': ['You need to upload an .ipa file for successful ios build jobs']})
        return data

    class Meta:
        model = AppKitJobs
        fields = ('pk', 'job_result', 'ipa_file')
        extra_kwargs = {
            'job_result' : {
                'required' : True,
            }
        }


class CreateAppKitSerializer(serializers.Serializer):
    
    number_of_apps = serializers.IntegerField()
    subdomain = serializers.CharField()
    tenant_admin_user_id = serializers.IntegerField()
    
    def validate_subdomain(self, value):
        value = value.strip().lower()
        
        try:
            value.encode('ascii')
        except:
            raise serializers.ValidationError(_('Use only [a-z] and [0-9] for the subdomain.') )

        if value in RESERVED_SUBDOMAINS:
            raise serializers.ValidationError(_('This subdomain is forbidden.'))

        if not value[0].isalpha():
            raise serializers.ValidationError(_('The subdomain has to start with a letter.'))

        if not value.isalnum():
            raise serializers.ValidationError(_('The subdomain has to be alphanumeric.'))

        if Domain.objects.filter(domain__startswith=value).exists():
            raise serializers.ValidationError(_('This subdomain already exists.'))
        return value
    
    def validate_tenant_admin_user_id(self, value):
        
        if User.objects.filter(pk=value).exists():
            return value
        
        raise serializers.ValidationError(_('The user does not exist.'))