#####################################################################################################
#
# APP PREVIEW BUILDER
# - builds a preview webapp without localcosmos features
# - used to provide a preview for OnlineContent and FactSheets
# - can only be built if the user provided all required assets defined in config.json
# - manages the preview folder, eg {settings.APP_KIT_ROOT}/{app.uuid}/version/{app.version}/preview/
# - manages locales and the locale files
# - manages app images that are uploaded by the user
#
#####################################################################################################

import os, shutil, json

from . import AppBuilderBase


class PreviewExists(Exception):
    pass


# builds a webapp without content, no android, no ios
class AppPreviewBuilder(AppBuilderBase):

    # previews are not being validated
    def validate(self):
        raise NotImplementedError('AppPreviewBuilder has no validate method')

    # create app preview, webapp only
    #- delete the preview folder and recreate the preview folder
    #- symlink/copy all necessary files, but no generic content
    #- the preview is for the online content, not for other contents
    #- raises an Exception if the preview folder already exists
    #- copy user content from older version (which ones?)
    def build(self):

        self.logger = self._get_logger('preview_build')
        self.logger.info('Starting AppPreviewBuilder.build process for app {0} version {1}'.format(self.meta_app.name,
                                                                                        self.meta_app.current_version))

        try:
            # STEP 1, create the root folder of the preview app, which then contains the www folder
            self.logger.info('(Re)Creating preview folder: {0}'.format(self._app_preview_path))
            self._recreate_preview_folder()

            # STEP 2
            self._build_Frontend()

            if not os.path.isdir(self._app_www_path):
                raise NotADirectoryError('www folder not present in the selected frontend. The frontend seems to be broken.')

            # STEP 3
            self.logger.info('Creating localcosmos_content_folder: {0}'.format(self._app_localcosmos_content_path))
            self._create_localcosmos_content_folder()

            # all content created by localcosmos app kit goes into localcosmos_content_folder
            
            # STEP 4: create and write preview settings
            self.logger.info('Writing settings.json: {0}'.format(self._app_settings_json_filepath))
            preview_settings = self._get_app_settings(preview=True)
            app_settings_string = json.dumps(preview_settings, indent=4, ensure_ascii=False)

            with open(self._app_settings_json_filepath, 'w', encoding='utf-8') as settings_json_file:
                settings_json_file.write(app_settings_string)

            # STEP 5: create empty features.json, required for FactSheet preview
            app_features_string = json.dumps({}, indent=4, ensure_ascii=False)
            app_features_json_file = self._app_features_json_filepath
            with open(app_features_json_file, 'w', encoding='utf-8') as f:
                f.write(app_features_string)


            # STEP 6: copy webapp specific files provided by the frontend
            self.logger.info('Copying webapp assets')
            self._build_Frontend_webapp_specific_assets()


            # STEP 6: create basic primary locale
            self.logger.info('Building locales')
            self._build_locales()

            # the preview also optionally supplies AppFrontendImages and AppFrontendTexts
            # however, the preview frontend should work without these assets


            # STEP 8: link to webserver
            self.logger.info('Linking to webserver')
            self._link_to_webserver()

            self.logger.info('App made available at {0}'.format(self.meta_app.app.preview_version_path))

            self.logger.info('Finished building preview')


        except Exception as e:
            
            self.logger.error(e, exc_info=True)
            
            # send email!
            self.send_bugreport_email(e)

    
    #############################################################################################
    # BUILD STEPS
    #############################################################################################

    def _recreate_preview_folder(self):

        if os.path.isdir(self._app_preview_path):
            shutil.rmtree(self._app_preview_path)

        os.makedirs(self._app_preview_path)


    def _create_localcosmos_content_folder(self):
        os.makedirs(self._app_localcosmos_content_path)

    
    def _link_to_webserver(self):
        # make the preview live, the preview live folder is a subfolder of settings.MEDIA_ROOT
        self.deletecreate_folder(self._preview_webapp_served_path)

        os.symlink(self._app_www_path, self._preview_webapp_served_www_path)

        # update the previre served folder in the database
        # set the apps preview folder - to the served folder, not the app-kits internal folder
        self.meta_app.app.preview_version_path = self._preview_webapp_served_www_path
        self.meta_app.app.save()


    #############################################################################################
    # BUILD BASIC LOCALIZATION
    # - the frontend developer may ship translation files in www/locales/{LANGUAGE_CODE}/plain.json
    # - provide basic fallback files to make it easier for the frontend developer:
    #   no check needed if a file is present (no 404)
    # - do not cover secondary languages in preview builds
    #############################################################################################
    def _build_locales(self):

        app_primary_locale_filepath = self._app_locale_filepath(self.meta_app.primary_language)
        primary_locale_folder = self._app_locale_path(self.meta_app.primary_language)

        primary_locale_fallback = {}

        if not os.path.isdir(primary_locale_folder):
            os.makedirs(primary_locale_folder)


        if not os.path.isfile(app_primary_locale_filepath):

            with open(app_primary_locale_filepath, 'w') as app_primary_locale_file:
                app_primary_locale_file.write(json.dumps(primary_locale_fallback))


        app_glossarized_primary_locale_filepath = self._app_glossarized_locale_filepath(self.meta_app.primary_language)

        if not os.path.isfile(app_glossarized_primary_locale_filepath):

            with open(app_glossarized_primary_locale_filepath, 'w') as app_glossarzied_primary_locale_file:
                app_glossarzied_primary_locale_file.write(json.dumps(primary_locale_fallback))

    
    #############################################################################################
    # PREVIEW SPECIFIC PATHS
    #############################################################################################
    @property
    def _app_www_path(self):
        return os.path.join(self._app_preview_path, 'www')