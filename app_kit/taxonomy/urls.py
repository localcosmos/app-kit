from django.urls import path
from taxonomy import views

urlpatterns = [
    path('searchtaxon/', views.SearchTaxon.as_view(), name='search_taxon'),
    path('create-meta-vernacular-name/<int:meta_app_id>/<str:taxon_source>/<uuid:name_uuid>/',
         views.ManageMetaVernacularName.as_view(), name='create_meta_vernacular_name'),
    path('manage-meta-vernacular-name/<int:meta_app_id>/<int:meta_vernacular_name_id>/',
         views.ManageMetaVernacularName.as_view(), name='manage_meta_vernacular_name'),
    path('delete-meta-vernacular-name/<int:meta_app_id>/<int:pk>/',
         views.DeleteMetaVernacularName.as_view(), name='delete_meta_vernacular_name'),
]

