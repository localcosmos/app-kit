from django.conf import settings
from django.urls import include, path
from . import views


urlpatterns = [
    # features
    #path('', include('app_kit.features.buttonmatrix.urls')),
    path('', include('app_kit.features.backbonetaxonomy.urls')),
    path('', include('taxonomy.urls')),
    path('online-content/', include('localcosmos_server.online_content.urls')),
    path('observation-forms/', include('app_kit.features.generic_forms.urls')),
    path('taxon-profiles/', include('app_kit.features.taxon_profiles.urls')),
    path('nature-guides/', include('app_kit.features.nature_guides.urls')),
    path('custom-taxonomy/', include('taxonomy.sources.custom.urls')),
    path('glossary/', include('app_kit.features.glossary.urls')),
    path('maps/', include('app_kit.features.maps.urls')),
    path('fact-sheets/', include('app_kit.features.fact_sheets.urls')),
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
    path('manage-content-image/<int:content_type_id>/<int:object_id>/',
        views.ManageContentImage.as_view(), name='manage_content_image'),
    path('manage-content-image/<int:content_type_id>/<int:object_id>/<str:image_type>/',
        views.ManageContentImage.as_view(), name='manage_content_image'),
    path('manage-content-image/<int:content_image_id>/',
        views.ManageContentImage.as_view(), name='manage_content_image'),
    path('delete-content-image/<int:pk>/',
        views.DeleteContentImage.as_view(), name='delete_content_image'),
    # content image with text
    path('manage-content-image-with-text/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageContentImageWithText.as_view(), name='manage_content_image_with_text'),
    path('manage-content-image-with-text/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/<str:image_type>/',
        views.ManageContentImageWithText.as_view(), name='manage_content_image_with_text'),
    path('manage-content-image-with-text/<int:meta_app_id>/<int:content_image_id>/',
        views.ManageContentImageWithText.as_view(), name='manage_content_image_with_text'),
    # content image suggestions
    path('manage-content-image-suggestions/<int:content_type_id>/<int:object_id>/',
        views.ManageContentImageSuggestions.as_view(), name='manage_content_image_suggestions'),
    path('manage-content-image-suggestions/<int:content_type_id>/',
        views.ManageContentImageSuggestions.as_view(), name='manage_content_image_suggestions'),
    # generic object order
    path('store-object-order/<int:content_type_id>/',
        views.StoreObjectOrder.as_view(), name='store_object_order'),
    # button placeholder
    path('mockbutton/',
        views.MockButton.as_view(), name='mockbutton'),
    # app design
    path('manage-app-design/<int:meta_app_id>/<str:theme_name>/',
        views.ManageAppDesign.as_view(), name='switch_app_design'),
    path('manage-app-design/<int:meta_app_id>/',
        views.ManageAppDesign.as_view(), name='manage_app_design'),
    # app theme images
    path('manage-app-theme-image/<int:meta_app_id>/<str:image_type>/',
        views.ManageAppThemeImage.as_view(), name='manage_app_theme_image'),
    path('delete-app-theme-image/<int:meta_app_id>/<str:image_type>/',
        views.DeleteAppThemeImage.as_view(), name='delete_app_theme_image'),
    path('get-app-theme-image-formfield/<int:meta_app_id>/<str:image_type>/',
        views.GetAppThemeImageFormField.as_view(), name='get_app_theme_image_formfield'),
    # anycluster, prefixed with app-kit to distinguish it from the API anycluster
    path('anycluster/', include('localcosmos_server.anycluster_schema_urls')),
    # spreadsheet import
    path('import-from-zip/<int:meta_app_id>/<int:content_type_id>/<int:generic_content_id>/',
         views.ImportFromZip.as_view(), name='import_from_zip'),
]
