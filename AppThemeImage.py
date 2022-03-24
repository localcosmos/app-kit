from django.templatetags.static import static
import os, json

'''
    AppThemeImage
    - file is stored on disk in the preview folder
    - makes AppThemeImage.url available
    - offers save and delete methods
'''
class AppThemeImage:

    # eg make self.url available
    def __init__(self, meta_app, image_type, image_file=None, licence={}, app_version=None):        
        self.meta_app = meta_app
        self.app_version = app_version
        if self.app_version == None:
            self.app_version = self.meta_app.current_version
            
        self.image_type = image_type
        self.licence = licence

        # set an image_file
        self.image_file = image_file

        theme = meta_app.get_theme()
        self.image_definition = theme.user_content['images'][image_type]

        filename, existing_image_diskpath = self._get_existing_image_diskpath()
        
        if existing_image_diskpath:
            self.url = os.path.join('https://', meta_app.app.get_preview_url(), 'user_content/themes',
                                    meta_app.theme, 'images', filename)             
        else:
            self.url = ''
        
    # the extension might vary of the existing_image_diskpath
    def _get_existing_image_diskpath(self):

        appbuilder = self.meta_app.get_preview_builder()
            
        images_folder = appbuilder._app_theme_user_content_images_folder(self.meta_app, self.app_version)

        filetypes = self.image_definition['restrictions'].get('file_type', [])

        for filename in os.listdir(images_folder):

            image_path = os.path.join(images_folder, filename)

            name, ext = filename.split('.')
            
            if name == self.image_type:

                if filetypes:
                    if ext in filetypes:
                        return filename, image_path
                    else:
                        continue
                else:
                    return filename, image_path
                

        return None, None

    def exists(self):
        filename, existing_image_diskpath = self._get_existing_image_diskpath()

        if existing_image_diskpath:
            return True
        return False

    def read(self):
        return self.image_file.read()

    def set_image(self, image_file, licence={}):
        self.image_file = image_file
        self.licence = licence

    def _licence_registry_path(self):
        appbuilder = self.meta_app.get_preview_builder()
 
        licence_registry_path = appbuilder._app_licence_registry_filepath(self.meta_app,
                                                                          app_version=self.app_version)
        return licence_registry_path

    def get_licence(self):
        filename, existing_image_diskpath = self._get_existing_image_diskpath()

        if filename:
            licence_registry_path = self._licence_registry_path()
            with open(licence_registry_path, 'r') as licence_file:
                licences = json.load(licence_file)

            if filename in licences['licences']:
                return licences['licences'][filename]

        return {}

    def set_licence(self, licence):
        self.licence = licence

    def delete(self):
        filename, existing_image_diskpath = self._get_existing_image_diskpath()
        if existing_image_diskpath and os.path.isfile(existing_image_diskpath):
            os.remove(existing_image_diskpath)

    # if no image_file is specified, check if an image exists and update the licence if so
    def save(self):

        filename, existing_image_diskpath = self._get_existing_image_diskpath()

        if not self.image_file and not existing_image_diskpath:
            raise ValueError('You did not specify AppThemeImage.image_file')
            
        # update the image file
        if self.image_file:
            self.delete()

            appbuilder = self.meta_app.get_preview_builder()
            
            images_folder = appbuilder._app_theme_user_content_images_folder(self.meta_app, self.app_version)

            uploaded_filename = self.image_file.name
            ext = uploaded_filename.split('.')[-1]

            image_filename = '{0}.{1}'.format(self.image_type, ext.lower())

            disk_path = os.path.join(images_folder, image_filename)
            
            with open(disk_path, 'wb+') as destination:
                for chunk in self.image_file.chunks():
                    destination.write(chunk)

        self.save_licence()

    def save_licence(self):
        # save the licence
        if self.licence:

            image_filename, existing_image_diskpath = self._get_existing_image_diskpath()
            
            licence_registry_path = self._licence_registry_path()

            with open(licence_registry_path, 'r') as licence_file:
                licences = json.load(licence_file)
                licences['licences'][image_filename] = self.licence

            with open(licence_registry_path, 'w') as licence_file:
                json.dump(licences, licence_file, indent=4)


    def __eq__(self, other):

        if other.__class__ == AppThemeImage:
            filename, existing_image_diskpath = self._get_existing_image_diskpath()
            other_filename, other_existing_image_diskpath = other._get_existing_image_diskpath()

            if filename == other_filename and existing_image_diskpath == other_existing_image_diskpath:
                return True

        return False
            
        
