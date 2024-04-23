from django.urls import path
from . import views

urlpatterns = [                    
    path('manage-map/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageMaps.as_view(), name='manage_map'),
    path('manage-project-area/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageProjectArea.as_view(), name='manage_project_area'),
    path('create-map-taxonomic-filter/<int:meta_app_id>/<int:map_id>/',
        views.ManageTaxonomicFilter.as_view(), name='create_map_taxonomic_filter'),
    path('manage-map-taxonomic-filter/<int:meta_app_id>/<int:map_id>/<int:taxonomic_filter_id>/',
        views.ManageTaxonomicFilter.as_view(), name='manage_map_taxonomic_filter'),
    path('get-map-taxonomic-filters/<int:meta_app_id>/<int:map_id>/',
        views.GetTaxonomicFilters.as_view(), name='get_map_taxonomic_filters'),
    path('delete-map-taxonomic-filters/<int:pk>/',
        views.DeleteTaxonomicFilter.as_view(), name='delete_map_taxonomic_filter'),
    path('delete-map-filter-taxon/<int:meta_app_id>/<int:map_id>/<int:taxonomic_filter_id>/<int:pk>/',
        views.DeleteFilterTaxon.as_view(), name='delete_map_filter_taxon'),
]
