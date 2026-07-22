from django.urls import path
from . import views

urlpatterns = [                    
    path('manage-object-classes/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageObjectClasses.as_view(), name='manage_objectclasses'),
    path('get-object-classes/<int:meta_app_id>/<int:object_classes_id>/',
        views.GetObjectClasses.as_view(), name='get_object_classes'),
    path('create_object-class/<int:meta_app_id>/<int:object_classes_id>/',
        views.ManageObjectClass.as_view(), name='create_object_class'),
    path('edit_object-class/<int:meta_app_id>/<int:object_classes_id>/<int:object_class_id>/',
        views.ManageObjectClass.as_view(), name='edit_object_class'),
    path('delete_object-class/<int:pk>/', 
        views.DeleteObjectClass.as_view(), name='delete_object_class'),
    path('add_object-class-taxon/<int:meta_app_id>/<int:object_classes_id>/<int:object_class_id>/',
        views.AddObjectClassTaxon.as_view(), name='add_object_class_taxon'),
    path('delete-object-class-taxon/<int:pk>/',
        views.DeleteObjectClassTaxon.as_view(), name='delete_object_class_taxon'),
    path('set-object-class-link/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.SetObjectClassLink.as_view(), name='set_object_class_link'),
]
