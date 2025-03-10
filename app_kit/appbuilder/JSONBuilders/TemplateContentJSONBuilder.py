from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder

from localcosmos_server.template_content.utils import get_published_image_type, get_component_image_type
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
            'slug' : 'pages',
            'list' : [],
            'lookup' : {},
            'slugs' : {},
            'assignments': {}
        }

        return generic_content_json


    def get_image_data(self, content_definition, localized_template_content, image_type):

        image_type = get_published_image_type(image_type)

        if content_definition.get('allowMultiple', False) == True:
            # do not mix up licences
            images = []
            content_images = localized_template_content.images(image_type=image_type)
            for content_image in content_images:
                image_urls = self.app_release_builder.build_content_image(content_image)
                licence = content_image.image_store.licences.first()
                licence_serializer = ContentLicenceSerializer(licence)

                image_json = {
                    'imageUrl' : image_urls,
                    'licence' : licence_serializer.data,
                }

                images.append(image_json)
            
            return images

        else: 
            image_urls = self._get_image_urls(localized_template_content, image_type=image_type,
                image_sizes=['all'])

            licence = {}

            if image_urls:
                content_image = localized_template_content.image(image_type=image_type)
                licence = content_image.image_store.licences.first()
                licence_serializer = ContentLicenceSerializer(licence)
                licence = licence_serializer.data

            image = {
                'imageUrl' : image_urls,
                'licence' : licence,
            }
            
            return image

    # create built urls instead of /media/... urls. this differs from localcosmos_server serializer
    def add_image_data_to_component(self, component_key, component, component_definition, localized_template_content):

        if component:
            component_uuid = component['uuid']

            for component_content_key, component_content_definition in component_definition['contents'].items():

                if component_content_definition['type'] == 'image':

                    image_type = get_component_image_type(component_key, component_uuid, component_content_key)

                    image_data = self.get_image_data(component_definition, localized_template_content, image_type)

                    component[component_content_key] = image_data
        
        return component

    def build_localized_template_content(self, localized_template_content):

        serializer = LocalizedTemplateContentSerializer(localized_template_content, context={'preview': False})
        content_json = serializer.data

        published_template = localized_template_content.template_content.template

        for content_key, content_definition in published_template.definition['contents'].items():

            if content_key in content_json['contents']:

                if content_definition['type'] == 'image':
        
                    image_type = content_key

                    image_data = self.get_image_data(content_definition, localized_template_content, image_type)

                    if content_definition.get('allowMultiple', False) == True:
                        content_json['contents'][content_key] = image_data
                    else:
                        if content_key not in content_json['contents'] or content_json['contents'][content_key] == None:
                            content_json['contents'][content_key] = {}
                        content_json['contents'][content_key].update(image_data)
                            

                elif content_definition['type'] == 'component':
                    
                    component_template = localized_template_content.template_content.get_component_template(content_key)
                    component_definition = component_template.definition

                    if content_definition.get('allowMultiple', False) == True:

                        components = content_json['contents'][content_key]

                        for component_index, component in enumerate(components, 0):
                            
                            # do not use add_image_data_to_component which uses djangos /media/... urls instead of built urls
                            component_with_image_data = self.add_image_data_to_component(content_key, component,
                                component_definition, localized_template_content)

                            content_json['contents'][content_key][component_index] = component_with_image_data

                    else:
                        
                        component = content_json['contents'][content_key]

                        component_with_image_data = self.add_image_data_to_component(content_key, component,
                            component_definition, localized_template_content)

                        content_json['contents'][content_key] = component_with_image_data

        return content_json