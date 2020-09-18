from django.urls import path
from . import views

urlpatterns = [                    
    path('manage-map/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageMaps.as_view(), name='manage_map'),
    path('manage-project-area/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageProjectArea.as_view(), name='manage_project_area'),
]
