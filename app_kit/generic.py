from django.db import models

from django.contrib.contenttypes.models import ContentType

from django.utils.translation import gettext_lazy as _

import uuid, os

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
from localcosmos_server.models import TaxonomicRestrictionBase, TaxonomicRestrictionManager
class AppContentTaxonomicRestriction(TaxonomicRestrictionBase):

    LazyTaxonClass = LazyTaxon

    objects = TaxonomicRestrictionManager


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
        locale = {}
        locale[self.name] = self.name

        if self.global_options and 'description' in self.global_options:
            description = self.get_global_option('description')
            if description and len(description) > 0:
                locale['description'] = description

        return locale

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


    def check_version(self):
        if self.published_version == self.current_version:
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

    def save(self, *args, **kwargs):
        set_published_version = kwargs.pop('set_published_version', False)
        increment_version = kwargs.pop('increment_version', True)

        if set_published_version == True:
            self.published_version = self.current_version

        elif self.published_version == self.current_version and increment_version == True:
            self.current_version += 1
        
        super().save(*args, **kwargs)


    def __str__(self):
        return self.name

    class Meta:
        abstract = True


PUBLICATION_STATUS = (
    ('draft', _('draft')),
    ('publish', _('publish')),
)