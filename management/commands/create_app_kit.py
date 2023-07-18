from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.conf import settings

from app_kit.multi_tenancy.models import Tenant, Domain

User = get_user_model()


class Command(BaseCommand):
    
    help = 'Create an app kit (tenant)'


    def add_arguments(self, parser):
        parser.add_argument('subdomain', type=str)

    def handle(self, *args, **options):

        if 'subdomain' not in options:
            raise CommandError('Subdomain is required')

        subdomain = options['subdomain']

        api_user_username = settings.APP_KIT_APIUSER_USERNAME
        superuser = User.objects.filter(is_superuser=True).exclude(username=api_user_username).first()
            
        tenant = Tenant.objects.create(superuser, subdomain)
        tenant.activate()

        # create appless domain
        public_domain_name = Domain.objects.get(tenant__schema_name='public', is_primary=True)
        domain_name = '{0}.{1}'.format(subdomain, public_domain_name)

        domain = Domain(
            tenant=tenant,
            domain=domain_name,
            is_primary=True,
        )

        domain.save()
            
        