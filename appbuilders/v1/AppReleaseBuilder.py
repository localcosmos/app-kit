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

from .AppBuilder import AppBuilder

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from localcosmos_appkit_utils.MetaAppDefinition import MetaAppDefinition

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


# TAXONOMY
from taxonomy.lazy import LazyTaxon

# GBIFLib
from app_kit.appbuilders.GBIFlib import GBIFlib

from app_kit.models import MetaAppGenericContent
from app_kit.utils import import_module
from app_kit.generic_content_validation import ValidationError, ValidationWarning
from app_kit.AppThemeImage import AppThemeImage

from app_kit.forms import AppDesignForm

import os, json, base64, time, shutil, hashlib, zipfile

from PIL import Image

# jobs
from app_kit.app_kit_api.models import AppKitJobs
from django.db import connection
    

class AppBuildFailed(Exception):
    pass


class AppIsLockedError(Exception):
    pass


class AppReleaseBuilder(AppBuilder):

    use_gbif = True

    android_keystore_name = 'localcosmos_android.keystore'

    nature_guides_vernacular_names = {}

    def get_empty_result(self, meta_app, app_version):

        result = {
            'app_version' :  app_version,
            'started_at' : int(time.time()),
            'warnings' : [], # a list of ValidationWarning instances
            'errors' : [], # a list of ValidationError instances
        }

        return result


    ###############################################################################################################
    # FOLDERS FOR THE BUILD/RELEASE VERSION
    ###############################################################################################################

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/build/
    # eg /opt/localcosmos/apps/{UUID}/1/build/
    def _app_root_folder(self, meta_app, app_version=None):
        return os.path.join(self._app_version_root_folder(meta_app, app_version), 'build')

    # release folder. the release folder is independant of all other folders in {app_version}/
    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/release/
    # eg /opt/localcosmos/apps/{UUID}/1/release/
    def _app_release_folder(self, meta_app, app_version=None):
        return os.path.join(self._app_version_root_folder(meta_app, app_version), 'release')


    ###############################################################################################################
    # FOLDERS OF THE BUILT (RELEASE CANDIDATE) APP
    #- subfolders of build/
    #- prefixed with _build

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/build/common/www/
    def _app_www_folder(self, meta_app, app_version = None):
        return os.path.join(self._app_root_folder(meta_app, app_version), 'common', 'www')

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/build/webapp/
    def _build_webapp_folder(self, meta_app, app_version=None):
        return os.path.join(self._app_root_folder(meta_app, app_version), 'webapp')

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/build/webapp/www/
    def _build_webapp_www_folder(self, meta_app, app_version=None):
        return os.path.join(self._build_webapp_folder(meta_app, app_version), 'www')


    ### folders for generic contents, absolute and relative (to www) ###
    def _build_absolute_generic_content_path(self, meta_app, app_version, generic_content, **kwargs):
        return os.path.join(self._app_www_folder(meta_app, app_version),
                            self._build_relative_generic_content_path(generic_content, **kwargs))
    
    def _build_relative_generic_content_path(self, generic_content, **kwargs):
        generic_content_type = kwargs.get('generic_content_type', generic_content.__class__.__name__)
        return os.path.join('features/', generic_content_type, str(generic_content.uuid))


    # folder for content images, relative to www
    def _build_relative_content_images_path(self):
        return os.path.join('user_content/', 'content_images')

    # {settings.APP_KIT_ROOT}/{meta_app.uuid}/{meta_app.version}/build/www/user_content/content_images/
    # eg /opt/localcosmos/apps/{UUID}/1/build/www/user_content/content_images
    def _build_absolute_content_images_path(self, meta_app, app_version=None):
        return os.path.join(self._app_www_folder(meta_app, app_version), self._build_relative_content_images_path())

    # folder for app theme images, relative to www
    def _build_relative_app_theme_images_path(self, theme_name):
        return os.path.join('user_content/', 'themes', theme_name, 'images')

    ###############################################################################################################
    # OUTPUT FOR REVIEWING
    # the webapp is serverd here for reviewing - after building but before release

    def apk_review_url(self, request, meta_app, app_version):
        CordovaBuilderClass = self._get_cordova_builder_class()
        meta_app_definition = MetaAppDefinition(app_version, meta_app=meta_app)
        url = '{0}://{1}/apk/review/{2}'.format(request.scheme, meta_app.domain,
                                                CordovaBuilderClass.get_apk_filename(meta_app_definition))
        return url

    # does not return scheme and host
    def apk_published_url(self, meta_app, app_version):
        CordovaBuilderClass = self._get_cordova_builder_class()
        meta_app_definition = MetaAppDefinition(app_version, meta_app=meta_app)
        apk_url = '/apk/published/{0}'.format(CordovaBuilderClass.get_apk_filename(meta_app_definition))
        return apk_url

    # relies on correct nginx conf
    # do not use request.get_host()
    def webapp_review_url(self, request, meta_app, app_version):
        url = '{0}://{1}/review/'.format(request.scheme, meta_app.domain)
        return url

    # pwa is the webapp (inthis case zipped)
    def pwa_zip_review_url(self, request, meta_app, app_version):
        url = '{0}://{1}/pwa/review/{2}'.format(request.scheme, meta_app.domain, self._pwa_zipfile_name(meta_app))
        return url

    def pwa_zip_published_url(self, meta_app, app_version):
        url = '/pwa/published/{0}'.format(self._pwa_zipfile_name(meta_app))
        return url

    # ios ipa files
    def ipa_review_url(self, request, meta_app, app_version):
        # search for a completed AppKitJob
        job = AppKitJobs.objects.filter(meta_app_uuid=meta_app.uuid, app_version=app_version, platform='ios',
                                       job_type='build').first()

        if job and job.job_result and job.job_result.get('success') == True:
            CordovaBuilderClass = self._get_cordova_builder_class()
            meta_app_definition = MetaAppDefinition(app_version, meta_app=meta_app)
            url = '{0}://{1}/ipa/review/{2}'.format(request.scheme, meta_app.domain,
                                                    CordovaBuilderClass.get_ipa_filename(meta_app_definition))
            return url

        return None


    # ios ipa files
    def ipa_published_url(self, meta_app, app_version):
        # search for a completed AppKitJob
        job = AppKitJobs.objects.filter(meta_app_uuid=meta_app.uuid, app_version=app_version, platform='ios',
                                       job_type='build').first()

        if job and job.job_result and job.job_result.get('success') == True:
            CordovaBuilderClass = self._get_cordova_builder_class()
            meta_app_definition = MetaAppDefinition(app_version, meta_app=meta_app)
            url = '/ipa/published/{0}'.format(CordovaBuilderClass.get_ipa_filename(meta_app_definition))
            return url

        return None

    ###############################################################################################################
    # FILES OF THE BUILT (RELEASE CANDIDATE) APP, that are not present in the preview version
    #- eg glossarized translations
    #- prefixed with _build

    def _build_glossarized_locale_filepath(self, meta_app, language_code, app_version=None):

        filename = 'glossarized.json'

        return os.path.join(self._app_locale_folder(meta_app, language_code, app_version=app_version), filename)



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
    def validate(self, meta_app):
        
        if meta_app.validation_status != 'in_progress':

            meta_app.validation_status = 'in_progress'
            
            # lock the meta_app, it will be unlicked if the validation failed
            meta_app.is_locked = True
            
            meta_app.save()

            result = self.get_empty_result(meta_app, meta_app.current_version)

            # validate theme
            theme_result = self.validate_theme(meta_app)
            result['warnings'] += theme_result['warnings']
            result['errors'] += theme_result['errors']

            # validate the meta_app itself
            app_result = self.validate_app(meta_app)
            result['warnings'] += app_result['warnings']
            result['errors'] += app_result['errors']

            # validate translations
            translations_result = self.validate_translations(meta_app)
            result['warnings'] += translations_result['warnings']
            result['errors'] += translations_result['errors']

            # lock generic contents
            meta_app.lock_generic_contents()

            # iterate over all content and validate it
            feature_links = MetaAppGenericContent.objects.filter(meta_app=meta_app)

            for feature_link in feature_links:

                generic_content = feature_link.generic_content

                validation_method_name = 'validate_%s' % generic_content.__class__.__name__
                if not hasattr(self, validation_method_name):
                    raise NotImplementedError('AppBuilder is missing the validation method %s.' % validation_method_name)

                ValidationMethod = getattr(self, validation_method_name)
                feature_result = ValidationMethod(meta_app, generic_content)

                result['errors'] += feature_result['errors']
                result['warnings'] += feature_result['warnings']

                # validate options
                options_result = self.validate_options(meta_app, generic_content)
                result['warnings'] += options_result['warnings']
                result['errors'] += options_result['errors']


            # store last validation result in db
            validation_result = 'valid'
            
            if result['errors']:
                validation_result = 'errors'
            elif result['warnings']:
                validation_result = 'warnings'

            validation_result_json = {
                'app_version' : meta_app.current_version,
                'started_at' : result['started_at'],
                'errors' : [error.dump() for error in result['errors']],
                'warnings' : [warning.dump() for warning in result['warnings']],
                'finished_at' : int(time.time()),
            }

            meta_app.validation_status = validation_result
            meta_app.last_validation_report = validation_result_json

            #if validation_result == 'errors':
            meta_app.is_locked = False
            meta_app.unlock_generic_contents()

            meta_app.save()

            # dump the logfile to the apps version folder
            log_folder = self._log_folder(meta_app)
            if not os.path.isdir(log_folder):
                os.makedirs(log_folder)
                
            logfile_path = self._last_validation_report_logfile_path(meta_app)
            with open(logfile_path, 'w', encoding='utf-8') as logfile:
                json.dump(validation_result_json, logfile, indent=4, ensure_ascii=False)
                

            return result

        return None
    

    '''
        - validate if the app is not empty
        - validate if LC private if the user runs LCPrivate
    '''
    def validate_app(self, meta_app):
        result = {
            'errors' : [],
            'warnings' :[],
        }

        # the app only makes sense if there is at least one natureguide or one generic form and at least one
        # taxon in the backbone taxonomy

        # check if there is one natureguide or one generic_form
        generic_form_ctype = ContentType.objects.get_for_model(GenericForm)
        nature_guide_ctype = ContentType.objects.get_for_model(NatureGuide)

        exists = MetaAppGenericContent.objects.filter(meta_app=meta_app, content_type__in=[generic_form_ctype,
                                                                             nature_guide_ctype]).exists()

        if not exists:
            error_message = _('Your app needs at least one nature nuide OR one observation form.')
            error = ValidationError(meta_app, meta_app, [error_message])
            result['errors'].append(error)
        
        options_result = self.validate_options(meta_app, meta_app)
        result['warnings'] += options_result['warnings']
        result['errors'] += options_result['errors']

        # validate LCPrivate if set
        lc_private = meta_app.get_global_option('localcosmos_private')

        if lc_private == True:

            lc_private_api_url = meta_app.get_global_option('localcosmos_private_api_url')

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
                    api_error_message = _('Local Cosmos Private API Error: {0}.'.format(e.code))

                except URLError as e:
                    api_error_message = _('Local Cosmos Private API Error: {0}.'.format(e.reason))
                    
                except:
                    error_message = _('Error validating your Local Cosmos Private API.')


                if api_error_message != None:
                    error = ValidationError(meta_app, meta_app, [api_error_message])
                    result['errors'].append(error)

                    
            else:
                error_message = _('You have to provide an API URL if you run Local Cosmos Private.')
                error = ValidationError(meta_app, meta_app, [error_message])
                result['errors'].append(error)
                

        return result
    

    def validate_theme(self, meta_app):

        result = {
            'warnings' : [],
            'errors' : [],
        }

        # first, validate self. this contains images and stuff
        theme = meta_app.get_theme()

        # check for required texts and images
        for image_type, definition in theme.user_content['images'].items():

            if definition.get('required', False) == True:
                image = AppThemeImage(meta_app, image_type)

                if not image.exists():
                    error_message = _('Your app is missing an image: %(image_type)s.') %{'image_type':image_type}
                    error = ValidationError(meta_app, meta_app, [error_message])

                    result['errors'].append(error)

        # validate texts

        # validate legal notice
        legal_notice = meta_app.get_global_option('legal_notice')

        if legal_notice:
            for field_name, field in AppDesignForm.legal_notice_fields.items():

                if field_name not in legal_notice or not legal_notice[field_name]:

                    if field_name != 'phone':

                        error_message = _('[Theme] Your legal notice is missing the field %(field_name)s.') % {
                            'field_name' : field_name }
                        
                        error = ValidationError(meta_app, meta_app, [error_message])

                        result['errors'].append(error)

        else:
            
            error_message = _('[Theme] Your app is missing the legal notice.')
            error = ValidationError(meta_app, meta_app, [error_message])

            result['errors'].append(error)

        return result


    def validate_translations(self, meta_app):

        app_preview_builder = meta_app.get_preview_builder()

        app_preview_builder.update_translation_files(meta_app)

        result = {
            'errors' : [],
            'warnings' : [],
        }
        

        primary_locale = app_preview_builder.get_translation(meta_app, meta_app.primary_language)
        
        required_keys = list(primary_locale.keys())
        
        # add keys for design and texts
        # AND check if the required texts are present in the primary language
        theme = meta_app.get_theme()
        for text_type, definition in theme.user_content['texts'].items():
            required = definition.get('required', True)
            if required:
                required_keys.append(text_type)

                if not text_type in primary_locale:
                    error_message = _('The theme %(theme_name)s requires the text %(text_type)s.') % {
                        'theme_name': theme.name,
                        'text_type' : text_type,
                    }
                    error = ValidationError(meta_app, meta_app, [error_message])
                    result['errors'].append(error)
                    

        for language_code in meta_app.secondary_languages():

            error_message = _('Translation for the language %(language)s is incomplete.') %{'language': language_code}
            
            translations = app_preview_builder.get_translation(meta_app, language_code)

            
            for key in required_keys:
                    
                if key in translations:
                    if len(translations[key]) == 0:
                        error = ValidationError(meta_app, meta_app, [error_message])
                        result['errors'].append(error)
                        break
                        
                else:
                    error = ValidationError(meta_app, meta_app, [error_message])
                    result['errors'].append(error)
                    break

        return result
        

    def validate_options(self, meta_app, generic_content):
        '''
        the default validation is: check all instance_fields of GenericContentOptionsForm
        options can be app specific (MetaAppGenericContent.options) or global (self.global_options)
        '''
        result = {
            'errors' : [],
            'warnings' : [],
        }

        # get the form
        if generic_content._meta.object_name == 'MetaApp':
            options_form_module_path = '%s.forms.%sOptionsForm' % (generic_content._meta.app_label,
                                                                   generic_content._meta.object_name)
        else:
            options_form_module_path = 'app_kit.features.%s.forms.%sOptionsForm' % (
                generic_content._meta.app_label, generic_content._meta.object_name)

        try:
            OptionsForm = import_module(options_form_module_path)
        except:
            print('No options form found at %s' %(options_form_module_path))
            OptionsForm = None

        if OptionsForm:
            
            if hasattr(OptionsForm, 'instance_fields'):

                for field_name in OptionsForm.instance_fields:
                    # check where the option is stored
                    if field_name in OptionsForm.global_options_fields:
                        options = generic_content.global_options

                    else:
                        link = meta_app.get_generic_content_link(generic_content)
                        options = link.options

                    if options:

                        options_entry = options.get(field_name, None)

                        if options_entry:
                            # see GenericContent.make_option_from_instance
                            if options_entry['app_label'] == 'app_kit':
                                model_path = '%s.models.%s' %(options_entry['app_label'], options_entry['model']) 
                            else:
                                model_path = 'app_kit.features.%s.models.%s' %(options_entry['app_label'], options_entry['model']) 
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
                                    link = meta_app.get_generic_content_link(option_instance)

                                    if not link:
                                        message = _('The object %(object_name)s is referenced in the option %(option_name)s but is not linked to this meta_app.') % {'object_name' : option_instance, 'option_name' : field_name}
                                        error = ValidationError(generic_content, generic_content, [message])
                                        result['errors'].append(error)
                                    
        
        return result


    # validation of features
    def validate_BackboneTaxonomy(self, meta_app, backbonetaxonomy):
        '''
        ERRORS:
        - The app needs at least one taxon. Otherwise, e.g. the observation form can not work
        '''
        
        result = {
            'warnings' : [],
            'errors' : [],
        }

        # check if there is at least one taxon
        taxon_count = meta_app.taxon_count()
        if not taxon_count:
            message = _('This app has no taxa.')
            error = ValidationError(meta_app, backbonetaxonomy, [message])
            result['errors'].append(error)
        
        return result


    def validate_NatureGuide(self, meta_app, nature_guide):
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

        result_action = nature_guide.get_option(meta_app, 'result_action')
        if not result_action:
            error_message = _('The nature guide %(name)s has no setting for what happens if the identification has finished.') % {'name':nature_guide.name}                      
            error = ValidationError(nature_guide, nature_guide, [error_message])
            result['errors'].append(error)
            

        nodes = NatureGuidesTaxonTree.objects.filter(nature_guide=nature_guide,
                                                     meta_node__node_type__in=['node'])
        
        for parent in nodes:

            # check for image, except for the start node
            if not parent.meta_node.node_type == 'root':
                image = parent.meta_node.image()
                if not image:
                    warning_message = _('Image is missing.')
                    warning = ValidationWarning(nature_guide, parent, [warning_message])
                    result['warnings'].append(warning)
            
            
            children = parent.children

            parent_errors = ValidationError(nature_guide, parent)
            
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
            image = ng_result.meta_node.image()
            if not image:
                warning_message = _('Image is missing.')
                warning = ValidationWarning(nature_guide, ng_result, [warning_message])
                result['warnings'].append(warning)
        
        return result
    

    def validate_TaxonProfiles(self, meta_app, taxon_profiles):

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
    

    def validate_GenericForm(self, meta_app, generic_form):
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


    def validate_Glossary(self, meta_app, glossary):

        result = {
            'errors' : [],
            'warnings' : [],
        }

        return result


    def validate_Map(self, meta_app, lc_map):

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
    def build(self, meta_app, app_version, dump_unencrypted_content=False):

        # LOCK app an features
        meta_app.is_locked = True
        meta_app.build_status = 'in_progress'

        # update build #
        if not meta_app.build_number:
            meta_app.build_number = 1

        else:
            meta_app.build_number = meta_app.build_number + 1

        meta_app.save()
        meta_app.lock_generic_contents()


        # BEGIN
        self.meta_app = meta_app
        self.app_version = app_version
        self.dump_unencrypted_content = dump_unencrypted_content

        if self.app_version == None:
            self.app_version = meta_app.current_version


        self.logger = self._get_logger(meta_app, 'build')
        self.logger.info('Starting build process')

        success = True
        app_is_valid = True
        
        build_report = self.get_empty_result(meta_app, app_version)
        build_report['result'] = 'success'

        try:
            
            # SECURITY CHECK
            # a released version is locked
            if meta_app.published_version and app_version <= meta_app.published_version:
                raise AppIsLockedError('You cannot build an app version if that version already has been released. Start a new version first')
            

            # check if the app is valid
            validation_result = self.validate(meta_app)

            # do not attempt to build an invalid app
            if not validation_result:
                
                app_is_valid = False
                
                msg = 'Unable to build app  meta_app.id={0}. Validation Failed, because another validation process of this app is in progress'.format(meta_app.id)
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
                msg = 'Unable to build app  meta_app.id={0}. Validation Failed. Errors: {1}'.format(meta_app.id,
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
            self.build_settings = self._get_build_settings(meta_app)

            self.build_features = {}
            
            # create build folder
            build_folder = self._app_root_folder(meta_app, app_version)

            # a build of a specific version always kills the previous build
            self.deletecreate_folder(build_folder)

            # build_common_www has to come first
            self._build_common_www()

            # legal stuff
            self.build_legal_notice()

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
            
            # send email! only if app validation succeeded
            if app_is_valid == True:
                self.send_bugreport_email(meta_app, e)


        # LOCK app an features
        meta_app.is_locked = False
        if success == True:
            meta_app.build_status = 'passing'
        else:

            if app_is_valid == True:
                meta_app.build_status = 'failing'
            else:
                # no build has been performed
                meta_app.build_status = None
                
        build_report['finished_at'] = int(time.time())
        meta_app.last_build_report = build_report
        
        meta_app.save()
        meta_app.unlock_generic_contents()

        return build_report

    
    ###############################################################################################################
    # BUILDING COMMON WWW
    # - www folder with the contents that all app builds (we, android, ios) use
    # - build locales first, glossary second, then the rest
    ###############################################################################################################
    def _build_common_www(self):

        # create the build www folder
        build_common_www_folder = self._app_www_folder(self.meta_app, self.app_version)
        os.makedirs(build_common_www_folder)

        ### BUILDING LOCALES ###
        # copy the locale folder from the preview
        # the translations are already complete
        self.logger.info('Building locales {0}'.format(','.join(self.meta_app.languages())))
        self._build_locales()
        self.logger.info('Done.')

        ### STARTING TO BUILD GENERIC CONTENTS ###

        # build the theme
        self._build_theme()

        # smylink blueprint
        self._symlink_blueprint(self.meta_app, app_version=self.app_version)

        # build the glossary first in case a generic_content_json needs hard coded localized texts
        # instead of i18next keys
        glossary_content_type = ContentType.objects.get_for_model(Glossary)
        # there is only 1 glossary per app
        glossary_link = MetaAppGenericContent.objects.filter(meta_app=self.meta_app,
                                                             content_type=glossary_content_type).first()

        if glossary_link:
            self.logger.info('Building %s %s' % (glossary_link.generic_content.__class__.__name__,
                                                 glossary_link.generic_content.uuid))

            # options are on the link, pass the link
            self._build_Glossary(glossary_link)        
        
        # iterate over all features (except glossary) and create the necessary json files
        generic_content_links = MetaAppGenericContent.objects.filter(meta_app=self.meta_app).exclude(
            content_type=glossary_content_type)

        for link in generic_content_links:
            generic_content = link.generic_content            
            self.logger.info('Building %s %s' % (generic_content.__class__.__name__, generic_content.uuid))

            # options are on the link, pass the link
            build_method = getattr(self, '_build_%s' % generic_content.__class__.__name__)
            build_method(link)
            

        # store settings as json
        app_settings_string = json.dumps(self.build_settings, indent=4, ensure_ascii=False)

        settings_json_filepath = self._app_settings_json_filepath(self.meta_app, self.app_version)
        with open(settings_json_filepath, 'w', encoding='utf-8') as settings_json_file:
            settings_json_file.write(app_settings_string)
        
        # store settings as js    
        app_settings_file = self._app_settings_js_filepath(self.meta_app, self.app_version)
        app_settings_js_string = 'var settings = %s;' % app_settings_string

        with open(app_settings_file, 'w', encoding='utf-8') as f:
            f.write(app_settings_js_string)


        # store api_settings
        api_settings_folder = self._app_api_folder(self.meta_app, self.app_version)
        os.makedirs(api_settings_folder)
        
        api_settings_file = self._app_api_settings_filepath(self.meta_app, self.app_version)
        api_settings = {
            'allow_anonymous_observations' : self.build_settings['OPTIONS'].get('allow_anonymous_observations',
                                                                                False)
        }
        with open(api_settings_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(api_settings, indent=4, ensure_ascii=False))


        # store features as json
        app_features_string = json.dumps(self.build_features, indent=4, ensure_ascii=False)
        app_features_json_file = self._app_features_json_filepath(self.meta_app, self.app_version)
        with open(app_features_json_file, 'w', encoding='utf-8') as f:
            f.write(app_features_string)
        

        # stor features as js
        app_features_file = self._app_features_js_filepath(self.meta_app, self.app_version)
        app_features_js_string = 'var app_features = %s' % app_features_string

        with open(app_features_file, 'w', encoding='utf-8') as f:
            f.write(app_features_js_string)
            
        # save licence registry
        # registry has been filled byt the build_ methods *
        licence_registry_filepath = self._app_licence_registry_filepath(self.meta_app, self.app_version)

        with open(licence_registry_filepath, 'w', encoding='utf-8') as f:
            json.dump(self.licence_registry, f, indent=4)        

    # LEGAL REQUIREMENT: imprint as json in app
    def build_legal_notice(self):

        legal_notice = self.meta_app.get_global_option('legal_notice')

        legal_notice_json_filepath = self._app_legal_notice_json_filepath(self.meta_app, self.app_version)

        with open(legal_notice_json_filepath, 'w', encoding='utf-8') as f:
            json.dump(legal_notice, f, indent=4)
            
    
    def _get_build_settings(self, meta_app):
        theme = meta_app.get_theme()
        
        settings = self._get_empty_settings(meta_app)
        settings["THEME"] = theme.name
        settings["API_URL"] = self._app_api_url(meta_app)
        settings["REMOTEDB_API_URL"] = self._app_road_remotedb_api_url(meta_app)

        settings["OPTIONS"] = {
            "allow_anonymous_observations" : False,
        }

        if meta_app.global_options:
            settings["OPTIONS"].update(meta_app.global_options)

        return settings


    ###############################################################################################################
    # BUILDING LOCALES
    # - translations are already complete
    # - copy tranlsation files into the build/common/www/xyz folder
    # - the structure is locale/{LOCALE}/plain.json
    # - include the theme translation in the locales
    ###############################################################################################################
    def _build_locales(self):
        
        build_locales_folder = self._app_locales_folder(self.meta_app, self.app_version)

        preview_builder = self.meta_app.get_preview_builder()
        
        preview_locales_folder = preview_builder._app_locales_folder(self.meta_app, self.app_version)


        # add the theme localizations to the locale files
        for dir_entry in os.listdir(preview_locales_folder):

            dir_entry_path = os.path.join(preview_locales_folder, dir_entry)

            if os.path.isdir(dir_entry_path):

                for locale_dir_entry in os.listdir(dir_entry_path):

                    locale_filepath = os.path.join(dir_entry_path, locale_dir_entry)

                    with open(locale_filepath, 'r', encoding='utf-8') as f:
                        locale = json.load(f)

                    # add theme locale
                    # in the app, locales have their own dir, in themes, locales are files like "en.json"
                    language_code = dir_entry
                    
                    app_theme = self.meta_app.get_theme()
                    app_theme_locale = app_theme.get_locale(language_code)

                    for key, value in app_theme_locale.items():
                        locale[key] = value


                    # add vernacular names to translation
                    vernacular_names = self._collect_vernacular_names_from_nature_guides(language_code)

                    for key, taxon_dic in vernacular_names.items():

                        if key not in locale:
                            locale[key] = taxon_dic['name']

                    # store the language file
                    destination_folder = os.path.join(build_locales_folder, dir_entry)

                    if not os.path.exists(destination_folder):
                        os.makedirs(destination_folder)

                    destination_filepath = os.path.join(destination_folder, locale_dir_entry)

                    with open(destination_filepath, 'w', encoding='utf-8') as f:
                        json.dump(locale, f, indent=4, ensure_ascii=False)


    def _create_taxon_dic_from_lazy_taxon(self, lazy_taxon, use_gbif):

        taxon_dic = {
            'taxon_source' : lazy_taxon.taxon_source,
            'taxon_latname' : lazy_taxon.taxon_latname,
            'taxon_author' : lazy_taxon.taxon_author,
            
            'name_uuid' : str(lazy_taxon.name_uuid),
            'taxon_nuid' : lazy_taxon.taxon_nuid,
            
            'gbif_nubKey' : None,
        }

        if use_gbif == True:
            gbif_nubKey = self.gbiflib.get_nubKey(lazy_taxon)
            
            if gbif_nubKey :
                taxon_dic['gbif_nubKey'] = gbif_nubKey

        return taxon_dic
        

    # add a localization of nature guide taxa directly to the locale
    # there might be more vernacular names stored inside the taxon dic of backbone taxonomy
    # this one is for quick access in the template
    # first, the primary language is collected
    def _collect_vernacular_names_from_nature_guides(self, language_code):

        if language_code not in self.nature_guides_vernacular_names:

            self.nature_guides_vernacular_names[language_code] = {}

            app_preview_builder = self.meta_app.get_preview_builder()

            content_type = ContentType.objects.get_for_model(NatureGuide)
            app_nature_guides = MetaAppGenericContent.objects.filter(meta_app=self.meta_app, content_type=content_type)


            for feature_link in app_nature_guides:

                nature_guide = feature_link.generic_content

                nodes_with_taxon = NatureGuidesTaxonTree.objects.filter(meta_node__name__isnull=False,
                                            nature_guide=nature_guide, meta_node__taxon_latname__isnull=False)

                for node in nodes_with_taxon:

                    taxon = node.meta_node.taxon

                    key = str(taxon.name_uuid)

                    taxon_dic = self._create_taxon_dic_from_lazy_taxon(taxon, self.use_gbif)

                    vernacular = None
                    
                    if language_code == self.meta_app.primary_language:
                        vernacular = node.meta_node.name
                    else:
                        # look up translation
                        translation = app_preview_builder.get_translation(self.meta_app, language_code)

                        if node.name in translation:
                            vernacular = translation[node.meta_node.name]

                    if vernacular:
                        taxon_dic['name'] = vernacular
                        self.nature_guides_vernacular_names[language_code][key] = taxon_dic

        return self.nature_guides_vernacular_names[language_code]
            

    ###############################################################################################################
    # BUILDING THE THEME
    # - uses symlinks
    # - there might be uploaded images that have to be copied
    # 
    ###############################################################################################################

    def _build_theme(self):

        # symlink the theme
        self.set_theme(self.meta_app, app_version=self.app_version)

        build_theme_images_folder = self._app_theme_user_content_images_folder(self.meta_app,
                                                                              app_version=self.app_version)

        # copy the theme images
        preview_builder = self.meta_app.get_preview_builder()

        preview_theme_images_folder = preview_builder._app_theme_user_content_images_folder(self.meta_app,
                                                                                app_version=self.app_version)


        shutil.copytree(preview_theme_images_folder, build_theme_images_folder)

        theme_images = {}
        images_folder = self._build_relative_app_theme_images_path(self.meta_app.theme)
        
        # iterate over all image files and create a dict of the files available
        for file in os.listdir(build_theme_images_folder):
            filename = os.fsdecode(file)

            base = os.path.basename(filename)

            image_type = os.path.splitext(base)[0]
            image_path = os.path.join(images_folder, filename)

            theme_images[image_type] = image_path
            

        theme_images_file = self._app_app_theme_images_js_filepath(self.meta_app, app_version=self.app_version)

        # store settings as js    
        theme_images_string = json.dumps(theme_images, indent=4, ensure_ascii=False)
        theme_images_js_string = 'var theme_images = {0};'.format(theme_images_string)


        with open(theme_images_file, 'w', encoding='utf-8') as f:
            f.write(theme_images_js_string)

        # app theme texts are contained in the locale files

        # add image licences


    ###############################################################################################################
    # BUILDING GENERIC CONTENTS
    # - use JSONBuilder classes
    # - dump the json to build/common/www/xyz
    # - fill build_featres{} which will be dumped as www/features.js
    ###############################################################################################################

    def _get_json_builder_class(self, generic_content):
        
        builder_version = getattr(self, '%s_builder_version' % generic_content.__class__.__name__)
        builder_class_name = '%sJSONBuilder' % generic_content.__class__.__name__
        builder_module_path = 'app_kit.appbuilders.JSONBuilders.%s.%s.%s.%s' % (
            generic_content.__class__.__name__, builder_version, builder_class_name, builder_class_name)
        
        JSONBuilderClass = import_module(builder_module_path)
        
        return JSONBuilderClass


    # feature entry of a generic content
    # build the entry for features.js which is used by the app to recognize which features are installed
    # and where to find them on the disk
    def _get_feature_entry(self, generic_content, **kwargs):

        generic_content_type = kwargs.get('generic_content_type', generic_content.__class__.__name__)

        feature_entry = {
            'generic_content_type' : generic_content_type,
            'uuid' : str(generic_content.uuid),
            'name' : {},
            'version' : generic_content.current_version,
        }

        # add localized names directly in the feature.js
        for language_code in self.meta_app.languages():
            localized_name = self.get_localized(self.meta_app, generic_content.name, language_code,
                                                app_version=self.app_version)
            
            feature_entry['name'][language_code] = localized_name


        # complete the settings_entry
        # one file per form, absolute path in webapp features.js
        relative_generic_content_folder =  self._build_relative_generic_content_path(generic_content)

        content_filename = '%s.content' % str(generic_content.uuid)
        
        relative_generic_content_filepath = os.path.join(relative_generic_content_folder, content_filename)

        feature_entry['path'] = relative_generic_content_filepath

        return feature_entry

    
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

        filename_identifier = str(generic_content.uuid)

        # generic_content_json has options and global_options
        fallback_options = kwargs.get('fallback_options', {})
        for key, value in fallback_options.items():

            if not key in generic_content_json['options']:
                generic_content_json['options'][key] = value

        generic_content_type = kwargs.get('generic_content_type', generic_content.__class__.__name__)

        # first make the folder
        absolute_generic_content_folder = self._build_absolute_generic_content_path(self.meta_app, self.app_version,
                                                                                    generic_content, **kwargs)

        # create the content folder
        if not os.path.isdir(absolute_generic_content_folder):
            os.makedirs(absolute_generic_content_folder)
        

        filename = '%s.content' % filename_identifier
        
        content_dump_file = os.path.join(absolute_generic_content_folder, filename)            
            
        with open(content_dump_file, 'w', encoding='utf-8') as f:
            # base64 encode
            string = json.dumps(generic_content_json)
            encoded = base64.b64encode(string.encode())
            f.write(encoded.decode())


        if self.dump_unencrypted_content:

            filename = '%s.json' % filename_identifier
            content_dump_file = os.path.join(absolute_generic_content_folder, filename)            
            
            with open(content_dump_file, 'w', encoding='utf-8') as f:
                json.dump(generic_content_json, f, indent=4, ensure_ascii=False)


        #get the json entry for features.js
        feature_entry = self._get_feature_entry(generic_content, generic_content_type=generic_content_type)

        if only_one_allowed == True:
            self.build_features[generic_content_type] = feature_entry

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


            self.build_features[generic_content_type]['list'].append(feature_entry)
            self.build_features[generic_content_type]['lookup'][filename_identifier] = feature_entry['path']



    ###############################################################################################################
    # BACKBONE TAXONOMY
    # - dump taxonomic trees as json
    # - files for quick searching in alphabet/AA.json and vernacular/en.json
    
    def _build_BackboneTaxonomy(self, app_generic_content):

        backbone_taxonomy = app_generic_content.generic_content

        primary_language = self.meta_app.primary_language

        JSONBuilderClass = self._get_json_builder_class(backbone_taxonomy)
        
        jsonbuilder = JSONBuilderClass(self, app_generic_content)
        backbone_taxonomy_json = jsonbuilder.build()

        # relative paths are used in the features.js file
        relative_generic_content_path = self._build_relative_generic_content_path(backbone_taxonomy)
        alphabet_relative_path = os.path.join(relative_generic_content_path, 'alphabet')
        vernacular_relative_path = os.path.join(relative_generic_content_path, 'vernacular')

        feature_entry = self._get_feature_entry(backbone_taxonomy)

        feature_entry.update({
            'alphabet' : alphabet_relative_path, # a folder
            'vernacular' : {}, # one file per language
        })


        # ALPHABET
        absolute_feature_path = self._build_absolute_generic_content_path(self.meta_app,
                                                                          self.app_version, backbone_taxonomy)

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
        feature_path = self._build_absolute_generic_content_path(self.meta_app, self.app_version, backbone_taxonomy)
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

        JSONBuilderClass = self._get_json_builder_class(taxon_profiles)
        jsonbuilder = JSONBuilderClass(self, app_generic_content)
        
        generic_content_type = taxon_profiles.__class__.__name__


        # add profiles to settings the default way
        feature_entry = self._get_feature_entry(taxon_profiles)
        del feature_entry['path']


        self.build_features[generic_content_type] = feature_entry

        # add the profiles directly to the features.js, instead of _add_generic_content_to_app
        taxon_profiles_json = jsonbuilder.build()

        for key, value in taxon_profiles_json.items():
            if key not in self.build_features[generic_content_type].items():
                self.build_features[generic_content_type][key] = value


        app_relative_taxonprofiles_folder =  self._build_relative_generic_content_path(taxon_profiles)
        self.build_features[generic_content_type]['files'] = app_relative_taxonprofiles_folder
        

        # paths for storing taxon profiles
        app_absolute_taxonprofiles_path = self._build_absolute_generic_content_path(self.meta_app, self.app_version,
                                                                                    taxon_profiles)

        if not os.path.isdir(app_absolute_taxonprofiles_path):
            os.makedirs(app_absolute_taxonprofiles_path)


        for profile_taxon in taxon_profiles.collected_taxa():
            
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


    ###############################################################################################################
    # GENERIC FORMS
    # - one file for all languages
    
    def _build_GenericForm(self, app_generic_content):

        generic_form = app_generic_content.generic_content

        JSONBuilderClass = self._get_json_builder_class(generic_form)

        # only build one file for all languages
        jsonbuilder = JSONBuilderClass(self, app_generic_content)

        generic_form_json = jsonbuilder.build()

        self._add_generic_content_to_app(generic_form, generic_form_json)


    ###############################################################################################################
    # NATURE GUIDES
    # - one file for all languages ???

    def _build_NatureGuide(self, app_generic_content):

        nature_guide = app_generic_content.generic_content

        JSONBuilderClass = self._get_json_builder_class(nature_guide)

        jsonbuilder = JSONBuilderClass(self, app_generic_content)

        nature_guide_json = jsonbuilder.build()

        self._add_generic_content_to_app(nature_guide, nature_guide_json)


    ###############################################################################################################
    # GLOSSARY
    # - there is only one glossary with keys for translation

    def _build_Glossary(self, app_generic_content):

        glossary = app_generic_content.generic_content

        JSONBuilderClass = self._get_json_builder_class(glossary)
        jsonbuilder = JSONBuilderClass(self, app_generic_content)
        
        glossary_json = jsonbuilder.build()

        self._add_generic_content_to_app(glossary, glossary_json, only_one_allowed=True)
        

        for language_code in self.meta_app.languages():
            # create a glossarized version of te language file and save it as {language}_glossarized.json
            glossarized_locale = jsonbuilder.glossarize_language_file(glossary, glossary_json, language_code)

            # store localized glossary file in the same folder as the language file
            glossarized_locale_filepath = self._build_glossarized_locale_filepath(self.meta_app, language_code,
                                                                                  app_version=self.app_version)


            with open(glossarized_locale_filepath, 'w', encoding='utf-8') as f:
                json.dump(glossarized_locale, f, indent=4, ensure_ascii=False)


    ###############################################################################################################
    # MAP
    # - maps are optional

    def _build_Map(self, app_generic_content):

        lc_map = app_generic_content.generic_content

        JSONBuilderClass = self._get_json_builder_class(lc_map)
        jsonbuilder = JSONBuilderClass(self, app_generic_content)
        
        map_json = jsonbuilder.build()

        self._add_generic_content_to_app(lc_map, map_json)


    ###############################################################################################################
    # BUILDING CONTENT IMAGES
    # - images of generic contents/features
    # - use proper image resizing
    # 
    ###############################################################################################################

    def save_content_image(self, content_image, size=None):

        if size == None:
            size = (500,500)

        image_file = content_image.image_store.source_image
        
        absolute_content_images_root = self._build_absolute_content_images_path(self.meta_app,
                                                                                app_version=self.app_version)

        if not os.path.isdir(absolute_content_images_root):
            os.makedirs(absolute_content_images_root)


        # open the image, apply crop parameters and resize
        crop_parameters = json.loads(content_image.crop_parameters)

        original = Image.open(image_file.path)

        right = crop_parameters['x'] + crop_parameters['width']
        bottom = crop_parameters['y'] + crop_parameters['height']
        box = (crop_parameters['x'], crop_parameters['y'], right, bottom)
        cropped = original.crop(box)

        # resize cropped image, default is maxwidth: 500 x  maxheight: 500 pixels
        #cropped.thumbnail(size, Image.ANTIALIAS)
        image_width, image_height = cropped.size

        if image_width != size[0] or image_height != size[1]:
            w_diff = image_width - size[0]
            h_diff = image_height - size[1]

            if w_diff >= h_diff:
                output_width = size[0]
                output_height = image_height * (size[0]/image_width)

            else:
                output_height = size[1]
                output_width = image_width * (size[1]/image_height)

            output_size = (output_width, output_height)
            cropped.thumbnail(output_size, Image.ANTIALIAS)

        filename = '{0}.{1}'.format(hashlib.md5(cropped.tobytes()).hexdigest(), original.format)

        relative_image_filepath = os.path.join(self._build_relative_content_images_path(), filename)
        absolute_image_filepath = os.path.join(absolute_content_images_root, filename)

        if not os.path.isfile(absolute_image_filepath):
            cropped.save(absolute_image_filepath, original.format)


        # add image to licence_registry
        licence = content_image.image_store.licences.first()
        if licence:
            content_licence = licence.content_licence().as_dict()

            registry_entry = {
                'creator_name' : licence.creator_name,
                'creator_link' : licence.creator_link,
                'source_link' : licence.source_link,
                'licence' : content_licence,
            }
            
            self.licence_registry['licences'][relative_image_filepath] = registry_entry

        return relative_image_filepath

    ###############################################################################################################
    # BUILDING WEBAPP
    # 
    ###############################################################################################################
    def _build_webapp(self):

        webapp_www_folder = self._build_webapp_www_folder(self.meta_app, app_version=self.app_version)

        if not os.path.isdir(webapp_www_folder):
            os.makedirs(webapp_www_folder)

        # symlinks to webapp
        blueprint_webapp_www_folder = self._builder_blueprint_webapp_www_folder()
        
        for content in os.listdir(blueprint_webapp_www_folder):
            source_path = os.path.join(blueprint_webapp_www_folder, content)
            dest_path = os.path.join(webapp_www_folder, content)
            os.symlink(source_path, dest_path)

        # symlink common www
        common_www_folder = self._app_www_folder(self.meta_app, app_version = self.app_version)
        for content in os.listdir(common_www_folder):
            source_path = os.path.join(common_www_folder, content)
            dest_path = os.path.join(webapp_www_folder, content)
            os.symlink(source_path, dest_path)


        # review folder
        review_folder = self._built_app_review_served_folder(self.meta_app)
        self.deletecreate_folder(review_folder)
        review_served_www = self._built_app_review_www_folder(self.meta_app)
        os.symlink(webapp_www_folder, review_served_www)

        # set localcosmos_server.app.review_version_path
        self.meta_app.app.review_version_path = review_served_www
        self.meta_app.app.save()

        # if lc private is set, serve the webapp zip
        # create a zipfile of the webapp folder
        lc_private = self.meta_app.get_global_option('localcosmos_private')
        if lc_private == True:
            
            zip_filepath = self._build_pwa_zip_filepath(self.meta_app, app_version=self.app_version)
            webapp_folder = self._build_webapp_folder(self.meta_app, app_version=self.app_version)

            with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as www_zip:

                for root, dirs, files in os.walk(webapp_www_folder, followlinks=True):

                    for filename in files:
                        # Create the full filepath by using os module.
                        app_file_path = os.path.join(root, filename)
                        arcname = app_file_path.split(webapp_folder)[-1]
                        www_zip.write(app_file_path, arcname=arcname)

            # serve the zipfile via symlink
            self.serve_preview_pwa(self.meta_app, self.app_version, zip_filepath)

    ##############################################################################################################
    # serving webapp zip files - pwa
    def _build_pwa_zip_filepath(self, meta_app, app_version):
        build_webapp_folder = self._build_webapp_folder(meta_app, app_version)
        return os.path.join(build_webapp_folder, self._pwa_zipfile_name(meta_app))
        
    def _pwa_zipfile_name(self, meta_app):
        zipfile_name = '{0}.zip'.format(meta_app.name)
        return zipfile_name

    def _served_review_pwa_folder(self, meta_app):
        return os.path.join(self._pwa_folder(meta_app), 'review')

    def _served_published_pwa_folder(self, meta_app):
        return os.path.join(self._pwa_folder(meta_app), 'published')
        
    def _served_review_pwa_filepath(self, meta_app, app_version):
        return os.path.join(self._served_review_pwa_folder(meta_app), self._pwa_zipfile_name(meta_app))

    def _served_published_pwa_filepath(self, meta_app, app_version):
        return os.path.join(self._served_published_pwa_folder(meta_app), self._pwa_zipfile_name(meta_app))

    def serve_preview_pwa(self, meta_app, app_version, pwa_source):
        # symlink the ipa file
        pwa_review_folder = self._served_review_pwa_folder(meta_app)
        self.deletecreate_folder(pwa_review_folder)

        pwa_dest = self._served_review_pwa_filepath(meta_app, app_version)
        os.symlink(pwa_source, pwa_dest)


    ###############################################################################################################
    # BUILDING iOS
    # - use BuildJobs, Mac queries BuildJobs and does Jobs
    # - tha actual build is done on a MAC
    ###############################################################################################################
        
    def _create_ios_build_job(self):

        # create a zipfile for cordova
        cordova_builder = self._get_cordova_builder(self.meta_app, self.app_version)
        
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
        apk_filename = CordovaBuilderClass.get_ipa_filename(meta_app_definition)
        return os.path.join(self._served_review_ipa_folder(meta_app), apk_filename)

    def _served_published_ipa_filepath(self, meta_app, app_version):
        meta_app_definition = MetaAppDefinition(app_version, meta_app=meta_app)
        CordovaBuilderClass = self._get_cordova_builder_class()
        apk_filename = CordovaBuilderClass.get_ipa_filename(meta_app_definition)
        return os.path.join(self._served_published_ipa_folder(meta_app), apk_filename)


    def serve_preview_ipa(self, meta_app, app_version, ipa_source):
        # symlink the ipa file
        ipa_review_folder = self._served_review_ipa_folder(meta_app)
        self.deletecreate_folder(ipa_review_folder)

        ipa_dest = self._served_review_ipa_filepath(meta_app, app_version)
        os.symlink(ipa_source, ipa_dest)

        # logger not available
        
        

    ###############################################################################################################
    # BUILDING ANDROID
    # - use CordovaAppBuilder
    ###############################################################################################################
    def _get_cordova_builder(self, meta_app, app_version):
            
        CordovaBuilderClass = self._get_cordova_builder_class()

        meta_app_definition = MetaAppDefinition(app_version, meta_app=meta_app)

        app_root_folder = self._app_root_folder(meta_app, app_version=app_version)
        common_www_folder = self._app_www_folder(meta_app, app_version=app_version)
        
        cordova_builder = CordovaBuilderClass(meta_app_definition, app_root_folder, common_www_folder)

        return cordova_builder
        
    
    def _build_android(self):

        keystore_path = self.get_keystore_path()
        
        cordova_builder = self._get_cordova_builder(self.meta_app, self.app_version)
        
        apk_source = cordova_builder.build_android(keystore_path, settings.APP_KIT_ANDROID_KEYSTORE_PASS,
                                                   settings.APP_KIT_ANDROID_KEY_PASS)

        # symlink the apk into a browsable location
        apk_review_folder = self._served_review_apk_folder(self.meta_app)
        self.deletecreate_folder(apk_review_folder)

        
        apk_dest = self._served_review_apk_filepath(self.meta_app, self.app_version)
        os.symlink(apk_source, apk_dest)

        self.logger.info('Successfully built Android')


    ##############################################################################################################
    # ANDROID SIGNING
    # 
    def get_keystore_path(self):
        keystore_path = os.path.join(self._certificates_folder, self.android_keystore_name)
        return keystore_path


    ##############################################################################################################
    # serving apks

    def _served_review_apk_folder(self, meta_app):
        return os.path.join(self._apk_folder(meta_app), 'review')

    def _served_published_apk_folder(self, meta_app):
        return os.path.join(self._apk_folder(meta_app), 'published')
        
    def _served_review_apk_filepath(self, meta_app, app_version):
        meta_app_definition = MetaAppDefinition(app_version, meta_app=meta_app)
        CordovaBuilderClass = self._get_cordova_builder_class()
        apk_filename = CordovaBuilderClass.get_apk_filename(meta_app_definition)
        return os.path.join(self._served_review_apk_folder(meta_app), apk_filename)

    def _served_published_apk_filepath(self, meta_app, app_version):
        meta_app_definition = MetaAppDefinition(app_version, meta_app=meta_app)
        CordovaBuilderClass = self._get_cordova_builder_class()
        apk_filename = CordovaBuilderClass.get_apk_filename(meta_app_definition)
        return os.path.join(self._served_published_apk_folder(meta_app), apk_filename)
    

    ##############################################################################################################
    # RELEASING
    # - copy build contents to release folder
    # - upload to app stores
    ##############################################################################################################

    def release(self, meta_app, app_version):

        release_report = self.get_empty_result(meta_app, app_version)

        release_report['result'] =  'success'

        self.logger = self._get_logger(meta_app, 'release')
        self.logger.info('Starting release process')

        try:
            self._release_webapp(meta_app, app_version)

            if 'android' in meta_app.build_settings['platforms']:
                self._release_android(meta_app, app_version)

            if 'ios' in settings.APP_KIT_SUPPORTED_PLATFORMS and 'ios' in meta_app.build_settings['platforms']:
                self._release_ios(meta_app, app_version)

            # app version bump
            meta_app.save(publish=True)

        except Exception as e:
            success = False
            self.logger.error(e, exc_info=True)

            release_report['result'] = 'failure'
            
            # send email!
            self.send_bugreport_email(meta_app, e)

        release_report['finished_at'] = int(time.time())
        meta_app.last_release_report = release_report
        meta_app.save()

        return release_report

    
    def _release_webapp(self, meta_app, app_version):

        published_folder = self._published_app_served_folder(meta_app)

        self.deletecreate_folder(published_folder)

        build_www = self._build_webapp_www_folder(meta_app, app_version=app_version)

        served_www = self._published_webapp_www_folder(meta_app)
        
        os.symlink(build_www, served_www)

        # remove the review folder
        review_folder = self._built_app_review_served_folder(meta_app)
        if os.path.isdir(review_folder):
            shutil.rmtree(review_folder)

        # update app.url, if hosted on LC
        localcosmos_private = meta_app.get_global_option('localcosmos_private')

        if localcosmos_private == True:
            # symlink the pwa zip to a browsable location
            pwa_release_folder = self._served_published_pwa_folder(meta_app)
            self.deletecreate_folder(pwa_release_folder)

            pwa_source = self._build_pwa_zip_filepath(meta_app, app_version=app_version)
            pwa_dest = self._served_published_pwa_filepath(meta_app, app_version)
            os.symlink(pwa_source, pwa_dest)

        else:
            # set the url of meta_app.app
            url = 'https://{0}.localcosmos.org/'.format(meta_app.app.uid)
            meta_app.app.url = url
            meta_app.app.save()



    ##############################################################################################################
    # release request email

    def _send_release_request_email(self, meta_app, app_version, platform):

        tenant = meta_app.tenant
        tenant_admin_emails = tenant.get_admin_emails()
            
        title = '[{0}] {1} release requested'.format(meta_app.name, platform)
        
        text_content = 'App name: {0}, app uuid: {1}, app uid: {2}, version: {3}, platform: {4}, Admins: {5}'.format(
            meta_app.name, str(meta_app.uuid), meta_app.app.uid, app_version, platform,
            ','.join(tenant_admin_emails))
            
        self.send_admin_email(title, text_content)
        
    ##############################################################################################################
    # RELEASE ANDROID APK
    # - delete review apk, symlink released apk
    # - [TODO:] auto-upload to the app store via fastlane.tools
    def _release_android(self, meta_app, app_version):

        self.logger.info('Releasing Android')

        cordova_builder = self._get_cordova_builder(meta_app, app_version)

        # remove review dir
        apk_review_folder = self._served_review_apk_folder(meta_app)
        if os.path.isdir(apk_review_folder):
            shutil.rmtree(apk_review_folder)

        # symlink the apk to a browsable location
        apk_release_folder = self._served_published_apk_folder(meta_app)
        self.deletecreate_folder(apk_release_folder)

        apk_source = cordova_builder.get_apk_filepath()
        apk_dest = self._served_published_apk_filepath(meta_app, app_version)
        os.symlink(apk_source, apk_dest)

        # FASTLANE APPSTORE RELEASE

        self.logger.info('Successfully released Android')

        # until fastlane is implemented: send an email
        if meta_app.build_settings['distribution'] == 'appstores':
            
            self.logger.info('Sending release email for Android')

            self._send_release_request_email(meta_app, app_version, 'Android')


    ##############################################################################################################
    # RELEASE iOS IPA
    # - delete review apk, symlink released ipa
    # - [TODO:] auto-upload to the app store via fastlane.tools
    def _release_ios(self, meta_app, app_version):

        self.logger.info('Releasing iOS')

        cordova_builder = self._get_cordova_builder(meta_app, app_version)

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

            self._send_release_request_email(meta_app, app_version, 'iOS')


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
        
        
        
