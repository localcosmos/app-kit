from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder

from app_kit.features.frontend.models import FrontendText, REQUIRED_FRONTEND_TEXTS

import os

'''
    Builds JSON for one TaxonProfiles
'''
class FrontendJSONBuilder(JSONBuilder):

    def build(self):

        frontend = self.app_generic_content.generic_content

        frontend_json = self._build_common_json()

        # map built json to Frontend's settings.json
        frontend_json['userContent'] = {
            'texts' : {},
            'images' : {},
            'configuration' : {},
        }

        if frontend.configuration:
            for configuration_key, configuration_value in frontend.configuration.items():
                configuration_key_json = self.to_camel_case(configuration_key)
                frontend_json['userContent']['configuration'][configuration_key_json] = configuration_value

        frontend_settings = self.app_release_builder._get_frontend_settings()

        text_types = list(frontend_settings['userContent']['texts'].keys()) + REQUIRED_FRONTEND_TEXTS

        for text_type in text_types:
            
            frontend_text = FrontendText.objects.filter(frontend=frontend, frontend_name=frontend.frontend_name, identifier=text_type).first()

            text = None

            if frontend_text:
                text = frontend_text.text

            text_key_json = text_type
            if text_type in REQUIRED_FRONTEND_TEXTS:
                text_key_json = self.to_camel_case(text_type)

            frontend_json['userContent']['texts'][text_key_json] = text


        for image_type, image_definition in frontend_settings['userContent']['images'].items():
            
            content_image = frontend.image(image_type)

            if content_image:

                source_image_path = content_image.image_store.source_image.path
                blankname, ext = os.path.splitext(os.path.basename(source_image_path))

                absolute_path = self.app_release_builder._app_absolute_frontend_images_path
                relative_path = self.app_release_builder._app_relative_frontend_images_path

                image_urls = self.app_release_builder.content_image_builder.build_content_image(content_image, absolute_path,
                                            relative_path, image_sizes=['all'])
            else:
                image_urls = None

            if image_urls:
                licence = self.app_release_builder.content_image_builder.build_licence(content_image)
            
            frontend_json['userContent']['images'][image_type] = {
                'imageUrl' : image_urls,
                'licence': licence
            }

        return frontend_json

    
