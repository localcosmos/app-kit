from django.urls import path
from . import views

urlpatterns = [
    # custom taxa
    path('custom-taxonomic-tree/<int:meta_app_id>/<str:language>/', views.ManageCustomTaxonTree.as_view(),
        name='manage_custom_taxontree'),
    path('create-new-root-taxon/<str:language>/', views.ManageCustomTaxon.as_view(),
        name='create_new_custom_root_taxon'),
    path('create-new-custom-taxon/<uuid:parent_name_uuid>/<str:language>/', views.ManageCustomTaxon.as_view(),
        name='create_new_custom_taxon'),
    path('manage-custom-taxon/<uuid:name_uuid>/<str:language>/', views.ManageCustomTaxon.as_view(),
        name='manage_custom_taxon'),
    path('delete-custom-taxon/<int:pk>/', views.DeleteTaxon.as_view(), name='delete_custom_taxon'),
    path('load-custom-children/<uuid:name_uuid>/<str:language>/',
        views.ManageCustomTaxonChildren.as_view(), name='load_custom_taxon_children'),
    path('move-custom-taxon/<uuid:name_uuid>/',
        views.MoveCustomTaxonTreeEntry.as_view(), name='move_custom_taxon'),
]
