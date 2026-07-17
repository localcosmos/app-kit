from django.urls import path
from . import views

urlpatterns = [                    
    path('manage-object-classes/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageObjectClasses.as_view(), name='manage_objectclasses'),
    path('get-object-classes/<int:meta_app_id>/<int:object_classes_id>/',
        views.GetObjectClasses.as_view(), name='get_object_classes'),
]
