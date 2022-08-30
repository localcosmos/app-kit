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
        }

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

                
                filename = '{0}{1}'.format(image_type, ext)
                relative_content_image_url = self.app_release_builder._save_content_image(content_image, absolute_path,
                                            relative_path, filename, size=2000)
            else:
                relative_content_image_url = None
            
            frontend_json['userContent']['images'][image_type] = relative_content_image_url

        return frontend_json

    
