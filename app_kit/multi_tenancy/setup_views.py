from django.views.generic import FormView, TemplateView
from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse

from django.db import connection

from django.contrib.auth import get_user_model

from .setup_forms import CreateInitialAppKitForm

from .models import Tenant, Domain

import threading

User = get_user_model()


'''
    SetupDemoApp
    - create a tenant (schema) and a domain
'''
class SetupInitialAppKit(FormView):

    template_name = 'localcosmos/setup/setup_initial_appkit.html'
    form_class = CreateInitialAppKitForm

    
    def get_public_domain_name(self):
        domain = Domain.objects.get(tenant__schema_name='public', is_primary=True)
        return domain.domain


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['appkit_creation_in_progress'] = False
        context['success'] = False
        if Tenant.objects.exclude(schema_name='public').exists():
            context['success'] = True

        return context
        

    def form_valid(self, form):

        # subdomain=schema_name
        subdomain = form.cleaned_data['subdomain']

        def run_in_thread():

            # create appkitapiuser after fetching the currently created superuser
            api_user_username = settings.APP_KIT_APIUSER_USERNAME
            api_user = User.objects.filter(username=api_user_username).first()
            if not api_user:
                api_user = User.objects.create_user(api_user_username,
                                        settings.APP_KIT_APIUSER_EMAIL,settings.APP_KIT_APIUSER_PASSWORD)

            # create the tenant
            superuser = User.objects.filter(is_superuser=True).exclude(username=api_user_username).first()
            
            tenant = Tenant.objects.create(superuser, subdomain)
            tenant.activate()

            # create appless domain
            public_domain_name = self.get_public_domain_name()
            domain_name = '{0}.{1}'.format(subdomain, public_domain_name)

            domain = Domain(
                tenant=tenant,
                domain=domain_name,
                is_primary=True,
            )

            domain.save()
            

            '''
            # create the app
            # -creates the domain
            # -subdomain.primary_domain
            # django-tenants does not use ports
            public_domain_name = self.get_public_domain_name()
            domain_name = '{0}.{1}'.format(subdomain, public_domain_name)

            extra_app_kwargs = {}
            if 'uuid' in form.cleaned_data and form.cleaned_data['uuid']:
                extra_app_kwargs['uuid'] = form.cleaned_data['uuid']
                
            
            meta_app = MetaApp.objects.create(form.cleaned_data['name'], form.cleaned_data['primary_language'],
                                              domain_name, tenant, subdomain, **extra_app_kwargs)

            '''
            # close conn at the end of thread
            connection.close()


        thread = threading.Thread(target=run_in_thread)
        thread.start()

        context = super().get_context_data(**self.kwargs)
        context['appkit_creation_in_progress'] = True
        context['success'] = True
        context['schema_name'] = subdomain
        return self.render_to_response(context)



class CheckInitialAppKitCreationStatus(TemplateView):

    def get_success_url(self, tenant):
        return reverse('appkit_home', urlconf='app_kit.urls')

    def get(self, request, *args, **kwargs):

        success_url = None
        success = False

        schema_name = kwargs['schema_name']

        tenant = Tenant.objects.filter(schema_name=schema_name).first()

        if tenant:
            domain = Domain.objects.filter(tenant=tenant, domain__icontains=schema_name).first()

            if domain:
                host = '{0}.{1}'.format(schema_name, request.META['HTTP_HOST'])     
                success_url = '{0}://{1}{2}'.format(request.scheme, host, self.get_success_url(tenant))
                success = True

        return JsonResponse({'success':success, 'success_url':success_url})
