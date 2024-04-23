from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from django_tenants.utils import get_tenant_model, get_tenant_domain_model
Tenant = get_tenant_model()
Domain = get_tenant_domain_model()

from django.contrib.sites.models import Site
from localcosmos_server.models import App


'''
    create an app in the languages english, german and japanese (testing characters)
'''
class Command(BaseCommand):
    
    help = 'Fix Staging domain names for all tenants, the public schema and Sites model'

    def handle(self, *args, **options):

        base_domain = getattr(settings, 'APP_KIT_STAGING_BASE_DOMAIN', 'staging.localcosmos.org')

        self.stdout.write('Fixing all domains.')

        site = Site.objects.all().first()

        site.domain = base_domain
        site.save()

        self.stdout.write('Fixed django.contrib.sites.models.Site. Is now {0}'.format(site.domain))

        public_domain = Domain.objects.get(tenant__schema_name='public')
        public_domain.domain = base_domain
        public_domain.save()
        
        self.stdout.write('Fixed public schema Domain. Is now {0}'.format(public_domain.domain))

        tenant_domains = Domain.objects.exclude(tenant__schema_name='public')

        for tenant_domain in tenant_domains:

            domain_prefix = tenant_domain.domain.split('.')[0]
            domain_name = '{0}.{1}'.format(domain_prefix, base_domain)

            tenant_domain.domain = domain_name
            tenant_domain.save()

            self.stdout.write('Fixed tenant schema Domain. Is now {0}'.format(tenant_domain.domain))


        for app in App.objects.all():

            if app.url:
                app.url = app.url.replace('localcosmos.org', base_domain)
                app.save()

                self.stdout.write('Fixed app.url. Is now {0}'.format(app.url))


        self.stdout.write('Finished fixing all domains.')
