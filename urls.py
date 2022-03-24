from django.conf import settings
from django.urls import include, path
from . import views

# prefix "app-kit/" is routed to django in nginx, and so is 'global/'

from app_kit.features.fact_sheets.views import GetFactSheetPreview

urlpatterns = [
    path(settings.APP_KIT_URL, views.ListManageApps.as_view(), name='appkit_home'),
    path(settings.APP_KIT_URL, include('app_kit.admin_urls')),

    path('api/fact-sheet-preview/<str:slug>/<int:meta_app_id>/', GetFactSheetPreview.as_view(),
         name='fact_sheet_preview'),

    path('server/', include('app_kit.global_urls')),
    
]
