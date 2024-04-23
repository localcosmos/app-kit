from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from django_tenants.models import TenantMixin, DomainMixin

from localcosmos_server.models import App

from django_tenants.utils import tenant_context


'''
    Domains and Tenants
    - one Domain per App
    - App is null only for the public schema
'''

class Domain(DomainMixin):
    # CASCADE would render the tenant subdomain unusable
    # is domain is secondary, it may be deleted
    app = models.ForeignKey(App, null=True, on_delete=models.SET_NULL)



'''
    Tenant
    - = a schema
    - covers AppKit (app_kit) and collected data (localcosmos_server.datasets)
'''
class TenantManager(models.Manager):


    def create(self, creator, schema_name, **extra_fields):
        
        tenant = self.model(
            schema_name=schema_name,
            **extra_fields
        )
        tenant.save()

        # the creator is admin
        admin_role = TenantUserRole(
            user = creator,
            tenant = tenant,
            role = 'admin',
        )
        admin_role.save()

        return tenant



class Tenant(TenantMixin):

    # default true, schema will be automatically created and synced when it is saved
    auto_create_schema = True
    
    created_at = models.DateTimeField(auto_now_add=True)

    # the number of apps this tenant is allowed to create
    number_of_apps = models.IntegerField(null=True)

    options = models.JSONField(null=True)

    objects = TenantManager()

    ### APPKIT URL
    # accessed from the commercial lc site -> we have to pass urlconf
    def appkit_url(self):
        domain = Domain.objects.get(tenant=self)

        # subdomains cannot be changed
        admin_url = '{0}{1}'.format(domain.domain, reverse('appkit_home', urlconf='app_kit.urls'))

        return admin_url

    def get_admin_emails(self):
        admins = TenantUserRole.objects.filter(tenant=self, role='admin')
        emails = [admin.user.email for admin in admins]

        return emails


    def get_meta_apps(self):
        from app_kit.models import MetaApp
        
        self.activate()
        return MetaApp.objects.all()
            


    def __str__(self):
        return '{0}'.format(self.schema_name)



USER_ROLES = (
    ('admin',_('Admin')), # can do everything
)
class TenantUserRole(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=60, choices=USER_ROLES, default='pending')

    def __str__(self):
        return '[{0}] {1}: {2}'.format(self.tenant.schema_name, self.user.username, self.role)

    class Meta:
        unique_together = ('user', 'tenant')

