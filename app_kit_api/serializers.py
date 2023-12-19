from rest_framework import serializers

from django.utils import timezone

from .models import AppKitJobs
from rest_framework import exceptions
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

import json

class ApiTokenSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        username = attrs[self.username_field]

        if username != 'APPKITAPIUSER':

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
