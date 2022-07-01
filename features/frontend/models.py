from django.db import models
from django.conf import settings

from django.contrib.contenttypes.models import ContentType

from app_kit.generic import GenericContent
from app_kit.models import ContentImageMixin, MetaAppGenericContent, SingleFeatureMixin

from django.utils.translation import gettext_lazy as _

from taxonomy.lazy import LazyTaxonList


# Frontend images are ContentImages
class Frontend(SingleFeatureMixin, ContentImageMixin, GenericContent):

    frontend_name = models.CharField(max_length=355, default=settings.APP_KIT_DEFAULT_FRONTEND)

    # if modified_at > built_at, rebuild preview app
    modified_at = models.DateTimeField(auto_now=True)
    preview_built_at = models.DateTimeField(null=True)

    allow_content_image_features = False

    class Meta:
        verbose_name = _('Frontend')
        verbose_name_plural = _('Frontends')


    def get_primary_localization(self, meta_app=None):

        locale = {
            '_meta' : {}
        }

        locale[self.name] = self.name

        frontend_texts = FrontendText.objects.filter(frontend=self, frontend_name=self.frontend_name)

        for text in frontend_texts:
            locale[text.text] = text.text

            locale['_meta'][text.text] = {
                'layoutability' : 'layoutable-full',
                'type' : 'html',
            } 
            
        return locale


    def taxa(self):
        return LazyTaxonList()

    def higher_taxa(self):
        return LazyTaxonList()


    def get_settings(self):

        app_builder = self.meta_app.get_app_builder()

        frontend_settings = app_builder._get_frontend_settings()

        return frontend_settings



    def get_content_image_restrictions(self, namespaced_image_type='image'):

        frontend_settings = self.get_settings()

        # image_type for frontends is namespaces like this:  FRONTEND_NAME:image_type , eg Flat:background
        image_type_parts = namespaced_image_type.split(':')
        image_type = image_type_parts[-1]

        image_definition = frontend_settings['user_content']['images'][image_type]

        restrictions = image_definition.get('restrictions', {})

        return restrictions

    def texts(self):
        return FrontendText.objects.filter(frontend=self, frontend_name=self.frontend_name)


    @property
    def namespace_prefix(self):
        prefix = '{0}:'.format(self.frontend_name)
        return prefix

    def get_namespaced_image_type(self, image_type):

        namespaced_image_type = image_type

        if not image_type.startswith(self.namespace_prefix):

            namespaced_image_type = '{0}{1}'.format(self.namespace_prefix, image_type)

        return namespaced_image_type

    # frontend images are always namespaces
    def image(self, image_type):
        content_image_type = self.get_namespaced_image_type(image_type)

        content_image = super().image(content_image_type)

        return content_image



FeatureModel = Frontend



class FrontendText(models.Model):
    
    frontend = models.ForeignKey(Frontend, on_delete=models.CASCADE)

    # texts and images are bound to a frontend_name. The user can change Frontend.frontend_name, and the Textx might be incompatible
    # displayed texts and images have to match Frontend.frontend_name at all times
    frontend_name = models.CharField(max_length=355, default=settings.APP_KIT_DEFAULT_FRONTEND)

    identifier = models.CharField(max_length=355)

    text = models.TextField()

    class Meta:
        unique_together=('frontend', 'identifier')