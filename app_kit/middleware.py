from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.exceptions import PermissionDenied

import rules

class AppKitPermissionsMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.


    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)
        
        if settings.APP_KIT_URL in request.path:

            if not request.user.is_authenticated == True:
                url = request.build_absolute_uri('%s?next=%s' %(reverse('log_in'), request.path))
                return HttpResponseRedirect(url)

            if request.user.is_authenticated == True:
                tenant = getattr(request, 'tenant', None)
                if tenant is not None:
                    
                    has_access = rules.test_rule('app_kit.has_access', request.user, tenant)

                    if not has_access:
                        raise PermissionDenied

        # Code to be executed for each request/response after
        # the view is called.
        
        return response
