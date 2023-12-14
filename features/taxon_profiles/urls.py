from django.urls import path
from . import views

urlpatterns = [
    path('manage-taxon-profiles/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
         views.ManageTaxonProfiles.as_view(), name='manage_taxonprofiles'),
    path('nature-guides-taxon-profile-page/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/<int:nature_guide_id>/<str:list_type>/',
         views.NatureGuideTaxonProfilePage.as_view(), name='get_nature_guide_taxonprofile_page'),
    path('create-taxon-profile/<int:meta_app_id>/<int:taxon_profiles_id>/<str:taxon_source>/<uuid:name_uuid>/',
         views.CreateTaxonProfile.as_view(), name='create_taxon_profile'),
    path('manage-taxon-profile/<int:meta_app_id>/<int:taxon_profiles_id>/<str:taxon_source>/<uuid:name_uuid>/',
         views.ManageTaxonProfile.as_view(), name='manage_taxon_profile'),
    path('delete-taxon-profile/<int:meta_app_id>/<int:pk>/',
        views.DeleteTaxonProfile.as_view(), name='delete_taxon_profile'),
    path('create-taxon-text-type/<int:meta_app_id>/<int:taxon_profiles_id>/<str:taxon_source>/<uuid:name_uuid>/',
         views.ManageTaxonTextType.as_view(), name='create_taxon_text_type'),
    path('manage-taxon-text-type/<int:meta_app_id>/<int:taxon_text_type_id>/<int:taxon_profiles_id>/<str:taxon_source>/<uuid:name_uuid>/',
        views.ManageTaxonTextType.as_view(), name='manage_taxon_text_type'),
    path('delete-taxon-text-type/<int:pk>/', views.DeleteTaxonTextType.as_view(), name='delete_taxon_text_type'),
    path('manage-taxon-text-types-order/<int:taxon_profiles_id>/', views.ManageTaxonTextTypesOrder.as_view(), name='manage_taxon_text_types_order'),
    # change publication status
    path('change-taxon-profile-publication-status/<int:meta_app_id>/<int:taxon_profile_id>/',
         views.ChangeTaxonProfilePublicationStatus.as_view(), name='change_taxon_profile_publication_status'),
    path('batch-change-taxon-profile-publication-status/<int:meta_app_id>/<int:taxon_profiles_id>/<int:nature_guide_id>/',
         views.BatchChangeNatureGuideTaxonProfilesPublicationStatus.as_view(),
         name='batch_change_taxon_profile_publication_status'),
    # this one is only for the autocomplete redirect
    path('manage-taxon-profile/<int:meta_app_id>/<int:taxon_profiles_id>/',
        views.ManageTaxonProfile.as_view(), name='manage_taxon_profile_baseurl'),
    path('get-taxon-profiles-manage-or-create-url/<int:meta_app_id>/<int:taxon_profiles_id>/',
         views.GetManageOrCreateTaxonProfileURL.as_view(), name='get_taxon_profiles_manage_or_create_url'),
    # load images in taxon profiles
    path('collect-taxon-images/<int:meta_app_id>/<int:pk>/<str:taxon_source>/<uuid:name_uuid>/',
        views.CollectTaxonImages.as_view(), name='collect_taxon_images'),
    path('collect-taxon-traits/<str:taxon_source>/<uuid:name_uuid>/',
        views.CollectTaxonTraits.as_view(), name='collect_taxon_traits'),
    # taxon profile images with text
    path('manage-taxon-profile-image/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageTaxonProfileImage.as_view(), name='manage_taxon_profile_image'),
    path('manage-taxon-profile-image/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/<str:image_type>/',
        views.ManageTaxonProfileImage.as_view(), name='manage_taxon_profile_image'),
    path('manage-taxon-profile-image/<int:meta_app_id>/<int:content_image_id>/',
        views.ManageTaxonProfileImage.as_view(), name='manage_taxon_profile_image'),
    # delete taxon profile image
    path('delete-taxon-profile-image/<int:meta_app_id>/<int:pk>/',
        views.DeleteTaxonProfileImage.as_view(), name='delete_taxon_profile_image'),
]
