'''
    =======================================================================================

    GENERAL
    =======================================================================================
    
    There are three types of apps for each version:
    - WEBAPP
    - android APP
    - ios APP

    which both run on the same code and the same dumped content

    APP FOLDERS:

    {settings.APP_KIT_ROOT} - should be in /opt, not in /var/www

    * the app kit folder of a specific app version:
    {settings.APP_KIT_ROOT}/{app.uuid}/version/{app.version}/

    {settings.APP_KIT_ROOT}/{app.uuid}/version/{app.version}/build/
    {settings.APP_KIT_ROOT}/{app.uuid}/version/{app.version}/log/
    {settings.APP_KIT_ROOT}/{app.uuid}/version/{app.version}/preview/
    {settings.APP_KIT_ROOT}/{app.uuid}/version/{app.version}/release/

    on app creation, the preview folder is filled with files and symlinks
    a symlink for this folder is created in settings.LOCALCOSMOS_APPS_ROOT


    FOLDERS OF SERVED APPS (by nginx, preview and published)
    {settings.LOCALCOSMOS_APPS_ROOT}/{meta_app.app.uid}/preview/
    {settings.LOCALCOSMOS_APPS_ROOT}/{meta_app.app.uid}/live/


    ===========================================================================================

    APP BUILDING
    ===========================================================================================

    ALWAYS AND ONLY BUILDS THE CURRENT VERSION

    WORKFLOW:

    A BUILD AN APP
    0. the app passes validation
    1. AppBuilder receives a MetaApp instance (app_kit.models.MetaApp)
    2. the apps folder is created if it is not present
    3. the folder for the version is created if not present
    4. the target folder for build is {settings.APP_KIT_ROOT}/{app.uuid}/version/{app.version}/build/
    5. app content (www-folder, config.xml) are created in the folder build/common/www/
    6. webapp, ios and android versions are built using the common www folder
    7. if the build was successful, a report file is dumped within the apps log folder
    

    B RELEASE - only for successful builds - triggered by user
    0. webapp is copied or symlinked (?) to /var/www/...
    1. the apps are uploaded to the appstore
    2. the version will be locked, no further edits possible
    2. a new version will be started - triggered by user ?
    
'''


from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.db import connection
from django.core import mail

from app_kit.utils import import_module


from localcosmos_appkit_utils.AppTheme import AppTheme

import logging, os, json, sys, shutil, traceback

# getting app specific API
from django_tenants.utils import get_tenant_domain_model
Domain = get_tenant_domain_model()


class AppVersionExistsError(Exception):
    pass



#####################################################################################################
#
# APP BUILDER BASE
# - superclass for AppPreviewBuilder and AppReleaseBuilder
# - supplies folder structures, version management
# - supplies information about which Features are available
# - the database operations like validation and build are performed by the subclasses of this class
#
#####################################################################################################

class AppBuilderBase:

    @property
    def version(self):
        raise NotImplementedError('Buider Version needed')

    # development or released
    @property
    def status(self):
        return 'development'

    # which versions of the JSONBuilder Classes this AppBuilder version uses
    BackboneTaxonomy_builder_version = 1
    ButtonMatrix_builder_version = 1
    GenericForm_builder_version = 1
    NatureGuide_builder_version = 1
    TaxonProfiles_builder_version = 1
    Glossary_builder_version = 1
    Map_builder_version = 1
    FactSheets_builder_version = 1

    # set self._builder_version_root_folder and load the config
    def __init__(self):

        # the path of the current appbuilder version
        self._builder_version_root_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                         'v%s' % self.version)

        self._certificates_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'certificates')

        # load config
        config_file_path = os.path.join(self._builder_version_root_folder, 'config.json')

        if not os.path.isfile(config_file_path):
            raise FileNotFoundError('Config file for AppBuilder version %s.%s not found at %s ' % (
                self.version, self.subversion, config_file_path))

        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        for key, value in config.items():
            setattr(self, key, value)


    '''
    required implementations
    '''
    def validate(self, meta_app, app_version=None):
        raise NotImplementedError('AppBuilder classes do need a validate method')

    def build(self, meta_app, app_version=None):
        raise NotImplementedError('AppBuilder classes do need a build method')


    # delete and recreate a folder
    def deletecreate_folder(self, folder):
        if os.path.isdir(folder):
            for root, dirs, files in os.walk(folder):
                for f in files:
                    os.unlink(os.path.join(root, f))
                for d in dirs:
                    dirpath = os.path.join(root, d)
                    if os.path.islink(dirpath):
                        os.unlink(dirpath)
                    else:
                        shutil.rmtree(dirpath)
        else:
            os.makedirs(folder)


    #############################################################################################
    # LOGGING
    #############################################################################################
    #- used during the build() and validate() process

    def _get_logger(self, meta_app, process_name):
        logger = logging.getLogger(__name__)
        logging_folder = '/var/log/localcosmos/apps/{}/'.format(process_name)

        if not os.path.isdir(logging_folder):
            os.makedirs(logging_folder)

        logfile_path = os.path.join(logging_folder, str(meta_app.uuid))
        hdlr = logging.FileHandler(logfile_path)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        logger.addHandler(hdlr)
        logger.setLevel(logging.INFO)

        return logger
    
    
    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/log/
    # eg /opt/localcosmos/apps/{UUID}/1/log/
    def _log_folder(self, meta_app, app_version=None):
        return os.path.join(self._app_version_root_folder(meta_app, app_version), 'log')

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/log/last_validation_result.json
    # eg /opt/localcosmos/apps/{UUID}/1/log/last_validation_result.json
    def _last_validation_report_logfile_path(self, meta_app, app_version=None):
        return os.path.join(self._log_folder(meta_app, app_version), 'last_validation_result.json')


    def send_bugreport_email(self, meta_app, error):

        subject = '[{0}] {1}'.format(self.__class__.__name__, error.__class__.__name__)

        tenant = meta_app.tenant
        tenant_admin_emails = tenant.get_admin_emails()
        tenant_text = 'Tenant schema: {0}. App uid: {1}. Admins: {2}.'.format(tenant.schema_name, meta_app.app.uid,
                                                    ','.join(tenant_admin_emails))
        
        text_content = '{0} \n\n {1}'.format(tenant_text, traceback.format_exc())

        mail.mail_admins(subject, text_content)


    def send_admin_email(self, title, text_content):
        mail.mail_admins(title, text_content)
        
    ##########################################################################################
    # APIs
    ##########################################################################################
    #- there can be two locations of APIs: hosted on the LC server, or hosted on the clients private server
    #- currently, the api urls do not work with the development server because of the port, e.g :8080
    #- api urls are in the form of localcosmos.org/api/    no ports, no protocol

    # for all apps running on the localcosmos server
    def _localcosmos_server_api_url(self, meta_app):

        # there might be multiple domains - fetch the first primary
        domain = Domain.objects.filter(app=meta_app.app).first()

        if not domain:
            raise ValueError('[AppBuilder] No Domain Found for app %s' % meta_app.name)

        api_url = '%s%s%s' % (settings.APP_KIT_API_PROTOCOL, domain.domain, reverse('api_home'))

        return api_url

    # for all apps running on the localcosmos server, used eg by the preview builder
    def _localcosmos_road_remotedb_api_url(self, meta_app):
        road_remotedb_url = self._localcosmos_server_api_url(meta_app) + 'road-remotedb-api/'
        return road_remotedb_url

    # can be a private localcosmos api hosted on the tenants own server
    def _app_api_url(self, meta_app):

        lc_private = meta_app.get_global_option('localcosmos_private')
        lc_private_api_url = meta_app.get_global_option('localcosmos_private_api_url')

        # lc private server
        if lc_private == True and lc_private_api_url:
            if not lc_private_api_url.endswith('/'):
                lc_private_api_url = '{0}/'.format(lc_private_api_url)
            return lc_private_api_url

        # lc server
        return self._localcosmos_server_api_url(meta_app)
    
    # can be a private localcosmos api hosted on the tenants own server
    def _app_road_remotedb_api_url(self, meta_app):
        road_remotedb_url = self._app_api_url(meta_app) + 'road-remotedb-api/'
        return road_remotedb_url


    ##########################################################################################
    # APP FEATURES
    ##########################################################################################
    #- methods covering the features and possibilities of this specific version
    
    def feature_choices(self):
        choices = []

        for feature in self.addable_features:
            
            feature_module = import_module(feature)
            FeatureModel = feature_module.models.FeatureModel

            content_type = ContentType.objects.get_for_model(FeatureModel)

            choice = {
                'content_type' : content_type,
                'feature_model' : FeatureModel,
            }
            choices.append(choice)

        return choices


    ##########################################################################################
    # CREATE NEW APP VERSION
    # - creates a new app version without any content
    # - you cannot init the same app version more than once
    ##########################################################################################
    
    def init_app_version(self, meta_app, app_version):

        app_version_root = self._app_version_root_folder(meta_app, app_version)

        if os.path.isdir(app_version_root):
            raise AppVersionExistsError('Version %s of the app %s already exists' % (app_version, meta_app))

        os.makedirs(app_version_root)

        # create the logs folder
        logs_folder = self._log_folder(meta_app, app_version)
        os.makedirs(logs_folder)

        # create private themes folder if it is not yet present
        private_themes_folder = self.private_themes_folder()
        if not os.path.isdir(private_themes_folder):
            os.makedirs(private_themes_folder)


    # preview, build and release version need the same folder structure
    def _create_general_folders(self, meta_app, app_version=None):

        # create the www folder
        www_folder = self._app_www_folder(meta_app, app_version)
        if not os.path.isdir(www_folder):
            os.makedirs(www_folder)

        # create the locales folder for AppThemeTexts
        for language_code in meta_app.languages():
            
            locale_folder = self._app_locale_folder(meta_app, language_code, app_version=app_version)
            if not os.path.isdir(locale_folder):
                os.makedirs(locale_folder)
        

    
    ##########################################################################################
    # THEMES
    ##########################################################################################
    # - public themes
    # - private (uploaded) themes
    
    # publicly installed themes, provided by localcosmos.org
    def public_themes_folder(self):
        return os.path.join(self._builder_version_root_folder, 'app', 'themes')

    # a user can create his own theme
    # this is the directory the theme is uploaded to, tenant-specific
    def private_themes_folder(self):
        return os.path.join(settings.APP_KIT_PRIVATE_THEMES_PATH, connection.schema_name)
    
    def available_themes(self):
        # find installed themes
        themes = []

        themes_path = self.public_themes_folder()

        for item in os.listdir(themes_path):

            theme_path = os.path.join(themes_path, item)
            
            if os.path.isdir(theme_path):
                theme = AppTheme(theme_path)
                themes.append(theme)

        private_themes_path = self.private_themes_folder()

        for item in os.listdir(private_themes_path):

            private_theme_path = os.path.join(private_themes_path, item)
            
            if os.path.isdir(private_theme_path):
                theme = AppTheme(private_theme_path)
                themes.append(theme)
        
        return themes
    

    # get an AppTheme instance
    def get_theme(self, theme_name):

        # first, look in the public theme folder
        theme_path = os.path.join(self.public_themes_folder(), theme_name)

        if not os.path.isdir(theme_path):
            theme_path = os.path.join(self.private_themes_folder(), theme_name)
        
        return AppTheme(theme_path)


    # if the user changes the theme, the theme folder in the preview has to be adjusted
    # this symlinks a new theme
    # already uploaded images are kept as they reside in www/user_content
    # in the release builder, the is symlinked, too
    def set_theme(self, meta_app, app_version=None):

        # symlinks to theme - use get_theme of the builder
        theme_name = meta_app.theme
        theme = self.get_theme(theme_name)

        # recreate the folder for the themes
        themes_folder = self._app_themes_folder(meta_app, app_version=app_version)
        self.deletecreate_folder(themes_folder)

        # symlink the theme      
        source_path = os.path.join(theme.disk_path)
        dest_path = self._app_theme_folder(meta_app, app_version=app_version)
        os.symlink(source_path, dest_path)


    ############################################################################################
    # SYMLINK BLUEPRINT
    ############################################################################################

    def _symlink_blueprint(self, meta_app, app_version=None):

        dest_www_folder = self._app_www_folder(meta_app, app_version=app_version)

        builder_blueprint_base_www_folder = self._builder_blueprint_base_www_folder()
        
        for content in os.listdir(builder_blueprint_base_www_folder):
            source_path = os.path.join(builder_blueprint_base_www_folder, content)
            dest_path = os.path.join(dest_www_folder, content)
            os.symlink(source_path, dest_path)


    #############################################################################################
    # LOCALIZATION
    #############################################################################################

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/preview/www/locales
    # eg /opt/localcosmos/apps/{UUID}/1/preview/www/locales
    def _app_locales_folder(self, meta_app, app_version=None):
        return os.path.join(self._app_www_folder(meta_app, app_version), 'locales')

    def _app_locale_folder(self, meta_app, language_code, app_version=None):
        return os.path.join(self._app_locales_folder(meta_app, app_version=app_version), language_code)
    
    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/preview/www/locales/{language_code}.json
    # eg /opt/localcosmos/apps/{UUID}/1/preview/www/locales/{language_code}/plain.json
    def _app_get_locale_filepath(self, meta_app, language_code, app_version=None):

        filename = 'plain.json'
        
        return os.path.join(self._app_locale_folder(meta_app, language_code, app_version=app_version), filename)


    # return the locale file of the primary translation
    def get_primary_locale(self, meta_app, app_version=None):
        return self.get_locale(meta_app, meta_app.primary_language, app_version)
        

    # get the locale file for a specific language
    def get_locale(self, meta_app, language_code, app_version=None):
        locale_path = self._app_get_locale_filepath(meta_app, language_code, app_version=app_version)
        
        locale = None
        if os.path.isfile(locale_path):

            with open(locale_path, 'r', encoding='utf-8') as locale_file:
                locale = json.load(locale_file)

        return locale

    def get_localized(self, meta_app, key, language_code, app_version=None):
        locale = self.get_locale(meta_app, language_code, app_version=app_version)
        return locale[key]


    ##########################################################################################
    # FOLDERS OF THE ACTUAL APP (preview, build or release)
    # - prefixed with _app
    ##########################################################################################
    
    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/
    # eg /opt/localcosmos/apps/{UUID}/1/
    def _app_version_root_folder(self, meta_app, app_version=None):
        if app_version == None:
            app_version = meta_app.current_version
        return os.path.join(settings.APP_KIT_ROOT, str(meta_app.uuid), 'version', str(app_version))

    
    # the root folder of the builder (preview, build or release)
    # subfolder of self._app_version_root_folder
    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/{preview/build/release}/
    # eg /opt/localcosmos/apps/{UUID}/1/preview/
    def _app_root_folder(self, meta_app, app_version=None):
        raise NotImplementedError('AppBuilderBase subclasses require a _root_folder() method')

    def _app_www_folder(self, meta_app, app_version = None):
        return os.path.join(self._app_root_folder(meta_app, app_version), 'www')
    
    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/preview/www/themes
    # eg /opt/localcosmos/apps/{UUID}/1/preview/www/themes/
    def _app_themes_folder(self, meta_app, app_version=None):
        return os.path.join(self._app_www_folder(meta_app, app_version), 'themes')

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/preview/www/themes/{theme_name}
    # eg /opt/localcosmos/apps/{UUID}/1/preview/www/themes/Flat
    def _app_theme_folder(self, meta_app, app_version=None):
        return os.path.join(self._app_themes_folder(meta_app, app_version), meta_app.theme)

    # the folder where the user uploads theme-specific files to, like background image etc
    # if the user switches a theme, the theme folder is deleted and re-symlinked
    # the theme specific uploaded files should not be deleted
    # therefore, the user_content folder is not a subfolder of the theme folder
    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/preview/www/user_content/themes/{theme_name}
    # eg /opt/localcosmos/apps/{UUID}/1/preview/www/user_content/themes/Flat
    def _app_theme_user_content_folder(self, meta_app, app_version=None):
        return os.path.join(self._app_www_folder(meta_app, app_version), 'user_content', 'themes', meta_app.theme)

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/preview/www/user_content/themes/{theme_name}/images
    # eg /opt/localcosmos/apps/{UUID}/1/preview/www/user_content/themes/Flat/images
    def _app_theme_user_content_images_folder(self, meta_app, app_version=None):
        return os.path.join(self._app_theme_user_content_folder(meta_app, app_version), 'images')


    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/preview/www/api/
    def _app_api_folder(self, meta_app, app_version=None):
        return os.path.join(self._app_www_folder(meta_app, app_version), 'api')


    
    ######################################################################################################
    # FOLDERS TO SERVE PUBLISHED AND PREVIEW APPS
    #- this folder is also used for the LCOS installation if auto-update is set to True and the LCOS server fetches the ap from the commercial server
    #- these have to be in sync with nginx config
    #- eg nginx maps http://demo.localcosmos.org/ to {settings.LOCALCOSMOS_APPS_ROOT}/{meta_app.app.uid}/published/www
    
    def _preview_app_served_folder(self, meta_app):
        return os.path.join(settings.LOCALCOSMOS_APPS_ROOT, meta_app.app.uid, 'preview')

    def _published_app_served_folder(self, meta_app):
        return os.path.join(settings.LOCALCOSMOS_APPS_ROOT, meta_app.app.uid, 'published')
    

    def _published_webapp_www_folder(self, meta_app):
        return os.path.join(self._published_app_served_folder(meta_app), 'www')


    # temporary folder for reviewing the webapp
    def _built_app_review_served_folder(self, meta_app):
        return os.path.join(settings.LOCALCOSMOS_APPS_ROOT, meta_app.app.uid, 'review')

    def _built_app_review_www_folder(self, meta_app):
        return os.path.join(self._built_app_review_served_folder(meta_app), 'www')


    # apk folder
    def _apk_folder(self, meta_app):
        return os.path.join(settings.LOCALCOSMOS_APPS_ROOT, meta_app.app.uid, 'apk')

    # ipa folder
    def _ipa_folder(self, meta_app):
        return os.path.join(settings.LOCALCOSMOS_APPS_ROOT, meta_app.app.uid, 'ipa')

    # pwa folder (zip, lcprivate) folder
    def _pwa_folder(self, meta_app):
        return os.path.join(settings.LOCALCOSMOS_APPS_ROOT, meta_app.app.uid, 'pwa')

    # job zipfile folder
    def _build_job_zipfile_served_folder(self, meta_app, app_version):
        return os.path.join(settings.LOCALCOSMOS_WWW_ROOT, 'build_jobs', meta_app.app.uid, str(app_version))

    # served url for build job data
    def _get_build_job_zipfile_url(self, meta_app, app_version, zipfile_name):
        return 'build_jobs/{0}/{1}/{2}'.format(meta_app.app.uid, str(app_version), zipfile_name)
        
        

    ##########################################################################################
    # FILES OF THE ACTUAL APP (preview, build or release)
    # - prefixed with _app
    ##########################################################################################

    def _app_settings_js_filepath(self, meta_app, app_version=None):
        return os.path.join(self._app_www_folder(meta_app, app_version), 'settings.js')
        
    def _app_settings_json_filepath(self, meta_app, app_version=None):
        return os.path.join(self._app_www_folder(meta_app, app_version), 'settings.json')

    def _app_features_js_filepath(self, meta_app, app_version=None):
        return os.path.join(self._app_www_folder(meta_app, app_version), 'features.js')

    def _app_features_json_filepath(self, meta_app, app_version=None):
        return os.path.join(self._app_www_folder(meta_app, app_version), 'features.json')

    def _app_licence_registry_filepath(self, meta_app, app_version=None):
        return os.path.join(self._app_www_folder(meta_app, app_version), 'licence_registry.json')

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/preview/www/api/settings.json
    def _app_api_settings_filepath(self, meta_app, app_version=None):
        return os.path.join(self._app_api_folder(meta_app, app_version), 'settings.json')

    def _app_app_theme_images_js_filepath(self, meta_app, app_version=None):
        return os.path.join(self._app_www_folder(meta_app, app_version), 'theme_images.js')

    def _app_legal_notice_json_filepath(self, meta_app, app_version=None):
        return os.path.join(self._app_www_folder(meta_app, app_version), 'legal_notice.json')


    ##########################################################################################
    # FOLDERS OF THE BUILDER
    # - prefixed with _builder
    # - the sources for symlinking some files into appversions, e.g. cordova.js
    ##########################################################################################
    # Blueprint www / webapp cordova.js folder
    def _builder_blueprint_base_folder(self):
        return os.path.join(self._builder_version_root_folder, 'app', 'base')

    def _builder_blueprint_base_www_folder(self):
        return os.path.join(self._builder_blueprint_base_folder(), 'www')

    def _builder_blueprint_webapp_folder(self):
        return os.path.join(self._builder_version_root_folder, 'app', 'webapp')

    def _builder_blueprint_webapp_www_folder(self):
        return os.path.join(self._builder_blueprint_webapp_folder(), 'www')


    ##########################################################################################
    # GET CORDOVA BUILDER
    ##########################################################################################
    def _get_cordova_builder_class(self):

        builder_module_path = 'localcosmos_cordova_builder.CordovaAppBuilder.CordovaAppBuilder'
        
        CordovaAppBuilderClass = import_module(builder_module_path)
        
        return CordovaAppBuilderClass
        

