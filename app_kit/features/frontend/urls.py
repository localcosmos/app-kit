from django.urls import path
from . import views

urlpatterns = [                    
    path('manage-frontend/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageFrontend.as_view(), name='manage_frontend'),
    path('manage-frontend-settings/<int:meta_app_id>/<int:frontend_id>/',
        views.ManageFrontendSettings.as_view(), name='manage_frontend_settings'),
    path('change-frontend/<int:meta_app_id>/<int:frontend_id>/',
        views.ChangeFrontend.as_view(), name='change_frontend'),
    path('upload-private-frontend/<int:meta_app_id>/<int:frontend_id>/',
        views.UploadPrivateFrontend.as_view(), name='upload_private_frontend'),
    path('install-private-frontend/<int:meta_app_id>/<int:frontend_id>/',
        views.InstallPrivateFrontend.as_view(), name='install_private_frontend'),
    path('update-used-frontend/<int:meta_app_id>/<int:frontend_id>/',
        views.UpdateUsedFrontend.as_view(), name='update_used_frontend'),
]
