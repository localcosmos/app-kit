import os, shutil

from PIL import Image

from localcosmos_server.template_content.api.serializers import ContentLicenceSerializer


# widths of the ouput image
# the height depends on the crop area set by the user
from localcosmos_server.models import IMAGE_SIZES

class ContentImageBuilder:

    def __init__(self, cache_folder):
        self.cache_folder = cache_folder
        self.image_cache = {}


    def get_file_extension(self, filepath):

        basename, ext = os.path.splitext(filepath)
        ext = ext.lower()
        return ext

    def get_output_filename(self, content_image, size):

        source_image_path = content_image.image_store.source_image.path
        ext = self.get_file_extension(source_image_path)

        # no image processing for svgs
        if ext == '.svg':
            output_filename = '{0}-{1}.svg'.format( content_image.image_type, content_image.id)

        else:
            file_extension = 'webp'

            suffix = ''
            if content_image.__class__.__name__ == 'ServerContentImage':
                suffix = '-s'


            output_filename = '{0}-{1}{2}-{3}.{4}'.format(content_image.image_type, content_image.id, suffix, size,
                                file_extension)

        return output_filename


    def get_on_disk_cached_image_filepath(self, content_image, size):
        output_filename = self.get_output_filename(content_image, size)
        image_filepath = os.path.join(self.cache_folder, output_filename)

        return image_filepath


    def build_cached_images(self, content_image, image_sizes=['regular', 'large'], force_build=False):

        if not os.path.isdir(self.cache_folder):
            os.makedirs(self.cache_folder)
        
        source_image_path = content_image.image_store.source_image.path

        ext = self.get_file_extension(source_image_path)

        if ext != '.svg':

            for image_sizes_key in image_sizes:
                for size_name, size in IMAGE_SIZES[image_sizes_key].items():

                    # cached image filepath
                    absolute_image_filepath = self.get_on_disk_cached_image_filepath(content_image, size)
                    if not os.path.isfile(absolute_image_filepath) or force_build == True:

                        original_image = Image.open(source_image_path)
                        processed_image = content_image.get_in_memory_processed_image(original_image, size)

                        output_format = 'WEBP'
                        processed_image.save(absolute_image_filepath, output_format, quality=70)


    def get_on_disk_cached_image(self, content_image, size):
        image_filepath = self.get_on_disk_cached_image_filepath(content_image, size)

        if os.path.isfile(image_filepath):
            return image_filepath

        return None

    # absolute_image_filepath has to be a built content image
    def save_to_on_disk_cache(self, content_image, size, absolute_image_filepath):

        if not os.path.isdir(self.cache_folder):
            os.makedirs(self.cache_folder)

        on_disk_cached_image_filepath = self.get_on_disk_cached_image_filepath(content_image, size)
        shutil.copyfile(absolute_image_filepath, on_disk_cached_image_filepath)
        

    def build_content_image(self, content_image, absolute_path, relative_path, image_sizes=['regular', 'large']):

        image_urls = {}
        
        for image_sizes_key in image_sizes:
            for size_name, size in IMAGE_SIZES[image_sizes_key].items():

                if content_image.__class__.__name__ == 'ServerContentImage':
                    cache_key = '{0}-s-{1}'.format(content_image.id, size)
                else:
                    cache_key = '{0}-{1}'.format(content_image.id, size)


                output_filename = self.get_output_filename(content_image, size)

                relative_image_filepath = os.path.join(relative_path, output_filename)
                absolute_image_filepath = os.path.join(absolute_path, output_filename)

                image_url = '/{0}'.format(relative_image_filepath)


                if cache_key in self.image_cache:
                    image_urls[size_name] = self.image_cache[cache_key]

                else:
                    # create the on disk imagefile for the app

                    if not os.path.isdir(absolute_path):
                        os.makedirs(absolute_path)

                    # check if the imag exists in the on_disk_cache
                    cached_image = self.get_on_disk_cached_image(content_image, size)
                    if cached_image:
                        # simply copy the file
                        shutil.copyfile(cached_image, absolute_image_filepath)

                    else:
                        # create a new file
                        source_image_path = content_image.image_store.source_image.path

                        ext = self.get_file_extension(source_image_path)

                        # no image processing for svgs
                        if ext == '.svg':
                            shutil.copyfile(source_image_path, absolute_image_filepath)

                        else:

                            if not os.path.isfile(absolute_image_filepath):
                        
                                original_image = Image.open(source_image_path)
                                processed_image = content_image.get_in_memory_processed_image(original_image, size)

                                # all processed images are webp
                                #original_format = original_image.format
                                #output_format = original_format
                                #allowed_formats = ['png', 'jpg', 'jpeg']
                                
                                output_format = 'WEBP'
                                processed_image.save(absolute_image_filepath, output_format)

                            self.save_to_on_disk_cache(content_image, size, absolute_image_filepath)
                        
                        
                    image_urls[size_name] = image_url

                    self.image_cache[cache_key] = image_url
        
        return image_urls


    def build_licence(self, content_image):

        licence_json = {}
        licence = content_image.image_store.licences.first()

        if licence:
            licence_serializer = ContentLicenceSerializer(licence)
            licence_json = licence_serializer.data

        return licence_json

    
    def clean_on_disk_cache(self):

         if self.image_cache:

            cached_image_filenames = []

            for size_name, image_url in self.image_cache.items():

                image_filename = os.path.basename(image_url)
                cached_image_filenames.append(image_filename)

            
            for filename in os.listdir(self.cache_folder):
                if filename not in cached_image_filenames:

                    filepath = os.path.join(self.cache_folder, filename)

                    if os.path.isfile(filepath):
                        os.remove(filepath)


    def empty_on_disk_cache(self):
        for filename in os.listdir(self.cache_folder):

            filepath = os.path.join(self.cache_folder, filename)
            os.remove(filepath)