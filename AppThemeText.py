from django.templatetags.static import static
import os, json

'''
    AppThemeText
    - file is stored on disk in the previews locales folder
    - offers save and delete methods
    - always uses app.primary_language
'''
class AppThemeText:

    # eg make self.url available
    def __init__(self, meta_app, text_type, text=None, app_version=None):        
        self.meta_app = meta_app
        self.app_version = app_version
        if self.app_version == None:
            self.app_version = self.meta_app.current_version
            
        self.text_type = text_type
        
        # set an image_file
        self.text = text

        theme = meta_app.get_theme()
        self.text_definition = theme.user_content['texts'][text_type]

        self.existing_text = self._get_existing_text()


    def _get_primary_locale(self):
        appbuilder = self.meta_app.get_preview_builder()
        return appbuilder.get_primary_locale(self.meta_app, self.app_version)
        
    # the extension might vary of the existing_image_diskpath
    def _get_existing_text(self):
            
        locale = self._get_primary_locale()

        if locale:

            if self.text_type in locale:
                text = locale[self.text_type]

                if text and len(text) > 0:
                    return text

        return None

    def exists(self):
        return self._get_existing_text() != None


    def delete(self):

        locale = self._get_primary_locale()

        if locale:

            if self.text_type in locale:
                del locale[self.text_type]
                
                with open(locale_path, 'w') as locale_file:
                    json.dump(locale, locale_file, indent=4)
        

    # if no text is specified, remove the text from the langfile
    # we cannot use AppPreviewBuilder.update_translation because this does not delete entries
    def save(self):

        locale = self._get_primary_locale()

        if not locale:
            # i18next format!
            locale = {}

        if self.text:
            locale[self.text_type] = self.text
        else:
            if self.text_type in locale:
                del locale[self.text_type]

        # save
        appbuilder = self.meta_app.get_preview_builder()
        locale_path = appbuilder._app_get_locale_filepath(self.meta_app, self.meta_app.primary_language,
                                                          self.app_version)
        
        with open(locale_path, 'w') as locale_file:
            json.dump(locale, locale_file, indent=4)

