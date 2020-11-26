from django.urls import path
from . import views

urlpatterns = [                    
    path('manage-factsheets/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageFactSheets.as_view(), name='manage_factsheets'),
    path('create-factsheet/<int:meta_app_id>/<int:fact_sheets_id>/', views.CreateFactSheet.as_view(),
         name='create_factsheet'),
    path('manage-factsheet/<int:meta_app_id>/<int:fact_sheet_id>/', views.ManageFactSheet.as_view(),
         name='manage_factsheet'),
]
