'''
    =======================================================================================

    GENERAL
    =======================================================================================
    
    There are three types of apps for each version:
    - browser
    - android APP
    - ios APP

    which both run on the same code and the same dumped content

    APP FOLDERS:

    {settings.APP_KIT_ROOT} - should be in /opt, not in /var/www

    * the app kit folder of a specific app version:
    {settings.APP_KIT_ROOT}/{app.uuid}/version/{app.version}/

    {settings.APP_KIT_ROOT}/{app.uuid}/version/{app.current_version}/{preview|release}/sources/
    {settings.APP_KIT_ROOT}/{app.uuid}/version/{app.current_version}/{preview|release}/sources/www/
    {settings.APP_KIT_ROOT}/{app.uuid}/version/{app.current_version}/{preview|release}/sources/assets/
    {settings.APP_KIT_ROOT}/{app.uuid}/version/{app.current_version}/{preview|release}/packages/
    {settings.APP_KIT_ROOT}/{app.uuid}/version/{app.current_version}/{preview|release}/cordova/


    {settings.APP_KIT_ROOT}/{app.uuid}/version/{app.current_version}/log/

    FOLDERS OF SERVED APPS (by nginx, preview and published)
    {settings.LOCALCOSMOS_APPS_ROOT}/{meta_app.app.uid}/preview/
    {settings.LOCALCOSMOS_APPS_ROOT}/{meta_app.app.uid}/review/
    {settings.LOCALCOSMOS_APPS_ROOT}/{meta_app.app.uid}/live/
    {settings.LOCALCOSMOS_APPS_ROOT}/{meta_app.app.uid}/packages/


    ===========================================================================================

    APP BUILDING
    ===========================================================================================

    ALWAYS AND ONLY BUILDS THE CURRENT VERSION

    WORKFLOW:

    A BUILD AN APP
    0. the app passes validation
    1. AppBuilder receives a MetaApp instance (app_kit.models.MetaApp)
    2. the apps folder is created if it is not present
    3. the folder for the app version is created if not present
    4. the target folder for build is {settings.APP_KIT_ROOT}/{app.uuid}/version/{app.version}/{release|preview}/
    5. app contents (www-folder etc) are created in the folder created by 5.
    6. browser, ios and android versions are built using the common www folder and cordova
    7. if the build was successful, a report file is dumped within the apps log folder
    

    B RELEASE - only for successful builds - triggered by user
    0. browser is symlinked to /var/www/...
    1. the apps are uploaded to the appstore
    2. the version will be locked, no further edits possible
    2. a new version will be started - triggered by user ?
    
'''


from xml.dom import NotFoundErr
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.db import connection
from django.core import mail

from app_kit.models import MetaAppGenericContent
from app_kit.features.frontend.models import Frontend

from localcosmos_cordova_builder import MetaAppDefinition, CordovaAppBuilder

import logging, os, json, shutil, traceback, inspect

# getting app specific API
from django_tenants.utils import get_tenant_domain_model


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

    required_features = [
		'app_kit.features.backbonetaxonomy',
		'app_kit.features.taxon_profiles',
	]

    single_content_features = [
		'app_kit.features.backbonetaxonomy',
		'app_kit.features.taxon_profiles',
		'app_kit.features.glossary',
		'app_kit.features.maps',
	]

    delete_on_app_delete = [
		'app_kit.features.backbonetaxonomy',
        'app_kit.features.frontend',
	]

    def __init__(self, meta_app):
        self.meta_app = meta_app
        self._builder_root_path = self._get_builder_root_path()#os.path.dirname(os.path.abspath(__file__))
        self.logger = None


    @property
    def _builder_identifier(self):
        raise NotImplementedError('AppBuilderBase subclasses require the property builder_identifier')


    @classmethod
    def _get_builder_root_path(cls):
        builder_root_path = os.path.dirname(os.path.abspath(inspect.getfile(cls)))
        return builder_root_path


    def validate(self):
        raise NotImplementedError('AppBuilderBase subclasses require a validate method')

    def build(self):
        raise NotImplementedError('AppBuilderBase subclasses require a build method')


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


    def to_camelcase(self, string):
        string_parts = string.split('_')
            
        for counter, string_part in enumerate(string_parts, 0):
            if counter > 0:
                capitalized_part = string_part.capitalize()
                string_parts[counter] = capitalized_part
        
        camel_case_string = ''.join(string_parts)

        return camel_case_string

    #############################################################################################
    # LOGGING
    #############################################################################################
    #- used during the build() and validate() process

    def _get_logger(self, process_name):

        if self.logger:
            return self.logger

        logger_name = '{0}-{1}'.format(self.__class__.__name__, process_name)

        logger = logging.getLogger(logger_name)
        logging_path = '/var/log/localcosmos/apps/{0}/{1}/'.format(self.__class__.__name__, process_name)

        if not os.path.isdir(logging_path):
            os.makedirs(logging_path)

        logfile_path = os.path.join(logging_path, str(self.meta_app.uuid))
        hdlr = logging.FileHandler(logfile_path)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        logger.addHandler(hdlr)
        logger.setLevel(logging.INFO)

        self.logger = logger

        return self.logger
    
    
    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/log/
    # eg /opt/localcosmos/apps/{UUID}/1/log/
    @property
    def _log_path(self):
        return os.path.join(self._app_version_root_path, 'log')

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/log/last_validation_result.json
    # eg /opt/localcosmos/apps/{UUID}/1/log/last_validation_result.json
    @property
    def _last_validation_report_logfile_path(self):
        return os.path.join(self._log_path, 'last_validation_result.json')


    def send_bugreport_email(self, error):

        subject = '[{0}] {1}'.format(self.__class__.__name__, error.__class__.__name__)

        tenant = self.meta_app.tenant
        tenant_admin_emails = tenant.get_admin_emails()
        tenant_text = 'Tenant schema: {0}. App uid: {1}. Admins: {2}.'.format(tenant.schema_name, self.meta_app.app.uid,
                                                    ','.join(tenant_admin_emails))
        
        text_content = '{0} \n\n {1}'.format(tenant_text, traceback.format_exc())

        mail.mail_admins(subject, text_content)


    def send_admin_email(self, title, text_content):
        mail.mail_admins(title, text_content)


    ###############################################################################################################
    # CORDOVA
    # the browser app is serverd here for reviewing - after building but before release

    def get_cordova_builder(self):

        meta_app_definition = MetaAppDefinition(meta_app=self.meta_app)

        cordova_builder = CordovaAppBuilder(meta_app_definition, self._cordova_build_path, 
            self._app_build_sources_path)

        return cordova_builder

        
    ###############################################################################################################
    # APIs
    ###############################################################################################################
    #- there can be two locations of APIs: hosted on the LC server, or hosted on the clients private server
    #- currently, the api urls do not work with the development server because of the port, e.g :8080
    #- api urls are in the form of localcosmos.org/api/    no ports, no protocol

    # for all apps running on the localcosmos server
    def _localcosmos_server_api_url(self):
        Domain = get_tenant_domain_model()

        # there might be multiple domains - fetch the first primary
        domain = Domain.objects.filter(app=self.meta_app.app).first()

        if not domain:
            raise ValueError('[AppBuilder] No Domain Found for app {0}'.format(self.meta_app.name))

        api_url = '{0}{1}{2}'.format(settings.APP_KIT_API_PROTOCOL, domain.domain, reverse('api_home'))

        return api_url


    # can be a private localcosmos api hosted on the tenants own server
    def _app_api_url(self):

        lc_private = self.meta_app.get_global_option('localcosmos_private')
        lc_private_api_url = self.meta_app.get_global_option('localcosmos_private_api_url')

        # lc private server
        if lc_private == True and lc_private_api_url:
            if not lc_private_api_url.endswith('/'):
                lc_private_api_url = '{0}/'.format(lc_private_api_url)

            return lc_private_api_url

        # lc server
        return self._localcosmos_server_api_url()

    
    ##########################################################################################
    # FRONTENDS
    ##########################################################################################
    @classmethod
    def get_installed_frontends(cls):
        frontends = []
        for public_frontend_name in os.listdir(cls._get_public_frontends_path()):
            frontends.append(public_frontend_name)

        private_frontends_path = cls._get_private_frontends_path()
        if os.path.isdir(private_frontends_path):
            for private_frontend_name in os.listdir(private_frontends_path):
                frontends.append(private_frontend_name)

        return frontends

    # publicly installed frontends, provided by localcosmos.org
    @property
    def public_frontends_path(self):
        return self._get_public_frontends_path()

    # support python versions < 3.8 which do not support using @property and @classmethod together
    @classmethod
    def _get_public_frontends_path(cls):
        return os.path.join(cls._get_builder_root_path(), 'app', 'frontends')

    # a user can create his own frontend
    # this is the directory the frontend is uploaded to, tenant-specific
    @property
    def private_frontends_path(self):
        return self._get_private_frontends_path()

    @classmethod
    def _get_private_frontends_path(cls):
        return os.path.join(settings.APP_KIT_PRIVATE_FRONTENDS_PATH, connection.schema_name)


    def _get_frontend(self):
        frontend_content_type = ContentType.objects.get_for_model(Frontend)
        frontend_link = MetaAppGenericContent.objects.get(content_type=frontend_content_type,
            meta_app=self.meta_app)

        frontend = frontend_link.generic_content

        return frontend

    def get_private_frontend_path(self, frontend_name):
        return os.path.join(self.private_frontends_path, frontend_name)

    @property
    def _frontend_root_path(self):

        frontend = self._get_frontend()

        public_frontend_path = os.path.join(self.public_frontends_path, frontend.frontend_name)

        if os.path.isdir(public_frontend_path):
            return public_frontend_path

        private_frontend_path = os.path.join(self.private_frontends_path, frontend.frontend_name)

        if os.path.isdir(private_frontend_path):
            return private_frontend_path

        raise NotFoundErr('No frontend found for name {0}'.format(frontend.frontend_name))


    @property
    def _frontend_cordova_path(self):
        return os.path.join(self._frontend_root_path, 'cordova')

    @property
    def _frontend_config_xml_path(self):
        return os.path.join(self._frontend_cordova_path, 'config.xml')

    @property
    def _frontend_cordova_res_path(self):
        return os.path.join(self._frontend_cordova_path, 'res')

    @property
    def _frontend_www_path(self):
        return os.path.join(self._frontend_root_path, 'www')

    @property
    def _frontend_locales_folder_path(self):
        return os.path.join(self._frontend_www_path, 'locales')

    @property
    def _frontend_settings_json_path(self):
        return os.path.join(self._frontend_root_path, 'settings.json')


    #############################################################################################
    # LOCALIZATION PATHS
    #############################################################################################

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/preview/www/locales
    # eg /opt/localcosmos/apps/{UUID}/1/preview/www/locales
    @property
    def _app_locales_path(self):
        return os.path.join(self._app_www_path, 'locales')

    def _app_locale_path(self, language_code):
        return os.path.join(self._app_locales_path, language_code)

    def _app_locale_filepath(self, language_code):
        filename = 'plain.json'
        return os.path.join(self._app_locale_path(language_code), filename)

    def _app_glossarized_locale_filepath(self, language_code):
        filename = 'glossarized.json'
        return os.path.join(self._app_locale_path(language_code), filename)
    
    # "complete" locale filepaths container taxon profile texts
    # these are only present because of already existing apps
    def _app_complete_locale_filepath(self, language_code):
        filename = 'plain_complete.json'
        return os.path.join(self._app_locale_path(language_code), filename)

    def _app_complete_glossarized_locale_filepath(self, language_code):
        filename = 'glossarized_complete.json'
        return os.path.join(self._app_locale_path(language_code), filename)


    ###################################################################################################################
    # LOCALIZATION
    # - meta_app.localizations JSON stores translations of texts
    # - primary localization is read by using GenericContent.get_primary_localization()
    # - ContentImage translations have the  key 'localized_content_image_{CONTENT_TYPE_ID}_{OBJECT_ID}_{IMAGE_TYPE}'
    ###################################################################################################################

    def fill_primary_localization(self):

        primary_localization = {
            '_meta' : {}
        }

        # first, get texts of meta_app        
        app_texts = self.meta_app.get_primary_localization()

        for key, locale in app_texts.items():

            if len(locale) > 0:
                primary_localization[key] = locale

        # second, get texts of generic contents
        generic_content_links = self.meta_app.features()
        for link in generic_content_links:

            generic_content = link.generic_content

            generic_content_primary_localization = generic_content.get_primary_localization(meta_app=self.meta_app)

            for key, locale in generic_content_primary_localization.items():

                if key == '_meta':

                    meta_data = locale
                    primary_localization['_meta'].update(meta_data)

                else:
                    if len(locale) > 0:
                        primary_localization[key] = locale            

        if not self.meta_app.localizations:
            self.meta_app.localizations = {}

        self.meta_app.localizations[self.meta_app.primary_language] = primary_localization
        self.meta_app.save()


    def get_localized(self, key, language_code):
        locale = {}

        if self.meta_app.localizations:
            locale = self.meta_app.localizations.get(language_code, {})
            
        localized = locale.get(key, None)
        return localized

    ##########################################################################################
    # PATHS OF THE ACTUAL APP (preview, build or release)
    # - prefixed with _app
    ##########################################################################################

    # the app_root path is necessary when deleting an app
    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/
    # eg /opt/localcosmos/apps/{UUID}/
    @property
    def _app_root_path(self):
        return os.path.join(settings.APP_KIT_ROOT, str(self.meta_app.uuid))

    @property
    def _app_content_images_cache_path(self):
        return os.path.join(self._app_root_path, 'cache/content_images/')
    
    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.current_version}/
    # eg /opt/localcosmos/apps/{UUID}/1/
    @property
    def _app_version_root_path(self):
        return os.path.join(self._app_root_path, 'version', str(self.meta_app.current_version))

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.current_version}/{release|preview}/
    @property
    def _app_builder_path(self):
        return os.path.join(self._app_version_root_path, self._builder_identifier)

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.current_version}/{release|preview}/sources/
    @property
    def _app_build_sources_path(self):
        return os.path.join(self._app_builder_path, 'sources')

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.current_version}/{release|preview}/sources/
    @property
    def _app_build_sources_cordova_assets_path(self):
        return os.path.join(self._app_build_sources_path, 'cordova')

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.current_version}/{release|preview}/sources/www/
    # www content for browser, android, ios
    @property
    def _app_www_path(self):
        return os.path.join(self._app_build_sources_path, 'www')

    # assets are launcher icon etc
    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.current_version}/{release|preview}/sources/assets/
    @property
    def _app_assets_path(self):
        return os.path.join(self._app_build_sources_path, 'assets')

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.current_version}/{release|preview}/packages/
    @property
    def _build_packages_path(self):
        return os.path.join(self._app_builder_path, 'packages')

    @property
    def _build_browser_zip_filepath(self):
        filename = '{0}.zip'.format(self.meta_app.name)
        return os.path.join(self._build_packages_path, filename)

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.current_version}/{release|preview}/cordova/
    @property
    def _cordova_build_path(self):
        return os.path.join(self._app_builder_path, 'cordova')

    # build jobs currently are only used during release builds
    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.current_version}/release/build_jobs
    @property
    def _app_build_jobs_path(self):
        return os.path.join(self._app_builder_path, 'build_jobs')

    # iOS zip
    @property
    def _build_jobs_zipfile_name(self):
        return '{0}-{1}-{2}.zip'.format(self.meta_app.app.uid, self.meta_app.current_version, self.meta_app.build_number)

    @property
    def _build_jobs_zipfile_filepath(self):
        return os.path.join(self._app_build_jobs_path, self._build_jobs_zipfile_name)

    # all LocalCosmos generated content goes into that directory
    # exception: localization, which lies in www/locales/{LANGUAGE_CODE}

    @property
    def _app_relative_localcosmos_content_path(self):
        return 'localcosmos'

    @property
    def _app_localcosmos_content_path(self):
        return os.path.join(self._app_www_path, self._app_relative_localcosmos_content_path)

    # ContentImages
    @property
    def _app_relative_content_images_path(self):
        return os.path.join(self._app_relative_localcosmos_content_path, 'content-images')

    
    def _app_relative_localized_content_images_path(self, language_code):
        return os.path.join(self._app_relative_content_images_path, language_code)


    @property
    def _app_content_images_path(self):
        return os.path.join(self._app_www_path, self._app_relative_content_images_path)

    
    def _app_localized_content_images_path(self, language_code):
        return os.path.join(self._app_www_path, self._app_relative_localized_content_images_path(language_code))

    
    ######################################################################################################
    # FOLDERS TO SERVE PUBLISHED AND PREVIEW APPS
    #- this folder is also used for the LCOS installation if auto-update is set to True and the LCOS server fetches the ap from the commercial server
    #- these have to be in sync with nginx config
    #- eg nginx maps http://demo.localcosmos.org/ to {settings.LOCALCOSMOS_APPS_ROOT}/{meta_app.app.uid}/published/www
    
    # location settings.LOCALCOSMOS_APPS_ROOT is served by nginx
    @property
    def _app_nginx_served_root(self):
        return os.path.join(settings.LOCALCOSMOS_APPS_ROOT, self.meta_app.app.uid)

    # browser preview
    @property
    def _preview_browser_served_path(self):
        return os.path.join(self._app_nginx_served_root, 'preview')

    @property
    def _preview_browser_served_www_path(self):
        return os.path.join(self._preview_browser_served_path, 'www')        
        

    ##########################################################################################
    # FILES OF THE ACTUAL APP (preview, build or release)
    # - prefixed with _app
    ##########################################################################################
    
    @property
    def _app_settings_json_filepath(self):
        return os.path.join(self._app_www_path, 'settings.json')

    @property
    def _app_features_json_filepath(self):
        return os.path.join(self._app_localcosmos_content_path, 'features.json')

    @property
    def _app_licence_registry_filepath(self):
        return os.path.join(self._app_localcosmos_content_path, 'licence_registry.json')

    def _app_legal_notice_json_filepath(self, meta_app, app_version=None):
        return os.path.join(self._app_www_folder(meta_app, app_version), 'legal_notice.json')


    ##########################################################################################
    # SETTINGS
    # - will be stored at /www/settings and can be extended by the frontend
    # - localcosmos_settings are provided by the AppBuilder
    # - frontend_settings are provided by the creator of the frontend
    # - app_settings are a merge of localcosmos_settings and frontend_settings
    ##########################################################################################
    def _get_localcosmos_settings(self, preview=False):

        if preview == True:
            api_url = self._localcosmos_server_api_url()
        else:
            api_url = self._app_api_url()

        root_url = api_url[:api_url.rfind("api/")]
        media_url = '{0}media/'.format(root_url)

        settings = {
            "NAME" : self.meta_app.name,
            "PACKAGE_NAME" : self.meta_app.package_name,
            "LANGUAGES" : [language_code for language_code in self.meta_app.languages()], # the languages supported by this app
            "PRIMARY_LANGUAGE" : self.meta_app.primary_language, # primary language is the fallback language
            "APP_UID" : self.meta_app.app.uid,
            "APP_UUID" : str(self.meta_app.uuid),
            "APP_VERSION" : self.meta_app.current_version,
            "BUILD_NUMBER" : self.meta_app.build_number,
            "API_URL" : api_url,
            "MEDIA_URL": media_url,
            "SERVER_URL" : root_url, # the server URL without the api part
            "PREVIEW" : preview, # True is only needed for previewing template_content
        }

        settings["OPTIONS"] = {
            "allowAnonymousObservations" : False,
            "doNotBuildLargeImages" : False,
        }

        if self.meta_app.global_options:
            
            for key, value in self.meta_app.global_options.items():
                camel_case_key = self.to_camelcase(key)
                settings["OPTIONS"][camel_case_key] = value
        
        return settings


    def _get_frontend_settings(self):

        with open(self._frontend_settings_json_path, 'r') as frontend_settings_file:
            frontend_settings = json.loads(frontend_settings_file.read())

        return frontend_settings


    def _get_app_settings(self, preview=True):
        
        app_settings = {}

        localcosmos_settings = self._get_localcosmos_settings(preview=preview)
        frontend_settings = self._get_frontend_settings()

        for key, value in localcosmos_settings.items():
            app_settings[key] = value

        for key, value in frontend_settings.items():
            app_settings[key] = value
        
        return app_settings


    #############################################################################################
    # COMMON BUILD STEPS
    #############################################################################################

    def _recreate_builder_folder(self):

        if os.path.isdir(self._app_builder_path):
            shutil.rmtree(self._app_builder_path)

        os.makedirs(self._app_builder_path)


    # building the frontend has to be possible on both AppPreviewBuilder (for TemplateContent preview) and AppReleaseBuilder
    def _build_Frontend(self):

        # copy the frontends www folder to /preview
        shutil.copytree(self._frontend_www_path, self._app_www_path, dirs_exist_ok=True)

        if not os.path.isdir(self._app_build_sources_cordova_assets_path):
            os.makedirs(self._app_build_sources_cordova_assets_path)

        if os.path.isfile(self._frontend_config_xml_path):
            target_config_xml_path = os.path.join(self._app_build_sources_cordova_assets_path, 'config.xml')
            shutil.copyfile(self._frontend_config_xml_path, target_config_xml_path)

        if os.path.isdir(self._frontend_cordova_res_path):
            target_cordova_res_path =  os.path.join(self._app_build_sources_cordova_assets_path, 'res')    
            shutil.copytree(self._frontend_cordova_res_path, target_cordova_res_path)


    def _create_localcosmos_content_folder(self):
        os.makedirs(self._app_localcosmos_content_path)


#####################################################################################################
# AppBuilder
# - can create and delete app versions
# - cannot build
# - AppPreviewBuilder and AppReleaseBuilder can not delete or create the _app_root_path
#####################################################################################################
class AppBuilder(AppBuilderBase):
    
    #################################################################################################
    # CREATE NEW APP VERSION
    # - creates a new app version
    # - you can only create meta_app.current_version
    # - you can only create an app version once
    # - only creates empty folders for this version
    # - copying frontend etc is done using AppPreviewBuilder.build() or AppReleaseBuilder.build()
    #################################################################################################
    
    def create_app_version(self):

        if os.path.isdir(self._app_version_root_path):
            raise AppVersionExistsError('Version {0} of the app {1} already exists'.format(
                self.meta_app.current_version, self.meta_app))

        # create the version root
        os.makedirs(self._app_version_root_path)

        # create the logs folder
        os.makedirs(self._log_path)


    def delete_app_version(self, app_version):
        if app_version == self.meta_app.current_version:
            raise NotImplementedError('You can only delete past app versions using delete_app_version.')

        app_version_path = os.path.join(self._app_root_path, 'version', str(app_version))
        if os.path.isdir(app_version_path):
            shutil.rmtree(app_version_path)


    def delete_app(self):
        if os.path.isdir(self._app_root_path):
            shutil.rmtree(self._app_root_path)