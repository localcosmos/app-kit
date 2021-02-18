from app_kit.appbuilders.JSONBuilders.JSONBuilder import JSONBuilder

from app_kit.features.fact_sheets.models import (FactSheets, FactSheet, FactSheetImages)

from app_kit.generic import MAX_IMAGE_DIMENSIONS

from django.template import Context

import base64, json, os

from PIL import Image

'''
    build one file for each language
'''    

class FactSheetsJSONBuilder(JSONBuilder):

    def build(self):

        fact_sheets_json = self._build_common_json()

        fact_sheets_json['fact_sheets'] = {}

        return fact_sheets_json

    # add the correct localized context to the fact_sheet
    # render html
    # return html
    def render_localized_fact_sheet(self, fact_sheet, language_code, plain_locale, glossarized_locale):

        locale = plain_locale

        if glossarized_locale:
            locale = glossarized_locale

        localized_and_glossarized_contents = {}

        for content_id, html in fact_sheet.contents.items():

            locale_key = fact_sheet.get_locale_key(content_id)
            html = locale[locale_key]
            localized_and_glossarized_contents[content_id] = html

        fact_sheet.contents = localized_and_glossarized_contents

        template = fact_sheet.get_template(self.meta_app)

        context = {
            'fact_sheet' : fact_sheet,
            'build' : True,
            'language_code' : language_code,
        }

        c = Context(context)
        rendered = template.render(c)

        # store all fact sheet images of this fact sheet
        # if the images need localization, the images already exist since the translation
        fact_sheet_images = FactSheetImages.objects.filter(fact_sheet=fact_sheet, requires_translation=False)
        for fact_sheet_image in fact_sheet_images:
            self.build_fact_sheet_image(fact_sheet_image, language_code)
        
        return rendered

    # only for untranslated images
    def build_fact_sheet_image(self, fact_sheet_image, language_code):

        # set attributes for building
        fact_sheet_image.build = True
        fact_sheet_image.language_code = language_code

        image_file = fact_sheet_image.image

        relative_filepath = fact_sheet_image.url
        absolute_root = self.app_release_builder._app_www_folder(self.meta_app,
                                                        app_version=self.app_release_builder.app_version)

        absolute_folder = os.path.join(absolute_root, os.path.dirname(relative_filepath))
        absolute_filepath = os.path.join(absolute_root, relative_filepath)
        
        if not os.path.isdir(absolute_folder):
            os.makedirs(absolute_folder)

        if os.path.isfile(absolute_filepath):
            os.remove(absolute_filepath)

        built_image = Image.open(image_file.path)
        built_image.thumbnail(MAX_IMAGE_DIMENSIONS, Image.BICUBIC)

        built_image.save(absolute_filepath, built_image.format)
