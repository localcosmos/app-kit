from django.urls import path
from . import views

urlpatterns = [                    
    path('manage-factsheets/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageFactSheets.as_view(), name='manage_factsheets'),
    path('create-factsheet/<int:meta_app_id>/<int:fact_sheets_id>/', views.CreateFactSheet.as_view(),
        name='create_factsheet'),
    path('manage-factsheet/<int:meta_app_id>/<int:fact_sheet_id>/', views.ManageFactSheet.as_view(),
        name='manage_factsheet'),
    path('delete-factsheet/<int:pk>/', views.DeleteFactSheet.as_view(), name='delete_fact_sheet'),
    path('upload-factsheet-template/<int:meta_app_id>/<int:fact_sheets_id>/',
        views.UploadFactSheetTemplate.as_view(), name='upload_factsheet_template'),
     # images
     path('manage-factsheet-image/<int:fact_sheet_id>/<str:microcontent_category>/<int:content_image_id>/',
        views.ManageFactSheetImage.as_view(), name='manage_factsheet_image'),
     path('manage-factsheet-image/<int:fact_sheet_id>/<str:microcontent_category>/<int:content_type_id>/<int:object_id>/<str:image_type>/', views.ManageFactSheetImage.as_view(),
        name='manage_factsheet_image'),
     path('delete-factsheet-image/<int:fact_sheet_id>/<str:microcontent_category>/<int:pk>/',
        views.DeleteFactSheetImage.as_view(), name='delete_factsheet_image'),
     path('get-factsheet-formfields/<int:fact_sheet_id>/<str:microcontent_category>/<str:microcontent_type>/',
        views.GetFactSheetFormFields.as_view(), name='get_factsheet_form_fields'),
]
