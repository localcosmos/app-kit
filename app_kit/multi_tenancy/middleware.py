from django.conf import settings
from django.urls import reverse
from django.shortcuts import redirect
from django.db import connection

from .models import Domain, Tenant

from django_tenants.middleware import TenantMainMiddleware

from localcosmos_server.utils import get_domain_name

'''
    Local Cosmos needs at least one superuser and one app kit to function properly.
    This applies to the commercial version only
    
    this middleware
    - checks if a demo app inlcuding the tenant exists

    and redirects to setup pages if not

    The default URLCONF is settings.ROOT_URLCONF
    we have to check if the urlconf has to be set to PUBLIC_SCHEMA_URLCONF

'''
class LocalCosmosTenantMiddleware(TenantMainMiddleware):
    

    def create_public_schema(self, request):
        public_schema = Tenant(
            schema_name = 'public',
        )
        public_schema.save()

        # django-tenants does not use ports
        setup_domain_name = get_domain_name(request)

        # create public_domain if not yet present
        public_domain = Domain.objects.filter(domain=setup_domain_name).first()

        if not public_domain:
            public_domain = Domain()
            public_domain.domain = setup_domain_name # don't add your port or www here! on a local server you'll want to use localhost here
            public_domain.tenant = public_schema
            public_domain.is_primary = True
            public_domain.save()


    def process_request(self, request):

        # Connection needs first to be set to the public schema for being able to query the Tenant model
        connection.set_schema_to_public()

        # before doing anything, check if the public schema has been created
        public_schema = Tenant.objects.filter(schema_name='public').first()
        if not public_schema:
            self.create_public_schema(request)

        # run TenantMainMiddleware
        # sets request.tenant and the correct db schema connection
        # doesnt return anything
        super().process_request(request)


        localcosmos_create_superuser_url = reverse('localcosmos_setup_superuser')
        initial_appkit_setup_url = reverse('setup_initial_appkit', urlconf='app_kit.multi_tenancy.setup_urls')
        
        # do not run this middleware if the superuser is being created or the demo app is being created
        # 'setup/check-initial-appkit-creation/<schema_name>/'
        if request.path_info in [localcosmos_create_superuser_url, initial_appkit_setup_url] or 'setup/check-initial-appkit-creation/' in request.path_info:
            return None

        tenant = Tenant.objects.exclude(schema_name='public').first()

        if not tenant:
            request.urlconf = settings.PUBLIC_SCHEMA_URLCONF
            return redirect(initial_appkit_setup_url)
        
