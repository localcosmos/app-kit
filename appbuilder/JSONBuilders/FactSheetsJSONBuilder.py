from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder

from django.template import Context

IMAGE_SIZE = (600,600)

'''
    build one file for each language
'''    

class FactSheetsJSONBuilder(JSONBuilder):

    def build(self):

        fact_sheets_json = self._build_common_json()

        fact_sheets_json['factSheets'] = {}

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
            'languageCode' : language_code,
        }

        c = Context(context)
        rendered = template.render(c)

        # store all fact sheet images of this fact sheet
        # if the images need localization, the images already exist since the translation
        fact_sheet_images = fact_sheet.all_images()
        for content_image in fact_sheet_images:
             self.app_release_builder.save_content_image(content_image)
        
        return rendered
