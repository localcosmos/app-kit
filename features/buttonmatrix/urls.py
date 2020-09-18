from django.urls import path
from app_kit.features.buttonmatrix import views

urlpatterns = [
    path('manage-buttonmatrix/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageButtonMatrix.as_view(), name='manage_buttonmatrix'),
    path('manage-buttonmatrix-button/<int:meta_app_id>/<int:button_matrix_id>/<int:row>/<int:column>/',
        views.ManageButtonMatrixButton.as_view(), name='manage_buttonmatrix_button'),
    path('delete-buttonmatrix-element/<str:content_type>/<int:object_pk>/',
        views.DeleteButtonMatrixElement.as_view(), name='delete_buttonmatrix_element'),
    path('get-exposed-field-options/<int:meta_app_id>/<int:buttonmatrix_id>/',
        views.GetButtonMatrixExposedFieldOptions.as_view(), name='get_exposed_field_options_base'),
    path('get-exposed-field-options/<int:meta_app_id>/<int:buttonmatrix_id>/<uuid:generic_form_uuid>/',
        views.GetButtonMatrixExposedFieldOptions.as_view(), name='get_exposed_field_options'),
]
