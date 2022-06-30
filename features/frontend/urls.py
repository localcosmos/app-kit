from django.urls import path
from . import views

urlpatterns = [                    
    path('manage-frontend/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageFrontend.as_view(), name='manage_frontend'),
    path('manage-frontend-settings/<int:meta_app_id>/<int:frontend_id>/',
        views.ManageFrontendSettings.as_view(), name='manage_frontend_settings'),
]
