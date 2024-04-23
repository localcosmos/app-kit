from django.conf import settings
from django_tenants.test.cases import TenantTestCase
from django.contrib.contenttypes.models import ContentType

from app_kit.appbuilder import AppReleaseBuilder
from app_kit.appbuilder.ContentImageBuilder import ContentImageBuilder, IMAGE_SIZES

from app_kit.tests.common import (test_settings, TESTS_ROOT, LARGE_SQUARE_TEST_IMAGE_PATH, TEST_SVG_IMAGE_PATH,
                                    TEST_IMAGE_PATH)
from app_kit.models import ContentImage
from app_kit.tests.mixins import WithMetaApp, WithMedia, WithUser, WithImageStore

from PIL import Image

import os, hashlib

class TestContentImageBuilder(WithMetaApp, WithUser, WithMedia, WithImageStore, TenantTestCase):

    def setUp(self):
        super().setUp()

        self.image_store = self.create_image_store()

        self.content_type = ContentType.objects.get_for_model(self.meta_app)

    def create_content_image(self, test_image_path=LARGE_SQUARE_TEST_IMAGE_PATH):

        image_store = self.create_image_store(test_image_path=test_image_path)

        self.assertTrue(os.path.isfile(image_store.source_image.path))

        content_image = ContentImage(
            image_store = image_store,
            content_type = self.content_type,
            object_id = self.meta_app.id,
        )

        content_image.save()

        return content_image


    def get_cache_path(self):
        self.release_builder = AppReleaseBuilder(self.meta_app)
        cache_path = self.release_builder._app_content_images_cache_path
        self.assertTrue(cache_path.startswith(TESTS_ROOT))

        return cache_path

    def get_content_image_builder(self):
        content_image_builder = ContentImageBuilder(self.get_cache_path())
        return content_image_builder


    @test_settings
    def test__init__(self):
        cache_path = self.get_cache_path()
        
        content_image_builder = ContentImageBuilder(cache_path)
        self.assertEqual(content_image_builder.image_cache, {})
        self.assertEqual(content_image_builder.cache_folder, cache_path)


    @test_settings
    def test_get_file_extension(self):

        filepaths = ['/path/to/file.svg', '/path/to/file.sVG']

        content_image_builder = self.get_content_image_builder()

        for filepath in filepaths:

            ext = content_image_builder.get_file_extension(filepath)
            self.assertEqual(ext, '.svg')


    @test_settings
    def test_get_output_filename(self):
        
        content_image_builder = self.get_content_image_builder()
        content_image = self.create_content_image()

        image_size = 500

        filename = content_image_builder.get_output_filename(content_image, image_size)

        self.assertEqual(filename, 'image-{0}-500.webp'.format(content_image.id))


    @test_settings
    def test_get_on_disk_cached_image_filepath(self):
        
        content_image_builder = self.get_content_image_builder()
        content_image = self.create_content_image()

        image_size = 500
        filepath = content_image_builder.get_on_disk_cached_image_filepath(content_image, image_size)

        self.assertTrue(filepath.startswith(content_image_builder.cache_folder))
        self.assertTrue(filepath.startswith(TESTS_ROOT))
        self.assertTrue(filepath.startswith(settings.APP_KIT_ROOT))

    
    @test_settings
    def test_build_cached_images(self):

        content_image_builder = self.get_content_image_builder()
        content_image = self.create_content_image()

        content_image_builder.build_cached_images(content_image)

        for size_name, size in IMAGE_SIZES['regular'].items():

            absolute_cached_image_filepath = content_image_builder.get_on_disk_cached_image_filepath(content_image, size)

            self.assertTrue(os.path.isfile(absolute_cached_image_filepath))

            image = Image.open(absolute_cached_image_filepath)

            width, height = image.size

            self.assertEqual(width, size)
            self.assertEqual(height, size)


    @test_settings
    def test_build_cached_images_force_build(self):

        content_image_builder = self.get_content_image_builder()
        content_image = self.create_content_image()

        content_image_builder.build_cached_images(content_image)

        md5s = {}

        for size_name, size in IMAGE_SIZES['regular'].items():

            absolute_cached_image_filepath = content_image_builder.get_on_disk_cached_image_filepath(content_image, size)

            self.assertTrue(os.path.isfile(absolute_cached_image_filepath))

            image = Image.open(absolute_cached_image_filepath)

            width, height = image.size

            self.assertEqual(width, size)
            self.assertEqual(height, size)

            md5s[size_name] = hashlib.md5(open(absolute_cached_image_filepath,'rb').read()).hexdigest()

        # change the content imag esource
        new_image_store = self.create_image_store(test_image_path=TEST_IMAGE_PATH)

        self.assertTrue(os.path.isfile(new_image_store.source_image.path))

        content_image.image_store = new_image_store
        content_image.save()

        content_image_builder.build_cached_images(content_image, force_build=True)

        for size_name, size in IMAGE_SIZES['regular'].items():

            absolute_cached_image_filepath = content_image_builder.get_on_disk_cached_image_filepath(content_image, size)

            self.assertTrue(os.path.isfile(absolute_cached_image_filepath))

            old_md5 = md5s[size_name]
            new_md5 = hashlib.md5(open(absolute_cached_image_filepath,'rb').read()).hexdigest()

            self.assertFalse(old_md5 == new_md5)

        

    @test_settings
    def test_get_on_disk_cached_image(self):
        
        content_image_builder = self.get_content_image_builder()
        content_image = self.create_content_image()

        for size_name, size in IMAGE_SIZES['regular'].items():

            image_filepath = content_image_builder.get_on_disk_cached_image(content_image, size)
            self.assertIsNone(image_filepath)


        content_image_builder.build_cached_images(content_image)

        for size_name, size in IMAGE_SIZES['regular'].items():

            image_filepath = content_image_builder.get_on_disk_cached_image(content_image, size)

            self.assertTrue(os.path.isfile(image_filepath))

 
    @test_settings
    def test_save_to_on_disk_cache(self):
        
        content_image_builder = self.get_content_image_builder()
        content_image = self.create_content_image()

        size = 500

        source_image_path = content_image.image_store.source_image.path

        absolute_path = self.release_builder._app_absolute_content_images_path
        os.makedirs(absolute_path)
        output_filename = content_image_builder.get_output_filename(content_image, size)

        absolute_image_filepath = os.path.join(absolute_path, output_filename)

        original_image = Image.open(source_image_path)
        processed_image = content_image.get_in_memory_processed_image(original_image, size)
           
        output_format = 'WEBP'
        processed_image.save(absolute_image_filepath, output_format)

        on_disk_cached_image_filepath = content_image_builder.get_on_disk_cached_image_filepath(content_image, size)

        self.assertTrue(os.path.isfile(absolute_image_filepath))
        self.assertFalse(os.path.isfile(on_disk_cached_image_filepath))

        content_image_builder.save_to_on_disk_cache(content_image, size, absolute_image_filepath)

        self.assertTrue(os.path.isfile(absolute_image_filepath))
        self.assertTrue(os.path.isfile(on_disk_cached_image_filepath))


    @test_settings
    def test_build_content_image(self):
        
        content_image_builder = self.get_content_image_builder()
        content_image = self.create_content_image()


        absolute_path = self.release_builder._app_content_images_path
        relative_path = self.release_builder._app_relative_content_images_path

        for size_name, size in IMAGE_SIZES['regular'].items():
            on_disk_cached_image_filepath = content_image_builder.get_on_disk_cached_image_filepath(content_image, size)
            self.assertFalse(os.path.isfile(on_disk_cached_image_filepath))

        image_urls = content_image_builder.build_content_image(content_image, absolute_path, relative_path)

        for size_name, size in IMAGE_SIZES['regular'].items():

            output_filename = content_image_builder.get_output_filename(content_image, size)
            absolute_image_filepath = os.path.join(absolute_path, output_filename)

            self.assertIn(size_name, image_urls)

            image_url = image_urls[size_name]
            self.assertTrue(image_url.startswith('/'))
            self.assertTrue(os.path.isfile(absolute_image_filepath))

            on_disk_cached_image_filepath = content_image_builder.get_on_disk_cached_image_filepath(content_image, size)
            self.assertTrue(os.path.isfile(on_disk_cached_image_filepath))

        image_urls = content_image_builder.build_content_image(content_image, absolute_path, relative_path)


    @test_settings
    def test_build_content_image_svg(self):
        
        content_image_builder = self.get_content_image_builder()
        content_image = self.create_content_image(test_image_path=TEST_SVG_IMAGE_PATH)

        absolute_path = self.release_builder._app_content_images_path
        relative_path = self.release_builder._app_relative_content_images_path

        for size_name, size in IMAGE_SIZES['regular'].items():
            on_disk_cached_image_filepath = content_image_builder.get_on_disk_cached_image_filepath(content_image, size)
            self.assertFalse(os.path.isfile(on_disk_cached_image_filepath))

        image_urls = content_image_builder.build_content_image(content_image, absolute_path, relative_path)

        for size_name, size in IMAGE_SIZES['regular'].items():

            output_filename = content_image_builder.get_output_filename(content_image, size)
            absolute_image_filepath = os.path.join(absolute_path, output_filename)

            self.assertIn(size_name, image_urls)

            image_url = image_urls[size_name]
            self.assertTrue(image_url.startswith('/'))
            self.assertTrue(image_url.endswith('.svg'))
            self.assertTrue(os.path.isfile(absolute_image_filepath))

            on_disk_cached_image_filepath = content_image_builder.get_on_disk_cached_image_filepath(content_image, size)
            
            # svgs are not cached
            self.assertFalse(os.path.isfile(on_disk_cached_image_filepath))

        image_urls = content_image_builder.build_content_image(content_image, absolute_path, relative_path)


    @test_settings
    def test_clean_on_disk_cache(self):
        content_image_builder = self.get_content_image_builder()

        content_image = self.create_content_image()
        content_image_2 = self.create_content_image(test_image_path=TEST_IMAGE_PATH)

        absolute_path = self.release_builder._app_content_images_path
        relative_path = self.release_builder._app_relative_content_images_path

        image_urls = content_image_builder.build_content_image(content_image, absolute_path, relative_path)
        image_2_urls = content_image_builder.build_content_image(content_image_2, absolute_path, relative_path)

        self.assertEqual(len(content_image_builder.image_cache), 6)

        for size_name, size in IMAGE_SIZES['regular'].items():
            on_disk_cached_image_filepath = content_image_builder.get_on_disk_cached_image_filepath(content_image, size)
            self.assertTrue(os.path.isfile(on_disk_cached_image_filepath))

            on_disk_cached_image_2_filepath = content_image_builder.get_on_disk_cached_image_filepath(content_image_2, size)
            self.assertTrue(os.path.isfile(on_disk_cached_image_2_filepath))


        for size_name, size in IMAGE_SIZES['regular'].items():

            cache_key = '{0}-{1}'.format(content_image_2.id, size)
            del content_image_builder.image_cache[cache_key]

        
        self.assertEqual(len(content_image_builder.image_cache), 3)
        content_image_builder.clean_on_disk_cache()


        for size_name, size in IMAGE_SIZES['regular'].items():
            on_disk_cached_image_filepath = content_image_builder.get_on_disk_cached_image_filepath(content_image, size)
            self.assertTrue(os.path.isfile(on_disk_cached_image_filepath))

            on_disk_cached_image_2_filepath = content_image_builder.get_on_disk_cached_image_filepath(content_image_2, size)
            self.assertFalse(os.path.isfile(on_disk_cached_image_2_filepath))


    @test_settings
    def test_empty_on_disk_cache(self):

        content_image_builder = self.get_content_image_builder()

        content_image = self.create_content_image()
        content_image_2 = self.create_content_image(test_image_path=TEST_IMAGE_PATH)

        absolute_path = self.release_builder._app_content_images_path
        relative_path = self.release_builder._app_relative_content_images_path

        image_urls = content_image_builder.build_content_image(content_image, absolute_path, relative_path)
        image_2_urls = content_image_builder.build_content_image(content_image_2, absolute_path, relative_path)

        self.assertEqual(len(content_image_builder.image_cache), 6)
        
        filecount = 0

        for filename in os.listdir(content_image_builder.cache_folder):
            filecount += 1

        self.assertEqual(filecount, 6)

        empty_filecount = 0
        content_image_builder.empty_on_disk_cache()

        for filename in os.listdir(content_image_builder.cache_folder):
            empty_filecount += 1

        self.assertEqual(empty_filecount, 0)
