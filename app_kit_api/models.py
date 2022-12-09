from django.db import models
from django.utils.translation import gettext_lazy as _

from django.contrib.sites.models import Site

import uuid

APP_KIT_STATUS = (
    ('live', _('live')),
    ('maintenance', _('maintenance')),
)

class AppKitStatus(models.Model):
    site = models.OneToOneField(Site, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, choices=APP_KIT_STATUS, default='live')
    
    def __str__(self):
        return '{0}: {1}'.format(self.site, self.status)



'''--------------------------------------------------------------------------------------------------------------
    APP KIT JOBS
    - builds that need specialized hardware, lice Apple
--------------------------------------------------------------------------------------------------------------'''
PLATFORM_CHOICES = (
    ('ios', 'iOS'),
    ('android', 'Android'),
)


JOB_TYPES = (
    ('build', 'Build'),
    ('release', 'Release'),
)


JOB_STATUS = (
    ('waiting_for_assignment', _('Waiting for assignment')),
    ('assigned', _('Assigned')),
    ('in_progress', _('Job in progress')),
    ('success', _('Success')),
    ('failed', _('Failed')),
)

class AppKitJobs(models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    meta_app_uuid = models.UUIDField()
    meta_app_definition = models.JSONField()
    app_version = models.IntegerField()
    platform = models.CharField(max_length=255, choices=PLATFORM_CHOICES)

    job_type = models.CharField(max_length=50, choices=JOB_TYPES)
    
    parameters = models.JSONField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    # the physical machine that is doing this job
    assigned_to = models.CharField(max_length=100, null=True)
    
    assigned_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)

    # job_status is used eg to give the user a feedback in the frontend
    job_status = models.CharField(max_length=50, choices=JOB_STATUS, default='waiting_for_assignment')
    job_result = models.JSONField(null=True)

    def __str__(self):
        name = self.meta_app_definition.get('name', str(self.uuid))
        return '{0} - {1}'.format(name, self.job_type)
        

    class Meta:
        unique_together = ('meta_app_uuid', 'app_version', 'platform', 'job_type')


