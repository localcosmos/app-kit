from django.conf import settings
from django.contrib import admin
from django.urls import path, include

from django.views.generic import RedirectView

urlpatterns = [

    # provide loggedout view for the tenants, results in redirect loop
    #path('server/loggedout/', RedirectView.as_view(pattern_name='loggedout')),
   
    # LC SERVER
    path('', include('localcosmos_server.urls')),
    
    # APP KIT, has to be below LC SERVER
    path('', include('app_kit.urls')),
    
]

# remove this line after development
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
