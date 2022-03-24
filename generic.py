from django.db import models
from django.apps import apps

from django.urls import reverse

from django.conf import settings

from django.contrib.contenttypes.models import ContentType

from django.utils.translation import gettext_lazy as _
from localcosmos_server.slugifier import create_unique_slug
from django.utils import timezone

import uuid, os

from .utils import import_module

from taxonomy.lazy import LazyTaxon

from PIL import Image


"""
    Linking Content to taxa: Forms, Fields
    - this model is used for taxonomic restrictions allowing multiple taxa
    - if only one taxon is used, use subclassing TaxonRequiredModel
"""

"""
    Certain App Contents can have taxonomic restrictions, like Form Fields or Forms
"""
from localcosmos_server.models import TaxonomicRestrictionBase
class AppContentTaxonomicRestriction(TaxonomicRestrictionBase):

    LazyTaxonClass = LazyTaxon


class GenericContentManager(models.Manager):

    def create(self, name, primary_language, **extra_fields):

        instance = self.model(**extra_fields)
        instance.primary_language = primary_language
        instance.name = name

        instance.save()
        
        return instance



class GenericContentMethodsMixin:
    
    def get_global_option(self, option):
        
        if self.global_options and option in self.global_options:
            return self.global_options[option]

        return None
        
    # app specific options
    def get_option(self, meta_app, option):
        app_generic_content = meta_app.get_generic_content_link(self)
        
        if app_generic_content.options and option in app_generic_content.options:
            return app_generic_content.options[option]

        return None

    def options(self, meta_app):
        app_generic_content = meta_app.get_generic_content_link(self)
        if app_generic_content and app_generic_content.options:
            return app_generic_content.options
        return {}


    def make_option_from_instance(self, instance):

        option = {
            'app_label' : instance._meta.app_label,
            'model' : instance.__class__.__name__,
            'uuid' : str(instance.uuid),
            'id' : instance.id,
            'action' : instance.__class__.__name__,
        }

        return option
    

    def taxa(self):
        raise NotImplementedError('Generic Content do need a customized taxa method')

    
    def get_primary_localization(self, meta_app=None):
        raise NotImplementedError('Generic Content do need a get_primary_localization method')


    def manage_url(self):
        return 'manage_{0}'.format(self.__class__.__name__.lower())

    def verbose_name(self):
        return self._meta.verbose_name

    @classmethod
    def feature_type(self):
        # .models strips taxon_profiles.models wrong
        return self.__module__.rstrip('models').rstrip('.')


    def media_path(self):
        path = '/'.join([self.feature_type(), str(self.uuid)])
        return path


    def lock(self, reason):
        self.is_locked = True

        if not self.messages:
            self.messages = {}
        self.messages['lock_reason'] = reason
        
        self.save()

    def unlock(self):
        
        self.is_locked = False

        if 'lock_reason' in self.messages:
            del self.messages['lock_reason']
        
        self.save()
    
'''
    Abstract Content Model
    - manages current_version and published_version
'''
class GenericContent(GenericContentMethodsMixin, models.Model):

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    primary_language = models.CharField(max_length=15)
    
    name = models.CharField(max_length=255, null=True)
    
    published_version = models.IntegerField(null=True)
    current_version = models.IntegerField(default=1)
    
    is_locked = models.BooleanField(default=False) # lock content if an app is being built

    # eg for lock_reason, zip_import status messages
    messages = models.JSONField(null=True)

    # these options are tied to the generic content and not app specific
    # for example, this applies to taxonomic filters of a nature guide
    # app-specific options are stored in MetaAppGenericContent.options
    global_options = models.JSONField(null=True)

    objects = GenericContentManager()

    zip_import_supported = False
    zip_import_class = None


    def __str__(self):
        return self.name

    class Meta:
        abstract = True



'''
    Class to manage image Localizations during translation
    - localized images have to be saved in the "locales" folder of the app
    - localizations are saved during translation
    - localizations somehow have to persist across app versions
'''
MAX_IMAGE_DIMENSIONS = [700,700]

class LocalizeableImage:

    def __init__(self, image_instance, model_field=None):
        self.image_instance = image_instance

        if model_field == None:
            model_field = getattr(image_instance, 'image_field', 'image')

        if '.' in model_field:

            self.image_file = image_instance
            
            path = model_field.split('.')

            for part in path:
                self.image_file = getattr(self.image_file, part)
                
        else:
            self.image_file = getattr(image_instance, model_field)

    
    @classmethod
    def get_relative_localized_image_folder(cls, language_code):
        path = 'locales/{0}/images/'.format(language_code)
        return path


    def get_localized_filename(self, language_code):

        content_type = ContentType.objects.get_for_model(self.image_instance)

        original_filename, file_extension = os.path.splitext(self.image_file.name)
        
        localized_filename = 'localized_image_{0}_{1}_{2}{3}'.format(content_type.id, self.image_instance.id,
                                                                 language_code, file_extension)

        return localized_filename


    # add _{language_code} to filename
    @classmethod
    def localize_language_independant_filename(cls, filename, language_code):

        parts = filename.split('.')
        parts[-2] = '{0}_{1}'.format(parts[-2], language_code)

        localized_filename = '.'.join(parts)

        return localized_filename


    def get_language_independant_filename(self):

        content_type = ContentType.objects.get_for_model(self.image_instance)

        original_filename, file_extension = os.path.splitext(self.image_file.name)
        
        filename = 'localized_image_{0}_{1}{2}'.format(content_type.id, self.image_instance.id,
                                                                 file_extension)

        return filename

        

    def get_relative_localized_image_path(self, language_code):
        
        folder = self.get_relative_localized_image_folder(language_code)
        
        localized_filename = self.get_localized_filename(language_code)

        path = os.path.join(folder, localized_filename)

        return path
    

    def get_locale(self, app_www_folder, language_code):
        relative_path = self.get_relative_localized_image_path(language_code)
        full_path = os.path.join(app_www_folder, relative_path)

        if os.path.isfile(full_path):
            return full_path

        return None
    

    def save_locale(self, app_www_folder, image_file, language_code):

        relative_folder = self.get_relative_localized_image_folder(language_code)
        full_folder_path = os.path.join(app_www_folder, relative_folder)

        if not os.path.isdir(full_folder_path):
            os.makedirs(full_folder_path)

        relative_image_path = self.get_relative_localized_image_path(language_code)
        full_localized_image_path = os.path.join(app_www_folder, relative_image_path)

        if os.path.isfile(full_localized_image_path):
            os.remove(full_localized_image_path)

        image_file.seek(0)
        localized_image = Image.open(image_file)
        localized_image.thumbnail(MAX_IMAGE_DIMENSIONS, Image.BICUBIC)
        localized_image.save(full_localized_image_path, localized_image.format)


    def url(self, language_code):
        return self.get_relative_localized_image_path(language_code)


    # app served www folder is provided by preview builder
    @classmethod
    def preview_url(cls, localized_filename, language_code):

        folder = cls.get_relative_localized_image_folder(language_code)
        path = os.path.join(folder, localized_filename)

        return path
        
        
    
