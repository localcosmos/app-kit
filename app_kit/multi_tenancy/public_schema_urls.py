from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.decorators import login_required

from . import views

from app_kit import views as app_kit_views

# PUBLIC SCHEMA URLCONF
urlpatterns = [
    # ADMIN
    path('admin/', admin.site.urls),
    
    ### IMPORTS FROM LOCALCOSMOS_SERVER
    path('server/', include('localcosmos_server.global_urls')),
    # API - the api is tenant specific, this inclusion is only to make the SCP work on the commerical installation
    path('api/', include('localcosmos_server.api.urls')),
    ###

    # app kit bulding api (eg ios), do not use app-kit in url
    path('api/building/', include('app_kit.app_kit_api.urls')),
    
    # SETUP
    path('', include('app_kit.multi_tenancy.setup_urls')),

    path('my-account/', login_required(views.MyAccount.as_view()), name='my_account'),
    path('edit-account/', login_required(views.EditAccount.as_view()), name='edit_account'),
    path('delete-account/', login_required(views.DeleteAccount.as_view()), name='delete_account'),

    # support
    path('contact-us/', views.ContactUs.as_view(), name='contact_us'),
    
    # LEGAL
    path('privacy-statement/', app_kit_views.PrivacyStatement.as_view(), name='privacy_statement'),
    path('legal-notice/', app_kit_views.LegalNotice.as_view(), name='legal_notice'),
]


# remove this line after development
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static('/build_jobs/', document_root='/var/www/localcosmos/build_jobs/')
