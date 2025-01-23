#####################################################################################################
#
# APP PREVIEW BUILDER
# - builds a browser preview without localcosmos features
# - used to provide a preview for TemplateContent
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


# builds a browser app without content, no android, no ios
class AppPreviewBuilder(AppBuilderBase):

    @property
    def _builder_identifier(self):
        return 'preview'

    # previews are not being validated
    def validate(self):
        raise NotImplementedError('AppPreviewBuilder has no validate method')


    def build(self):

        self.logger = self._get_logger('build')
        self.logger.info('Starting AppPreviewBuilder.build process for app {0} version {1}'.format(self.meta_app.name,
                                                                                        self.meta_app.current_version))

        try:
            # STEP 1, create the root folder of the preview app, which then contains the www folder
            self.logger.info('(Re)Creating preview folder: {0}'.format(self._app_builder_path))
            self._recreate_builder_folder()

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

            # STEP 5: create empty features.json, required for TemplateContent preview
            app_features_string = json.dumps({}, indent=4, ensure_ascii=False)
            app_features_json_file = self._app_features_json_filepath
            with open(app_features_json_file, 'w', encoding='utf-8') as f:
                f.write(app_features_string)


            # STEP 6: create basic primary locale
            self.logger.info('Building locales')
            self._build_locales()


            # STEP 7: run cordova build browser inside cordova
            self.logger.info('Building cordova app')
            cordova_builder = self.get_cordova_builder()

            browser_built_path, browser_zip_filepath = cordova_builder.build_browser(build_zip=False)

            # the preview also will optionally suppliy AppFrontendImages and AppFrontendTexts (in the future)
            # however, the preview frontend should work without these assets

            # STEP 8: link to webserver
            self.logger.info('Linking to webserver')
            self._link_to_webserver(browser_built_path)

            self.logger.info('App made available at {0}'.format(self.meta_app.app.preview_version_path))

            self.logger.info('Finished building preview')


        except Exception as e:
            
            self.logger.error(e, exc_info=True)
            
            # send email!
            self.send_bugreport_email(e)

    
    #############################################################################################
    # BUILD STEPS
    #############################################################################################

    
    def _link_to_webserver(self, browser_built_path):
        # make the preview live, the preview live folder is a subfolder of settings.MEDIA_ROOT
        self.deletecreate_folder(self._preview_browser_served_path)

        os.symlink(browser_built_path, self._preview_browser_served_www_path)

        # update the previre served folder in the database
        # set the apps preview folder - to the served folder, not the app-kits internal folder
        self.meta_app.app.preview_version_path = self._preview_browser_served_www_path
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
    # METHODS FOR USAGE APP KIT VIEWS
    # - 
    #############################################################################################
    
    def get_app_settings(self):

        with open(self._app_settings_json_filepath, 'r') as app_settings_file:
            app_settings = json.loads(app_settings_file.read())

        return app_settings