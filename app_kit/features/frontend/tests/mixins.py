from app_kit.tests.common import (VALID_TEST_FRONTEND_ZIP_FILEPATH, INVALID_TEST_FRONTEND_ZIP_FILEPATH, APP_KIT_TMP,
                                    TESTS_ROOT)

from django.core.files.uploadedfile import SimpleUploadedFile

import os, shutil

class WithFrontendZip:

    def get_valid_zip_file(self):

        upload_file = open(VALID_TEST_FRONTEND_ZIP_FILEPATH, 'rb')
        zip_file = SimpleUploadedFile('Frontend.zip', upload_file.read())
        return zip_file

    def get_invalid_zip_file(self):

        upload_file = open(INVALID_TEST_FRONTEND_ZIP_FILEPATH, 'rb')
        zip_file = SimpleUploadedFile('Frontend.zip', upload_file.read())
        return zip_file


class CleanFrontendTestFolders:

    def tearDown(self):
        super().tearDown()

        if os.path.isdir(APP_KIT_TMP):

            for subitem in os.listdir(APP_KIT_TMP):
                subitem_path = os.path.join(APP_KIT_TMP, subitem)

                if os.path.isdir(subitem_path):
                    shutil.rmtree(subitem_path)
                
                else:
                    os.remove(subitem_path)

        
        frontend_path = os.path.join(TESTS_ROOT, 'private_frontends', 'test')

        if os.path.isdir(frontend_path):
            shutil.rmtree(frontend_path)