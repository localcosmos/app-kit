from django.conf import settings
from django.urls import include, path
from . import views

# prefix "app-kit/" is routed to django in nginx, and so is 'global/'


urlpatterns = [
    path(settings.APP_KIT_URL, views.ListManageApps.as_view(), name='appkit_home'),
    path(settings.APP_KIT_URL, include('app_kit.admin_urls')),

    path('server/', include('app_kit.global_urls')),

    path('api/get-translation/<int:meta_app_id>/', views.GetDeepLTranslation.as_view(),
         name='get_translation'),
    
]
