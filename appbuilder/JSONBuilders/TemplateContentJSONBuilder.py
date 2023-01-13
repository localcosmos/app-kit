from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder

from localcosmos_server.template_content.models import PUBLISHED_IMAGE_TYPE_PREFIX
from localcosmos_server.template_content.api.serializers import LocalizedTemplateContentSerializer, ContentLicenceSerializer

'''
     save template_contents_json to features/TemplateContent/app_uuid.json
'''
class TemplateContentJSONBuilder(JSONBuilder):

    def __init__(self, app_release_builder, meta_app):

        self.app_release_builder = app_release_builder
        self.meta_app = meta_app


    def build(self):

        template_contents_json = self._build_common_json()

        return template_contents_json

    # language independant
    def _build_common_json(self):
        
        generic_content_json = {
            'uuid' : str(self.meta_app.app.uuid),
            'version' : 1,
            'options' : {},
            'globalOptions' : {},
            'name' : 'TemplateContent', #{}, translated in-app
            'slug' : 'template-content',
            'list' : [],
            'lookup' : {},
            'slugs' : {},
        }

        return generic_content_json


    def build_localized_template_content(self, localized_template_content):

        serializer = LocalizedTemplateContentSerializer(localized_template_content, context={'preview': False})
        content_json = serializer.data

        for content_key, content_definition in content_json['contents'].items():

            image_type = '{0}{1}'.format(PUBLISHED_IMAGE_TYPE_PREFIX, content_key)

            if content_definition['type'] == 'image':
                image_urls = self._get_image_urls(localized_template_content, image_type=image_type)
                content_json['contents'][content_key]['value']['imageUrl'] = image_urls


            elif content_definition['type'] == 'multi-image':
                # do not mix up licences
                value = []
                content_images = localized_template_content.images(image_type=image_type)
                for content_image in content_images:
                    image_urls = self.app_release_builder.build_content_image(content_image)
                    licence = content_image.image_store.licences.first()
                    licence_serializer = ContentLicenceSerializer(licence)

                    image_json = {
                        'imageUrl' : image_urls,
                        'licence' : licence_serializer.data,
                    }

                    value.append(image_json)
                
                content_json['contents'][content_key]['value'] = value

        return content_json