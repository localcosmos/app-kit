from django.urls import path, re_path
from . import views

urlpatterns = [
    path('manage-natureguide/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageNatureGuide.as_view(), name='manage_natureguide'),
    path('manage-natureguide/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/<int:parent_node_id>/',
        views.ManageNatureGuide.as_view(), name='manage_natureguide'),
    # node creation
    path('create-natureguide-node/<str:node_type>/<int:meta_app_id>/<int:parent_node_id>/',
        views.ManageNodelink.as_view(), name='create_nodelink'), # create
    path('manage-natureguide-node/<int:meta_app_id>/<int:parent_node_id>/<int:node_id>/',
        views.ManageNodelink.as_view(), name='manage_nodelink'), # manage
    # create branch copies
    path('copy-tree-branch/<int:meta_app_id>/<int:node_id>/',
        views.CopyTreeBranch.as_view(), name='copy_tree_branch'),
    # node loading
    path('load-keynodes/<int:meta_app_id>/<int:parent_node_id>/',
        views.LoadKeyNodes.as_view(), name='load_keynodes'),
    # nodelink deletion
    path('delete-nodelink/<int:parent_node_id>/<int:child_node_id>/',
        views.DeleteNodelink.as_view(), name='delete_nodelink'),
    # add existing nodes
    path('add-natureguide-node/<int:meta_app_id>/<int:parent_node_id>/',
        views.AddExistingNodes.as_view(), name='add_existing_nodes'),
    # node order
    path('store-node-order/<int:parent_node_id>/',
        views.StoreNodeOrder.as_view(), name='store_node_order'),
    # move node
    path('move-natureguide-node/<int:meta_app_id>/<int:parent_node_id>/<int:child_node_id>/',
        views.MoveNatureGuideNode.as_view(), name='move_natureguide_node'),
    path('search-move-to-group/<int:meta_app_id>/<int:nature_guide_id>/',
        views.SearchMoveToGroup.as_view(), name='search_move_to_group'),
    # load menu - used if children count is high
    path('load-nodemenu/<int:meta_app_id>/<int:parent_node_id>/<int:node_id>/',
        views.LoadNodeManagementMenu.as_view(), name='load_nodemenu'),
    # matrix filters
    path('load-matrix-filters/<int:meta_app_id>/<int:meta_node_id>/',
        views.LoadMatrixFilters.as_view(), name='load_matrix_filters'),
    path('create-matrix-filter/<int:meta_app_id>/<int:meta_node_id>/<str:filter_type>/',
         views.ManageMatrixFilter.as_view(), name='create_matrix_filter'),
    path('manage-matrix-filter/<int:meta_app_id>/<int:matrix_filter_id>/',
         views.ManageMatrixFilter.as_view(), name='manage_matrix_filter'),
    path('delete-matrix-filter/<int:meta_app_id>/<int:pk>/',
        views.DeleteMatrixFilter.as_view(), name='delete_matrix_filter'),
    # space management
    path('create-matrix-filter-space/<int:meta_app_id>/<int:matrix_filter_id>/',
         views.ManageMatrixFilterSpace.as_view(), name='create_matrix_filter_space'),
    path('manage-matrix-filter-space/<int:meta_app_id>/<int:space_id>/',
         views.ManageMatrixFilterSpace.as_view(), name='manage_matrix_filter_space'),
    path('delete-matrix-filter_space/<int:meta_app_id>/<int:pk>/',
        views.DeleteMatrixFilterSpace.as_view(), name='delete_matrix_filter_space'),
    # additional space image
    path('manage-additional-matrix-filter-space-image/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/<str:image_type>/',
        views.ManageAdditionalMatrixFilterSpaceImage.as_view(),
        name='manage_additional_matrix_filter_space_image'),
    path('delete-additional-matrix-filter-space-image/<int:meta_app_id>/<int:pk>/',
        views.DeleteAdditionalMatrixFilterSpaceImage.as_view(),
        name='delete_additional_matrix_filter_space_image'),
    # node search
    path('search-for-node/<int:meta_app_id>/<int:nature_guide_id>/',
        views.SearchForNode.as_view(), name='search_for_node'),
    # node analysis
    path('node-analysis/<int:meta_app_id>/<int:meta_node_id>/',
        views.NodeAnalysis.as_view(), name='node_analysis'),
    # getting the (cached) identification matrix
    path('get-identification-matrix/<int:meta_node_id>/',
        views.GetIdentificationMatrix.as_view(), name='get_identification_matrix'),
    # matrix filter restrictions
    path('manage-matrix-filter-restrictions/<int:meta_app_id>/<int:meta_node_id>/<int:matrix_filter_id>',
         views.ManageMatrixFilterRestrictions.as_view(), name='manage_matrix_filter_restrictions'),
    # identification mode
    path('set-identification-mode/<int:meta_node_id>/<str:identification_mode>/',
         views.StoreIdentificationMode.as_view(), name='store_identification_mode'),
    # overview image
    path('manage-overview-image/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/<str:image_type>/',
        views.ManageOverviewImage.as_view(), name='manage_overview_image'),
    path('delete-overview-image/<int:meta_app_id>/<int:pk>/', views.DeleteOverviewImage.as_view(),
        name='delete_overview_image'),
]
