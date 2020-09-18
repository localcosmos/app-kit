#####################################################################################################
#
# APP PREVIEW
# - manages the preview folder, eg {settings.APP_KIT_ROOT}/{app.uuid}/version/{app.version}/preview/
# - manages locales and the locale files
# - manages app images that are uploaded by the user
#
#####################################################################################################

import os, shutil, json

from app_kit.models import MetaAppGenericContent
from .AppBuilder import AppBuilder



class PreviewExists(Exception):
    pass



class AppPreviewBuilder(AppBuilder):

    # previews are not being validated
    def validate(self, meta_app, app_version=None):
        raise NotImplementedError('AppPreviewBuilder has no validate method')

    # create app preview
    #- delete the preview folder and recreate the preview
    #- symlink/copy all necessary files, but no generic content
    #- the preview is for the online content, not for other contents
    #- create a settings file (-> app uuid and theme)
    #- create a new app preview, not usable for update
    #- raises an Exception if the preview folder already exists
    # copy user content from older version
    def build(self, meta_app, app_version):

        self.logger = self._get_logger(meta_app, 'preview_build')
        self.logger.info('Starting AppPreviewBuilder.build process for app {0} version {1}'.format(meta_app.name,
                                                                                                   app_version))

        try:

            if app_version == None:
                app_version = meta_app.current_version
            
            preview_folder = self._app_root_folder(meta_app, app_version)
            if os.path.isdir(preview_folder):
                raise PreviewExists('Preview for the app_version %s already exists and cannot be created' % app_version)

            os.makedirs(preview_folder)

            self._create_general_folders(meta_app, app_version)

            # the www folder of the preview is now present
            preview_www_folder = self._app_www_folder(meta_app, app_version=app_version)

            # create the preview settings
            preview_settings = self._create_settings(meta_app, app_version)

            # dump the settings as json and .js
            settings_filepath = self._app_settings_js_filepath(meta_app, app_version)
            settings_json_filepath = self._app_settings_json_filepath(meta_app, app_version)
            

            app_settings_string = json.dumps(preview_settings, indent=4, ensure_ascii=False)

            with open(settings_json_filepath, 'w', encoding='utf-8') as settings_json_file:
                settings_json_file.write(app_settings_string)
                
            
            app_settings_js_string = 'var settings = %s' % app_settings_string

            with open(settings_filepath, 'w', encoding='utf-8') as settings_file:
                settings_file.write(app_settings_js_string)


            # create an empty features.js file
            app_features = {}
            
            app_features_file = self._app_features_js_filepath(meta_app, app_version)
            app_features_string = json.dumps(app_features, indent=4, ensure_ascii=False)
            app_features_js_string = 'var app_features = %s' % app_features_string

            with open(app_features_file, 'w', encoding='utf-8') as f:
                f.write(app_features_js_string)
                

            # write the licence_registry file
            # copy old licence_registry.json into new preview folder IF AVAILABLE
            previous_app_version = app_version - 1

            previous_licence_registry_path = self._app_licence_registry_filepath(meta_app, previous_app_version)

            licence_registry_filepath = self._app_licence_registry_filepath(meta_app, app_version)

            if app_version > 1 and os.path.isfile(previous_licence_registry_path):
                shutil.copyfile(previous_licence_registry_path, licence_registry_filepath)

            else:
                # create empty licence registry
                empty_licence_registry = {
                    'licences' : {}
                }
                with open(licence_registry_filepath, 'w', encoding='utf-8') as licence_registry_file:
                    json.dump(empty_licence_registry, licence_registry_file, indent=4, ensure_ascii=False)

            
            # symlink the blueprint files
            self._symlink_blueprint(meta_app, app_version=app_version)


            # symlinks to webapp cordova
            webapp_www_folder = self._builder_blueprint_webapp_www_folder()
            for content in os.listdir(webapp_www_folder):
                source_path = os.path.join(webapp_www_folder, content)
                dest_path = os.path.join(preview_www_folder, content)
                os.symlink(source_path, dest_path)

            # change app theme
            self.set_theme(meta_app, app_version=app_version)
            # theme images
            self._create_theme_user_content_images_folder(meta_app, app_version=app_version)

            # initial translation files
            self.update_translation_files(meta_app)

            # make the preview live, the preview live folder is a subfolder of settings.MEDIA_ROOT
            preview_live_folder = self._preview_app_served_folder(meta_app)
            self.deletecreate_folder(preview_live_folder)

            preview_live_symlink = os.path.join(preview_live_folder, 'www')
            os.symlink(self._app_www_folder(meta_app, app_version), preview_live_symlink)

            # copy user content from older version
            self._copy_previous_theme_user_content(meta_app, app_version)

            self.logger.info('Finished AppPreviewBuilder.build process')


        except Exception as e:
            
            self.logger.error(e, exc_info=True)
            
            # send email!
            self.send_bugreport_email(meta_app, e)


    # the preview settings must use the APIs of the localcosmos server
    # you cannot use the remote server APIs for the preview
    def _create_settings(self, meta_app, app_version):

        # the app has not theme folder yet
        theme_name = meta_app.theme
        theme = self.get_theme(theme_name)
        
        settings = self._get_empty_settings(meta_app, app_version)
        settings["THEME"] = theme.name
        settings["API_URL"] = self._localcosmos_server_api_url(meta_app)
        settings["REMOTEDB_API_URL"] = self._localcosmos_road_remotedb_api_url(meta_app)
        settings["PREVIEW"] = True

        return settings


    ###########################################################################################
    # FOLDERS FOR THE PREVIEW VERSION
    ###########################################################################################

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/preview/
    # eg /opt/localcosmos/apps/{UUID}/1/preview/
    # the AppPreviewBuilder Class only manipulates the contents of this folder (and its subfolders)
    def _app_root_folder(self, meta_app, app_version=None):
        return os.path.join(self._app_version_root_folder(meta_app, app_version), 'preview')
    

    #############################################################################################
    # THEME
    #############################################################################################

    def _create_theme_user_content_images_folder(self, meta_app, app_version=None):

        # user_content_folder: uploads for theme images
        # this lies outside the theme folder, it is not deleted if the user changes a theme
        theme_user_content_images_folder = self._app_theme_user_content_images_folder(meta_app,
                                                                                      app_version=app_version)

        if not os.path.isdir(theme_user_content_images_folder):
            os.makedirs(theme_user_content_images_folder)


    def _copy_previous_theme_user_content(self, meta_app, app_version=None):

        if app_version == None:
            app_version = meta_app.current_version

        # current versions theme user content images folder
        theme_user_content_images_folder = self._app_theme_user_content_images_folder(meta_app,
                                                                                      app_version=app_version)

        # try to get last translation file
        # app_version is an integer starting with 1 for the first version
        if app_version > 1:
            previous_app_version = app_version - 1

            previous_theme_user_content_images_folder = self._app_theme_user_content_images_folder(meta_app,
                                                                                app_version=previous_app_version)
            
            if os.path.isdir(previous_theme_user_content_images_folder):

                for filename in os.listdir(previous_theme_user_content_images_folder):

                    filepath = os.path.join(previous_theme_user_content_images_folder, filename)

                    if os.path.isfile(filepath):
                        dest_filepath = os.path.join(theme_user_content_images_folder, filename)
                        shutil.copyfile(filepath, dest_filepath)


    #############################################################################################
    # LOCALIZATION
    #############################################################################################

    # i18next
    # stored in a separate, version specific /locales/ folder
    # copied into www folder during build
    # GLOSSARY: both glossarized and glossary free language files are created
    
    # create an empty langilfe in i18next json format
    def _get_empty_translation_json(self, language_code):
        return {}

    # read db content into primary language file
    # create language files for secondary languages
    def update_translation_files(self, meta_app):

        primary_language = meta_app.primary_language
        secondary_languages = meta_app.secondary_languages()

        # check if a translation file aready exists
        # first, check the primary language
        primary_language_path = self._app_get_locale_filepath(meta_app, primary_language)
        if not os.path.isfile(primary_language_path):
            self.create_initial_translation_file(meta_app, primary_language)

        # secondary languages
        for language_code in secondary_languages:
            secondary_language_path = self._app_get_locale_filepath(meta_app, language_code)
            if not os.path.isfile(secondary_language_path):
                self.create_initial_translation_file(meta_app, language_code)

        # all langfiles are created now

        # this will later be compared with the stored json
        new_primary_locale_translations = {}

        # read all app contents and add the texts to the langfiles
        # first, get the app texts
        app_texts = meta_app.get_primary_localization()

        for key, locale in app_texts.items():

            if len(locale) > 0:
                new_primary_locale_translations[key] = locale

        # second, get the texts of the app's generic_contents
        generic_content_links = MetaAppGenericContent.objects.filter(meta_app=meta_app)
        for link in generic_content_links:

            generic_content_texts = link.generic_content.get_primary_localization()
            for key, locale in generic_content_texts.items():
                if len(locale) > 0:
                    new_primary_locale_translations[key] = locale


        # update the primary language file
        # the primary language key-value pairs are fully in the database, no comparison needed
        # simply overwrite the existing primary language file
        with open(primary_language_path, 'w', encoding='utf-8') as primary_language_file:
            primary_locale_filecontent = new_primary_locale_translations
            json.dump(primary_locale_filecontent, primary_language_file, indent=4, ensure_ascii=False)

        
        # the secondary languages are updated using the translation tool, when the user actually translates            


    # the initial translation file can be of two types:
    #- an empty translation file, if no translation exists yet
    #- the translation file of the last version, if no translation file exists for the current version
    #- the preview version of the app only supports plain translations files (without glossary)
    def create_initial_translation_file(self, meta_app, language_code, app_version=None):

        if app_version == None:
            app_version = meta_app.current_version

        localization_folder = self._app_locale_folder(meta_app, language_code, app_version=app_version)

        if not os.path.isdir(localization_folder):
            os.makedirs(localization_folder)

        localization_file_path = self._app_get_locale_filepath(meta_app, language_code, app_version=app_version)

        # if the translation file for this version does not exist, try to fetch a previous translation
        # if no previous translation exists, create an empty translation
        if not os.path.isfile(localization_file_path):

            # empty fallback content, if no previous translation file is found
            content = self._get_empty_translation_json(language_code)

            # try to get last translation file
            # app_version is an integer starting with 1 for the first version
            while app_version > 1:
                app_version = app_version - 1
                previous_localization_file_path = self._app_get_locale_filepath(meta_app, language_code,
                                                                                app_version)
                if os.path.isfile(previous_localization_file_path):
                    with open(previous_localization_file_path, 'r', encoding='utf-8') as previous_langfile:
                        content = json.load(previous_langfile)

            with open(localization_file_path, 'w', encoding='utf-8') as langfile:
                json.dump(content, langfile, indent=4, ensure_ascii=False)

    # below 2 methods are used by the TranslateApp View
    # you only can translate the preview app, not a released app
    def get_translation(self, meta_app, language_code, app_version=None):

        localization_file_path = self._app_get_locale_filepath(meta_app, language_code, app_version)
        
        if os.path.isfile(localization_file_path):
            with open(localization_file_path, 'r', encoding='utf-8') as localization_file:
                translation = json.load(localization_file)
        else:
            translation = self._get_empty_translation_json(language_code)

        return translation

    
    def update_translation(self, meta_app, language_code, translation_dict, app_version=None):

        translation = self.get_translation(meta_app, language_code, app_version)

        for key, value in translation_dict.items():
            translation[key] = value

        
        localization_file_path = self._app_get_locale_filepath(meta_app, language_code, app_version)
        with open(localization_file_path, 'w', encoding='utf-8') as langfile:
            json.dump(translation, langfile, indent=4, ensure_ascii=False)

