from django.urls import path
from . import views

urlpatterns = [                    
    path('manage-observation-form/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageGenericForm.as_view(), name='manage_genericform'),
    # fields
    path('manage-generic-field/<int:meta_app_id>/<int:generic_form_id>/',
        views.ManageGenericFormField.as_view(), name='create_generic_field'), # POST, CREATE
    path('manage-generic-field/<int:meta_app_id>/<int:generic_form_id>/<str:generic_field_class>/', 
        views.ManageGenericFormField.as_view(), name='manage_generic_field'), # GET for creation
    path('manage-generic-field/<int:meta_app_id>/<int:generic_form_id>/<str:generic_field_class>/<str:generic_field_role>/', 
        views.ManageGenericFormField.as_view(), name='manage_generic_field'), # GET for creation with role
    path('edit-generic-field/<int:meta_app_id>/<int:generic_form_id>/<int:generic_field_id>/',
        views.ManageGenericFormField.as_view(), name='edit_generic_field'), # GET, POST editing
    path('get-generic-field/<int:meta_app_id>/<int:generic_form_id>/<int:generic_field_id>/',
        views.GetGenericField.as_view(), name='get_generic_field'),
    path('delete-generic-field/<int:meta_app_id>/<int:generic_field_id>/', views.DeleteGenericField.as_view(),
        name='delete_generic_field'),
    # values
    path('add-generic-field-value/<int:meta_app_id>/<int:generic_form_id>/<int:generic_field_id>/',
        views.AddFieldValue.as_view(), name='add_generic_field_value'),
    path('delete-generic-field-value/<int:meta_app_id>/<int:generic_form_id>/<int:generic_field_id>/<int:generic_value_id>/',
        views.DeleteFieldValue.as_view(), name='delete_generic_field_value'),
]
