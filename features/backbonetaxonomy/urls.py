from django.urls import path
from app_kit.features.backbonetaxonomy import views

urlpatterns = [
    path('manage-backbonetaxonomy/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageBackboneTaxonomy.as_view(), name='manage_backbonetaxonomy'),
    path('add-backbone-taxon/<int:meta_app_id>/<int:backbone_id>/',
        views.AddBackboneTaxon.as_view(), name='add_backbone_taxon'),
    path('add-multiple-backbone-taxa/<int:meta_app_id>/<int:backbone_id>/',
        views.AddMultipleBackboneTaxa.as_view(), name='add_backbone_taxa'),
    path('remove-backbone-taxon/<int:meta_app_id>/<int:backbone_id>/<uuid:name_uuid>/<str:source>/',
        views.RemoveBackboneTaxon.as_view(), name='remove_backbone_taxon'),
    path('manage-backbone-fulltree/<int:content_type_id>/<int:pk>/',
        views.BackboneFulltreeUpdate.as_view(), name='manage_backbone_fulltree'),
    path('search-backbonetaxonomy/<int:meta_app_id>/',
        views.SearchBackboneTaxonomy.as_view(), name='search_backbonetaxonomy'),
]
