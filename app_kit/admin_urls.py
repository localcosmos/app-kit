from django.conf import settings
from django.urls import include, path
from . import views

from localcosmos_server import generic_views

urlpatterns = [
    # locale switcher
    path('i18n/', include('django.conf.urls.i18n')),
    # features
    #path('', include('app_kit.features.buttonmatrix.urls')),
    path('', include('app_kit.features.backbonetaxonomy.urls')),
    path('', include('taxonomy.urls')),
    path('template-content/', include('localcosmos_server.template_content.urls')),
    path('observation-forms/', include('app_kit.features.generic_forms.urls')),
    path('taxon-profiles/', include('app_kit.features.taxon_profiles.urls')),
    path('nature-guides/', include('app_kit.features.nature_guides.urls')),
    path('custom-taxonomy/', include('taxonomy.sources.custom.urls')),
    path('glossary/', include('app_kit.features.glossary.urls')),
    path('maps/', include('app_kit.features.maps.urls')),
    path('frontend/', include('app_kit.features.frontend.urls')),
    # apps
    # create apps
    path('create-app/', views.CreateApp.as_view(), name='create_app'), # generic forms etc need app_to_feature
    path('get-app-card/<int:meta_app_id>/', views.GetAppCard.as_view(), name='get_app_card'),
    path('app-limit-reached/', views.AppLimitReached.as_view(), name='app_limit_reached'),
    # delete app
    path('delete-app/<int:pk>/', views.DeleteApp.as_view(), name='delete_app'),
    # manage app
    path('manage-app/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/', views.ManageApp.as_view(),
        name='manage_metaapp'),
    # TRANSLATE APP
    path('translate-app/<int:meta_app_id>/', views.TranslateApp.as_view(), name='translate_app'),
    path('translate-vernacular-names/<int:meta_app_id>/', views.TranslateVernacularNames.as_view(),
         name='translate_vernacular_names'),
    # BUILD APP
    path('build-app/<int:meta_app_id>/', views.BuildApp.as_view(), name='build_app'),
    path('build-app/<int:meta_app_id>/<str:action>/', views.BuildApp.as_view(), name='build_app'),
    # NEW APP VERSION
    path('start-new-app-version/<int:meta_app_id>/', views.StartNewAppVersion.as_view(),
         name='start_new_app_version'),
    # create generic app content
    path('create-appcontent/<int:meta_app_id>/<int:content_type_id>/',
        views.CreateGenericAppContent.as_view(), name='create_generic_appcontent'), # generic forms etc need app_to_feature
    # generic content
    path('add-existing-generic-content/<int:meta_app_id>/<int:content_type_id>/',
         views.AddExistingGenericContent.as_view(), name='add_existing_generic_content'),
    path('remove-app-generic-content/<int:pk>/', views.RemoveAppGenericContent.as_view(),
         name='remove_app_generic_content'),
    path('edit-generic-content-name/<int:content_type_id>/<int:generic_content_id>/',
         views.EditGenericContentName.as_view(), name='edit_generic_content_name'),
    path('generic-content-card/<int:meta_app_id>/<int:generic_content_link_id>/',
         views.GetGenericContentCard.as_view(), name='generic_content_card'),
    path('change_generic_content_status/<int:meta_app_id>/<int:generic_content_link_id>/',
         views.ChangeGenericContentPublicationStatus.as_view(), name='change_generic_content_status'),
    # app languages
    path('manage-app-languages/<int:meta_app_id>/', views.ManageAppLanguages.as_view(),
         name='manage_app_languages'),
    path('manage-app-languages/<int:meta_app_id>/<str:action>/', views.ManageAppLanguages.as_view(),
        name='add_app_languages'),
    path('manage-app-languages/<int:meta_app_id>/<str:action>/<str:language>/',
        views.ManageAppLanguages.as_view(), name='manage_app_languages'),
    path('delete-app-language/<int:pk>/', views.DeleteAppLanguage.as_view(),
        name='delete_app_language'), # POST
    path('delete-app-language/<int:meta_app_id>/<str:language>/', views.DeleteAppLanguage.as_view(),
        name='delete_app_language'), # GET
    # taxonomic restriction
    path('add_taxonomic_restriction/<int:content_type_id>/<int:object_id>/',
        views.AddTaxonomicRestriction.as_view(), name='add_taxonomic_restriction'),
    path('add_taxonomic_restriction/<int:content_type_id>/<int:object_id>/<str:typed>/',
        views.AddTaxonomicRestriction.as_view(), name='add_taxonomic_restriction'),
    path('remove_taxonomic_restriction/<int:pk>/',
        views.RemoveTaxonomicRestriction.as_view(), name='remove_taxonomic_restriction'),
    # app and content images
    path('manage-content-image/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageContentImage.as_view(), name='manage_content_image'),
    path('manage-content-image/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/<str:image_type>/',
        views.ManageContentImage.as_view(), name='manage_content_image'),
    path('manage-content-image/<int:meta_app_id>/<int:content_image_id>/',
        views.ManageContentImage.as_view(), name='manage_content_image'),
    path('delete-content-image/<int:meta_app_id>/<int:pk>/',
        views.DeleteContentImage.as_view(), name='delete_content_image'),
    # content image with text
    path('manage-content-image-with-text/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageContentImageWithText.as_view(), name='manage_content_image_with_text'),
    path('manage-content-image-with-text/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/<str:image_type>/',
        views.ManageContentImageWithText.as_view(), name='manage_content_image_with_text'),
    path('manage-content-image-with-text/<int:meta_app_id>/<int:content_image_id>/',
        views.ManageContentImageWithText.as_view(), name='manage_content_image_with_text'),
    # urls for multiple content images
    path('content-images-list/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ContentImagesList.as_view(), name='content_images_list'),
    path('manage-content-images-with-text/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageContentImagesWithText.as_view(), name='manage_content_images_with_text'),
    path('manage-content-images-with-text/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/<str:image_type>/',
        views.ManageContentImagesWithText.as_view(), name='manage_content_images_with_text'),
    path('manage-content-images-with-text/<int:meta_app_id>/<int:content_image_id>/',
        views.ManageContentImagesWithText.as_view(), name='manage_content_images_with_text'),
    path('delete-content-images/<int:meta_app_id>/<int:pk>/',
        views.DeleteContentImages.as_view(), name='delete_content_images'),
    # localized content image
    path('manage-localized-content-image/<int:content_image_id>/<str:language_code>/',
        views.ManageLocalizedContentImage.as_view(), name='manage_localized_content_image'),
    path('delete-localized-content-image/<int:pk>/',
        views.DeleteLocalizedContentImage.as_view(), name='delete_localized_content_image'),
    # content image suggestions
    path('manage-content-image-suggestions/<int:content_type_id>/<int:object_id>/',
        views.ManageContentImageSuggestions.as_view(), name='manage_content_image_suggestions'),
    path('manage-content-image-suggestions/<int:content_type_id>/',
        views.ManageContentImageSuggestions.as_view(), name='manage_content_image_suggestions'),
    # button placeholder
    path('mockbutton/',
        views.MockButton.as_view(), name='mockbutton'),
    # anycluster, prefixed with app-kit to distinguish it from the API anycluster
    #path('anycluster/', include('localcosmos_server.anycluster_schema_urls')),
    # spreadsheet import
    path('import-from-zip/<int:meta_app_id>/<int:content_type_id>/<int:generic_content_id>/',
         views.ImportFromZip.as_view(), name='import_from_zip'),
    # TAGS
    path('tag-any-element/<int:content_type_id>/<int:object_id>/', views.TagAnyElement.as_view(), name='tag_any_element'),
    path('reload-tags/<int:content_type_id>/<int:object_id>/', views.ReloadTags.as_view(), name='reload_tags'),
    # object order
    path('store-object-order/<int:content_type_id>/',
        generic_views.StoreObjectOrder.as_view(), name='store_app_kit_object_order'),
    path('manage-object-order/<int:content_type_id>/',
        views.ManageObjectOrder.as_view(), name='manage_app_kit_object_order'),
    # SEO
    path('manage-seo/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/', views.ManageAppKitSeoParameters.as_view(),
         name='manage_app_kit_seo_parameters'),
]
