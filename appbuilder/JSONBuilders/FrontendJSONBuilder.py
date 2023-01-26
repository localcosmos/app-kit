from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder

from app_kit.features.frontend.models import FrontendText

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
            frontend_json['userContent']['configuration'] = frontend.configuration

        frontend_settings = self.app_release_builder._get_frontend_settings()

        for text_type, text_definition in frontend_settings['userContent']['texts'].items():
            
            frontend_text = FrontendText.objects.filter(frontend=frontend, identifier=text_type).first()

            text = None

            if frontend_text:
                text = frontend_text.text

            text_key_json = text_type
            if text_type == 'legal_notice':
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
                                            relative_path, image_sizes='all')
            else:
                image_urls = None
            
            frontend_json['userContent']['images'][image_type] = {
                'imageUrl' : image_urls,
            }

        return frontend_json

    
