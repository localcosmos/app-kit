"use strict";

// name is required
var urlpatterns = urlpatterns.concat([
    path("/", Home.as_view(), {"name" : "home" }),
    path("login/", LoginView.as_view(), {"name" : "login" }),
    path("logout/", LogoutView, {"name" : "logout"}),
	path("sponsors/", Sponsors.as_view(), {"name" : "sponsors"}),
	path("my-account/", AccountView.as_view(), {"name" : "myaccount"}),
	path("delete-account/", DeleteAccountView.as_view(), {"name" : "delete_account"}),
	path("registration/", RegistrationView.as_view(), {"name" : "registration"}),
	path("password/reset/", PasswordResetView.as_view(), {"name" : "password_reset"}),
	path("observation/<int:pk>/", ObservationDetailView.as_view(), {"name" : "observation_detail"}),
	path("observation/new/<uuid:observation_form_uuid>/", ObservationView.as_view(), {"name" : "new_observation"}),
	path("observation/edit/<int:dataset_id>/<str:storage_location>/", ObservationView.as_view(), {"name" : "edit_observation"}),
	path("observation/delete/<int:dataset_id>/<str:storage_location>/", DeleteObservation.as_view(), {"name" : "delete_observation"}),
	path("observation/save-warning/", ObservationViewSaveWarning.as_view(), {"name" : "observation_view_save_warning" }),
	path("observation/new/<str:taxonSource>/<uuid:nameUuid>/<str:taxonNuid>/<str:taxonLatname>/", ObservationView.as_view(), {"name" : "GenericForm"}),
	path("my-observations/", MyObservations.as_view(), {"name" : "my_observations"}),
	path("all-observations/", AllObservations.as_view(), {"name" : "all_observations"}),
	path("sync-observations/<str:action>/", SynchronizeObservations.as_view(), {"name" : "sync_observations"}),
	path("geolocation-report/", GeolocationReport.as_view(), {"name" : "geolocation_report"}),
	path("taxon-profile/<str:taxonSource>/<uuid:nameUuid>/<str:taxonNuid>/<str:taxonLatname>/", TaxonProfiles.as_view(), {"name" : "TaxonProfiles"}),
	path("taxon-profile/<str:taxonSource>/<uuid:nameUuid>/", TaxonProfiles.as_view(), {"name" : "TaxonProfilesUUID"}),
	path("occurrence-map/<str:gbifNubkey>/", OccurrenceMap.as_view(), {"name" : "occurrence_map"}),
	path("quick-logging/<uuid:buttonmatrix_uuid>/", ButtonMatrixView.as_view(), {"name" : "buttonmatrix"}),
	path("log-from-matrix/<uuid:buttonmatrix_uuid>/<int:row>/<int:column>/", LogFromMatrix.as_view(), {"name" : "log_from_matrix"}),
	path("switch-buttonmatrix/", SwitchButtonMatrix.as_view(), {"name" : "switch_buttonmatrix"}),
	path("nature-guide/<uuid:nature_guide_uuid>/", NatureGuideView.as_view(), {"name" : "nature_guide"}),
	path("nature-guide/<uuid:nature_guide_uuid>/<uuid:node_uuid>/", NatureGuideView.as_view(), {"name" : "nature_guide"}),
	path("next-identification-step/", NextIdentificationStep.as_view(), {"name" : "next_identification_step" }),
	//path("nature-guide/<uuid:natureguide_uuid>/<str:letter>/", NatureGuideView.as_view(), {"name" : "nature_guide"}),
	path("toggle/<str:element_id>/", Toggle.as_view(), {"name" : "toggle"}),
	path("online-content/<str:slug>/", OnlineContentView.as_view(), {"name" : "online_content"}),
	path("online-content/<str:slug>/<str:preview_token>/", OnlineContentView.as_view(), {"name" : "online_content_preview"}),
	path("pages/<str:slug>/", TemplateContentView.as_view(), {"name" : "template_content"}),
	path("pages/<str:template_content_id>/", TemplateContentModal.as_view(), {"name" : "template_content_modal"}),
	path("overview-image-modal/", OverviewImageModal.as_view(), {"name" : "overview_image_modal"}),
	path("map/<uuid:map_uuid>/", MapView.as_view(), {"name" : "map"}),
	path("glossary/<uuid:glossary_uuid>/", GlossaryView.as_view(), {"name" : "glossary"}),
	path("taxon-profiles-registry/", TaxonProfilesRegistry.as_view(), {"name" : "taxon_profiles_registry"}),
	path("theme-text/<str:key>/", ThemeTextView.as_view(), {"name" : "theme_text"}),
	path("funding-partners/", FundingPartners.as_view(), {"name" : "funding_partners"}),
	path("legalNotice/", LegalNotice.as_view(), {"name" : "legalNotice"}),
	path("privacy-statement/", PrivacyStatement.as_view(), {"name" : "privacy_statement"})
]);
