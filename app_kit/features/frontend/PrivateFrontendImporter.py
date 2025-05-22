from django.conf import settings
from django.db import connection

from django.utils.translation import gettext_lazy as _

from localcosmos_cordova_builder.required_assets import REQUIRED_ASSETS

import os, shutil, zipfile, json


class PrivateFrontendImporter:

    def __init__(self, meta_app):

        self.preview_builder = meta_app.get_preview_builder()
        self.is_valid = False
        self.temporary_frontend_folder = None
        self.errors = []

    @property
    def zip_destination_dir(self):
        return os.path.join(settings.APP_KIT_TEMPORARY_FOLDER, connection.schema_name, 'frontend')

    @property
    def unzip_path(self):
        return os.path.join(self.zip_destination_dir, 'contents')
    
    def validate(self):
        self.errors = []

        self.validate_temporary_frontend_folder()

        if not self.errors:
            settings = self.get_frontend_settings()

            if settings:
                self.validate_settings_json(settings)

        if not self.errors:
            self.validate_frontend_files()

        self.is_valid = len(self.errors) == 0

        if not self.is_valid:

            if os.path.isdir(self.zip_destination_dir):
                shutil.rmtree(self.zip_destination_dir)

        return self.is_valid


    def validate_temporary_frontend_folder(self):

        if not self.errors:

            counter = 0

            frontend_folder = None

            for subitem in os.listdir(self.unzip_path):

                counter += 1

                if counter > 1:
                    frontend_folder = None
                    self.errors.append(_('Found more than one subitem in the Frontend zip file. The Frontend zip file may only contain one folder'))
                    break

                subitem_path = os.path.join(self.unzip_path, subitem)
                if os.path.isdir(subitem_path):
                    frontend_folder = subitem_path
                    
            if not frontend_folder:
                self.errors.append(_('The Frontend zip file does not contain a folder. The Frontend zip file has to contain one folder'))

            self.temporary_frontend_folder  = frontend_folder

    
    def get_frontend_settings(self):

        settings = {}

        if not self.errors and self.temporary_frontend_folder:
            settings_path = os.path.join(self.temporary_frontend_folder, 'settings.json')
            if os.path.isfile(settings_path):
                with open(settings_path, 'rb') as settings_file:
                    try:
                        settings = json.loads(settings_file.read())
                    except Exception as e:
                        self.errors.append(_('Invalid json in settings.json file.'))

        if not settings and not self.errors:
            self.errors.append(_('The uploaded Frontend is missing the settings.json file.'))
        return settings


    def unzip_to_temporary_folder(self, zip_file):

        zip_filename = 'Frontend.zip'
        
        if os.path.isdir(self.zip_destination_dir):
            shutil.rmtree(self.zip_destination_dir)

        os.makedirs(self.zip_destination_dir)

        zip_destination_path = os.path.join(self.zip_destination_dir, zip_filename)
        
        with open(zip_destination_path, 'wb+') as zip_destination:
            for chunk in zip_file.chunks():
                zip_destination.write(chunk)

        # unzip zipfile
        if os.path.isdir(self.unzip_path):
            shutil.rmtree(self.unzip_path)

        os.makedirs(self.unzip_path)
        
        with zipfile.ZipFile(zip_destination_path, 'r') as zip_file:
            zip_file.extractall(self.unzip_path)


    def validate_settings_json(self, frontend_settings):
        frontend_folder_name = os.path.basename(self.temporary_frontend_folder)
        frontend_name = frontend_settings.get('frontend', None)

        if not frontend_folder_name == frontend_name:
            self.errors.append(_('The folder inside your zip-file does not match the frontend name in settings.json'))

        if 'version' not in frontend_settings:
            self.errors.append(_("'version' not found in settings.json"))

        if 'userContent' not in frontend_settings:
            self.errors.append(_("'version' not found in settings.json"))

        else:

            if 'images' not in frontend_settings['userContent']:
                self.errors.append(_("'images' not found in settings.userContent"))

            else:

                for image_key, image_filename in REQUIRED_ASSETS.items():

                    if image_key not in frontend_settings['userContent']['images']:
                        self.errors.append(_("'%(image_key)s' not found in settings.userContent.images") % {
                            'image_key' : image_key
                        })

                    else:
                        image_definition = frontend_settings['userContent']['images'][image_key]

                        required = image_definition.get('required', False)

                        if required != True:
                            self.errors.append(_('settings.userContent.images.%(image_key)s.required has to be set to true') % {
                                'image_key' : image_key
                            })

                        restrictions = image_definition.get('restrictions', {})

                        file_type = restrictions.get('fileType', [])
                        if file_type != ['svg']:
                            self.errors.append(_('settings.userContent.images.%(image_key)s.restrictions.fileType has to be ["svg"]') % {
                                'image_key' : image_key
                            })

                        ratio = restrictions.get('ratio', None)
                        if ratio != '1:1':
                            self.errors.append(_('settings.userContent.images.%(image_key)s.restrictions.ratio has to be "1:1"') % {
                                'image_key' : image_key
                            })

    def validate_frontend_files(self):

        if not self.errors and self.temporary_frontend_folder:

            required_subitems = {
                'www' : 'folder',
                'settings.json' : 'file',
            }

            for subitem, item_type in required_subitems.items():
                
                subitem_path = os.path.join(self.temporary_frontend_folder, subitem)

                if item_type == 'folder' and not os.path.isdir(subitem_path):
                    self.errors.append(_('%(subitem)s of your frontend is not a folder') % {
                        'subitem' : subitem
                    })

                if item_type == 'file' and not os.path.isfile(subitem_path):
                    self.errors.append(_('%(subitem)s of your frontend is not a file') % {
                        'subitem' : subitem
                    })

        
    def get_frontend_name(self):

        if self.is_valid:
            frontend_settings = self.get_frontend_settings()
            return frontend_settings['frontend']
        
        raise ValueError('Cannot get name if the frontend did not validate')


    def install_frontend(self):
        
        if (self.is_valid == True):
            
            frontend_name = self.get_frontend_name()
            target_path = self.preview_builder.get_private_frontend_path(frontend_name)

            if os.path.isdir(target_path):
                shutil.rmtree(target_path)

            shutil.move(self.temporary_frontend_folder, target_path)

            if os.path.isdir(self.zip_destination_dir):
                shutil.rmtree(self.zip_destination_dir)
            
        else:
            raise ValueError('Could not install Frontend because the Frontend did not validate')


    



    
