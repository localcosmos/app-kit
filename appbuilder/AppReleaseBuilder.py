###################################################################################################################
#
# APP RELEASE
# - manages the build folder, eg {settings.APP_KIT_ROOT}/{app.uuid}/version/{app.version}/build/
# - the build folder is referenced as AppReleaseBuilder._app_root_folder()
# - offers validate_* and build_* methods for generic contents
# - offers the feature to release a version
#
#
###################################################################################################################

from . import AppBuilderBase

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from django.template.defaultfilters import slugify

### CHECK LC PRIVATE API
import ssl
from urllib import request
from urllib.error import HTTPError, URLError

### FEATURES
from app_kit.features.nature_guides.models import NatureGuide, NatureGuidesTaxonTree, MatrixFilter
from app_kit.features.generic_forms.models import (GenericForm, GenericFieldToGenericForm, FIELD_ROLES,
                                                       GenericValues, DJANGO_FIELD_CLASSES)

from app_kit.features.glossary.models import Glossary
from app_kit.features.taxon_profiles.models import TaxonProfile
from app_kit.features.frontend.models import Frontend

from app_kit.features.fact_sheets.models import FactSheet


# TAXONOMY
from taxonomy.lazy import LazyTaxon

# GBIFLib
from app_kit.appbuilder.GBIFlib import GBIFlib

from app_kit.models import (MetaAppGenericContent, LOCALIZED_CONTENT_IMAGE_TRANSLATION_PREFIX, ContentImage,
                            LocalizedContentImage)
from app_kit.utils import import_module
from app_kit.generic_content_validation import ValidationError, ValidationWarning

from localcosmos_cordova_builder import MetaAppDefinition, CordovaAppBuilder

import os, json, base64, time, shutil, hashlib, zipfile

from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

# jobs
from app_kit.app_kit_api.models import AppKitJobs

import csv, uuid

NO_IMAGE_URL = None #'img/noimage.svg'

# output filenames for assets required to build cordova apps
ASSET_FILENAMES = {
    'android' : {
        'launcherIcon' : 'launcher_icon.svg',
        'launcherBackground' : 'launcher_background.svg',
        'splashscreen' : 'splashscreen.svg',
    },
    'ios' : {
        'launcherIcon' : 'launcher_icon.svg',
        'launcherBackground' : 'launcher_background.svg',
        'splashscreen' : 'splashscreen.svg',
    }
}

class AppBuildFailed(Exception):
    pass


class AppIsLockedError(Exception):
    pass


class AppReleaseBuilder(AppBuilderBase):

    use_gbif = False

    no_image_url = NO_IMAGE_URL

    android_keystore_name = 'localcosmos_android.keystore'

    nature_guides_vernacular_names = {}

    def get_empty_result(self):

        result = {
            'app_version' :  self.meta_app.current_version,
            'started_at' : int(time.time()),
            'warnings' : [], # a list of ValidationWarning instances
            'errors' : [], # a list of ValidationError instances
        }

        return result


    ###############################################################################################################
    # Cordova
    # the webapp is serverd here for reviewing - after building but before release

    def get_cordova_builder(self):

        meta_app_definition = MetaAppDefinition(meta_app=self.meta_app)

        cordova_builder = CordovaAppBuilder(meta_app_definition, self._cordova_build_path, self._app_packages_path,
                                            self._app_build_sources_path)

        return cordova_builder


    ###############################################################################################################
    # FOLDERS OF THE BUILT (RELEASE CANDIDATE) APP
    # - webapp
    # - www folder for android and ios app

    @property
    def _app_build_sources_path(self):
        return os.path.join(self._app_release_path, 'sources')

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.current_version}/release/common/www/
    # www content for browser, android, ios
    @property
    def _app_www_path(self):
        return os.path.join(self._app_build_sources_path, 'common', 'www')

    # path for output packages like .aab .ipa .zip
    @property
    def _app_packages_path(self):
        return os.path.join(self._app_release_path, 'packages')

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.current_version}/release/webapp/
    @property
    def _build_webapp_path(self):
        return os.path.join(self._app_release_path, 'webapp')

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.current_version}/build/webapp/www/
    @property
    def _build_webapp_www_path(self):
        return os.path.join(self._build_webapp_path, 'www')

    @property
    def _cordova_build_path(self):
        return os.path.join(self._app_release_path, 'cordova')

    # platform specific assets that have to be passed to CordovaAppbuilder
    # android
    @property
    def _build_android_root(self):
        return os.path.join(self._app_build_sources_path, 'android')

    # assets are launcher icon etc
    @property
    def _build_android_assets_path(self):
        return os.path.join(self._build_android_root, 'assets')

    @property
    def _build_android_www_path(self):
        return os.path.join(self._build_android_root, 'www')

    # ios
    @property
    def _build_ios_root(self):
        return os.path.join(self._app_build_sources_path, 'ios')

    # assrts are launcher icon etc
    @property
    def _build_ios_assets_path(self):
        return os.path.join(self._build_ios_root, 'assets')

    @property
    def _build_ios_www_path(self):
        return os.path.join(self._build_ios_root, 'www')

    # assets supplied by frontend
    @property
    def _frontend_ios_www_path(self):
        return os.path.join(self._frontend_root_path, 'ios', 'www')

    @property
    def _frontend_android_www_path(self):
        return os.path.join(self._frontend_root_path, 'android', 'www')

    # PACKAGES
    # webapp zip
    @property
    def _build_webapp_zip_filepath(self):
        filename = '{0}.zip'.format(self.meta_app.name)
        return os.path.join(self._app_release_path, 'packages', filename)

    ###############################################################################################################
    # FOLDERS OF BUILT CONTENT
    # - both absolute an relative paths are needed
    # - relative paths are referenced by the frontend


    ### folders for generic contents, absolute and relative (to www) ###
    def _app_relative_generic_content_path(self, generic_content, **kwargs):
        generic_content_type = kwargs.get('generic_content_type', generic_content.__class__.__name__)
        return os.path.join(self._app_relative_localcosmos_content_path, 'features/', generic_content_type,
                            str(generic_content.uuid))


    def _app_absolute_generic_content_path(self, generic_content, **kwargs):
        return os.path.join(self._app_www_path,
            self._app_relative_generic_content_path(generic_content, **kwargs))


    # folder for content images, relative to www
    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/build/www/user_content/content_images/
    # eg /opt/localcosmos/apps/{UUID}/1/build/www/user_content/content_images
    @property
    def _app_relative_content_images_path(self):
        return os.path.join(self._app_relative_localcosmos_content_path, 'user_content/', 'content_images')


    @property
    def _app_absolute_content_images_path(self):
        return os.path.join(self._app_www_path, self._app_relative_content_images_path)

    # frontend images require the correct filename
    @property
    def _app_relative_frontend_images_path(self):
        return os.path.join(self._app_relative_localcosmos_content_path, 'user_content/', 'frontend', 'images')


    @property
    def _app_absolute_frontend_images_path(self):
        return os.path.join(self._app_www_path, self._app_relative_frontend_images_path)


    ###############################################################################################################
    # OUTPUT FOR REVIEWING
    # the webapp is serverd here for reviewing - after building but before release

    def aab_review_url(self, request):
        cordova_builder = self.get_cordova_builder()
        url = '{0}://{1}/packages/review/android/{2}'.format(request.scheme, self.meta_app.domain, cordova_builder._aab_filename)
        return url

    # does not return scheme and host
    def aab_published_url(self):
        cordova_builder = self.get_cordova_builder()
        url = '/packages/published/android/{0}'.format(cordova_builder._aab_filename)
        return url

    # relies on correct nginx conf
    # do not use request.get_host()
    def webapp_review_url(self, request):

        from django_tenants.utils import get_tenant_domain_model
        Domain = get_tenant_domain_model()
        
        domain = Domain.objects.filter(tenant__schema_name='public').first()
        url = '{0}://{1}.review.{2}/'.format(request.scheme, self.meta_app.app.uid, domain.domain)

        return url

    # the zipped webapp
    def webapp_zip_review_url(self, request):
        url = '{0}://{1}/packages/review/webapp/{2}'.format(request.scheme, self.meta_app.domain, self._webapp_zipfile_name)
        return url

    def webapp_zip_published_url(self):
        url = '/packages/published/webapp/{0}'.format(self._webapp_zipfile_name)
        return url

    # ios ipa files
    def ipa_review_url(self, request):
        # search for a completed AppKitJob
        job = AppKitJobs.objects.filter(meta_app_uuid=self.meta_app.uuid, app_version=self.meta_app.current_version,
                                        platform='ios', job_type='build').first()

        if job and job.job_result and job.job_result.get('success') == True:
            meta_app_definition = MetaAppDefinition(self.meta_app)
            url = '{0}://{1}/packages/review/ios/{2}'.format(request.scheme, self.meta_app.domain,
                                                    CordovaAppBuilder.get_ipa_filename(meta_app_definition))
            return url

        return None


    # ios ipa files
    def ipa_published_url(self):
        # search for a completed AppKitJob
        job = AppKitJobs.objects.filter(meta_app_uuid=self.meta_app.uuid, app_version=self.meta_app.current_version,
                                        platform='ios', job_type='build').first()

        if job and job.job_result and job.job_result.get('success') == True:
            meta_app_definition = MetaAppDefinition(self.meta_app)
            url = '/packages/published/ios/{0}'.format(CordovaAppBuilder.get_ipa_filename(meta_app_definition))
            return url

        return None

    ###############################################################################################################
    # FILES OF THE BUILT (RELEASE CANDIDATE) APP, that are not present in the preview version
    #- eg glossarized translations
    #- prefixed with _build

    def _app_glossarized_locale_filepath(self, language_code):

        filename = 'glossarized.json'

        return os.path.join(self._app_locale_path(language_code), filename)


    # absolute glossary paths
    def _app_localized_glossaries_path(self, glossary, language_code):

        glossary_path = self._app_absolute_generic_content_path(glossary)

        return os.path.join(glossary_path, language_code)


    def _app_localized_glossary_filepath(self, glossary, language_code):
        localized_glossaries_path = self._app_localized_glossaries_path(glossary, language_code)

        filename = 'glossary.json'

        return os.path.join(localized_glossaries_path, filename)


    def _app_localized_glossary_csv_filepath(self, glossary, language_code):
        localized_glossaries_path = self._app_localized_glossaries_path(glossary, language_code)

        filename = 'glossary.csv'

        return os.path.join(localized_glossaries_path, filename)


    def _app_used_terms_glossary_filepath(self, glossary, language_code):

        localized_glossaries_path = self._app_localized_glossaries_path(glossary, language_code)

        filename = 'used_terms_glossary.json'
        
        return os.path.join(localized_glossaries_path, filename)


    def _app_used_terms_glossary_csv_filepath(self, glossary, language_code):

        localized_glossaries_path = self._app_localized_glossaries_path(glossary, language_code)

        filename = 'used_terms_glossary.csv'
        
        return os.path.join(localized_glossaries_path, filename)


    # relative glossary paths
    def _app_relative_localized_glossaries_path(self, glossary, language_code):
        relative_glossary_path = self._app_relative_generic_content_path(glossary)

        return os.path.join(relative_glossary_path, language_code)


    def _app_relative_localized_glossary_filepath(self, glossary, language_code):
        localized_glossaries_relative_path = self._app_relative_localized_glossaries_path(glossary, language_code)

        filename = 'glossary.json'

        return os.path.join(localized_glossaries_relative_path, filename)


    def _app_relative_localized_glossary_csv_filepath(self, glossary, language_code):
        
        localized_glossaries_relative_path = self._app_relative_localized_glossaries_path(glossary, language_code)

        filename = 'glossary.csv'

        return os.path.join(localized_glossaries_relative_path, filename)


    def _app_relative_used_terms_glossary_filepath(self, glossary, language_code):

        localized_glossaries_relative_path = self._app_relative_localized_glossaries_path(glossary, language_code)

        filename = 'used_terms_glossary.json'
        
        return os.path.join(localized_glossaries_relative_path, filename)


    def _app_relative_used_terms_glossary_csv_filepath(self, glossary, language_code):

        localized_glossaries_relative_path = self._app_relative_localized_glossaries_path(glossary, language_code)

        filename = 'used_terms_glossary.csv'
        
        return os.path.join(localized_glossaries_relative_path, filename)



    ###############################################################################################################
    # VALIDATION
    # - async validation, storing result in a json column and in a log file
    #
    # errors/warnings contains error/warning collections for a generic content
    #
    # {'object' : <the object with the error>, 'error_messages':[<list of strings>]}
    # warnings contains:
    # {'object' : <the object with the warning>, 'warning_messages':[<list of strings>]}
    ###############################################################################################################
    def validate(self):

        self.logger = self._get_logger('validate')
        self.logger.info('Starting validation process')

        finished_msg = 'Finished validation process.'

        try:
        
            if self.meta_app.validation_status != 'in_progress':

                self.meta_app.validation_status = 'in_progress'
                
                # lock the meta_app, it will be unlicked if the validation failed
                self.meta_app.is_locked = True
                
                self.meta_app.save()

                result = self.get_empty_result()

                # validate the meta_app itself
                app_result = self.validate_app()
                result['warnings'] += app_result['warnings']
                result['errors'] += app_result['errors']

                # validate translations
                translations_result = self.validate_translations()
                result['warnings'] += translations_result['warnings']
                result['errors'] += translations_result['errors']

                # lock generic contents
                self.meta_app.lock_generic_contents()

                # iterate over all content and validate it
                feature_links = MetaAppGenericContent.objects.filter(meta_app=self.meta_app)

                for feature_link in feature_links:

                    generic_content = feature_link.generic_content

                    validation_method_name = 'validate_{0}'.format(generic_content.__class__.__name__)
                    if not hasattr(self, validation_method_name):
                        raise NotImplementedError('AppBuilder is missing the validation method {0}.'.format(validation_method_name))

                    ValidationMethod = getattr(self, validation_method_name)
                    feature_result = ValidationMethod(generic_content)

                    result['errors'] += feature_result['errors']
                    result['warnings'] += feature_result['warnings']

                    # validate options
                    options_result = self.validate_options(generic_content)
                    result['warnings'] += options_result['warnings']
                    result['errors'] += options_result['errors']


                # store last validation result in db
                validation_result = 'valid'
                
                if result['errors']:
                    validation_result = 'errors'
                elif result['warnings']:
                    validation_result = 'warnings'

                validation_result_json = {
                    'app_version' : self.meta_app.current_version,
                    'started_at' : result['started_at'],
                    'errors' : [error.dump() for error in result['errors']],
                    'warnings' : [warning.dump() for warning in result['warnings']],
                    'finished_at' : int(time.time()),
                }

                self.meta_app.validation_status = validation_result
                self.meta_app.last_validation_report = validation_result_json

                #if validation_result == 'errors':
                self.meta_app.is_locked = False
                self.meta_app.unlock_generic_contents()

                self.meta_app.save()

                # dump the logfile to the apps version folder
                if not os.path.isdir(self._log_path):
                    os.makedirs(self._log_path)
                    
                logfile_path = self._last_validation_report_logfile_path
                with open(logfile_path, 'w', encoding='utf-8') as logfile:
                    json.dump(validation_result_json, logfile, indent=4, ensure_ascii=False)

                
                self.logger.info(finished_msg)

                return result

        except Exception as e:

            self.logger.error(e, exc_info=True)

            try:
                self.send_bugreport_email(e)
                
            except Exception as emailException:
                pass

        self.logger.info(finished_msg)

        return None
    

    ######################################################################################################
    #    - validate if the app is not empty
    #    - validate if LC private if the user runs LCPrivate
    def validate_app(self):
        result = {
            'errors' : [],
            'warnings' :[],
        }

        # the app only makes sense if there is at least one natureguide or one generic form and at least one
        # taxon in the backbone taxonomy

        # check if there is one natureguide or one generic_form
        generic_form_ctype = ContentType.objects.get_for_model(GenericForm)
        nature_guide_ctype = ContentType.objects.get_for_model(NatureGuide)

        exists = MetaAppGenericContent.objects.filter(meta_app=self.meta_app, content_type__in=[generic_form_ctype,
                                                                             nature_guide_ctype]).exists()

        if not exists:
            error_message = _('Your app needs at least one nature nuide OR one observation form.')
            error = ValidationError(self.meta_app, self.meta_app, [error_message])
            result['errors'].append(error)
        
        options_result = self.validate_options(self.meta_app)
        result['warnings'] += options_result['warnings']
        result['errors'] += options_result['errors']

        # validate LCPrivate if set
        lc_private = self.meta_app.get_global_option('localcosmos_private')

        if lc_private == True:

            lc_private_api_url = self.meta_app.get_global_option('localcosmos_private_api_url')

            if lc_private_api_url:

                # ignore sslcert errors. this should be disabled at some date in the future
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

                api_error_message = None
                
                try:
                    response = request.urlopen(lc_private_api_url, context=ctx)
                    json_response = json.loads(response.read())
                    
                except HTTPError as e:
                    api_error_message = _('Local Cosmos Private API HTTP Error: {0}.'.format(e.code))

                except URLError as e:
                    api_error_message = _('Local Cosmos Private API URL Error: {0}.'.format(e.reason))
                    
                except:
                    error_message = _('Error validating your Local Cosmos Private API.')


                if api_error_message != None:
                    error = ValidationError(self.meta_app, self.meta_app, [api_error_message])
                    result['errors'].append(error)

                    
            else:
                error_message = _('You have to provide an API URL if you run Local Cosmos Private.')
                error = ValidationError(self.meta_app, self.meta_app, [error_message])
                result['errors'].append(error)
                

        return result


    def validate_Frontend(self, frontend):

        result = {
            'errors' : [],
            'warnings' :[],
        }
        
        texts = frontend.texts()

        text_types = texts.values_list('identifier', flat=True)

        # legal_notice is not legalNotice because it does not come from the frontends settings.json
        if 'legal_notice' not in text_types:
            error_message = _('Your app requires a legal notice.')
            error = ValidationError(self.meta_app, frontend, [error_message])
            result['errors'].append(error)

        # check all required images and texts - defined by the frontend settings
        frontend_settings = self._get_frontend_settings()

        for image_type, image_definition in frontend_settings['userContent']['images'].items():
            
            image_is_required = image_definition.get('required', False)

            if image_is_required:
                
                # image is a ContentImage of Frontend
                namespaced_image_type = frontend.get_namespaced_image_type(image_type)
                image = frontend.image(namespaced_image_type)

                if not image:
                    image_type_verbose = ' '.join(image_type.split('_')).capitalize()
                    error_message = _('Your frontend is missing the image "{0}"'.format(image_type_verbose))
                    error = ValidationError(self.meta_app, frontend, [error_message])
                    result['errors'].append(error)


        for text_type, text_definition in frontend_settings['userContent']['texts'].items():
            
            text_is_required = text_definition.get('required', False)

            if text_is_required:
                
                text = texts.filter(identifier=text_type).first()

                if not text or len(text.text) == 0:

                    text_type_verbose = ' '.join(text_type.split('_')).capitalize()
                    
                    error_message = _('Your frontend is missing the text "{0}"'.format(text_type_verbose))
                    error = ValidationError(self.meta_app, frontend, [error_message])
                    result['errors'].append(error)


        return result
    

    ###############################################################################################################
    # TRANSLATIONS
    # - text translations are in meta_app.localization
    # - image translations are using ContentImage.get_image_locale_key
    def validate_translations(self):

        result = {
            'errors' : [],
            'warnings' : [],
        }

        self.fill_primary_localization()

        primary_localization = self.meta_app.localizations[self.meta_app.primary_language]

        for language_code in self.meta_app.secondary_languages():

            localization = self.meta_app.localizations.get(language_code, {})

            error_message = _('The translation for the language {0} is incomplete'.format(language_code))

            for key, text in primary_localization.items():

                if key == '_meta':
                    continue

                if key.startswith(LOCALIZED_CONTENT_IMAGE_TRANSLATION_PREFIX):

                    image_definition = text
                    content_image_id = image_definition['content_image_id']
                    content_image = ContentImage.objects.filter(pk=content_image_id).first()

                    if content_image:
                        localization_exists = LocalizedContentImage.objects.filter(content_image=content_image,
                                                language_code=language_code).exists()

                        if not localization_exists:
                            error = ValidationError(self.meta_app, self.meta_app, [error_message])
                            result['errors'].append(error)
                            break

                    else:
                        msg = 'Content image not found. pk: {0}'.format(content_image_id)
                        self.logger.error(msg)


                else:
                    if key not in localization or len(text) == 0:

                        error = ValidationError(self.meta_app, self.meta_app, [error_message])
                        
                        result['errors'].append(error)
                        break
                    
        
        return result
        

    # the default validation is: check all instance_fields of GenericContentOptionsForm
    # options can be app specific (MetaAppGenericContent.options) or global (self.global_options)
    def validate_options(self, generic_content):
        
        result = {
            'errors' : [],
            'warnings' : [],
        }

        # get the form
        if generic_content._meta.object_name == 'MetaApp':
            options_form_module_path = '{0}.forms.{1}OptionsForm'.format(generic_content._meta.app_label,
                                                                   generic_content._meta.object_name)
        else:
            options_form_module_path = 'app_kit.features.{0}.forms.{1}OptionsForm'.format(
                generic_content._meta.app_label, generic_content._meta.object_name)

        try:
            OptionsForm = import_module(options_form_module_path)
        except:
            print('No options form found at {0}'.format(options_form_module_path))
            OptionsForm = None

        if OptionsForm:
            
            if hasattr(OptionsForm, 'instance_fields'):

                for field_name in OptionsForm.instance_fields:
                    # check where the option is stored
                    if field_name in OptionsForm.global_options_fields:
                        options = generic_content.global_options

                    else:
                        link = self.meta_app.get_generic_content_link(generic_content)
                        options = link.options

                    if options:

                        options_entry = options.get(field_name, None)

                        if options_entry:
                            # see GenericContent.make_option_from_instance
                            if options_entry['app_label'] == 'app_kit':
                                model_path = '{0}.models.{1}'.format(options_entry['app_label'], options_entry['model']) 
                            else:
                                model_path = 'app_kit.features.{0}.models.{1}'.format(options_entry['app_label'],
                                                                                        options_entry['model']) 
                            Model = import_module(model_path)

                            # check if the instance exists
                            option_instance = Model.objects.filter(pk=options_entry['id']).first()

                            if not option_instance:
                                message = _('The object referenced in the option %(option_name)s does not exist.') % {'option_name' : field_name}
                                error = ValidationError(generic_content, generic_content, [message])
                                result['errors'].append(error)
                                continue

                            else:

                                if option_instance.__class__.__name__ in ['IdentificationKey', 'GenericForm', 'ButtonMatrix', 'BackboneTaxonomy', 'NatureGuide', 'TaxonProfiles']:
                                    # check if the instance is part of this app - for the generic contents
                                    link = self.meta_app.get_generic_content_link(option_instance)

                                    if not link:
                                        message = _('The object %(object_name)s is referenced in the option %(option_name)s but is not linked to this meta_app.') % {'object_name' : option_instance, 'option_name' : field_name}
                                        error = ValidationError(generic_content, generic_content, [message])
                                        result['errors'].append(error)
                                    
        
        return result


    # validation of features
    def validate_BackboneTaxonomy(self, backbonetaxonomy):
        '''
        ERRORS:
        - The app needs at least one taxon. Otherwise, e.g. the observation form can not work
        '''
        
        result = {
            'warnings' : [],
            'errors' : [],
        }

        # check if there is at least one taxon
        taxon_count = self.meta_app.taxon_count()
        if not taxon_count:
            message = _('This app has no taxa.')
            error = ValidationError(self.meta_app, backbonetaxonomy, [message])
            result['errors'].append(error)
        
        return result


    def validate_NatureGuide(self, nature_guide):
        '''
            Things that need checking:
            ERRORS:
            - childless nodes
            - filters: MatrixFilter without a selectable space
            - no result action
            WARNINGS:
            - missing images
            - [MISSING, ADVANCED] check how filter affects the node entries

            how to treat missing description texts?
        '''


        result = {
            'warnings' : [],
            'errors' : [],
        }

        result_action = nature_guide.get_option(self.meta_app, 'result_action')
        if not result_action:
            error_message = _('The nature guide %(name)s has no setting for what happens if the identification has finished.') % {'name':nature_guide.name}                      
            error = ValidationError(nature_guide, nature_guide, [error_message])
            result['errors'].append(error)
            

        nodes = NatureGuidesTaxonTree.objects.filter(nature_guide=nature_guide,
                                                     meta_node__node_type__in=['node', 'root'])
        
        for parent in nodes:

            is_active = True

            if parent.additional_data:
                is_active = parent.additional_data.get('is_active', True)

            if is_active == False:
                continue

            # check for image, except for the start node
            if not parent.meta_node.node_type == 'root':
                image = parent.meta_node.image()
                if not image:
                    warning_message = _('Image is missing.')
                    warning = ValidationWarning(nature_guide, parent, [warning_message])
                    result['warnings'].append(warning)
            
            
            children = parent.children
            
            if not children:

                if parent.meta_node.node_type == 'root':
                    error_message = _('The nature guide is empty.')

                else:
                    error_message = _('The group %(name)s is empty.') % {'name':parent}
                                      
                error = ValidationError(nature_guide, parent, [error_message])
                result['errors'].append(error)


            # iterate over all filters
            matrix_filters = MatrixFilter.objects.filter(meta_node=parent.meta_node)

            for matrix_filter in matrix_filters:

                # check if the matrix_filter does have a space assigned
                space = matrix_filter.get_space()

                if space:
                    # future: check if the space makes sense
                    pass
                else:
                    error_message = _('This filter is empty.')
                    error = ValidationError(nature_guide, matrix_filter, [error_message])
                    result['errors'].append(error)
                    

        ng_results = NatureGuidesTaxonTree.objects.filter(nature_guide=nature_guide,
                                                          meta_node__node_type='result')
        
        for ng_result in ng_results:

            is_active = True

            if ng_result.additional_data:
                is_active = ng_result.additional_data.get('is_active', True)

            if is_active == False:
                continue
            
            image = ng_result.meta_node.image()
            if not image:
                warning_message = _('Image is missing.')
                warning = ValidationWarning(nature_guide, ng_result, [warning_message])
                result['warnings'].append(warning)
        
        return result
    

    def validate_TaxonProfiles(self, taxon_profiles):

        result = {
            'warnings' : [],
            'errors' : [],
        }

        missing_profile_count = 0

        # warn if a taxon has no profile
        for taxon in taxon_profiles.collected_taxa():
            taxon_profile = TaxonProfile.objects.filter(taxon_source=taxon.taxon_source,
                                taxon_latname=taxon.taxon_latname, taxon_author=taxon.taxon_author).first()

            if not taxon_profile:
                missing_profile_count += 1

        if missing_profile_count > 0:
            
            warning_message = _('Profile of %(count)s taxa missing. A generic profile will be used instead.') % {
                'count':missing_profile_count}
            warning = ValidationWarning(taxon_profiles, taxon_profiles, [warning_message])
            result['warnings'].append(warning)
            
        return result


    def validate_FactSheets(self, fact_sheets):
        
        result = {
            'warnings' : [],
            'errors' : [],
        }

        return result
    

    def validate_GenericForm(self, generic_form):
        '''
           Things that need checking:
           ERRORS:
           - fields with the roles taxonomic_reference, temporal_reference, geographic_reference have to be present
           - multiplechoicefields need at least 2 choices
           WARNINGS:
           None
        '''

        result = {
            'errors' : [],
            'warnings' : [],
        }

        generic_field_links = GenericFieldToGenericForm.objects.filter(generic_form=generic_form)

        for generic_field_link in generic_field_links:

            generic_field = generic_field_link.generic_field
    
            # check specific field requirements
            # choicefield, multiplechoicefield
            if generic_field.field_class == 'MultipleChoiceField' or generic_field.field_class == 'ChoiceField':
                choices = GenericValues.objects.filter(generic_field=generic_field)

                if len(choices) < 2:
                    verbose_field_class = generic_field.field_class

                    for tup in DJANGO_FIELD_CLASSES:
                        if tup[0] == generic_field.field_class:
                            verbose_field_class = tup[1]
                            break
                    
                    error_message = _('%(field_class)s needs at least 2 choices') % {
                        'field_class':verbose_field_class }
                    error = ValidationError(generic_form, generic_field, [error_message])
                    result['errors'].append(error)


        for role in ['taxonomic_reference', 'temporal_reference', 'geographic_reference']:

            role_verbose = role
            for role_entry in FIELD_ROLES:
                if role == role_entry[0]:
                    role_verbose = role_entry[1]
                    break

            role_field = GenericFieldToGenericForm.objects.filter(generic_form=generic_form,
                                                                  generic_field__role=role)
            if not role_field.exists():
                error_message = _('%(role)s field is missing') % {'role':role_verbose}
                role_error = ValidationError(generic_form, generic_form, [error_message])
                result['errors'].append(role_error)

        return result


    def validate_Glossary(self, glossary):

        result = {
            'errors' : [],
            'warnings' : [],
        }

        return result


    def validate_Map(self, map):

        result = {
            'errors' : [],
            'warnings' : [],
        }

        return result


    ###############################################################################################################
    # BUILDING
    # - uses the build folder within the app_version_folder
    # - {app_version_folder}/build/common/www/
    # - {app_version_folder}/build/webapp/
    # - {app_version_folder}/build/cordova/
    ###############################################################################################################
    def build(self):

        # LOCK app an features
        self.meta_app.is_locked = True
        self.meta_app.build_status = 'in_progress'

        # update build #
        if not self.meta_app.build_number:
            self.meta_app.build_number = 1

        else:
            self.meta_app.build_number = self.meta_app.build_number + 1

        self.meta_app.save()
        self.meta_app.lock_generic_contents()


        # BEGIN
        self.meta_app = self.meta_app

        self.logger = self._get_logger('build')
        self.logger.info('Starting build process')

        success = True
        app_is_valid = True
        
        build_report = self.get_empty_result()
        build_report['result'] = 'success'

        try:
            
            # SECURITY CHECK
            # a released version is locked
            if self.meta_app.published_version and self.meta_app.current_version <= self.meta_app.published_version:
                raise AppIsLockedError('You cannot build an app version if that version already has been released. Start a new version first')
            

            # check if the app is valid
            validation_result = self.validate()

            # do not attempt to build an invalid app
            if not validation_result:
                
                app_is_valid = False
                
                msg = 'Unable to build app  meta_app.id={0}. Validation Failed, because another validation process of this app is in progress'.format(
                            self.meta_app.id)
                self.logger.error(msg)
                raise AppBuildFailed(msg)

            elif len(validation_result['errors']) > 0:

                app_is_valid = False
                
                validation_result_json = {
                    'started_at' : validation_result['started_at'],
                    'errors' : [error.dump() for error in validation_result['errors']],
                    #'warnings' : [warning.dump() for warning in validation_result['warnings']],
                    'finished_at' : int(time.time()),
                }
                msg = 'Unable to build app  meta_app.id={0}. Validation Failed. Errors: {1}'.format(self.meta_app.id,
                                        json.dumps(validation_result_json))
                
                self.logger.error(msg)

                raise AppBuildFailed(msg)
            
            # prepare
            self.gbiflib = GBIFlib()

            # imageFilename : { "creator":"", "licence":"", "licence_link":""}
            # will be filled by build_* methods
            self.licence_registry = {
                'licences' : {},
            }

            # make the settings available to all methods
            # settings will be filled by build_* methods
            self.app_settings = self._get_app_settings(preview=False)

            self.build_features = {}
            
            # create build folder
            # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.current_version}/release/common/www/
            # a build of a specific version always kills the previous build
            self.logger.info('deleting and recreating {0}'.format(self._app_release_path))
            self.deletecreate_folder(self._app_release_path)

            # build_common_www has to come first
            self._build_common_www()

            # build webapp
            self._build_webapp()

            # build ios, done on a mac
            if 'ios' in settings.APP_KIT_SUPPORTED_PLATFORMS and 'ios' in self.meta_app.build_settings['platforms']:
                self._create_ios_build_job()

            # build android
            if 'android' in self.meta_app.build_settings['platforms']:
                self._build_android()

        
        except Exception as e:
            success = False
            self.logger.error(e, exc_info=True)

            build_report['result'] = 'failure'
            
            # send email! only if app building failed and validation was successful
            if app_is_valid == True:
                # execute code below if sending of email fails
                try:
                    self.send_bugreport_email(e)
                    
                except Exception as emailException:
                    pass

        # LOCK app an features
        self.meta_app.is_locked = False
        if success == True:
            self.meta_app.build_status = 'passing'
        else:

            if app_is_valid == True:
                self.meta_app.build_status = 'failing'
            else:
                # no build has been performed
                self.meta_app.build_status = None
                
        build_report['finished_at'] = int(time.time())
        self.meta_app.last_build_report = build_report
        
        self.meta_app.save()
        self.meta_app.unlock_generic_contents()

        return build_report

    
    ###############################################################################################################
    # BUILDING COMMON WWW
    # - www folder with the contents that all app builds (we, android, ios) use
    # - build locales first, glossary second, then the rest
    ###############################################################################################################
    def _build_common_www(self):

        ### STARTING TO BUILD GENERIC CONTENTS ###

        # build the frontend first
        self.logger.info('Building the Frontend')
        frontend_content_type = ContentType.objects.get_for_model(Frontend)
        self._build_Frontend()
        self.logger.info('Done.')

        ### BUILDING LOCALES ###
        # the translations are already complete
        self.logger.info('Building locales {0}'.format(','.join(self.meta_app.languages())))
        self._build_locales()
        self.logger.info('Done.')

        # build the glossary first in case a generic_content_json needs hard coded localized texts
        # instead of i18next keys
        glossary_content_type = ContentType.objects.get_for_model(Glossary)
        # there is only 1 glossary per app
        glossary_link = MetaAppGenericContent.objects.filter(meta_app=self.meta_app,
                                                             content_type=glossary_content_type).first()

        if glossary_link:
            self.logger.info('Building {0} {1}'.format(glossary_link.generic_content.__class__.__name__,
                                                 glossary_link.generic_content.uuid))

            # options are on the link, pass the link
            self._build_Glossary(glossary_link)        
        
        # iterate over all features (except glossary) and create the necessary json files
        generic_content_links = MetaAppGenericContent.objects.filter(meta_app=self.meta_app).exclude(
            content_type=glossary_content_type).exclude(content_type=frontend_content_type)

        for link in generic_content_links:
            generic_content = link.generic_content            
            self.logger.info('Building {0} {1}'.format(generic_content.__class__.__name__, generic_content.uuid))

            # options are on the link, pass the link
            build_method = getattr(self, '_build_{0}'.format(generic_content.__class__.__name__))
            build_method(link)
            

        # store settings as json
        
        app_settings_string = json.dumps(self.app_settings, indent=4, ensure_ascii=False)

        with open(self._app_settings_json_filepath, 'w', encoding='utf-8') as settings_json_file:
            settings_json_file.write(app_settings_string)
        
        # store features as json
        app_features_string = json.dumps(self.build_features, indent=4, ensure_ascii=False)
        app_features_json_file = self._app_features_json_filepath
        with open(app_features_json_file, 'w', encoding='utf-8') as f:
            f.write(app_features_string)
        
            
        # save licence registry
        # registry has been filled byt the build_ methods *

        with open(self._app_licence_registry_filepath, 'w', encoding='utf-8') as f:
            json.dump(self.licence_registry, f, indent=4)     
           

    ###############################################################################################################
    # BUILDING LOCALES
    # - translations are already complete
    # - the structure is locale/{LOCALE}/plain.json
    # - the frontend creator might have supplied base translation files, add to those files if present
    ###############################################################################################################
    def _build_locales(self):
        
        app_primary_locale_filepath = self._app_locale_filepath(self.meta_app.primary_language)
        primary_locale_folder = self._app_locale_path(self.meta_app.primary_language)

        if not os.path.isdir(primary_locale_folder):
            os.makedirs(primary_locale_folder)

        primary_locale = self.meta_app.localizations[self.meta_app.primary_language]

        frontend_primary_locale = self._get_frontend_locale(self.meta_app.primary_language)
        for key, localization in frontend_primary_locale.items():
            primary_locale[key] = localization

        with open(app_primary_locale_filepath, 'w') as app_primary_locale_file:
            app_primary_locale_file.write(json.dumps(primary_locale))


        localized_content_images = self.meta_app.get_localized_content_images()


        for language_code in self.meta_app.secondary_languages():
            
            locale = self.meta_app.localizations[language_code].copy()

            frontend_locale = self._get_frontend_locale(language_code)
            for key, localization in frontend_locale.items():
                locale[key] = localization

            locale_folder = self._app_locale_path(language_code)

            if not os.path.isdir(locale_folder):
                os.makedirs(locale_folder)

            # build folder for LocalizedContentImages
            localized_images_path = self._app_localized_content_images_path(language_code)

            if not os.pathisdir(localized_images_path):
                os.makedirs(localized_images_path)

            for locale_key, image_definition in localized_content_images.items():

                content_image_id = image_definition['content_image_id']
                content_image = ContentImage.objects.get(pk=content_image_id)

                localized_content_image = LocalizedContentImage.objects.get(content_image=content_image,
                    language_code=language_code)

                relative_url = self.save_localized_content_image(localized_content_image)

                image_definition['media_url'] = relative_url

                locale[locale_key] = image_definition

            locale_filepath = self._app_locale_filepath(language_code)

            with open(locale_filepath, 'w') as locale_file:
                locale_file.write(json.dumps(locale))


    def _get_frontend_locale(self, language_code):
        
        locale = {}
        locale_filepath = os.path.join(self._frontend_locales_folder_path, language_code, 'plain.json')

        if os.path.isfile(locale_filepath):
            with open(locale_filepath, 'r') as locale_file:
                locale = json.load(locale_file)
        else:
            self.logger.warn('No locale file found for langauge {0}'.format(language_code))

        return locale


    def _add_to_locale(self, dictionary, language_code):
        locale_filepath = self._app_locale_filepath(language_code)

        with open(locale_filepath, 'r') as locale_file:
            locale = json.loads(locale_file.read())

        for key, value in dictionary.items():
            locale[key] = value
        
        with open(locale_filepath, 'w') as locale_file:
            locale_file.write(json.dumps(locale))


    def _create_taxon_json_from_lazy_taxon(self, lazy_taxon, use_gbif):

        taxon_json = {
            'taxonSource' : lazy_taxon.taxon_source,
            'taxonLatname' : lazy_taxon.taxon_latname,
            'taxonAuthor' : lazy_taxon.taxon_author,
            
            'nameUuid' : str(lazy_taxon.name_uuid),
            'taxonNuid' : lazy_taxon.taxon_nuid,
            
            'gbifNubKey' : None,
        }

        if use_gbif == True:
            gbif_nubKey = self.gbiflib.get_nubKey(lazy_taxon)
            
            if gbif_nubKey :
                taxon_json['gbifNubKey'] = gbif_nubKey

        return taxon_json
        

    # add a localization of nature guide taxa directly to the locale
    # there might be more vernacular names stored inside the taxon dic of backbone taxonomy
    # this one is for quick access in the template
    # first, the primary language is collected
    def _collect_vernacular_names_from_nature_guides(self, language_code):

        if language_code not in self.nature_guides_vernacular_names:

            self.nature_guides_vernacular_names[language_code] = {}

            content_type = ContentType.objects.get_for_model(NatureGuide)
            app_nature_guides = MetaAppGenericContent.objects.filter(meta_app=self.meta_app, content_type=content_type)


            for feature_link in app_nature_guides:

                nature_guide = feature_link.generic_content

                nodes_with_taxon = NatureGuidesTaxonTree.objects.filter(nature_guide=nature_guide,
                                        meta_node__name__isnull=False, meta_node__taxon_latname__isnull=False)

                for node in nodes_with_taxon:

                    taxon = node.meta_node.taxon

                    key = str(taxon.name_uuid)

                    taxon_json = self._create_taxon_json_from_lazy_taxon(taxon, self.use_gbif)

                    vernacular = None
                    
                    if language_code == self.meta_app.primary_language:
                        vernacular = node.meta_node.name
                    else:
                        # look up translation
                        translation = self.meta_app.localizations[language_code]

                        if node.name in translation:
                            vernacular = translation[node.meta_node.name]

                    if vernacular:
                        taxon_json['name'] = vernacular
                        self.nature_guides_vernacular_names[language_code][key] = taxon_json

        return self.nature_guides_vernacular_names[language_code]



    ###############################################################################################################
    # BUILDING THE FRONTEND
    # - for the blank Frontend, use AppBuilderBase._build_Frontend
    # - use FrontendJSONBuilder for user generated content
    # - build the frontend specific images in a way that the Frontend creator can access them:
    #   - filenames according to frontend_settings
    #   - destination path of images: localcosmos/frontend/{FILENAME}
    ###############################################################################################################     

    def _build_Frontend(self):
        # copy all frontend files
        super()._build_Frontend()

        frontend_content_type = ContentType.objects.get_for_model(Frontend)

        frontend_link = MetaAppGenericContent.objects.get(meta_app=self.meta_app, content_type=frontend_content_type)

        frontend = frontend_link.generic_content

        jsonbuilder = self.get_json_builder(frontend_link)

        frontend_json = jsonbuilder.build()

        self._add_generic_content_to_app(frontend, frontend_json, only_one_allowed=True)

    ###############################################################################################################
    # BUILDING GENERIC CONTENTS
    # - use JSONBuilder classes
    # - dump the json to build/common/www/xyz
    # - fill build_featres{} which will be dumped as www/features.js
    ###############################################################################################################

    def get_json_builder(self, app_generic_content):

        generic_content = app_generic_content.generic_content

        builder_class_name = '{0}JSONBuilder'.format(generic_content.__class__.__name__)
        builder_module_path = 'app_kit.appbuilder.JSONBuilders.{0}.{1}'.format(builder_class_name, builder_class_name)
        
        JSONBuilderClass = import_module(builder_module_path)
        
        jsonbuilder = JSONBuilderClass(self, app_generic_content)

        return jsonbuilder


    # feature entry of a generic content
    # build the entry for features.js which is used by the app to recognize which features are installed
    # and where to find them on the disk
    def _get_feature_entry(self, generic_content, **kwargs):

        generic_content_type = kwargs.get('generic_content_type', generic_content.__class__.__name__)

        feature_entry_json = {
            'genericContentType' : generic_content_type,
            'uuid' : str(generic_content.uuid),
            'name' : {},
            'version' : generic_content.current_version,
        }

        # add localized names directly in the feature.js
        '''
        for language_code in self.meta_app.languages():
            localized_name = self.get_localized(generic_content.name, language_code)
            
            feature_entry['name'][language_code] = localized_name
        '''
        feature_entry_json['name'] = generic_content.name


        # complete the settings_entry
        # one file per form, absolute path in webapp features.js
        relative_generic_content_folder =  self._app_relative_generic_content_path(generic_content)

        content_filename = '{0}.json'.format(str(generic_content.uuid))
        
        relative_generic_content_filepath = os.path.join(relative_generic_content_folder, content_filename)

        feature_entry_json['path'] = relative_generic_content_filepath
        feature_entry_json['folder'] = relative_generic_content_folder

        return feature_entry_json

    
    # adding a default feature, e.g. a default observation form
    def _add_default_to_features(self, generic_content_type, generic_content, force_add=False):
        if generic_content_type in ['GenericForm', 'ButtonMatrix']:

            if force_add == True or 'default' not in self.build_features[generic_content_type]:
                option_entry = generic_content.make_option_from_instance(generic_content)
                self.build_features[generic_content_type]['default'] = option_entry


    
    # one content dump per language OR one file for all languages
    # stores the json on disk
    # adds feature_entry to features.js
    def _add_generic_content_to_app(self, generic_content, generic_content_json, only_one_allowed=False, **kwargs):

        if only_one_allowed == True:
            generic_content_json['isMulticontent'] = False
        else:
            generic_content_json['isMulticontent'] = True


        filename_identifier = str(generic_content.uuid)

        # generic_content_json has options and global_options
        fallback_options = kwargs.get('fallback_options', {})
        for key, value in fallback_options.items():

            if not key in generic_content_json['options']:
                generic_content_json['options'][key] = value

        generic_content_type = kwargs.get('generic_content_type', generic_content.__class__.__name__)

        # first make the folder
        absolute_generic_content_folder = self._app_absolute_generic_content_path(generic_content, **kwargs)

        # create the content folder
        if not os.path.isdir(absolute_generic_content_folder):
            os.makedirs(absolute_generic_content_folder)
        
        '''
        filename = '{0}.content'.format(filename_identifier)
        
        content_dump_file = os.path.join(absolute_generic_content_folder, filename)            
            
        with open(content_dump_file, 'w', encoding='utf-8') as f:
            # base64 encode
            string = json.dumps(generic_content_json)
            encoded = base64.b64encode(string.encode())
            f.write(encoded.decode())
        '''

        filename = '{0}.json'.format(filename_identifier)
        content_dump_file = os.path.join(absolute_generic_content_folder, filename)            
        
        with open(content_dump_file, 'w', encoding='utf-8') as f:
            json.dump(generic_content_json, f, indent=4, ensure_ascii=False)


        #get the json entry for features.js
        feature_entry_json = self._get_feature_entry(generic_content, generic_content_type=generic_content_type)

        if only_one_allowed == True:
            self.build_features[generic_content_type] = feature_entry_json

        else:
            if generic_content_type not in self.build_features:
                self.build_features[generic_content_type] = {
                    'list' : [],
                    'lookup' : {},
                }

            # always add the first entry as default
            # replace the first entry if an entry with is_default is passed
            is_default = generic_content_json['options'].get('is_default', False)
            self._add_default_to_features(generic_content_type, generic_content, force_add=is_default)


            self.build_features[generic_content_type]['list'].append(feature_entry_json)
            self.build_features[generic_content_type]['lookup'][filename_identifier] = feature_entry_json['path']



    ###############################################################################################################
    # BACKBONE TAXONOMY
    # - dump taxonomic trees as json
    # - files for quick searching in alphabet/AA.json and vernacular/en.json
    
    def _build_BackboneTaxonomy(self, app_generic_content):

        backbone_taxonomy = app_generic_content.generic_content

        jsonbuilder = self.get_json_builder(app_generic_content)
        #backbone_taxonomy_json = jsonbuilder.build()

        # relative paths are used in the features.js file
        relative_generic_content_path = self._app_relative_generic_content_path(backbone_taxonomy)
        alphabet_relative_path = os.path.join(relative_generic_content_path, 'alphabet')
        vernacular_relative_path = os.path.join(relative_generic_content_path, 'vernacular')

        feature_entry = self._get_feature_entry(backbone_taxonomy)

        feature_entry.update({
            'alphabet' : alphabet_relative_path, # a folder
            'vernacular' : {}, # one file per language
        })


        # ALPHABET
        absolute_feature_path = self._app_absolute_generic_content_path(backbone_taxonomy)

        alphabet_absolute_path = os.path.join(absolute_feature_path, 'alphabet')
        # create folder
        if not os.path.isdir(alphabet_absolute_path):
            os.makedirs(alphabet_absolute_path)

        for start_letters, letters_taxa in jsonbuilder.build_latname_alphabet(self.use_gbif):
            
            letter_file = os.path.join(alphabet_absolute_path, '{0}.json'.format(start_letters))

            # check existing letters taxa
            existing_letters_taxa = []
            if os.path.isfile(letter_file):
                with open(letter_file, 'r', encoding='utf-8') as f:
                    existing_letters_taxa = json.load(f)

            letters_taxa_merged = existing_letters_taxa + letters_taxa

            # remove duplicates
            letters_taxa_distinct = [dict(t) for t in {tuple(d.items()) for d in letters_taxa_merged}]
            
            with open(letter_file, 'w', encoding='utf-8') as f:
                json.dump(letters_taxa_distinct, f, indent=4, ensure_ascii=False)
            

        # VERNACULAR NAMES
        
        # absolute path for dumping
        feature_path = self._app_absolute_generic_content_path(backbone_taxonomy)
        vernacular_absolute_path = os.path.join(feature_path, 'vernacular')

        if not os.path.isdir(vernacular_absolute_path):
            os.makedirs(vernacular_absolute_path)

        for language_code, vernacular_names_list in jsonbuilder.build_vernacular_names(self.use_gbif):

            # remove duplicates
            vernacular_names_distinct = [dict(t) for t in {tuple(d.items()) for d in vernacular_names_list}]

            # dump the language specific file
            # one file per language for vernacular names for search
            locale_filename = '{0}.json'.format(language_code)
            language_file = os.path.join(vernacular_absolute_path, locale_filename)
            with open(language_file, 'w', encoding='utf-8') as f:
                json.dump(vernacular_names_distinct, f, indent=4, ensure_ascii=False)

            vernacular_language_specific_path = os.path.join(vernacular_relative_path, locale_filename)
            feature_entry['vernacular'][language_code] = vernacular_language_specific_path


        # add to settings, there is only one BackboneTaxonomy per app
        self.build_features[backbone_taxonomy.__class__.__name__] =  feature_entry



    ###############################################################################################################
    # TAXON PROFILES
    # - one file per taxon profile which includes all languages
    
    def _build_TaxonProfiles(self, app_generic_content):

        taxon_profiles = app_generic_content.generic_content        

        jsonbuilder = self.get_json_builder(app_generic_content)
        
        generic_content_type = taxon_profiles.__class__.__name__


        # add profiles to settings the default way
        feature_entry_json = self._get_feature_entry(taxon_profiles)
        del feature_entry_json['path']


        self.build_features[generic_content_type] = feature_entry_json

        self.logger.info('running TaxonProfilesJSONBuilder.build')

        # add the profiles directly to the features.js, instead of _add_generic_content_to_app
        taxon_profiles_json = jsonbuilder.build()

        for key, value in taxon_profiles_json.items():
            if key not in self.build_features[generic_content_type].items():
                self.build_features[generic_content_type][key] = value


        app_relative_taxonprofiles_folder =  self._app_relative_generic_content_path(taxon_profiles)
        self.build_features[generic_content_type]['files'] = app_relative_taxonprofiles_folder
        

        # paths for storing taxon profiles
        app_absolute_taxonprofiles_path = self._app_absolute_generic_content_path(taxon_profiles)

        if not os.path.isdir(app_absolute_taxonprofiles_path):
            os.makedirs(app_absolute_taxonprofiles_path)


        collected_taxa = taxon_profiles.collected_taxa()

        self.logger.info('Building taxon profiles for collected taxa')
        
        for profile_taxon in collected_taxa:
            
            profile_json = jsonbuilder.build_taxon_profile(profile_taxon, self.gbiflib,
                                                           languages=self.meta_app.languages())

            
            if profile_json is not None:

                # dump the profile
                source_folder = os.path.join(app_absolute_taxonprofiles_path, profile_taxon.taxon_source)
                if not os.path.isdir(source_folder):
                    os.makedirs(source_folder)

                profile_filepath = os.path.join(source_folder, '{0}.json'.format(profile_taxon.name_uuid))

                with open(profile_filepath, 'w', encoding='utf-8') as f:
                    json.dump(profile_json, f, indent=4, ensure_ascii=False)


        # build search index and registry
        languages = self.meta_app.languages()
        taxon_profiles_registry = jsonbuilder.build_alphabetical_registry(collected_taxa, languages)
        registry_absolute_filepath = os.path.join(app_absolute_taxonprofiles_path, 'registry.json')
        
        with open(registry_absolute_filepath, 'w', encoding='utf-8') as f:
            json.dump(taxon_profiles_registry, f, indent=4, ensure_ascii=False)


        taxon_profiles_search_indices = jsonbuilder.build_search_indices(collected_taxa, languages)
        search_indices_absolute_filepath = os.path.join(app_absolute_taxonprofiles_path, 'search.json')

        with open(search_indices_absolute_filepath, 'w', encoding='utf-8') as f:
            json.dump(taxon_profiles_search_indices, f, indent=4, ensure_ascii=False)

        # add paths to features.json
        relative_registry_path = os.path.join(app_relative_taxonprofiles_folder, 'registry.json')
        relative_search_index_path = os.path.join(app_relative_taxonprofiles_folder, 'search.json')

        self.build_features[generic_content_type]['registry'] = relative_registry_path
        self.build_features[generic_content_type]['search'] = relative_search_index_path

        self.logger.info('finished building TaxonProfiles')

    ###############################################################################################################
    # FACT SHEETS
    # - one file per fact sheet and locale
    # - respect taxonomic restriction if any

    def _app_relative_fact_sheet_locale_filepath(self, fact_sheet, language_code):

        filename = '{0}.html'.format(language_code)
        folder = '{0}-{1}'.format(str(fact_sheet.pk), slugify(fact_sheet.title))

        path = os.path.join(folder, filename)

        return path
    
    
    def _build_FactSheets(self, app_generic_content):

        fact_sheets = app_generic_content.generic_content

        jsonbuilder = self.get_json_builder(app_generic_content)

        fact_sheets_json = jsonbuilder.build()

        linked_fact_sheets = FactSheet.objects.filter(fact_sheets=fact_sheets)

        # path for storing fact sheets
        # features/fact_sheets/str(fact_sheets.uuid)/
        app_absolute_fact_sheets_folder = self._app_absolute_generic_content_path(fact_sheets)

        # create the content folder
        if not os.path.isdir(app_absolute_fact_sheets_folder):
            os.makedirs(app_absolute_fact_sheets_folder)

        for fact_sheet in linked_fact_sheets:

            fact_sheets_json['localizedSlugs'] = {}

            taxonomic_restriction = jsonbuilder.get_taxonomic_restriction(fact_sheet)
            fact_sheet_json = {
                'taxonomicRestriction' : taxonomic_restriction,
                'localized' : {},
                'title' : fact_sheet.title,
            }
            
            for language_code in self.meta_app.languages():

                # there are two locale files: plain.json and glossarized.json
                plain_locale_path = self._app_locale_filepath(language_code)
                glossarized_locale_path = self._app_glossarized_locale_filepath(language_code)

                with open(plain_locale_path, 'r') as f:
                    plain_locale = json.loads(f.read())

                if os.path.isfile(glossarized_locale_path):
                    with open(glossarized_locale_path, 'r') as f:
                        glossarized_locale = json.loads(f.read())
                else:
                    glossarized_locale = None

                fact_sheet_relative_path = self._app_relative_fact_sheet_locale_filepath(fact_sheet,
                                                                                               language_code)

                html = jsonbuilder.render_localized_fact_sheet(fact_sheet, language_code,
                                                               plain_locale, glossarized_locale)

                localized_title = plain_locale.get(fact_sheet.title, fact_sheet.title)

                localized_slug = slugify(localized_title)
                fact_sheets_json['localizedSlugs'][localized_slug] = fact_sheet.id

                localized_fact_sheet_json = {
                    'path' : fact_sheet_relative_path,
                    'slug' : localized_slug,
                }

                fact_sheet_json['localized'][language_code] = localized_fact_sheet_json

                absolute_fact_sheet_path = os.path.join(app_absolute_fact_sheets_folder,
                                                        fact_sheet_relative_path)

                fact_sheet_folder = os.path.dirname(absolute_fact_sheet_path)
                if not os.path.isdir(fact_sheet_folder):
                    os.makedirs(fact_sheet_folder)

                # store the fact sheet
                with  open(absolute_fact_sheet_path, 'w') as fact_sheet_file:
                    fact_sheet_file.write(html)

            
            fact_sheets_json['factSheets'][str(fact_sheet.pk)] = fact_sheet_json

        
        self._add_generic_content_to_app(fact_sheets, fact_sheets_json)
        
    ###############################################################################################################
    # GENERIC FORMS
    # - one file for all languages
    
    def _build_GenericForm(self, app_generic_content):

        generic_form = app_generic_content.generic_content

        # only build one file for all languages
        jsonbuilder = self.get_json_builder(app_generic_content)
        generic_form_json = jsonbuilder.build()

        self._add_generic_content_to_app(generic_form, generic_form_json)


    ###############################################################################################################
    # NATURE GUIDES
    # - one file for all languages ???

    def _build_NatureGuide(self, app_generic_content):

        nature_guide = app_generic_content.generic_content

        jsonbuilder = self.get_json_builder(app_generic_content)

        nature_guide_json = jsonbuilder.build()

        localized_slugs = jsonbuilder.localized_slugs

        for language_code, slugs in localized_slugs.items():
            
            self._add_to_locale(slugs, language_code)

        self._add_generic_content_to_app(nature_guide, nature_guide_json)


    ###############################################################################################################
    # GLOSSARY
    # - there is only one glossary, with keys for translation

    def _build_Glossary(self, app_generic_content):

        glossary = app_generic_content.generic_content

        jsonbuilder = self.get_json_builder(app_generic_content)
        
        # only contains the primary language
        glossary_json = jsonbuilder.build()

        self._add_generic_content_to_app(glossary, glossary_json, only_one_allowed=True)

        generic_content_type = glossary.__class__.__name__
        self.build_features[generic_content_type]['localized'] = {}
        

        for language_code in self.meta_app.languages():

            self.build_features[generic_content_type]['localized'][language_code] = {}
            
            # create a glossarized version of te language file and save it as {language}_glossarized.json
            glossarized_locale, used_terms_glossary = jsonbuilder.glossarize_language_file(glossary_json, language_code)

            # store localized glossary file in the same folder as the language file
            glossarized_locale_filepath = self._app_glossarized_locale_filepath(language_code)


            with open(glossarized_locale_filepath, 'w', encoding='utf-8') as f:
                json.dump(glossarized_locale, f, indent=4, ensure_ascii=False)


            # localized glossary
            localized_glossary_folder = self._app_localized_glossaries_path(glossary, language_code)

            if not os.path.isdir(localized_glossary_folder):
                os.makedirs(localized_glossary_folder)

            # store localized glossary which only contains used terms
            used_terms_glossary_filepath = self._app_used_terms_glossary_filepath(glossary, language_code)

            with open(used_terms_glossary_filepath, 'w', encoding='utf-8') as f:
                json.dump(used_terms_glossary, f, indent=4, ensure_ascii=False)


            used_terms_glossary_relative_path = self._app_relative_used_terms_glossary_filepath(glossary, language_code)

            self.build_features[generic_content_type]['localized'][language_code]['usedTerms'] = used_terms_glossary_relative_path

            # create a downloadable csv file
            used_terms_glossary_csv = jsonbuilder.create_glossary_for_csv(used_terms_glossary)
            used_terms_glossary_csv_filepath = self._app_used_terms_glossary_csv_filepath(glossary, language_code)

            
            with open(used_terms_glossary_csv_filepath, 'w', newline='') as utg_csvfile:
                utg_writer = csv.writer(utg_csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                for utg_row in used_terms_glossary_csv:
                    utg_writer.writerow(utg_row)

            used_terms_glossary_csv_relative_path = self._app_relative_used_terms_glossary_csv_filepath(glossary,
                language_code)

            self.build_features[generic_content_type]['localized'][language_code]['usedTermsCsv'] = used_terms_glossary_csv_relative_path


            # localized glossary, all terms
            localized_glossary = jsonbuilder.build_localized_glossary(glossary_json, language_code)
            localized_glossary_filepath = self._app_localized_glossary_filepath(glossary, language_code)
            
            with open(localized_glossary_filepath, 'w', encoding='utf-8') as f:
                json.dump(localized_glossary, f, indent=4, ensure_ascii=False)


            localized_glossary_relative_path = self._app_relative_localized_glossary_filepath(glossary, language_code)
            
            self.build_features[generic_content_type]['localized'][language_code]['allTerms'] = localized_glossary_relative_path


            # downloadable csv file of all terms

            # create a downloadable csv file
            localized_glossary_csv = jsonbuilder.create_glossary_for_csv(localized_glossary)
            localized_glossary_csv_filepath = self._app_localized_glossary_csv_filepath(glossary, language_code)

            
            with open(localized_glossary_csv_filepath, 'w', newline='') as lg_csvfile:
                lg_writer = csv.writer(lg_csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                for lg_row in localized_glossary_csv:
                    lg_writer.writerow(lg_row)

            localized_glossary_csv_relative_path = self._app_relative_localized_glossary_csv_filepath(glossary,
                language_code)

            self.build_features[generic_content_type]['localized'][language_code]['allTermsCsv'] = localized_glossary_csv_relative_path


    ###############################################################################################################
    # MAP
    # - maps are optional

    def _build_Map(self, app_generic_content):

        lc_map = app_generic_content.generic_content

        jsonbuilder = self.get_json_builder(app_generic_content)
        
        map_json = jsonbuilder.build()

        self._add_generic_content_to_app(lc_map, map_json)


    ###############################################################################################################
    # BUILDING CONTENT IMAGES
    # - images of generic contents/features
    # - use proper image resizing
    # - respect crop parameters
    # - respect features
    # 
    ###############################################################################################################
    def _save_content_image(self, content_image, absolute_path, relative_path, filename=None, size=None):

        if size == None:
            size = 500

        if not os.path.isdir(absolute_path):
            os.makedirs(absolute_path)


        source_image_path = content_image.image_store.source_image.path

        # pil does not support svg, simply copy file
        if source_image_path.endswith('.svg'):
            if not filename:
                filename = os.path.basename(source_image_path)
            
            relative_image_filepath = os.path.join(relative_path, filename)
            absolute_image_filepath = os.path.join(absolute_path, filename)

            shutil.copyfile(source_image_path, absolute_image_filepath)

        # use pil to manipulate the image
        else:
            original_image = Image.open(source_image_path)

            processed_image = content_image.get_in_memory_processed_image(original_image, size)

            # all processed images are webp
            #original_format = original_image.format
            #output_format = original_format
            #allowed_formats = ['png', 'jpg', 'jpeg']

            #if original_format not in allowed_formats:
            file_extension = 'webp'
            output_format = 'WEBP'


            if filename:
                blankname, ext = os.path.splitext(filename)
                output_filename = '{0}.{1}'.format(blankname, file_extension)
            else:
                output_filename = '{0}-{1}-{2}.{3}'.format(content_image.image_type, content_image.id, size, file_extension)
                #output_filename = '{0}.{1}'.format(uuid.uuid4(), file_extension)


            relative_image_filepath = os.path.join(relative_path, output_filename)
            absolute_image_filepath = os.path.join(absolute_path, output_filename)
            

            if not os.path.isfile(absolute_image_filepath):

                if output_format == 'JPEG':
                    image_with_white_background = Image.new("RGB", processed_image.size, (255, 255, 255))
                    image_with_white_background.paste(processed_image)
                    image_with_white_background.save(absolute_image_filepath, output_format, quality=95)

                else:
                    processed_image.save(absolute_image_filepath, output_format)


            # add image to licence_registry
            licence = content_image.image_store.licences.first()
            if licence:
                content_licence = licence.content_licence().as_dict()

                registry_entry = {
                    'creatorName' : licence.creator_name,
                    'creatorLink' : licence.creator_link,
                    'sourceLink' : licence.source_link,
                    'licence' : content_licence,
                }
                
                self.licence_registry['licences'][relative_image_filepath] = registry_entry
            

        return relative_image_filepath


    def save_localized_content_image(self, localized_content_image, filename=None, size=None):
        
        language_code = localized_content_image.language_code
        
        absolute_path = self._app_localized_content_images_path(language_code)
        relative_path = self._app_relative_localized_content_images_path(language_code)

        relative_filepath = self._save_content_image(localized_content_image, absolute_path, relative_path,
                                                        filename=filename, size=size)

        return relative_filepath


    def save_content_image(self, content_image, filename=None, size=None):
        
        absolute_path = self._app_content_images_path
        relative_path = self._app_relative_content_images_path

        relative_filepath = self._save_content_image(content_image, absolute_path, relative_path, filename=filename,
                                                        size=size)

        return relative_filepath
        

    ###############################################################################################################
    # BUILDING WEBAPP
    # - symlink or copy all folders and files from common/www
    # - add additional files supplied by frontend in {FRONTEND_NAME}/webapp
    ###############################################################################################################
    def _build_Frontend_webapp_specific_assets(self):

        if os.path.isdir(self._frontend_webapp_assets_www_path):
            shutil.copytree(self._frontend_webapp_assets_www_path, self._build_webapp_www_path, dirs_exist_ok=True)
        
    def _build_webapp(self):

        self.logger.info('Building webapp')

        webapp_www_folder = self._build_webapp_www_path

        if not os.path.isdir(webapp_www_folder):
            os.makedirs(webapp_www_folder)
        else:
            self.logger.info('[webapp] webapp www folder already exists')

        # symlink common www
        common_www_folder = self._app_www_path
        for content in os.listdir(common_www_folder):
            source_path = os.path.join(common_www_folder, content)
            dest_path = os.path.join(webapp_www_folder, content)
            os.symlink(source_path, dest_path)


        # copy webapp specific assets supplied by frontend
        self.logger.info('[webapp] copying frontend specific assets')
        self._build_Frontend_webapp_specific_assets()


        # served review folder
        if os.path.islink(self._review_webapp_served_www_path):
            os.unlink(self._review_webapp_served_www_path)

        if not os.path.isdir(self._review_served_root):
            os.makedirs(self._review_served_root)

        os.symlink(webapp_www_folder, self._review_webapp_served_www_path)

        # set localcosmos_server.app.review_version_path
        self.meta_app.app.review_version_path = self._review_webapp_served_www_path
        self.meta_app.app.save()

        # if lc private is set, serve the webapp zip
        # create a zipfile of the webapp folder
        lc_private = self.meta_app.get_global_option('localcosmos_private')
        if lc_private == True:
            
            zip_filepath = self._build_webapp_zip_filepath
            webapp_www_folder = self._build_webapp_www_path

            with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as www_zip:

                for root, dirs, files in os.walk(webapp_www_folder, followlinks=True):

                    for filename in files:
                        # Create the full filepath by using os module.
                        app_file_path = os.path.join(root, filename)
                        arcname = app_file_path.split(webapp_www_folder)[-1]
                        www_zip.write(app_file_path, arcname=arcname)

            # serve the zipfile via symlink
            self.serve_review_webapp_zip()

        self.logger.info('Successfully built webapp')


    def serve_review_webapp_zip(self):
        
        self.deletecreate_folder(self._review_webapp_zip_served_path)
        os.symlink(self._build_webapp_zip_filepath, self._review_webapp_zip_served_filepath)


    ##############################################################################################################
    # NGINX paths

    # serving built products for review
    # served roots for review and published
    @property
    def _review_served_root(self):
        return os.path.join(settings.LOCALCOSMOS_APPS_ROOT, self.meta_app.app.uid, 'review')

    @property
    def _published_served_root(self):
        return os.path.join(settings.LOCALCOSMOS_APPS_ROOT, self.meta_app.app.uid, 'published')

    # webapp www folder of review and published
    @property
    def _review_webapp_served_www_path(self):
        return os.path.join(self._review_served_root, 'www')
    
    @property
    def _published_webapp_served_www_path(self):
        return os.path.join(self._published_served_root, 'www')


    # PACKAGES
    # do not make explicit nginx mappings for each package
    # nginx map: location /packages {
    #            alias /var/www/localcosmos/apps/$1/packages;
    # }
    @property
    def _served_packages_root(self):
        return os.path.join(settings.LOCALCOSMOS_APPS_ROOT, self.meta_app.app.uid, 'packages')

    @property
    def _review_served_packages_path(self):
        return os.path.join(self._served_packages_root, 'review')

    @property
    def _published_served_packages_path(self):
        return os.path.join(self._served_packages_root, 'published')

    # android, review and published
    @property
    def _review_android_served_path(self):
        return os.path.join(self._review_served_packages_path, 'android')

    @property
    def _published_android_served_path(self):
        return os.path.join(self._published_served_packages_path, 'android')

    @property
    def _review_android_served_aab_filepath(self):
        cordova_builder = self.get_cordova_builder()
        aab_filename = cordova_builder._aab_filename
        return os.path.join(self._review_android_served_path, aab_filename)

    @property
    def _published_android_served_aab_filepath(self):
        cordova_builder = self.get_cordova_builder()
        aab_filename = cordova_builder._aab_filename
        return os.path.join(self._published_android_served_path, aab_filename)

    # ios, review and published
    @property
    def _review_ios_served_path(self):
        return os.path.join(self._review_served_packages_path, 'ios')

    @property
    def _published_ios_served_path(self):
        return os.path.join(self._published_served_packages_path, 'ios')


    # webapp
    @property
    def _review_webapp_zip_served_path(self):
        return os.path.join(self._review_served_packages_path, 'webapp')

    @property
    def _published_webapp_zip_served_path(self):
        return os.path.join(self._published_served_packages_path, 'webapp')

    @property
    def _review_webapp_zip_served_filepath(self):
        return os.path.join(self._review_webapp_zip_served_path, self._webapp_zipfile_name)

    @property
    def _published_webapp_zip_served_filepath(self):
        return os.path.join(self._published_served_packages_path, self._webapp_zipfile_name)
    
    @property
    def _webapp_zipfile_name(self):
        zipfile_name = '{0}.zip'.format(self.meta_app.name)
        return zipfile_name


    ###############################################################################################################
    # BUILDING iOS
    # - use BuildJobs, Mac queries BuildJobs and does Jobs
    # - tha actual build is done on a MAC
    ###############################################################################################################
        
    def _create_ios_build_job(self):

        # create a zipfile for cordova
        cordova_builder = self.get_cordova_builder(self.meta_app, self.app_version)
        
        zipfile_path = cordova_builder.create_zipfile()

        # make the zipfile available
        zipfile_served_folder = self._build_job_zipfile_served_folder(self.meta_app, self.app_version)

        self.deletecreate_folder(zipfile_served_folder)

        zipfile_name = '{0}.zip'.format(self.meta_app.app.uid)
        zipfile_served_path = os.path.join(zipfile_served_folder, zipfile_name)
        
        os.symlink(zipfile_path, zipfile_served_path)

        # relies on nginx conf
        zipfile_url = self._get_build_job_zipfile_url(self.meta_app, self.app_version, zipfile_name)

        # remember: AppKitJobs lies in the public schema
        # create a BuildJob so the Mac can download and build app
        build_jobs = AppKitJobs.objects.filter(meta_app_uuid=str(self.meta_app.uuid), platform='ios',
                                               app_version=self.app_version, job_type__in=['build', 'release'])

        for build_job in build_jobs:
            build_job.delete()

        parameters = {
            'zipfile_url' : zipfile_url,
        }

        meta_app_definition = MetaAppDefinition.to_dict(self.app_version, self.meta_app)

        build_job = AppKitJobs(
            meta_app_uuid = str(self.meta_app.uuid),
            meta_app_definition = meta_app_definition,
            app_version = self.app_version,
            platform = 'ios',
            job_type = 'build',
            parameters = parameters,
        )
        
        build_job.save()


    ##############################################################################################################
    # serving ipas
    # ._ipa_folder() is the served folder for ipas
    def _served_review_ipa_folder(self, meta_app):
        return os.path.join(self._ipa_folder(meta_app), 'review')

    def _served_published_ipa_folder(self, meta_app):
        return os.path.join(self._ipa_folder(meta_app), 'published')
        
    def _served_review_ipa_filepath(self, meta_app, app_version):
        meta_app_definition = MetaAppDefinition(app_version, meta_app=meta_app)
        CordovaBuilderClass = self._get_cordova_builder_class()
        ipa_filename = CordovaBuilderClass.get_ipa_filename(meta_app_definition)
        return os.path.join(self._served_review_ipa_folder(meta_app), ipa_filename)

    def _served_published_ipa_filepath(self, meta_app, app_version):
        meta_app_definition = MetaAppDefinition(app_version, meta_app=meta_app)
        CordovaBuilderClass = self._get_cordova_builder_class()
        ipa_filename = CordovaBuilderClass.get_ipa_filename(meta_app_definition)
        return os.path.join(self._served_published_ipa_folder(meta_app), ipa_filename)


    def serve_preview_ipa(self, meta_app, app_version, ipa_source):
        # symlink the ipa file
        ipa_review_folder = self._served_review_ipa_folder(meta_app)
        self.deletecreate_folder(ipa_review_folder)

        ipa_dest = self._served_review_ipa_filepath(meta_app, app_version)
        os.symlink(ipa_source, ipa_dest)

        # logger not available
        

    ###############################################################################################################
    # BUILDING ANDROID
    # - fetch logo, splash and other .svg images file from frontend if any
    # - use CordovaAppBuilder
    ###############################################################################################################

    # ANDROID SIGNING
    def get_keystore_path(self):
        keystore_path = os.path.join(self._certificates_path, self.android_keystore_name)
        return keystore_path


    def get_asset_filename(self, platform, asset_type):
        return ASSET_FILENAMES[platform][asset_type]
    

    def _build_android_assets(self):

        self.logger.info('Building Android assets')

        if not os.path.isdir(self._build_android_assets_path):
            os.makedirs(self._build_android_assets_path)

        frontend_settings = self._get_frontend_settings()
        frontend = self._get_frontend()

        for image_type in ['launcherIcon', 'splashscreen']:

            image_definition = frontend_settings['android'][image_type]

            if image_definition['type'] == 'userContent':
                image_identifier = image_definition['imageIdentifier']

                content_image = frontend.image(image_identifier)

                image_filepath = content_image.image_store.source_image.path

                filename = self.get_asset_filename('android', image_type)

                destination_filepath = os.path.join(self._build_android_assets_path, filename)
                shutil.copyfile(image_filepath, destination_filepath)

            else:
                raise NotImplementedError('[Frontend settings] android {0} of type {1} is not supported'.format(
                    image_type, image_definition['type']))

    # 1. symlink common www. 2. symlink android specific files
    def _build_android_www(self):

        self.logger.info('Building Android www')
        
        # symlink common www
        common_www_folder = self._app_www_path
        android_www_folder = self._build_android_www_path

        if not os.path.isdir(android_www_folder):
            os.makedirs(android_www_folder)

        for content in os.listdir(common_www_folder):
            source_path = os.path.join(common_www_folder, content)
            dest_path = os.path.join(android_www_folder, content)
            os.symlink(source_path, dest_path)

        # add android specific files, if any
        # the android folder does not have to be present
        if os.path.isdir(self._frontend_android_www_path):
            shutil.copytree(self._frontend_android_www_path, self._build_android_www_path, dirs_exist_ok=True)

    def _build_android(self):

        self.logger.info('Building Android')

        self._build_android_assets()

        self._build_android_www()

        keystore_path = self.get_keystore_path()
        
        cordova_builder = self.get_cordova_builder()
        
        aab_source = cordova_builder.build_android(keystore_path, settings.APP_KIT_ANDROID_KEYSTORE_PASS,
                                                   settings.APP_KIT_ANDROID_KEY_PASS)

        # symlink the aab into a browsable location
        self.deletecreate_folder(self._review_android_served_path)

        aab_dest = self._review_android_served_aab_filepath
        os.symlink(aab_source, aab_dest)

        self.logger.info('Successfully built Android')

    ##############################################################################################################
    # serving aabs


    def _served_published_aab_filepath(self, meta_app, app_version):
        meta_app_definition = MetaAppDefinition(app_version, meta_app=meta_app)
        CordovaBuilderClass = self._get_cordova_builder_class()
        aab_filename = CordovaBuilderClass.get_aab_filename(meta_app_definition)
        return os.path.join(self._served_published_aab_folder(meta_app), aab_filename)
    

    ##############################################################################################################
    # RELEASING
    # - copy build contents to release folder
    # - upload to app stores
    ##############################################################################################################

    def release(self):

        release_report = self.get_empty_result()

        release_report['result'] =  'success'

        self.logger = self._get_logger('release')
        self.logger.info('Starting release process')

        try:
            self._release_webapp()

            if 'android' in self.meta_app.build_settings['platforms']:
                self._release_android()

            if 'ios' in settings.APP_KIT_SUPPORTED_PLATFORMS and 'ios' in self.meta_app.build_settings['platforms']:
                self._release_ios()

            # app version bump
            self.meta_app.save(publish=True)

        except Exception as e:
            success = False
            self.logger.error(e, exc_info=True)

            release_report['result'] = 'failure'
            
            # send email!
            self.send_bugreport_email(e)

        release_report['finished_at'] = int(time.time())
        self.meta_app.last_release_report = release_report
        self.meta_app.save()

        return release_report

    
    def _release_webapp(self):

        build_webapp_www_folder = self._build_webapp_www_path

        served_published_www_folder = self._published_webapp_served_www_path
        if os.path.islink(served_published_www_folder):
            os.unlink(served_published_www_folder)
        
        os.symlink(build_webapp_www_folder, served_published_www_folder)

        # update app.url, if hosted on LC
        localcosmos_private = self.meta_app.get_global_option('localcosmos_private')

        if localcosmos_private == True:
            # symlink the pwa zip to a browsable location
            webapp_zip_release_folder = self._published_webapp_zip_served_path
            self.deletecreate_folder(webapp_zip_release_folder)

            webapp_zip_source = self._build_webapp_zip_filepath
            webapp_zip_dest = self._published_webapp_zip_served_path
            os.symlink(webapp_zip_source, webapp_zip_dest)

        else:
            # set the url of meta_app.app
            url = 'https://{0}.localcosmos.org/'.format(self.meta_app.app.uid)
            self.meta_app.app.url = url
            self.meta_app.app.save()



    ##############################################################################################################
    # release request email

    def _send_release_request_email(self, platform):

        tenant = self.meta_app.tenant
        tenant_admin_emails = tenant.get_admin_emails()
            
        title = '[{0}] {1} release requested'.format(self.meta_app.name, platform)
        
        text_content = 'App name: {0}, app uuid: {1}, app uid: {2}, version: {3}, platform: {4}, Admins: {5}'.format(
            self.meta_app.name, str(self.meta_app.uuid), self.meta_app.app.uid, self.meta_app.current_version, platform,
            ','.join(tenant_admin_emails))
            
        self.send_admin_email(title, text_content)
        
    ##############################################################################################################
    # RELEASE ANDROID AAB
    # - delete review aab, symlink released aab
    # - [TODO:] auto-upload to the app store via fastlane.tools
    def _release_android(self):

        self.logger.info('Releasing Android')

        cordova_builder = self.get_cordova_builder()

        # remove review dir
        if os.path.isdir(self._review_android_served_path):
            shutil.rmtree(self._review_android_served_path)

        # symlink the aab to a browsable location
        self.deletecreate_folder(self._published_android_served_path)

        # file lies in release/cordova/{... cordova specific paths}
        aab_source = cordova_builder._aab_filepath
        aab_dest = self._published_android_served_aab_filepath

        os.symlink(aab_source, aab_dest)

        self.logger.info('Successfully released Android')

        if self.meta_app.build_settings['distribution'] == 'appstores':
            
            self.logger.info('Sending release email for Android')

            #self._send_release_request_email('Android')


    ##############################################################################################################
    # RELEASE iOS IPA
    # - delete review ipa, symlink released ipa
    # - [TODO:] auto-upload to the app store via fastlane.tools
    def _release_ios(self, meta_app, app_version):

        self.logger.info('Releasing iOS')

        cordova_builder = self.get_cordova_builder(meta_app, app_version)

        # remove review dir
        ipa_review_folder = self._served_review_ipa_folder(meta_app)
        if os.path.isdir(ipa_review_folder):
            shutil.rmtree(ipa_review_folder)

        # symlink the ipa to a browsable location
        ipa_release_folder = self._served_published_ipa_folder(meta_app)
        self.deletecreate_folder(ipa_release_folder)

        ipa_source = cordova_builder.get_ipa_filepath()
        ipa_dest = self._served_published_ipa_filepath(meta_app, app_version)
        os.symlink(ipa_source, ipa_dest)

        # for fastlane appstore release, done on a mac
        # self._create_ios_release_job(meta_app, app_version)

        self.logger.info('Successfully released Android')

        # until fastlane is implemented: send email
        # ad-hoc or appstores
        if meta_app.build_settings['distribution'] == 'appstores':
            
            self.logger.info('Sending release email for iOS')

            self._send_release_request_email('iOS')


    def _create_ios_release_job(self, meta_app, app_version):

        meta_app_definition = MetaAppDefinition.to_dict(app_version, meta_app)

        existing_release_job = AppKitJobs.objects.filter(meta_app_uuid=meta_app.uuid, app_version=app_version,
                                                         job_type='release').first()

        if existing_release_job:
            existing_release_job.delete()

        release_job = AppKitJobs(
            meta_app_uuid = str(meta_app.uuid),
            meta_app_definition = meta_app_definition,
            app_version = app_version,
            platform = 'ios',
            job_type = 'release',
            parameters = {},
        )
        
        release_job.save()
        
        
        
